from cogniaudit.gemini_client import FakeGeminiClient


def test_fake_embed_is_deterministic() -> None:
    c = FakeGeminiClient()
    assert c.embed_text("hello") == c.embed_text("hello")
    assert c.embed_text("hello") != c.embed_text("world")


def test_fake_generate_text_is_jsonish() -> None:
    c = FakeGeminiClient()
    out = c.generate_text("prompt")
    assert out.strip().startswith("{")
    assert '"status"' in out

