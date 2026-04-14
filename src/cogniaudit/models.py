from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


Role = Literal["user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str
    user_index: Optional[int] = None


class AuditStatus(str, Enum):
    ok = "ok"
    no_meaningful_shift = "no_meaningful_shift"
    processing_error = "processing_error"


class PostState(BaseModel):
    status: AuditStatus = AuditStatus.ok
    shift_reason: str = Field(default="", max_length=200)
    new_perspective: str = Field(default="", max_length=200)
    evidence_anchor: list[str] = Field(default_factory=list)

