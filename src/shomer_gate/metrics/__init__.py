"""Measurement of the guardrail against planted ground truth.

Public surface:

- :class:`~shomer_gate.metrics.evaluator.GroundTruthCase`: one labelled prompt.
- :class:`~shomer_gate.metrics.evaluator.EvaluationReport`: the full scorecard.
- :func:`~shomer_gate.metrics.evaluator.evaluate`: run the engine over a dataset.
- :func:`~shomer_gate.metrics.evaluator.load_ground_truth`: read the JSON dataset.
"""

from __future__ import annotations

from shomer_gate.metrics.evaluator import (
    EvaluationReport,
    GroundTruthCase,
    evaluate,
    load_ground_truth,
)

__all__ = ["EvaluationReport", "GroundTruthCase", "evaluate", "load_ground_truth"]
