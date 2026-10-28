# ADR 0002: Three-state verdict, not a boolean

Status: accepted

## Context

A guardrail could answer allow or block. A binary answer is simple, but it
forces the ambiguous middle into one of the two confident outcomes. A prompt
with a single weak signal is either waved through or blocked, and both are
wrong: it deserves a second look, not a guess.

## Decision

The verdict has three states: allow, review, block. Review is the band where
the deterministic signal is present but not strong enough to block on its own.
In measurement, review is an abstention: it is never counted as a catch and
never as a benign pass, only as reduced coverage.

## Consequences

- The baseline can say "I am not sure" honestly instead of being forced to
  pick. The cases that most need a human or a model are the ones that surface.
- Recall cannot be inflated by routing hard cases to review, because review does
  not count toward recall. The cost of abstaining is paid in coverage, in the
  open.
- Downstream has to handle three outcomes, not two. Block rejects, allow
  proceeds, review escalates to a model or a person. This is more wiring, and it
  is the point.
- Confidence is defined so that review peaks in the middle of the band and falls
  toward either threshold, which matches where the baseline is genuinely least
  sure.
