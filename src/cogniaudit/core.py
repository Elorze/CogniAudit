from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .audit import MicroAuditor, build_audit_prompt
from .drift import SignalState
from .gemini_client import ChatClient, EmbeddingClient
from .models import AuditStatus, ChatMessage, PostState


@dataclass
class CogniAuditEngine:
    embedding_client: EmbeddingClient
    audit_client: ChatClient
    k: int = 3
    delta: float = 0.02

    signal: SignalState = field(init=False)
    auditor: MicroAuditor = field(init=False)

    # stateful fields
    primary_context: str = ""

    def __post_init__(self) -> None:
        self.signal = SignalState(k=self.k, delta=self.delta)
        self.auditor = MicroAuditor(client=self.audit_client)

    def reset(self) -> None:
        self.signal.reset()
        self.primary_context = ""

    def maybe_audit_on_user_message(
        self,
        *,
        messages: list[ChatMessage],
        user_msg_index: int,
    ) -> Optional[PostState]:
        """
        Called after a new user message is appended to `messages`.

        - Computes embedding for that user message
        - Updates ADWIN using d_t stream
        - If drift detected at this index -> run micro audit
        """
        user_msg = messages[user_msg_index]
        if user_msg.role != "user":
            raise ValueError("user_msg_index must point to a user message")

        if len(user_msg.content.strip()) < 10:
            return None

        if user_msg.user_index is None:
            raise ValueError("user messages must carry `user_index` for drift mapping")

        vec = self.embedding_client.embed_text(user_msg.content)
        out = self.signal.ingest_user_vector(vec)
        if not out["drift_detected"]:
            return None

        t_drift = out["user_index"]
        if t_drift != user_msg.user_index:
            # Drift event must correspond to the triggering user turn (Final Spec).
            raise RuntimeError("Internal drift index mismatch; this should never happen.")

        evidence: list[ChatMessage] = []
        start_u = max(0, t_drift - 2)
        end_u = t_drift
        for ui in range(start_u, end_u + 1):
            # find message with this user ordinal
            um = next((m for m in messages if m.role == "user" and m.user_index == ui), None)
            if um is None:
                continue
            evidence.append(um)
            mi = messages.index(um)
            if mi + 1 < len(messages) and messages[mi + 1].role == "assistant":
                evidence.append(messages[mi + 1])

        if not self.primary_context:
            # cold start: summarize first 3 user messages as primary context
            first3_users = [m.content for m in messages if m.role == "user"][:3]
            self.primary_context = "；".join([t.strip() for t in first3_users if t.strip()])[:300]

        prompt = build_audit_prompt(primary_context=self.primary_context, evidence_messages=evidence)
        post = self.auditor.audit(prompt)

        if post.status == AuditStatus.ok:
            self.primary_context = post.new_perspective

        return post

