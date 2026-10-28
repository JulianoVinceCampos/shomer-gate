# Spec 002: Tamper-evident decision ledger

## Problem

After an incident, someone asks a simple question: what did the guardrail
decide, and in what order? A plain log file cannot answer that with confidence,
because a plain log can be edited after the fact and nobody can tell. The ledger
has to make tampering detectable.

## Goals

- Append each guardrail decision as a sealed, ordered entry.
- Detect any edit, deletion, or reordering of past entries.
- Make the seal unforgeable without a secret key, not merely a bare hash.
- Verify the whole chain in one pass and name the first broken entry.
- Offer optional durable storage without changing the verification model.

## Non-goals

- Distributed consensus or replication. This is a single-writer log.
- Confidentiality of the entries. The ledger proves integrity and order, not
  secrecy. Sensitive content is kept out by storing a prompt digest, not the
  prompt (see spec 001).

## Acceptance criteria

1. WHEN a payload is appended, THE ledger SHALL seal it with an HMAC over the
   previous seal and the entry's canonical bytes, and SHALL assign a
   monotonically increasing sequence number.
2. THE first entry SHALL link to a fixed genesis seal.
3. WHEN any past entry's content is altered, THE verify pass SHALL fail and
   SHALL report the sequence number of the first broken entry.
4. WHEN an entry is removed or two entries are reordered, THE verify pass SHALL
   fail.
5. WHEN the chain is verified with a key other than the one used to seal it,
   verification SHALL fail.
6. GIVEN a configured file path, THE ledger SHALL persist each entry on append
   and SHALL load and verify the chain on construction.
7. WHEN a persisted ledger fails verification on load, THE constructor SHALL
   raise rather than silently continue.
8. THE ledger SHALL be safe to append to from multiple threads.
