"""HTTP surface for shomer-gate.

Everything here is a thin shell over the zero-dependency engine. Authentication
(:mod:`~shomer_gate.api.auth`) is implemented with the standard library only:
PBKDF2 for the password and an HS256 JWT hand-rolled over ``hmac``, so the
security-sensitive path has no third-party code in it. The FastAPI app in
:mod:`~shomer_gate.api.app` wires the engine, the ledger and the evaluator to
routes and serves the static dashboard.
"""

from __future__ import annotations

__all__ = ["app", "auth"]
