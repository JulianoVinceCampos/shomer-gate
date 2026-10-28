"""Runtime configuration, read from the environment with safe defaults.

A tiny ``.env`` loader is included so the project runs with zero extra
dependencies. Precedence is: real environment variable first, then ``.env``,
then the hard-coded default. The signing key has *no* usable default on
purpose. A throwaway is generated per process if none is set, which keeps the
demo running while making it obvious that production must supply its own.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_LEDGER = _PROJECT_ROOT / "data" / "ledger.jsonl"
_DEFAULT_GROUND_TRUTH = _PROJECT_ROOT / "data" / "ground_truth.json"


def _load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_DOTENV = _load_dotenv(_PROJECT_ROOT / ".env")


def _get(key: str, default: str) -> str:
    return os.environ.get(key) or _DOTENV.get(key) or default


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable view of the process configuration."""

    signing_key: str
    admin_user: str
    admin_password: str
    token_ttl: int
    block_threshold: float
    review_threshold: float
    host: str
    port: int
    ledger_path: Path
    ground_truth_path: Path

    @classmethod
    def from_env(cls) -> Settings:
        signing_key = _get("SHOMER_SIGNING_KEY", "")
        if not signing_key:
            # Ephemeral key: the demo keeps working, production is forced to set one.
            signing_key = secrets.token_urlsafe(48)
        return cls(
            signing_key=signing_key,
            admin_user=_get("SHOMER_ADMIN_USER", "shomer"),
            admin_password=_get("SHOMER_ADMIN_PASSWORD", "emet-2026"),
            token_ttl=int(_get("SHOMER_TOKEN_TTL", "3600")),
            block_threshold=float(_get("SHOMER_BLOCK_THRESHOLD", "7.0")),
            review_threshold=float(_get("SHOMER_REVIEW_THRESHOLD", "3.0")),
            host=_get("SHOMER_HOST", "0.0.0.0"),
            port=int(_get("SHOMER_PORT", "8080")),
            ledger_path=Path(_get("SHOMER_LEDGER_PATH", str(_DEFAULT_LEDGER))),
            ground_truth_path=Path(_get("SHOMER_GROUND_TRUTH", str(_DEFAULT_GROUND_TRUTH))),
        )


def get_settings() -> Settings:
    """Return a freshly-read settings object."""
    return Settings.from_env()
