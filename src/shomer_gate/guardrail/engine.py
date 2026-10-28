"""The guardrail engine: a pure function from prompt to verdict.

Design decisions, each one deliberate and documented in ``docs/adr``:

- **Deterministic first.** No model call happens here. The engine is a pure
  function of the input and the rule set, so the same prompt always yields the
  same verdict and the same evidence. That is what lets the model be *measured*
  against it instead of trusted ahead of it.
- **Three states, not two.** A binary allow/block hides the cases the baseline
  cannot settle. ``REVIEW`` is a first-class outcome: it means "the signal is
  real but not strong enough to block on its own", and it never counts as a
  pass. See ADR 0002.
- **Evidence travels with the verdict.** Every decision carries the exact rules
  that fired and the spans they matched, so a reviewer argues with a reason, not
  with a number.
"""

from __future__ import annotations

import hashlib
import re
import time
import unicodedata
from dataclasses import dataclass, field
from enum import Enum

from shomer_gate.guardrail.patterns import RULES, Rule

# Zero-width and bidi control characters used to hide payloads from eyeballs and
# from naive filters. Stripped before matching so evasion does not buy anything.
_INVISIBLE = dict.fromkeys(
    [0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E]
)


class Verdict(str, Enum):
    """The three possible outcomes. Values are stable wire strings."""

    ALLOW = "allow"
    REVIEW = "review"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class RuleHit:
    """One rule firing on one span, carried as evidence."""

    rule_id: str
    category: str
    weight: float
    rationale: str
    snippet: str
    span: tuple[int, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "weight": self.weight,
            "rationale": self.rationale,
            "snippet": self.snippet,
            "span": list(self.span),
        }


@dataclass(frozen=True, slots=True)
class Decision:
    """The full result of evaluating one prompt.

    The raw prompt is never stored on the decision; only its SHA-256 digest is,
    so the ledger can prove *which* prompt was judged without retaining the
    content. See ADR 0003 and ``docs/security.md``.
    """

    verdict: Verdict
    score: float
    confidence: float
    prompt_sha256: str
    hits: tuple[RuleHit, ...]
    rationale: str
    latency_ms: float
    categories: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict.value,
            "score": round(self.score, 3),
            "confidence": round(self.confidence, 4),
            "prompt_sha256": self.prompt_sha256,
            "hits": [h.to_dict() for h in self.hits],
            "rationale": self.rationale,
            "latency_ms": round(self.latency_ms, 3),
            "categories": list(self.categories),
        }


_HSPACE = re.compile(r"[^\S\n]+")
_MULTINEWLINE = re.compile(r"\n{3,}")


def _normalise(text: str) -> str:
    """NFKC-fold, strip invisible controls, collapse horizontal whitespace.

    Newlines are preserved on purpose: line-anchored detectors (a forged
    ``system:`` role header, for instance) depend on line structure, so only
    runs of spaces and tabs are collapsed. Zero-width and bidi controls are
    removed first, so hiding a payload between invisible characters buys the
    attacker nothing.
    """
    folded = unicodedata.normalize("NFKC", text).translate(_INVISIBLE)
    folded = folded.replace("\r\n", "\n").replace("\r", "\n")
    folded = _HSPACE.sub(" ", folded)
    folded = _MULTINEWLINE.sub("\n\n", folded)
    return folded.strip()


def _snippet(normalised: str, span: tuple[int, int], width: int = 48) -> str:
    start, end = span
    text = normalised[start:end]
    return text if len(text) <= width else text[: width - 1] + "\u2026"


class GuardrailEngine:
    """Evaluate prompts against the deterministic rule set.

    Args:
        block_threshold: Score at or above which the verdict is ``BLOCK``.
        review_threshold: Score at or above which the verdict is ``REVIEW``.
            Must be strictly below ``block_threshold``.
        rules: The rule set to evaluate. Defaults to the frozen baseline.
    """

    def __init__(
        self,
        block_threshold: float = 7.0,
        review_threshold: float = 3.0,
        rules: tuple[Rule, ...] = RULES,
    ) -> None:
        if not 0 < review_threshold < block_threshold:
            raise ValueError(
                "thresholds must satisfy 0 < review_threshold < block_threshold "
                f"(got review={review_threshold}, block={block_threshold})"
            )
        self.block_threshold = block_threshold
        self.review_threshold = review_threshold
        self.rules = rules

    def evaluate(self, prompt: str) -> Decision:
        """Judge a single prompt and return a fully-evidenced decision."""
        started = time.perf_counter()
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        normalised = _normalise(prompt)

        hits: list[RuleHit] = []
        score = 0.0
        for rule in self.rules:
            spans = rule.scan(normalised)
            if not spans:
                continue
            score += rule.weight  # each rule contributes once, however many spans
            first = spans[0]
            hits.append(
                RuleHit(
                    rule_id=rule.id,
                    category=rule.category,
                    weight=rule.weight,
                    rationale=rule.rationale,
                    snippet=_snippet(normalised, first),
                    span=first,
                )
            )

        verdict = self._verdict(score)
        confidence = self._confidence(score, verdict)
        categories = tuple(dict.fromkeys(h.category for h in hits))
        rationale = self._rationale(verdict, hits, score)
        latency_ms = (time.perf_counter() - started) * 1000.0

        return Decision(
            verdict=verdict,
            score=score,
            confidence=confidence,
            prompt_sha256=digest,
            hits=tuple(sorted(hits, key=lambda h: -h.weight)),
            rationale=rationale,
            latency_ms=latency_ms,
            categories=categories,
        )

    def _verdict(self, score: float) -> Verdict:
        if score >= self.block_threshold:
            return Verdict.BLOCK
        if score >= self.review_threshold:
            return Verdict.REVIEW
        return Verdict.ALLOW

    def _confidence(self, score: float, verdict: Verdict) -> float:
        """Distance from the nearest decision boundary, normalised to 0..1.

        REVIEW is the inconclusive band by construction, so its confidence peaks
        in the middle of the band and falls off toward either threshold. The
        verdict is most honestly "unsure" exactly where the score is ambiguous.
        """
        if verdict is Verdict.ALLOW:
            return 1.0 - min(1.0, score / self.review_threshold)
        if verdict is Verdict.BLOCK:
            headroom = self.block_threshold * 0.5
            return min(1.0, (score - self.block_threshold) / headroom + 0.5)
        band = self.block_threshold - self.review_threshold
        midpoint = self.review_threshold + band / 2.0
        return max(0.0, 0.5 - abs(score - midpoint) / band)

    @staticmethod
    def _rationale(verdict: Verdict, hits: list[RuleHit], score: float) -> str:
        if not hits:
            return "No injection signal detected by the deterministic baseline."
        top = max(hits, key=lambda h: h.weight)
        named = ", ".join(sorted({h.rule_id for h in hits}))
        lead = {
            Verdict.BLOCK: "Blocked",
            Verdict.REVIEW: "Held for review",
            Verdict.ALLOW: "Allowed despite a weak signal",
        }[verdict]
        return (
            f"{lead} at score {score:.1f}. Leading signal {top.rule_id} "
            f"({top.category}): {top.rationale} Rules fired: {named}."
        )
