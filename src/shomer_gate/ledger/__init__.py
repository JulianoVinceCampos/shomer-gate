"""Tamper-evident decision ledger.

Public surface:

- :class:`~shomer_gate.ledger.chain.Ledger`: append-only, HMAC-chained log.
- :class:`~shomer_gate.ledger.chain.LedgerRecord`: one sealed entry.
- :class:`~shomer_gate.ledger.chain.IntegrityReport`: the verify() result.
"""

from __future__ import annotations

from shomer_gate.ledger.chain import IntegrityReport, Ledger, LedgerRecord

__all__ = ["IntegrityReport", "Ledger", "LedgerRecord"]
