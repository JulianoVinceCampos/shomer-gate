# Security policy

## Reporting a vulnerability

Open a private security advisory on the hosting platform rather than a public
issue. Include the version, a reproduction, and the impact as you see it.

## What is in scope

- The guardrail engine, the ledger, and the authentication layer.
- The container image and its configuration.

## What is out of scope

The threat model in `docs/security.md` lists what the guardrail is designed to
address and what it is not, including multi-turn injection, RAG-borne injection,
and non-text modalities. A finding outside that scope is useful context but is
not a vulnerability in this component.

## Handling of secrets

The signing key protects both session tokens and ledger seals. It must come
from a secret store in production and never be committed. The example in
`.env.example` is a placeholder and is not a working secret.
