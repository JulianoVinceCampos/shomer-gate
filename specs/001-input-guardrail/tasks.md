# Spec 001: Tasks

- [x] 1. Define the `Rule` dataclass and the frozen `RULES` set across eight
      categories, each with id, weight, rationale and compiled regex.
      _Covers criteria 1, 5._
- [x] 2. Implement input normalisation (NFKC, strip invisible, collapse
      horizontal whitespace, preserve newlines). _Covers criterion 6._
- [x] 3. Implement `GuardrailEngine.evaluate`: scan, score, map to verdict,
      build evidence, hash the prompt. _Covers criteria 2, 3, 4, 7._
- [x] 4. Validate thresholds at construction time. _Covers criterion 9._
- [x] 5. Implement confidence as distance from the nearest boundary.
- [x] 6. Add the rule catalog surface for the API `/rules` endpoint.
- [x] 7. Unit tests: verdicts, evidence, determinism, evasion, thresholds.
      _Covers criterion 8 and all above._
- [x] 8. Wire the engine into the CLI `check` subcommand.

Status: implemented. Tests live in `tests/test_guardrail.py`; the catalog is
exercised in `tests/test_api.py::test_rules_endpoint_is_public`.
