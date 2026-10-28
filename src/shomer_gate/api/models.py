"""Request and response schemas for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_in: int
    subject: str


class CheckRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20_000)
    # When false, the decision is returned but not written to the ledger.
    record: bool = True


class HealthResponse(BaseModel):
    status: str
    version: str
    ledger_length: int
    ledger_ok: bool
