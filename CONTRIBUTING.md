# Contributing

Thanks for looking. This repository doubles as a working console and a worked
example of a way of building, so the process is part of the product.

## The loop

1. Start from a spec. A change to behaviour starts in `specs/`, as updated
   acceptance criteria, before any code. See `specs/README.md`.
2. Write the test that proves the criterion, then the code that passes it.
3. Run the full local gate. It is the same gate CI runs:

   ```bash
   make all        # ruff, mypy (strict), pytest with coverage, eval gate
   ```

## Standards

- The engine (`guardrail`, `ledger`, `metrics`) stays dependency-free. If a
  change needs a third-party package in the engine, it probably belongs in the
  API layer instead.
- Coverage has a ratchet at 85 percent. It goes up, not down.
- Types are strict. `mypy` runs with `--strict` and must be clean.
- The eval gate must stay green: recall at least 0.80, false positive rate at
  most 0.05 on the committed ground truth. If a rule change moves those, the
  scorecard in `docs/metrics.md` is updated in the same change.
- Prose in this repository avoids the em dash. It is a small, deliberate style
  rule; use a period, colon, comma, or parentheses instead.

## Adding a detection rule

1. Add the rule to `src/shomer_gate/guardrail/patterns.py` with a stable id, a
   category, a weight, a one-line rationale and a tested regex.
2. Add labelled cases to `data/ground_truth.json` that exercise it, both the
   attack and a benign near-miss.
3. Run `shomer eval` and confirm recall and the false positive rate hold.
4. Record any threshold change as a note in `docs/metrics.md`.

## Commit hygiene

Small, focused commits with a clear message. Tests and the spec change travel in
the same commit as the behaviour they describe.
