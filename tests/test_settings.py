from pathlib import Path

from cogniaudit.settings import load_settings


def test_load_settings_defaults(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("COGNIAUDIT_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("COGNIAUDIT_AUDIT_MODEL", raising=False)

    s = load_settings(project_root=tmp_path)
    assert s.gemini_api_key is None
    assert s.embedding_model == "text-embedding-004"
    assert s.audit_model == "gemini-1.5-flash"

