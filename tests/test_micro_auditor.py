from cogniaudit.audit import MicroAuditor
from cogniaudit.gemini_client import ChatClient
from cogniaudit.models import AuditStatus


class FlakyJsonClient(ChatClient):
    def __init__(self) -> None:
        self._n = 0

    def generate_text(self, prompt: str, *, temperature=None) -> str:
        self._n += 1
        if self._n == 1:
            return "not json"
        return (
            "{"
            '"status":"ok",'
            '"shift_reason":"r",'
            '"new_perspective":"p",'
            '"evidence_anchor":["e"]'
            "}"
        )


def test_micro_auditor_retries_then_parses() -> None:
    m = MicroAuditor(client=FlakyJsonClient())
    post = m.audit("prompt")
    assert post.status == AuditStatus.ok
    assert post.new_perspective == "p"


class AlwaysBadClient(ChatClient):
    def generate_text(self, prompt: str, *, temperature=None) -> str:
        return "not json"


def test_micro_auditor_placeholder_on_total_failure() -> None:
    m = MicroAuditor(client=AlwaysBadClient())
    post = m.audit("prompt")
    assert post.status == AuditStatus.processing_error
    assert "解析" in post.new_perspective
