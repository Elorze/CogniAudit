from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    gemini_api_key: Optional[str]
    embedding_model: str
    audit_model: str


def load_settings(project_root: Optional[Path] = None) -> Settings:
    """
    Load settings from environment variables.

    Notes:
    - We intentionally only read from env (optionally loaded from `.env`).
    - Never print or log API keys.
    """
    if project_root is None:
        # cogniaudit/src/cogniaudit/settings.py -> cogniaudit/
        project_root = Path(__file__).resolve().parents[2]

    load_dotenv(project_root / ".env", override=False)

    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        embedding_model=os.getenv("COGNIAUDIT_EMBEDDING_MODEL", "text-embedding-004"),
        audit_model=os.getenv("COGNIAUDIT_AUDIT_MODEL", "gemini-1.5-flash"),
    )

