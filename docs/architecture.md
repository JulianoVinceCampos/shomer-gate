# Architecture

shomer-gate is a guardrail that sits in front of an LLM. A deterministic
baseline decides what happens to each prompt, the model is measured against that
baseline rather than trusted ahead of it, and every verdict is written to a
tamper-evident ledger.

## Components

```mermaid
flowchart TD
  subgraph client["Browser console (zero deps)"]
    LOGIN["login screen"]
    DASH["dashboard:<br/>scenario editor, verdict,<br/>metrics, ledger view"]
    MIRROR["JS mirror engine<br/>(offline demo only)"]
  end

  subgraph api["API (FastAPI)"]
    AUTH["auth<br/>PBKDF2 + HS256 JWT"]
    ROUTES["routes:<br/>/login /check /ledger<br/>/metrics /rules /health"]
  end

  subgraph engine["Engine (pure stdlib, zero deps)"]
    GUARD["guardrail<br/>rules + verdict"]
    LEDGER["ledger<br/>HMAC chain"]
    METRICS["evaluator<br/>vs. ground truth"]
  end

  DATA["ground_truth.json<br/>(planted labels)"]

  LOGIN --> AUTH
  DASH --> ROUTES
  DASH -.offline.-> MIRROR
  ROUTES --> GUARD
  ROUTES --> LEDGER
  ROUTES --> METRICS
  GUARD --> LEDGER
  METRICS --> DATA
  METRICS --> GUARD
```

The engine is the core and depends on nothing. The API is a thin shell that
wires the engine to HTTP and adds authentication. The browser console talks to
the API; with no backend reachable it falls back to a JavaScript mirror of the
same rules, so the demo still runs on a static host. The mirror is explicitly
not authoritative: the Python engine is the one the tests and the CI gate
measure.

## A request, end to end

```mermaid
sequenceDiagram
  autonumber
  participant U as User
  participant W as Console
  participant A as API
  participant G as Guardrail engine
  participant L as Ledger

  U->>W: sign in (shomer / passphrase)
  W->>A: POST /api/login
  A->>A: verify_password (PBKDF2, constant time)
  A-->>W: HS256 JWT (bearer)

  U->>W: paste a prompt, Evaluate
  W->>A: POST /api/guardrail/check (Bearer)
  A->>A: verify_token
  A->>G: evaluate(prompt)
  G->>G: normalise, scan rules, score
  G-->>A: Decision (verdict, score, evidence, sha256)
  A->>L: append({subject, decision})
  L->>L: seal = HMAC(prev_seal + canonical(payload))
  L-->>A: seq, seal
  A-->>W: decision + ledger seq + seal
  W->>U: verdict card, evidence, live ledger row
```

## Verdict state machine

```mermaid
stateDiagram-v2
  direction LR
  [*] --> scored
  scored --> ALLOW: score < review
  scored --> REVIEW: review <= score < block
  scored --> BLOCK: score >= block
  ALLOW --> [*]
  BLOCK --> [*]
  REVIEW --> escalate: to model or human
  escalate --> [*]
```

`REVIEW` is a real outcome, not a rounding of allow or block. It is the band
where the deterministic signal is present but not strong enough to block alone.
It is never scored as a catch when the baseline is measured.

## Trust boundary

```mermaid
flowchart LR
  subgraph untrusted["Untrusted"]
    IN["prompt text"]
  end
  subgraph trusted["Trusted process"]
    NORM["normalise"]
    RULES["rule scan"]
    DEC["decision + sha256 only"]
  end
  IN --> NORM --> RULES --> DEC
  DEC --> LED["ledger (integrity, not secrecy)"]
```

The prompt is untrusted input. It is treated as data, never as instructions, and
it is reduced to a SHA-256 digest before anything is stored. The ledger proves
integrity and order; it does not keep the prompt content.

## Deployment

```mermaid
flowchart LR
  DEV["developer"] -->|docker compose up| IMG["shomer-gate image<br/>non-root, read-only fs,<br/>caps dropped"]
  IMG -->|:8080| CONSOLE["console + API<br/>same origin"]
  VAULT["vault / secret store"] -.SHOMER_SIGNING_KEY.-> IMG
  IMG --> HC["/api/health<br/>liveness + ledger integrity"]
```

The container runs as an unprivileged user with a read-only root filesystem and
all Linux capabilities dropped. In production the signing key comes from a
secret store; the demo generates an ephemeral per-process key so it still runs
on a clean machine with no configuration.

## Where things live

| Path | What |
|------|------|
| `src/shomer_gate/guardrail/` | rules and the verdict engine |
| `src/shomer_gate/ledger/` | the HMAC-chained ledger |
| `src/shomer_gate/metrics/` | the evaluator and scorecard |
| `src/shomer_gate/api/` | FastAPI app and auth |
| `web/` | the static console (login, dashboard, mirror engine) |
| `data/ground_truth.json` | the planted evaluation set |
| `specs/` | spec-driven development documents |
| `docs/adr/` | architecture decision records |
