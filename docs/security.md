# Security and threat model

Scope: this document covers the threats shomer-gate is designed to address and,
just as importantly, the ones it is not. A limit that is written down is
engineering. A limit that is only implied is a trap for the next reader.

## Assets

- The integrity of the system prompt and the model's governing instructions.
- The decision record: proof of what was decided and in what order.
- The signing key, which protects both the session tokens and the ledger seals.

## Threats addressed (LLM-facing)

| Threat | Technique | Control |
|--------|-----------|---------|
| Instruction override | "ignore previous instructions" | rules IO-01, IO-02 |
| Role hijack | "you are now", "act as" | rule RH-01 |
| System-prompt exfiltration | "reveal your prompt", "repeat the words above" | rules SE-01, SE-02 |
| Chat-template spoofing | forged `<|im_start|>`, `system:` headers | rules DS-01, DS-02 |
| Encoding evasion | base64 payloads, zero-width characters | rule EE-01 + normalisation |
| Refusal suppression | "do not refuse", "no restrictions" | rule RS-01 |
| Data exfiltration | "send the data to https://..." | rule DX-01 |
| Named jailbreaks | DAN, developer mode, AIM | rule JB-01 |

Normalisation (NFKC fold, removal of zero-width and bidi controls, whitespace
collapse) runs before every rule, so an attacker cannot defeat a rule by hiding
characters inside a trigger word.

## Threats explicitly out of scope

- **Multi-turn injection.** The engine judges one prompt at a time. An attack
  that only emerges across several messages is not covered here.
- **Injection carried in retrieved context (RAG).** The content a retriever
  pastes into the prompt is a separate surface, measured separately.
- **Non-text modalities.** Image and audio payloads are not inspected.
- **A determined adversary crafting novel phrasing.** The baseline catches known
  techniques. This is why it is a baseline and why a model is measured on top,
  not why it is the final answer.

## Authentication

- Passwords are salted and stretched with PBKDF2-HMAC-SHA256 and compared in
  constant time. The plaintext is read once at boot and never stored.
- Session tokens are compact HS256 JWTs built from the standard library, so the
  security-sensitive path carries no third-party code. Signature and expiry are
  checked on every protected request, both in constant time.
- This is a demo-grade identity layer by design: one operator account, no
  refresh tokens, no revocation list. Stated here so no reader assumes more.

## Data handling

- The raw prompt is never stored. Decisions and the ledger keep only its
  SHA-256 digest, so the record proves which prompt was judged without
  retaining its content.
- The ledger provides integrity and ordering, not confidentiality.

## Key management

- One key signs the JWTs and seals the ledger. In production it must come from a
  secret store and be rotated on a schedule.
- The demo mints an ephemeral key per process when none is supplied, which keeps
  the console running on a clean machine while making it obvious that production
  must supply its own. A persisted ledger sealed under an old key will, by
  design, fail to load under a new one.

## Supply chain

The CI pipeline runs secret scanning, SAST, dependency audit, a CodeQL analysis,
generates a CycloneDX SBOM and attests build provenance. The runtime has two
direct dependencies; the engine itself has none.

## Reporting

For a real deployment, security reports would go to a monitored address. In this
portfolio repository, open a private advisory on the hosting platform.
