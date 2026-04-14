from cogniaudit.audit import parse_post_state
from cogniaudit.models import AuditStatus


def test_parse_post_state_strict_json() -> None:
    text = (
        '{'
        '"status":"ok",'
        '"shift_reason":"r",'
        '"new_perspective":"p",'
        '"evidence_anchor":["a","b"]'
        '}'
    )
    ps = parse_post_state(text)
    assert ps is not None
    assert ps.status == AuditStatus.ok
    assert ps.evidence_anchor == ["a", "b"]


def test_parse_post_state_markdown_wrapped() -> None:
    text = "```json\n" + (
        '{'
        '"status":"no_meaningful_shift",'
        '"shift_reason":"",'
        '"new_perspective":"",'
        '"evidence_anchor":"一句话"'
        '}'
    ) + "\n```"
    ps = parse_post_state(text)
    assert ps is not None
    assert ps.status == AuditStatus.no_meaningful_shift
    assert ps.evidence_anchor == ["一句话"]


def test_parse_post_state_rejects_non_json() -> None:
    assert parse_post_state("hello") is None

