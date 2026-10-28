# Spec 001: Deterministic input guardrail

## Problem

An LLM-facing service receives untrusted text. Some of that text is a prompt
injection: an attempt to override the system instructions, hijack the model's
role, exfiltrate the hidden prompt, or smuggle a payload past a naive filter.
The service needs a fast, explainable first line of defence that decides what to
do with each prompt, before any model is called.

## Goals

- Decide every prompt as one of three outcomes: allow, review, or block.
- Carry the reason for the decision with the decision itself.
- Be deterministic: the same input always yields the same output.
- Run with zero third-party dependencies and in well under a millisecond.

## Non-goals

- Detecting multi-turn injections that only emerge across several messages.
- Inspecting payloads inside retrieved documents (RAG context).
- Replacing a model-based classifier. This is the baseline the model is
  measured against, not the final word.

## Acceptance criteria

1. WHEN a prompt contains a known injection technique, THE engine SHALL return a
   non-allow verdict and list at least one rule that fired.
2. WHEN the cumulative severity score is at or above the block threshold, THE
   engine SHALL return `block`.
3. WHEN the score is at or above the review threshold but below the block
   threshold, THE engine SHALL return `review`.
4. WHEN the score is below the review threshold, THE engine SHALL return
   `allow`.
5. THE engine SHALL attach, for each rule that fired, the rule id, its category,
   its weight, and the exact matched span of text.
6. THE engine SHALL normalise the input (Unicode NFKC fold, removal of
   zero-width and bidi controls, collapse of horizontal whitespace) before
   matching, so invisible-character evasion does not bypass a rule.
7. THE engine SHALL record the SHA-256 of the original prompt and SHALL NOT
   retain the raw prompt on the decision object.
8. GIVEN the same prompt and the same rule set, THE engine SHALL produce an
   identical decision on every call, except for the measured latency.
9. WHEN constructed with thresholds that do not satisfy
   `0 < review < block`, THE engine SHALL raise an error at construction time.

## Measured obligations (see spec notes and docs/metrics.md)

- Against the committed ground truth, recall SHALL be at least 0.80 and the
  false positive rate SHALL be at most 0.05, enforced by the CI eval gate.
- A `review` verdict SHALL NOT be counted as a catch in recall.
