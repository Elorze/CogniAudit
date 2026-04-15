from __future__ import annotations

import html as html_lib
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from cogniaudit.core import CogniAuditEngine
from cogniaudit.demo_offline import build_novel_demo_bundle, build_offline_demo_bundle
from cogniaudit.gemini_client import FakeGeminiClient, GeminiClient
from cogniaudit.models import ChatMessage
from cogniaudit.settings import load_settings


# ── CSS ──────────────────────────────────────────────────────────────────────

_CSS = """
<style>
/* ── chrome ───────────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stAppViewContainer"] { background: #fafaf8; }
[data-testid="stSidebar"] {
    background: #f4f4f2;
    border-right: 1px solid #e8e8e5;
}

/* ── hide default Streamlit chat bubbles we replace with custom HTML ─── */
[data-testid="stChatMessage"] { display: none !important; }

/* ── title ────────────────────────────────────── */
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

/* ── chat layout ──────────────────────────────── */
.chat-wrap { max-width: 700px; margin: 0 auto; }

.chat-row {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    margin: 6px 0;
}
.user-row   { flex-direction: row-reverse; }

/* avatars */
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

/* bubbles */
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

/* ── round pill ───────────────────────────────── */
.round-pill {
    display: inline-block;
    padding: 2px 10px;
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 12px;
    font-size: 0.65rem;
    color: #16a34a;
    letter-spacing: 0.06em;
    margin-bottom: 12px;
}

/* ── cognitive path ───────────────────────────── */
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

/* ── buttons ─────────────────────────────────── */
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
/* primary stays clearly distinct */
[data-testid="stButton"] > button[kind="primary"] {
    background: #22c55e !important;
    color: #fff !important;
    border-color: #22c55e !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #16a34a !important;
    border-color: #16a34a !important;
}

/* ── chat input ──────────────────────────────── */
[data-testid="stChatInput"] > div {
    background: #fff !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: 10px !important;
}

/* ── sidebar ─────────────────────────────────── */
.sidebar-section {
    font-size: 0.65rem;
    font-weight: 600;
    color: #bbb;
    letter-spacing: 0.1em;
    margin-bottom: 0.5rem;
}
</style>
"""


# ── helpers ───────────────────────────────────────────────────────────────────

def _esc(text: str) -> str:
    """Escape HTML special chars and convert newlines to <br>."""
    return html_lib.escape(text).replace("\n", "<br>")


def _user_bubble(content: str) -> str:
    return (
        f'<div class="chat-row user-row">'
        f'<div class="av av-user">我</div>'
        f'<div class="bubble user-bubble">{_esc(content)}</div>'
        f'</div>'
    )


def _bot_bubble(content: str) -> str:
    return (
        f'<div class="chat-row">'
        f'<div class="av av-bot">◈</div>'
        f'<div class="bubble bot-bubble">{_esc(content)}</div>'
        f'</div>'
    )


