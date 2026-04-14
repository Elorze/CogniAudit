from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from cogniaudit.core import CogniAuditEngine
from cogniaudit.demo_offline import build_offline_demo_bundle
from cogniaudit.gemini_client import FakeGeminiClient, GeminiClient
from cogniaudit.models import ChatMessage
from cogniaudit.settings import load_settings


def _get_engine() -> CogniAuditEngine:
    settings = load_settings()
    use_fake = os.getenv("COGNIAUDIT_USE_FAKE", "").lower() in {"1", "true", "yes"}

    if use_fake or not settings.gemini_api_key:
        embed = FakeGeminiClient()
        audit = FakeGeminiClient()
    else:
        embed = GeminiClient(
            api_key=settings.gemini_api_key,
            embedding_model=settings.embedding_model,
            chat_model=settings.audit_model,
        )
        audit = embed

    return CogniAuditEngine(embedding_client=embed, audit_client=audit)


def _init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages: list[ChatMessage] = []
    if "next_user_index" not in st.session_state:
        st.session_state.next_user_index = 0
    if "audit_history" not in st.session_state:
        st.session_state.audit_history = []
    if "offline_demo" not in st.session_state:
        st.session_state.offline_demo = False
    if "engine" not in st.session_state:
        st.session_state.engine = _get_engine()


def _apply_offline_bundle() -> None:
    b = build_offline_demo_bundle()
    st.session_state.messages = b.messages
    st.session_state.next_user_index = b.next_user_index
    st.session_state.audit_history = b.audit_history
    st.session_state.offline_demo = True
    st.session_state.engine.reset()


def _maybe_autoload_demo_on_first_run() -> None:
    if st.session_state.get("_demo_autoload_done"):
        return
    q = st.query_params.get("demo")
    env_on = os.getenv("COGNIAUDIT_AUTOLOAD_DEMO", "").lower() in {"1", "true", "yes"}
    if env_on or q == "1":
        _apply_offline_bundle()
    st.session_state._demo_autoload_done = True


def main() -> None:
    st.set_page_config(page_title="CogniAudit Demo", layout="centered")
    _init_state()
    _maybe_autoload_demo_on_first_run()

    st.title("CogniAudit Demo")
    st.caption("Streamlit + Gemini + ADWIN（静默监测 / 漂移触发微审计 / 线性认知路径）")

    if st.session_state.offline_demo:
        st.success(
            "当前为 **离线演示剧本**（侧栏可查看预置认知路径）。"
            "继续输入将按普通模式走监测逻辑，与剧本无关；录屏建议先 **Reset** 或新开无痕窗口。"
        )

    with st.sidebar:
        st.subheader("控制台")
        st.caption(
            "**路演/录屏推荐**：使用「一键加载离线剧本」——零 API、确定性亮灯。"
            " URL 追加 `?demo=1` 或设置环境变量 `COGNIAUDIT_AUTOLOAD_DEMO=1` 可在打开页面时自动加载。"
        )
        if st.button("一键加载离线演示剧本（零 API）", type="secondary"):
            _apply_offline_bundle()
            st.rerun()

        if st.button("归零 Reset", type="primary"):
            st.session_state.messages = []
            st.session_state.audit_history = []
            st.session_state.next_user_index = 0
            st.session_state.offline_demo = False
            st.session_state.engine.reset()
            st.rerun()

        st.divider()
        st.subheader("认知路径（Audit History）")
        if st.session_state.audit_history:
            for i, post in enumerate(st.session_state.audit_history, start=1):
                st.markdown(f"**#{i}** `{post['status']}`")
                if post.get("shift_reason"):
                    st.write("诱因：", post["shift_reason"])
                if post.get("new_perspective"):
                    st.write("新立场：", post["new_perspective"])
                ea = post.get("evidence_anchor") or []
                if ea:
                    st.write("证据：")
                    for q in ea:
                        st.code(q)
                st.divider()
        else:
            st.info("暂无漂移记录。可加载离线剧本，或继续对话并由后台监测。")

    for m in st.session_state.messages:
        with st.chat_message(m.role):
            st.write(m.content)

    prompt = st.chat_input("输入你的想法…")
    if not prompt:
        return

    # user message
    ui = int(st.session_state.next_user_index)
    st.session_state.next_user_index = ui + 1

    user_msg = ChatMessage(role="user", content=prompt, user_index=ui)
    st.session_state.messages.append(user_msg)
    with st.chat_message("user"):
        st.write(prompt)

    # assistant response (for demo, use audit model as chat model too)
    engine: CogniAuditEngine = st.session_state.engine
    settings = load_settings()
    if os.getenv("COGNIAUDIT_USE_FAKE", "").lower() in {"1", "true", "yes"} or not settings.gemini_api_key:
        assistant_text = "（Fake 模式）我收到了。"
    else:
        # very simple assistant prompt; demo only
        assistant_text = engine.auditor.client.generate_text(
            "你是一个友好的助手。请简洁回应用户：\n" + prompt,
            temperature=0.7,
        )

    assistant_msg = ChatMessage(role="assistant", content=assistant_text)
    st.session_state.messages.append(assistant_msg)
    with st.chat_message("assistant"):
        st.write(assistant_text)

    # silent drift monitoring + micro-audit
    post = engine.maybe_audit_on_user_message(
        messages=st.session_state.messages,
        user_msg_index=len(st.session_state.messages) - 2,
    )
    if post is not None and post.status.value in {"ok", "processing_error"}:
        st.session_state.audit_history.append(post.model_dump())


if __name__ == "__main__":
    main()

