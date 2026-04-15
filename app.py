from __future__ import annotations

import html as html_lib
import os
import sys
import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from cogniaudit.core import CogniAuditEngine
from cogniaudit.gemini_client import FakeGeminiClient, GeminiClient
from cogniaudit.models import ChatMessage
from cogniaudit.settings import load_settings


# ── CSS ──────────────────────────────────────────────────────────────────────

_CSS = """
<style>
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stAppViewContainer"] { background: #fafaf8; }
[data-testid="stSidebar"] {
    background: #f4f4f2;
    border-right: 1px solid #e8e8e5;
}
[data-testid="stChatMessage"] { display: none !important; }

.cog-wordmark {
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #16a34a;
    margin: 0 0 0.1rem 0;
}
.cog-tagline {
    font-size: 0.68rem;
    color: #aaa;
    letter-spacing: 0.05em;
    margin-bottom: 1.6rem;
}

.chat-wrap { max-width: 700px; margin: 0 auto; }

.chat-row {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    margin: 6px 0;
}
.user-row   { flex-direction: row-reverse; }

.av {
    width: 32px;
    height: 32px;
    min-width: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
    flex-shrink: 0;
    line-height: 1;
}
.av-user { background: #dcfce7; color: #15803d; }
.av-bot  { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; font-size: 16px; }

.bubble {
    max-width: 72%;
    padding: 10px 14px;
    font-size: 0.88rem;
    line-height: 1.72;
    color: #1a1a1a;
    word-break: break-word;
}
.user-bubble {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 14px 4px 14px 14px;
}
.bot-bubble {
    background: #ffffff;
    border: 1px solid #e8e8e5;
    border-radius: 4px 14px 14px 14px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.path-header {
    font-size: 0.72rem;
    font-weight: 600;
    color: #16a34a;
    letter-spacing: 0.08em;
    margin: 2rem 0 0.8rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #e8e8e5;
}
.path-card {
    background: #ffffff;
    border: 1px solid #e8e8e5;
    border-left: 3px solid #22c55e;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.path-idx  { font-size: 0.62rem; color: #22c55e; letter-spacing: 0.1em; margin-bottom: 0.35rem; font-weight: 600; }
.path-why  { font-size: 0.78rem; color: #888; line-height: 1.55; margin-bottom: 0.5rem; }
.path-view { font-size: 0.88rem; color: #1a1a1a; line-height: 1.65; margin-bottom: 0.5rem; }
.path-quote {
    font-family: monospace;
    font-size: 0.73rem;
    color: #888;
    background: #f9fafb;
    border-left: 2px solid #d1fae5;
    padding: 0.35rem 0.65rem;
    margin-top: 0.4rem;
    border-radius: 0 4px 4px 0;
    line-height: 1.5;
}

[data-testid="stButton"] > button {
    border-radius: 6px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    transition: all 0.12s !important;
    border: 1px solid #bbf7d0 !important;
    background: #f0fdf4 !important;
    color: #15803d !important;
}
[data-testid="stButton"] > button:hover {
    background: #dcfce7 !important;
    border-color: #86efac !important;
}
[data-testid="stButton"] > button[kind="primary"] {
    background: #22c55e !important;
    color: #fff !important;
    border-color: #22c55e !important;
}

[data-testid="stChatInput"] > div {
    background: #fff !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: 10px !important;
}

.sidebar-section {
    font-size: 0.65rem;
    font-weight: 600;
    color: #bbb;
    letter-spacing: 0.1em;
    margin-bottom: 0.6rem;
}
</style>
"""


def _esc(text: str) -> str:
    return html_lib.escape(text).replace("\n", "<br>")


def _user_bubble(content: str) -> str:
    return (
        f'<div class="chat-row user-row">'
        f'<div class="av av-user">我</div>'
        f'<div class="bubble user-bubble">{_esc(content)}</div>'
        f"</div>"
    )


def _bot_bubble(content: str) -> str:
    return (
        f'<div class="chat-row">'
        f'<div class="av av-bot">◈</div>'
        f'<div class="bubble bot-bubble">{_esc(content)}</div>'
        f"</div>"
    )


