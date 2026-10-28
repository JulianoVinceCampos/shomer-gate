"""An append-only, HMAC-chained ledger of guardrail decisions.

Why a chain and not just a log file: a plain log can be edited after the fact
and nobody is the wiser. Here each entry is sealed with an HMAC over the
previous seal plus the entry's own canonical bytes. Change any past entry, drop
one, or reorder two, and every seal from that point on stops verifying. Because
the seal is an HMAC and not a bare hash, an attacker who can write the file
still cannot forge a valid chain without the signing key.

This is the same shape as the tamper-evident scheme in ledger-forensics, scoped
down to what a guardrail needs: prove, after an incident, exactly what was
decided and in what order.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

GENESIS_SEAL = "0" * 64


def _canonical(payload: dict[str, object]) -> bytes:
    """Deterministic JSON bytes: sorted keys, no insignificant whitespace."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _seal(key: bytes, prev_seal: str, payload: dict[str, object]) -> str:
    mac = hmac.new(key, prev_seal.encode("ascii") + _canonical(payload), hashlib.sha256)
    return mac.hexdigest()


@dataclass(frozen=True, slots=True)
class LedgerRecord:
    """One sealed entry in the chain."""

    seq: int
    timestamp: str
    payload: dict[str, object]
    prev_seal: str
    seal: str

    def to_dict(self) -> dict[str, object]:
        return {
            "seq": self.seq,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "prev_seal": self.prev_seal,
            "seal": self.seal,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> LedgerRecord:
        return cls(
            seq=int(cast("str | int", raw["seq"])),
            timestamp=str(raw["timestamp"]),
            payload=cast("dict[str, object]", raw["payload"]),
            prev_seal=str(raw["prev_seal"]),
            seal=str(raw["seal"]),
        )


@dataclass(frozen=True, slots=True)
class IntegrityReport:
    """Result of verifying the chain end to end."""

    ok: bool
    length: int
    head_seal: str
    first_broken_seq: int | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "length": self.length,
            "head_seal": self.head_seal,
            "first_broken_seq": self.first_broken_seq,
            "reason": self.reason,
        }


class Ledger:
    """Thread-safe, append-only HMAC chain with optional JSONL persistence.

    Args:
        signing_key: Secret used for the HMAC seals. The same key is required to
            append and to verify.
        path: Optional JSONL file. When given, existing records are loaded and
            verified on construction, and new records are flushed on append.
    """

    def __init__(self, signing_key: str | bytes, path: str | Path | None = None) -> None:
        self._key = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
        self._path = Path(path) if path is not None else None
        self._records: list[LedgerRecord] = []
        self._lock = threading.Lock()
        if self._path is not None and self._path.exists():
            self._load()

    # -- writing --------------------------------------------------------------
    def append(self, payload: dict[str, object]) -> LedgerRecord:
        """Seal ``payload`` onto the head of the chain and return the record."""
        with self._lock:
            prev_seal = self._records[-1].seal if self._records else GENESIS_SEAL
            seq = len(self._records)
            timestamp = datetime.now(UTC).isoformat(timespec="milliseconds")
            sealed_payload = {"seq": seq, "timestamp": timestamp, "data": payload}
            seal = _seal(self._key, prev_seal, sealed_payload)
            record = LedgerRecord(
                seq=seq,
                timestamp=timestamp,
                payload=sealed_payload,
                prev_seal=prev_seal,
                seal=seal,
            )
            self._records.append(record)
            if self._path is not None:
                self._flush(record)
            return record

    # -- reading --------------------------------------------------------------
    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterator[LedgerRecord]:
        return iter(tuple(self._records))

    @property
    def head_seal(self) -> str:
        return self._records[-1].seal if self._records else GENESIS_SEAL

    def tail(self, n: int = 50) -> list[LedgerRecord]:
        """Return the most recent ``n`` records, newest last."""
        return list(self._records[-n:])

    # -- verification ---------------------------------------------------------
    def verify(self) -> IntegrityReport:
        """Recompute every seal from genesis and report the first break, if any."""
        prev_seal = GENESIS_SEAL
        for record in self._records:
            if record.prev_seal != prev_seal:
                return IntegrityReport(
                    ok=False,
                    length=len(self._records),
                    head_seal=self.head_seal,
                    first_broken_seq=record.seq,
                    reason="prev_seal link does not match the previous record's seal",
                )
            expected = _seal(self._key, prev_seal, record.payload)
            if not hmac.compare_digest(expected, record.seal):
                return IntegrityReport(
                    ok=False,
                    length=len(self._records),
                    head_seal=self.head_seal,
                    first_broken_seq=record.seq,
                    reason="seal does not verify: record was altered or key is wrong",
                )
            prev_seal = record.seal
        return IntegrityReport(
            ok=True,
            length=len(self._records),
            head_seal=self.head_seal,
            reason="chain intact",
        )

    # -- persistence ----------------------------------------------------------
    def _flush(self, record: LedgerRecord) -> None:
        assert self._path is not None
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.to_dict(), separators=(",", ":")) + "\n")

    def _load(self) -> None:
        assert self._path is not None
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    self._records.append(LedgerRecord.from_dict(json.loads(line)))
        report = self.verify()
        if not report.ok:
            raise ValueError(
                f"loaded ledger failed verification at seq {report.first_broken_seq}: "
                f"{report.reason}"
            )


# Optional module-level helpers for callers that only need a one-shot chain.
def build_from_payloads(
    signing_key: str | bytes, payloads: list[dict[str, object]]
) -> Ledger:
    """Construct an in-memory ledger from a list of payloads (useful in tests)."""
    ledger = Ledger(signing_key)
    for payload in payloads:
        ledger.append(payload)
    return ledger


__all__ = [
    "GENESIS_SEAL",
    "IntegrityReport",
    "Ledger",
    "LedgerRecord",
    "build_from_payloads",
]
