# Specs: spec-driven development

Every feature in shomer-gate starts as a spec, not as code. A spec is three
short documents that travel together:

1. `requirements.md`: what the feature must do, written as testable acceptance
   criteria. No solution here, only the obligations.
2. `design.md`: how the feature meets those obligations, with the data shapes,
   the control flow and the trade-offs that were considered and rejected.
3. `tasks.md`: the ordered, checkable units of work that implement the design.

The order is deliberate. Requirements constrain the design, the design
constrains the tasks, and the tasks produce the code and the tests. When a test
exists, it points back to the acceptance criterion it proves.

## Active specs

| Spec | Feature | Status |
|------|---------|--------|
| [001](001-input-guardrail/requirements.md) | Deterministic input guardrail | implemented |
| [002](002-decision-ledger/requirements.md) | Tamper-evident decision ledger | implemented |

## Why spec-first here

This project exists to show a way of working, not just a running console. The
baseline is deterministic so it can be reasoned about; the spec is written first
so the reasoning is on record before a line of code locks in a decision. A limit
that is written down is engineering. A limit that is only implied is a trap for
whoever reads the code next.
