"""The deterministic rule set.

Every rule is a named, weighted, explainable matcher. There is no model here on
purpose: this is the baseline that the model has to beat before anyone trusts
the model. A rule names the attack technique it detects, carries a severity
weight, and returns the exact span it matched so the decision can quote its own
evidence instead of asking the reader to take a score on faith.

Weights are calibrated in ``docs/metrics.md`` against the synthetic ground truth
in ``data/ground_truth.json``. They are data, not opinion: change a weight and
the evaluator tells you what happened to precision, recall and the false
positive rate on the next run.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

# MITRE-ATLAS-flavoured categories. Kept as plain strings so the ledger stays
# readable and the dashboard can group by them without a lookup table.
CATEGORY_INSTRUCTION_OVERRIDE = "instruction_override"
CATEGORY_ROLE_HIJACK = "role_hijack"
CATEGORY_SYSTEM_PROMPT_EXFIL = "system_prompt_exfil"
CATEGORY_DELIMITER_SPOOF = "delimiter_spoof"
CATEGORY_ENCODING_EVASION = "encoding_evasion"
CATEGORY_REFUSAL_SUPPRESSION = "refusal_suppression"
CATEGORY_DATA_EXFIL = "data_exfil"
CATEGORY_JAILBREAK_KNOWN = "jailbreak_known"


@dataclass(frozen=True, slots=True)
class Rule:
    """A single deterministic detector.

    Attributes:
        id: Stable identifier, cited verbatim in the ledger and the dashboard.
        category: One of the ``CATEGORY_*`` constants above.
        weight: Severity contribution added to the score when the rule fires.
        rationale: One line a human reads to understand why this matters.
        pattern: Compiled regex evaluated against the normalised prompt.
    """

    id: str
    category: str
    weight: float
    rationale: str
    pattern: re.Pattern[str]

    def scan(self, normalised: str) -> list[tuple[int, int]]:
        """Return the (start, end) spans this rule matches, possibly empty."""
        return [m.span() for m in self.pattern.finditer(normalised)]


def _ci(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


# The frozen baseline. Ordered by category for readability; order has no effect
# on the score, which is a pure sum over the rules that fire.
RULES: tuple[Rule, ...] = (
    # --- Instruction override: the canonical prompt-injection move. ----------
    Rule(
        id="IO-01",
        category=CATEGORY_INSTRUCTION_OVERRIDE,
        weight=5.0,
        rationale="Tells the model to ignore or discard its prior instructions.",
        pattern=_ci(r"\b(ignore|disregard|forget|override)\b[^.]{0,40}\b"
                    r"(previous|prior|above|earlier|all)\b[^.]{0,20}\b"
                    r"(instruction|instructions|prompt|prompts|rule|rules|context)\b"),
    ),
    Rule(
        id="IO-02",
        category=CATEGORY_INSTRUCTION_OVERRIDE,
        weight=4.0,
        rationale="Resets the conversation to erase the governing system prompt.",
        pattern=_ci(r"\b(start over|begin again|reset)\b[^.]{0,30}"
                    r"\b(ignoring|without)\b[^.]{0,30}\b(instruction|rule|constraint)"),
    ),
    # --- Role hijack: redefine who the model is. -----------------------------
    Rule(
        id="RH-01",
        category=CATEGORY_ROLE_HIJACK,
        weight=3.5,
        rationale="Reassigns the model's persona to escape its guardrails.",
        pattern=_ci(r"\b(you are now|from now on,? you are|act as|pretend to be|"
                    r"roleplay as|behave like)\b"),
    ),
    # --- System-prompt exfiltration. -----------------------------------------
    Rule(
        id="SE-01",
        category=CATEGORY_SYSTEM_PROMPT_EXFIL,
        weight=4.0,
        rationale="Attempts to read back the hidden system prompt or instructions.",
        pattern=_ci(r"\b(reveal|show|print|repeat|output|display|tell me)\b"
                    r"[^.]{0,30}\b(your|the)\b[^.]{0,20}\b"
                    r"(system prompt|instructions|rules|prompt|guidelines)\b"),
    ),
    Rule(
        id="SE-02",
        category=CATEGORY_SYSTEM_PROMPT_EXFIL,
        weight=3.5,
        rationale="The 'repeat the words above' exfiltration trick.",
        pattern=_ci(r"\brepeat\b[^.]{0,20}\b(the )?(words|text|everything)\b"
                    r"[^.]{0,10}\babove\b"),
    ),
    # --- Delimiter / chat-template spoofing. ---------------------------------
    Rule(
        id="DS-01",
        category=CATEGORY_DELIMITER_SPOOF,
        weight=4.5,
        rationale="Injects fake chat-template markers to forge a system turn.",
        pattern=re.compile(r"(<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]|"
                           r"<<SYS>>|<</SYS>>)"),
    ),
    Rule(
        id="DS-02",
        category=CATEGORY_DELIMITER_SPOOF,
        weight=3.0,
        rationale="Forges a role header (system:/assistant:) to hijack the turn.",
        pattern=_ci(r"(^|\n)\s*(###\s*)?(system|assistant|developer)\s*:"),
    ),
    # --- Encoding evasion. ---------------------------------------------------
    Rule(
        id="EE-01",
        category=CATEGORY_ENCODING_EVASION,
        weight=3.0,
        rationale="A long base64 blob used to smuggle a payload past text filters.",
        pattern=re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
    ),
    # --- Refusal suppression. ------------------------------------------------
    Rule(
        id="RS-01",
        category=CATEGORY_REFUSAL_SUPPRESSION,
        weight=2.5,
        rationale="Pressures the model to drop its safety refusals.",
        pattern=_ci(r"\b(do not|don't|never)\b[^.]{0,15}\b(refuse|decline|warn|"
                    r"apologi[sz]e)\b|\b(no (warnings?|disclaimers?|restrictions?)|"
                    r"without (any )?(restriction|filter|limit)s?)\b"),
    ),
    # --- Data exfiltration to an attacker-controlled sink. -------------------
    Rule(
        id="DX-01",
        category=CATEGORY_DATA_EXFIL,
        weight=4.0,
        rationale="Asks the model to ship data to an external endpoint.",
        pattern=_ci(r"\b(send|post|exfiltrate|upload|forward|leak)\b[^.]{0,30}"
                    r"\b(to )?(https?://|ftp://|curl|webhook|my (server|endpoint))"),
    ),
    # --- Known named jailbreaks. ---------------------------------------------
    Rule(
        id="JB-01",
        category=CATEGORY_JAILBREAK_KNOWN,
        weight=5.0,
        rationale="Matches a named jailbreak persona (DAN, developer mode, etc.).",
        pattern=_ci(r"\b(DAN|do anything now|developer mode|jailbreak|STAN|"
                    r"AIM mode|unfiltered mode)\b"),
    ),
)


def rules_by_category(rules: Iterable[Rule] = RULES) -> dict[str, list[Rule]]:
    """Group the rule set by category for reporting and docs generation."""
    grouped: dict[str, list[Rule]] = {}
    for rule in rules:
        grouped.setdefault(rule.category, []).append(rule)
    return grouped


@dataclass(frozen=True, slots=True)
class RuleCatalogEntry:
    """Flat, serialisable view of a rule for the API ``/rules`` endpoint."""

    id: str
    category: str
    weight: float
    rationale: str
    source: str = field(default="")


def catalog(rules: Iterable[Rule] = RULES) -> list[RuleCatalogEntry]:
    """Return a JSON-friendly catalog of the active rules."""
    return [
        RuleCatalogEntry(
            id=r.id,
            category=r.category,
            weight=r.weight,
            rationale=r.rationale,
            source=r.pattern.pattern,
        )
        for r in rules
    ]
