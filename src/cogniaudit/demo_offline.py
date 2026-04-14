"""
离线演示剧本（零 API、确定性）。

说明：
- 「漂移触发」在演示模式下由剧本中的 user_index 显式指定（导演模式），
  保证录屏/路演时每次在同一轮、同一句话亮灯。
- 认知路径上的文案来自本模块预置的 PostState，不调用大模型。
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import AuditStatus, ChatMessage, PostState


# 在哪些「用户回合」（0-based）触发一次认知审计（亮灯）
DEMO_DRIFT_USER_INDICES = (4, 9)


def _posts() -> tuple[PostState, PostState]:
    return (
        PostState(
            status=AuditStatus.ok,
            shift_reason="话题从「朋友/竞品/投入」转向「我想做什么」：开始把自己的命题说清楚。",
            new_perspective="我不只想围观别人的项目，我要解决自己在长对话里「迷路」的问题。",
            evidence_anchor=[
                "他那个思路确实启发了我。我也想之后做一些跟 Agent 有关的东西。",
            ],
        ),
        PostState(
            status=AuditStatus.ok,
            shift_reason="从「对话结束后分析」升级到「流式可量化审计」：要把转折点从感觉变成机制。",
            new_perspective="转折点不能只靠一段 prompt；要用语义漂移（如 ADWIN）做工程化监测与复盘。",
            evidence_anchor=[
                "光用自然语言定义转折点会太空洞，我需要有工程上的抓手与创新点。",
            ],
        ),
    )


@dataclass(frozen=True)
class OfflineDemoBundle:
    messages: list[ChatMessage]
    next_user_index: int
    audit_history: list[dict]
    drift_user_indices: tuple[int, ...]


def build_offline_demo_bundle() -> OfflineDemoBundle:
    """
    构造完整对话 + 与 drift 对齐的 audit_history（每条对应一次亮灯）。
    """
    p1, p2 = _posts()

    turns: list[tuple[str, str]] = [
        (
            "我朋友在前端 CLI 和模型之间做了一层中间协议，用来解决多 Agent 协作时的路径依赖：用户还能改路径，不是死板一条线。我想知道这算不算「AI 记忆产品」，竞品大概有哪些？",
            "更像「多 Agent 的上下文/状态管理中间层」。记忆是其中一块；主流 Mem/RAG/Graph 路线各有取舍，你朋友的核心差异是把「路径控制权」交回给用户。",
        ),
        (
            "他说想转 AI 产品经理，开了 Claude Pro 和 Cursor Pro，每月大概 40 刀。竞争激烈，这种投入到底图什么？",
            "作品型路线和创业路线评判标准不同：关键是他能否讲清「为谁解决什么」以及做过哪些取舍，而不只是把协议跑通。",
        ),
        (
            "群里有人提 OpenArena/openarena.to，奖金池、打榜、项目方……我其实没完全看懂。我朋友那种项目能参赛吗？",
            "如果能在 OpenClaw/Agent 生态里讲清楚创新点、开源可运行、材料完整，就有机会被看见；但要以官方规则与可核验信息为准。",
        ),
        (
            "我顺着往下想：长期和 AI 协作时，我经常不知道自己从什么时候开始被「带节奏」，想法怎么变的过程也丢了。我不想只做另一个聊天壳。",
            "你把问题从「工具层」推进到「关系与过程」：要留住的不是聊天记录，而是你在关系里如何被塑造、又如何主动转向。",
        ),
        (
            "我想做的东西更像：对话结束后（甚至过程中）抓住「想法转变」的瞬间，把它们串成轨迹；不是导出 Claude 的记忆，而是我自己的一层记录。",
            "这就是「模型之外的你的记忆层」：平台侧旁听与沉淀，而不是向模型要 memory。",
        ),
        (
            "有人拿 Poe 类比：都能切换模型。我的区别是什么？",
            "Poe 更像模型聚合；你要的是聚合之外留下「你怎么变了」——轻量、属于你、可迁移。",
        ),
        (
            "但我担心：如果转折点只靠一段 prompt 判定，会很不稳，也很像玄学。我想把它做成可审计的机制。",
            "所以你会自然走向「信号 + 机制」：语言线索、语义偏移、统计检验，而不是一次性让模型拍脑袋。",
        ),
        (
            "我查资料时看到信念追踪、漂移检测这类方向。MVP 时间很紧，我想先跑通最小闭环：监测—标记—复盘。",
            "最小闭环先证明「能稳定抓到转折」比「界面华丽」更重要；路径展示是 Demo 的说服力来源。",
        ),
        (
            "所以我把 CogniAudit 的核心压到两件事：流式语义监测（例如 ADWIN）+ 认知路径复盘。我想让评审一眼看到「不是套壳」。",
            "这就是把创新点从叙事落到可执行规格：监测是引擎，路径是叙事。",
        ),
        (
            "最后帮我收个尾：如果只用一句话解释 CogniAudit，它到底是什么？",
            "一句话：**别在 AI 的回声里丢了自己**——系统记录你与模型协作中的认知偏移与转折，让过程可回看、可归因。",
        ),
    ]

    messages: list[ChatMessage] = []
    audit_history: list[dict] = []

    drift_i = 0
    for ui, (u, a) in enumerate(turns):
        messages.append(ChatMessage(role="user", content=u, user_index=ui))
        messages.append(ChatMessage(role="assistant", content=a))
        if ui in DEMO_DRIFT_USER_INDICES:
            post = (p1, p2)[drift_i]
            drift_i += 1
            audit_history.append(post.model_dump())

    return OfflineDemoBundle(
        messages=messages,
        next_user_index=len(turns),
        audit_history=audit_history,
        drift_user_indices=DEMO_DRIFT_USER_INDICES,
    )
