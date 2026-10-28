"""Tests for the tamper-evident ledger."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shomer_gate.ledger.chain import GENESIS_SEAL, Ledger, build_from_payloads

KEY = "test-signing-key-not-a-secret"


def test_empty_ledger_verifies() -> None:
    ledger = Ledger(KEY)
    report = ledger.verify()
    assert report.ok
    assert report.length == 0
    assert ledger.head_seal == GENESIS_SEAL


def test_append_links_to_previous_seal() -> None:
    ledger = Ledger(KEY)
    first = ledger.append({"decision": "allow"})
    second = ledger.append({"decision": "block"})
    assert first.prev_seal == GENESIS_SEAL
    assert second.prev_seal == first.seal
    assert ledger.verify().ok
    assert len(ledger) == 2


def test_tamper_with_payload_breaks_chain() -> None:
    ledger = build_from_payloads(KEY, [{"v": i} for i in range(5)])
    assert ledger.verify().ok
    # Mutate a sealed record in place to simulate an after-the-fact edit.
    ledger._records[2].payload["data"]["v"] = 999  # type: ignore[index]
    report = ledger.verify()
    assert not report.ok
    assert report.first_broken_seq == 2


def test_dropping_a_record_breaks_the_links() -> None:
    ledger = build_from_payloads(KEY, [{"v": i} for i in range(4)])
    del ledger._records[1]
    report = ledger.verify()
    assert not report.ok
    assert report.first_broken_seq is not None


def test_wrong_key_fails_verification() -> None:
    ledger = build_from_payloads(KEY, [{"v": 1}, {"v": 2}])
    stolen = Ledger("a-different-key")
    stolen._records = ledger._records  # attacker copied the file but not the key
    assert not stolen.verify().ok


def test_persistence_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    writer = Ledger(KEY, path=path)
    writer.append({"decision": "allow"})
    writer.append({"decision": "review"})
    assert path.exists()
    # A fresh reader loads and verifies the same chain.
    reader = Ledger(KEY, path=path)
    assert len(reader) == 2
    assert reader.verify().ok
    assert reader.head_seal == writer.head_seal


def test_loading_tampered_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger(KEY, path=path)
    ledger.append({"decision": "allow"})
    # Corrupt the persisted line.
    lines = path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    record["payload"]["data"]["decision"] = "block"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="verification"):
        Ledger(KEY, path=path)


def test_tail_returns_most_recent() -> None:
    ledger = build_from_payloads(KEY, [{"v": i} for i in range(10)])
    tail = ledger.tail(3)
    assert [r.payload["data"]["v"] for r in tail] == [7, 8, 9]
