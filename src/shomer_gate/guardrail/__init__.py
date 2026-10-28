"""Deterministic prompt-injection guardrail.

Public surface:

- :class:`~shomer_gate.guardrail.engine.GuardrailEngine`: evaluates a prompt.
- :class:`~shomer_gate.guardrail.engine.Decision`: the verdict plus evidence.
- :class:`~shomer_gate.guardrail.engine.Verdict`: ALLOW / REVIEW / BLOCK.
- :data:`~shomer_gate.guardrail.patterns.RULES`: the frozen rule set.
"""

from __future__ import annotations

from shomer_gate.guardrail.engine import Decision, GuardrailEngine, RuleHit, Verdict
from shomer_gate.guardrail.patterns import RULES, Rule

__all__ = ["RULES", "Decision", "GuardrailEngine", "Rule", "RuleHit", "Verdict"]
