# Spec 002: Tasks

- [x] 1. Define `LedgerRecord` and `IntegrityReport` dataclasses with
      serialisation. _Covers criteria 1, 3._
- [x] 2. Implement canonical JSON bytes and the HMAC seal function.
      _Covers criteria 1, 2._
- [x] 3. Implement `Ledger.append` with sequence numbering and genesis linking,
      thread-safe under a lock. _Covers criteria 1, 2, 8._
- [x] 4. Implement `Ledger.verify` as a single pass reporting the first break.
      _Covers criteria 3, 4, 5._
- [x] 5. Implement JSONL persistence: flush on append, load and verify on
      construction, raise on a bad load. _Covers criteria 6, 7._
- [x] 6. Add `tail` and iteration for the API ledger view.
- [x] 7. Tests: append/verify, tamper, drop, reorder, wrong key, round-trip,
      corrupt-load. _Covers all criteria._
- [x] 8. Wire the ledger into the API `check`, `ledger` and `ledger/verify`
      routes.

Status: implemented. Tests live in `tests/test_ledger.py`.