def _stream_bot(placeholder: st.delta_generator.DeltaGenerator, content: str, delay: float = 0.014) -> None:
    displayed = ""
    step = 3
    for i, ch in enumerate(content):
        displayed += ch
        if i % step == 0 or i == len(content) - 1:
            placeholder.markdown(
                f'<div class="chat-row">'
                f'<div class="av av-bot">◈</div>'
                f'<div class="bubble bot-bubble">{_esc(displayed)}|</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
        time.sleep(delay)
    placeholder.markdown(_bot_bubble(content), unsafe_allow_html=True)


def _scroll_to_bottom() -> None:
    components.html(
        """
        <script>
        function go() {
          try {
            const roots = [window.parent, window.parent && window.parent.parent].filter(Boolean);
            for (const w of roots) {
              try {
                const doc = w.document;
                const sel = ['section.main', '[data-testid="stAppViewContainer"]', '.main'];
                for (const s of sel) {
                  const el = doc.querySelector(s);
                  if (el && el.scrollHeight > el.clientHeight) {
                    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
                    return;
                  }
                }
                const se = doc.scrollingElement || doc.documentElement;
                if (se) w.scrollTo({ top: se.scrollHeight, behavior: 'smooth' });
              } catch (e) {}
            }
          } catch (e) {}
        }
        setTimeout(go, 80);
        setTimeout(go, 350);
        </script>
        """,
        height=0,
        width=0,
    )


def _path_cards(audit_history: list[dict]) -> None:
    st.markdown(
        '<div class="path-header">── 认知路径图谱 ──────────────────────</div>',
        unsafe_allow_html=True,
    )
    for i, post in enumerate(audit_history, start=1):
        reason = post.get("shift_reason", "")
        perspective = post.get("new_perspective", "")
        quotes_html = "".join(
            f'<div class="path-quote">❝ {_esc(a)}</div>'
            for a in (post.get("evidence_anchor") or [])
        )
        st.markdown(
            f'<div class="path-card">'
            f'<div class="path-idx">SHIFT · #{i:02d}</div>'
            f'<div class="path-why">→ {_esc(reason)}</div>'
            f'<div class="path-view">{_esc(perspective)}</div>'
            f"{quotes_html}"
            f"</div>",
            unsafe_allow_html=True,
        )


def _get_engine() -> CogniAuditEngine:
    settings = load_settings()
    use_fake = os.getenv("COGNIAUDIT_USE_FAKE", "").lower() in {"1", "true", "yes"}
    if use_fake or not settings.gemini_api_key:
        client: FakeGeminiClient | GeminiClient = FakeGeminiClient()
    else:
        client = GeminiClient(
            api_key=settings.gemini_api_key,
            embedding_model=settings.embedding_model,
            chat_model=settings.audit_model,
        )
    return CogniAuditEngine(embedding_client=client, audit_client=client)


def _init_state() -> None:
    defaults: dict = {
        "messages": [],
        "next_user_index": 0,
        "audit_history": [],
        "engine": _get_engine(),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _reset() -> None:
    st.session_state.messages = []
    st.session_state.audit_history = []
    st.session_state.next_user_index = 0
    st.session_state.engine.reset()


def _render_ui() -> None:
    for m in st.session_state.messages:
        if m.role == "user":
            st.markdown(f'<div class="chat-wrap">{_user_bubble(m.content)}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-wrap">{_bot_bubble(m.content)}</div>', unsafe_allow_html=True)

    if st.session_state.audit_history:
        _path_cards(st.session_state.audit_history)

    prompt = st.chat_input("输入你的想法…")
    if not prompt:
        return

    ui = int(st.session_state.next_user_index)
    st.session_state.next_user_index = ui + 1
    user_msg = ChatMessage(role="user", content=prompt, user_index=ui)
    st.session_state.messages.append(user_msg)
    st.markdown(f'<div class="chat-wrap">{_user_bubble(prompt)}</div>', unsafe_allow_html=True)

    engine: CogniAuditEngine = st.session_state.engine
    settings = load_settings()
    use_fake = os.getenv("COGNIAUDIT_USE_FAKE", "").lower() in {"1", "true", "yes"}

    if use_fake or not settings.gemini_api_key:
        assistant_text = "（Fake 模式）已收到。"
    else:
        assistant_text = engine.auditor.client.generate_text(
            "你是一个简洁友好的助手，请简要回应用户：\n" + prompt,
            temperature=0.7,
        )

    assistant_msg = ChatMessage(role="assistant", content=assistant_text)
    st.session_state.messages.append(assistant_msg)
    placeholder = st.empty()
    _stream_bot(placeholder, assistant_text)

    post = engine.maybe_audit_on_user_message(
        messages=st.session_state.messages,
        user_msg_index=len(st.session_state.messages) - 2,
    )
    if post is not None and post.status.value in {"ok", "processing_error"}:
        st.session_state.audit_history.append(post.model_dump())
        st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="CogniAudit",
        page_icon="◈",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.markdown(_CSS, unsafe_allow_html=True)
    _init_state()

    with st.sidebar:
        st.markdown('<div class="sidebar-section">CONTROLS</div>', unsafe_allow_html=True)
        if st.button("↺  Reset", use_container_width=True):
            _reset()
            st.rerun()

    st.markdown('<div class="cog-wordmark">◈ CogniAudit</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="cog-tagline">认知漂移监测 · ADWIN 算法 · 非侵入式</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.messages:
        st.caption("在下方输入框开始对话；漂移触发后会在此汇总认知路径节点。")

    _render_ui()

    if st.session_state.messages:
        _scroll_to_bottom()


if __name__ == "__main__":
    main()
