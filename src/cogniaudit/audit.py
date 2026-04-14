from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from .gemini_client import ChatClient
from .models import AuditStatus, ChatMessage, PostState


JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json_object(text: str) -> Optional[str]:
    m = JSON_RE.search(text)
    if not m:
        return None
    return m.group(0)


def parse_post_state(text: str) -> Optional[PostState]:
    """
    Try to parse PostState from a possibly messy LLM response.
    Strategy:
    - Extract outermost {...}
    - json.loads
    """
    obj = _extract_json_object(text) or text
    try:
        data = json.loads(obj)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    # Normalize evidence_anchor to list[str]
    ea = data.get("evidence_anchor", [])
    if isinstance(ea, str):
        ea = [ea]
    if not isinstance(ea, list):
        ea = []
    ea = [str(x) for x in ea][:2]

    status = data.get("status", "ok")
    if status not in {s.value for s in AuditStatus}:
        status = "ok"

    return PostState(
        status=AuditStatus(status),
        shift_reason=str(data.get("shift_reason", ""))[:200],
        new_perspective=str(data.get("new_perspective", ""))[:200],
        evidence_anchor=ea,
    )


def build_audit_prompt(
    *,
    primary_context: str,
    evidence_messages: list[ChatMessage],
) -> str:
    evidence_lines: list[str] = []
    for m in evidence_messages:
        prefix = "用户" if m.role == "user" else "AI"
        evidence_lines.append(f"{prefix}: {m.content}")

    evidence = "\n".join(evidence_lines)
    return f"""你是 CogniAudit 的微审计员。

主背景（既定立场/状态A）：
{primary_context}

增量证据（漂移窗口）：
{evidence}

任务：
- 对比主背景与增量证据，识别是否发生“有意义的观念转变”。
- 若仅语气变化/无新信息/难以提炼新立场：status 必须为 "no_meaningful_shift"。
- 否则：status 为 "ok"，并填写 shift_reason/new_perspective/evidence_anchor。

输出要求（非常重要）：
- Reply ONLY with valid JSON (no markdown, no extra text).
- evidence_anchor 必须为数组，包含 1-2 句用户原话。

JSON Schema:
{{
  "status": "ok | no_meaningful_shift | processing_error",
  "shift_reason": "≤50字",
  "new_perspective": "≤30字",
  "evidence_anchor": ["..."]
}}
"""


@dataclass
class MicroAuditor:
    client: ChatClient
    model_temperature: float = 0.6

    def audit(self, prompt: str) -> PostState:
        # 1) first try
        text = self.client.generate_text(prompt, temperature=self.model_temperature)
        parsed = parse_post_state(text)
        if parsed is not None:
            return parsed

        # 2) one cold retry
        retry_prompt = prompt + "\nIMPORTANT: Reply ONLY with JSON."
        text = self.client.generate_text(retry_prompt, temperature=0.0)
        parsed = parse_post_state(text)
        if parsed is not None:
            return parsed

        # 3) placeholder
        return PostState(
            status=AuditStatus.processing_error,
            shift_reason="",
            new_perspective="检测到深层思维波动，正在解析中...",
            evidence_anchor=[],
        )

