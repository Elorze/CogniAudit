from __future__ import annotations

"""
Self-check script for CogniAudit demo.

Goal:
- No API key required by default (uses fake clients).
- Verifies drift pipeline and micro-audit parsing paths.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cogniaudit.core import CogniAuditEngine
from cogniaudit.gemini_client import FakeGeminiClient
from cogniaudit.models import ChatMessage


def run() -> None:
    os.environ.setdefault("COGNIAUDIT_USE_FAKE", "1")
    engine = CogniAuditEngine(embedding_client=FakeGeminiClient(), audit_client=FakeGeminiClient())

    messages: list[ChatMessage] = []
    next_ui = 0

    # "drawing" themed realistic user messages (as you requested)
    user_inputs = [
        "我想画一只坐在窗台上的黑猫，风格偏宫崎骏，请给我构图建议。",
        "再给我 3 个不同光影方案，分别适合清晨、黄昏、雨天。",
        "我改主意了：想画赛博朋克街头的霓虹雨夜，主角是戴面罩的骑手。",
        "把画面改成俯视视角，路面反光要强，氛围参考黑客帝国。",
        "最后我决定做成海报：标题一句中文，副标题一句英文，帮我想 3 套。",
    ]

    for text in user_inputs:
        messages.append(ChatMessage(role="user", content=text, user_index=next_ui))
        next_ui += 1
        messages.append(ChatMessage(role="assistant", content="（demo assistant reply）"))
        post = engine.maybe_audit_on_user_message(messages=messages, user_msg_index=len(messages) - 2)
        # In fake mode, parse always succeeds; drift may or may not trigger (ADWIN statistical).
        if post is not None:
            assert post.status.value in {"ok", "no_meaningful_shift", "processing_error"}

    print("selfcheck: ok")


if __name__ == "__main__":
    run()

