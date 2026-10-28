"""Score the deterministic baseline against a labelled dataset.

The dataset plants the attack on purpose: each case declares whether it is an
injection or benign traffic, and which technique it exercises. Because the label
is known, precision and recall are *calculated*, not estimated.

One rule governs the arithmetic, and it is the whole point of the three-state
design: a ``REVIEW`` verdict is an abstention. It is never scored as a pass and
never as a block. It is reported separately as coverage, so a baseline cannot
inflate its recall by quietly sending the hard cases to review. See ADR 0002.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from shomer_gate.guardrail.engine import GuardrailEngine, Verdict

LABEL_INJECTION = "injection"
LABEL_BENIGN = "benign"


@dataclass(frozen=True, slots=True)
class GroundTruthCase:
    """One labelled prompt in the evaluation set."""

    id: str
    prompt: str
    label: str
    technique: str = "unspecified"

    def __post_init__(self) -> None:
        if self.label not in (LABEL_INJECTION, LABEL_BENIGN):
            raise ValueError(f"case {self.id}: label must be injection|benign, got {self.label!r}")


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """The scorecard. All rates are over the *decided* set unless noted."""

    total: int
    decided: int
    abstained: int
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    accuracy: float
    coverage: float
    recall_by_technique: dict[str, float] = field(default_factory=dict)
    abstain_by_label: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "decided": self.decided,
            "abstained": self.abstained,
            "confusion": {
                "tp": self.true_positive,
                "fp": self.false_positive,
                "tn": self.true_negative,
                "fn": self.false_negative,
            },
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "accuracy": round(self.accuracy, 4),
            "coverage": round(self.coverage, 4),
            "recall_by_technique": {k: round(v, 4) for k, v in self.recall_by_technique.items()},
            "abstain_by_label": self.abstain_by_label,
        }


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate(
    cases: list[GroundTruthCase], engine: GuardrailEngine | None = None
) -> EvaluationReport:
    """Run ``engine`` over every case and compute the scorecard.

    A ``BLOCK`` is the positive prediction, an ``ALLOW`` the negative, and a
    ``REVIEW`` an abstention excluded from the confusion matrix but reported as
    coverage. Recall is also broken out per declared technique so a weak spot is
    named rather than averaged away.
    """
    engine = engine or GuardrailEngine()
    tp = fp = tn = fn = 0
    abstained = 0
    abstain_by_label: Counter[str] = Counter()
    technique_total: Counter[str] = Counter()
    technique_caught: Counter[str] = Counter()

    for case in cases:
        verdict = engine.evaluate(case.prompt).verdict
        is_attack = case.label == LABEL_INJECTION

        if verdict is Verdict.REVIEW:
            abstained += 1
            abstain_by_label[case.label] += 1
            continue

        blocked = verdict is Verdict.BLOCK
        if is_attack:
            technique_total[case.technique] += 1
            if blocked:
                tp += 1
                technique_caught[case.technique] += 1
            else:
                fn += 1
        else:
            if blocked:
                fp += 1
            else:
                tn += 1

    decided = tp + fp + tn + fn
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    fpr = _safe_div(fp, fp + tn)
    accuracy = _safe_div(tp + tn, decided)
    coverage = _safe_div(decided, len(cases))
    recall_by_technique = {
        tech: _safe_div(technique_caught[tech], total)
        for tech, total in sorted(technique_total.items())
    }

    return EvaluationReport(
        total=len(cases),
        decided=decided,
        abstained=abstained,
        true_positive=tp,
        false_positive=fp,
        true_negative=tn,
        false_negative=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        false_positive_rate=fpr,
        accuracy=accuracy,
        coverage=coverage,
        recall_by_technique=recall_by_technique,
        abstain_by_label=dict(abstain_by_label),
    )


def load_ground_truth(path: str | Path) -> list[GroundTruthCase]:
    """Load and validate the JSON ground-truth dataset."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = raw["cases"] if isinstance(raw, dict) else raw
    return [
        GroundTruthCase(
            id=str(c["id"]),
            prompt=str(c["prompt"]),
            label=str(c["label"]),
            technique=str(c.get("technique", "unspecified")),
        )
        for c in cases
    ]
