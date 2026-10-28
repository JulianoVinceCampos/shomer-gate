"""shomer-gate. The guardian at the gate.

A guardrail gateway for LLM traffic. A deterministic baseline decides whether a
prompt is allowed, blocked or sent for review; the model is measured against
that baseline, never trusted ahead of it; and every verdict is appended to a
tamper-evident ledger.

The engine (``guardrail``, ``ledger``, ``metrics``) is pure standard library and
imports with zero third-party dependencies. The optional ``api`` package adds a
FastAPI surface on top, but nothing in the engine depends on it.
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["__version__"]
