"""FastAPI application wiring the engine, ledger and evaluator to HTTP.

Routes under ``/api`` carry the logic; the static dashboard is mounted at ``/``.
The ledger is kept in memory for the life of the process: the signing key may be
ephemeral, so loading a ledger sealed by a previous key would (correctly) fail
verification. Persistence is a deployment choice, enabled by pointing
``SHOMER_LEDGER_PATH`` at a file and supplying a stable ``SHOMER_SIGNING_KEY``.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from shomer_gate import __version__
from shomer_gate.api import auth
from shomer_gate.api.models import CheckRequest, HealthResponse, LoginRequest, LoginResponse
from shomer_gate.config import get_settings
from shomer_gate.guardrail.engine import GuardrailEngine
from shomer_gate.guardrail.patterns import catalog
from shomer_gate.ledger.chain import Ledger
from shomer_gate.metrics.evaluator import evaluate, load_ground_truth

_WEB_DIR = Path(__file__).resolve().parents[3] / "web"

settings = get_settings()
engine = GuardrailEngine(
    block_threshold=settings.block_threshold,
    review_threshold=settings.review_threshold,
)
ledger = Ledger(settings.signing_key)  # in-memory on purpose; see module docstring
_admin_hash = auth.hash_password(settings.admin_password)

app = FastAPI(
    title="shomer-gate",
    version=__version__,
    description="Deterministic guardrail gateway for LLM traffic, with a tamper-evident ledger.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # same-origin in the demo; tighten per deployment
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# -- auth dependency ----------------------------------------------------------
def require_subject(authorization: Annotated[str | None, Header()] = None) -> str:
    """Resolve the Bearer token to a subject or reject with 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = auth.verify_token(token, settings.signing_key)
    except auth.AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return str(claims["sub"])


Subject = Annotated[str, Depends(require_subject)]


# -- public routes ------------------------------------------------------------
@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    report = ledger.verify()
    return HealthResponse(
        status="ok",
        version=__version__,
        ledger_length=report.length,
        ledger_ok=report.ok,
    )


@app.post("/api/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    user_ok = auth.hmac_safe_equals(body.username, settings.admin_user)
    pass_ok = auth.verify_password(body.password, _admin_hash)
    # Evaluate both regardless of the first result to avoid a timing oracle.
    if not (user_ok and pass_ok):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    token = auth.issue_token(body.username, settings.signing_key, settings.token_ttl)
    return LoginResponse(token=token, expires_in=settings.token_ttl, subject=body.username)


@app.get("/api/rules")
def rules() -> JSONResponse:
    return JSONResponse(
        {
            "block_threshold": settings.block_threshold,
            "review_threshold": settings.review_threshold,
            "rules": [asdict(entry) for entry in catalog()],
        }
    )


# -- protected routes ---------------------------------------------------------
@app.post("/api/guardrail/check")
def guardrail_check(body: CheckRequest, subject: Subject) -> JSONResponse:
    decision = engine.evaluate(body.prompt)
    response = decision.to_dict()
    if body.record:
        record = ledger.append({"subject": subject, "decision": decision.to_dict()})
        response["ledger_seq"] = record.seq
        response["ledger_seal"] = record.seal
    return JSONResponse(response)


@app.get("/api/ledger")
def ledger_tail(subject: Subject, limit: int = 50) -> JSONResponse:
    limit = max(1, min(limit, 500))
    report = ledger.verify()
    return JSONResponse(
        {
            "integrity": report.to_dict(),
            "records": [r.to_dict() for r in ledger.tail(limit)],
        }
    )


@app.get("/api/ledger/verify")
def ledger_verify(subject: Subject) -> JSONResponse:
    return JSONResponse(ledger.verify().to_dict())


@app.get("/api/metrics")
def metrics(subject: Subject) -> JSONResponse:
    cases = load_ground_truth(settings.ground_truth_path)
    report = evaluate(cases, engine)
    return JSONResponse(report.to_dict())


# -- static dashboard ---------------------------------------------------------
if _WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_WEB_DIR), html=True), name="web")
