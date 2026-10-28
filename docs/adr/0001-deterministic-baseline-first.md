# ADR 0001: Deterministic baseline before any model

Status: accepted

## Context

The task is to decide whether a prompt is a prompt-injection attempt. The
obvious reach is for a model: ask an LLM to classify it. But if a model is the
thing that decides, there is nothing left to measure the model against, and the
decision becomes a score a reader has to believe rather than a conclusion they
can argue with.

## Decision

The first line of defence is a deterministic rule engine with zero model calls.
It is a pure function of the input and the rule set. The model, when present,
runs after the baseline and is measured against it, never ahead of it.

## Consequences

- The same prompt always yields the same verdict and the same evidence, so
  behaviour is reproducible and testable.
- The baseline is explainable: every verdict names the rules that produced it.
  At 3 a.m. an on-call gets a reason, not a probability.
- The baseline will miss novel phrasing. That is expected and is exactly why a
  model is measured on top. The miss is visible in the scorecard as coverage,
  not hidden.
- The engine has no third-party dependencies, which keeps the trusted path
  small and auditable.