def _stream_bot(placeholder: st.delta_generator.DeltaGenerator, content: str, delay: float = 0.014) -> None:
    """Stream content into a custom-styled assistant bubble, chunk by chunk."""
    displayed = ""
    step = 3  # chars per UI update
    for i, ch in enumerate(content):
        displayed += ch
        if i % step == 0 or i == len(content) - 1:
            placeholder.markdown(
                f'<div class="chat-row">'
                f'<div class="av av-bot">◈</div>'
                f'<div class="bubble bot-bubble">{_esc(displayed)}|</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        time.sleep(delay)
    # Final without cursor
    placeholder.markdown(_bot_bubble(content), unsafe_allow_html=True)


def _scroll_to_bottom() -> None:
    """尽量像微信一样滚到页面底部（Streamlit 主滚动区）。"""
    components.html(
        """
        <script>
        function go() {
          try {
            const roots = [window.parent, window.parent && window.parent.parent].filter(Boolean);
            for (const w of roots) {
              try {
                const doc = w.document;
                const sel = [
                  'section.main',
                  '[data-testid="stAppViewContainer"]',
                  '.main',
                ];
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


def _path_cards(audit_history: list[dict], animated: bool = False) -> None:
    st.markdown('<div class="path-header">── 认知路径图谱 ──────────────────────</div>', unsafe_allow_html=True)
    for i, post in enumerate(audit_history, start=1):
        if animated:
            time.sleep(0.3)
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
            f'{quotes_html}'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── engine ────────────────────────────────────────────────────────────────────

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


# ── state ─────────────────────────────────────────────────────────────────────

# 离线剧本：每隔多少秒多展示一轮对话（录屏用，可用环境变量 COGNIAUDIT_DEMO_TICK 覆盖）
def _demo_tick_seconds() -> float:
    raw = os.getenv("COGNIAUDIT_DEMO_TICK", "1.35")
    try:
        return max(0.4, float(raw))
    except ValueError:
        return 1.35


_OFFLINE_DEMO_INTERVAL = timedelta(seconds=_demo_tick_seconds())


def _init_state() -> None:
    defaults: dict = {
        "messages": [],
        "next_user_index": 0,
        "audit_history": [],
        "offline_demo": False,
        "engine": _get_engine(),
        "demo_bundle_msgs": [],
        "demo_total": 0,
        "demo_line_step": 1,
        "demo_autoplay_path_done": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _load_demo(builder_fn) -> None:
    b = builder_fn()
    st.session_state.demo_bundle_msgs = b.messages
    st.session_state.demo_total = b.next_user_index
    st.session_state.demo_line_step = 1
    st.session_state.demo_autoplay_path_done = False
    st.session_state.audit_history = b.audit_history
    st.session_state.messages = []
    st.session_state.next_user_index = 0
    st.session_state.offline_demo = True
    st.session_state.engine.reset()


def _maybe_autoload() -> None:
    if st.session_state.get("_autoload_done"):
        return
    q = st.query_params.get("demo")
    env_on = os.getenv("COGNIAUDIT_AUTOLOAD_DEMO", "").lower() in {"1", "true", "yes"}
    if env_on or q == "1":
        _load_demo(build_novel_demo_bundle)
    elif q == "orig":
        _load_demo(build_offline_demo_bundle)
    st.session_state._autoload_done = True


def _reset() -> None:
    st.session_state.update({
        "messages": [],
        "audit_history": [],
        "demo_bundle_msgs": [],
        "demo_total": 0,
        "demo_line_step": 1,
        "demo_autoplay_path_done": False,
        "offline_demo": False,
        "next_user_index": 0,
    })
    st.session_state.engine.reset()


# ── 离线剧本：定时自动推进（无需点击「下一步」）──────────────────────────────

@st.fragment(run_every=_OFFLINE_DEMO_INTERVAL)
def _offline_demo_autoplay() -> None:
    """定时增加一条气泡：先用户、再助手，像微信一条条出现；结束后展示认知路径。"""
    if not st.session_state.get("offline_demo"):
        return

    bundle = st.session_state.demo_bundle_msgs
    total_pairs = st.session_state.demo_total
    if not bundle or total_pairs <= 0:
        return

    max_lines = 2 * total_pairs
    ls = int(st.session_state.get("demo_line_step", 1))
    ls = max(1, min(ls, max_lines))

    path_done = bool(st.session_state.get("demo_autoplay_path_done"))

    if path_done:
        visible = max_lines
        label = "演示已结束"
    else:
        visible = ls
        label = f"消息 {visible} / {max_lines} 条 · 自动播放中"

    st.markdown(f'<div class="round-pill">{label}</div>', unsafe_allow_html=True)

    for idx in range(visible):
        pair_i = idx // 2
        u = bundle[pair_i * 2]
        a = bundle[pair_i * 2 + 1]
        if idx % 2 == 0:
            st.markdown(f'<div class="chat-wrap">{_user_bubble(u.content)}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-wrap">{_bot_bubble(a.content)}</div>', unsafe_allow_html=True)

    if not path_done:
        if ls < max_lines:
            st.session_state.demo_line_step = ls + 1
        else:
            st.session_state.demo_autoplay_path_done = True

    if st.session_state.get("demo_autoplay_path_done") and st.session_state.audit_history:
        _path_cards(st.session_state.audit_history, animated=False)

    _scroll_to_bottom()


# ── live renderer ─────────────────────────────────────────────────────────────

def _render_live() -> None:
    for m in st.session_state.messages:
        if m.role == "user":
            st.markdown(f'<div class="chat-wrap">{_user_bubble(m.content)}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-wrap">{_bot_bubble(m.content)}</div>', unsafe_allow_html=True)

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


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="CogniAudit",
        page_icon="◈",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.markdown(_CSS, unsafe_allow_html=True)
    _init_state()
    _maybe_autoload()

    # ── sidebar ───────────────────────────────────────────────
    with st.sidebar:
        st.markdown('<div class="sidebar-section">DEMO</div>', unsafe_allow_html=True)
        if st.button("📖  小说剧本（推荐）", use_container_width=True):
            _load_demo(build_novel_demo_bundle)
            st.rerun()
        if st.button("◈  原版剧本", use_container_width=True):
            _load_demo(build_offline_demo_bundle)
            st.rerun()
        st.write("")
        st.markdown('<div class="sidebar-section">CONTROLS</div>', unsafe_allow_html=True)
        if st.button("↺  Reset", use_container_width=True):
            _reset()
            st.rerun()

    # ── header ────────────────────────────────────────────────
    st.markdown('<div class="cog-wordmark">◈ CogniAudit</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="cog-tagline">认知漂移监测 · ADWIN 算法 · 非侵入式</div>',
        unsafe_allow_html=True,
    )

    # ── empty state ───────────────────────────────────────────
    if not st.session_state.offline_demo and not st.session_state.messages:
        st.write("")
        _, c2, _ = st.columns([1, 2, 1])
        with c2:
            st.markdown(
                '<div style="text-align:center;color:#ccc;font-size:0.72rem;'
                'letter-spacing:0.06em;margin-bottom:1rem;">开始一段对话</div>',
                unsafe_allow_html=True,
            )
            if st.button("📖  加载小说演示（零 API）", use_container_width=True):
                _load_demo(build_novel_demo_bundle)
                st.rerun()
            st.write("")
            if st.button("◈  加载原版演示", use_container_width=True):
                _load_demo(build_offline_demo_bundle)
                st.rerun()

    # ── content ───────────────────────────────────────────────
    if st.session_state.offline_demo:
        _offline_demo_autoplay()
    else:
        _render_live()

    # 自由对话模式：新消息后滚到底（离线演示在 fragment 内已滚动）
    if not st.session_state.offline_demo and st.session_state.messages:
        _scroll_to_bottom()


if __name__ == "__main__":
    main()
