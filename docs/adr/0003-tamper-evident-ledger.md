# ADR 0003: HMAC-chained ledger, not a plain log

Status: accepted

## Context

After an incident someone needs to know what the guardrail decided and in what
order. A plain log file cannot answer that with confidence: it can be edited
after the fact and no one can tell. A plain hash chain detects accidental
corruption, but an attacker who can rewrite the file can also recompute every
hash.

## Decision

Each entry is sealed with an HMAC-SHA256 over the previous seal plus the entry's
canonical bytes, under a secret key. The key makes the chain unforgeable: an
attacker who can write the file still cannot produce valid seals without it.
Verification recomputes the chain from genesis in one pass and names the first
broken sequence number.

## Consequences

- Any edit, deletion, or reordering of past entries breaks verification from
  that point to the head, and the first break is named rather than averaged into
  a vague "something is wrong".
- The same key seals the ledger and signs the session tokens, so key management
  is one problem, not two. It must come from a secret store in production.
- The ledger proves integrity and order, not secrecy. Sensitive content is kept
  out by storing a prompt digest rather than the prompt.
- Because the key may be ephemeral per process, the API keeps the ledger in
  memory by default. Durable storage pairs a stable key with a file path, and a
  file sealed under an old key correctly fails to load.
