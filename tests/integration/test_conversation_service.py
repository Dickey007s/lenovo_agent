from packages.authorization import AuthorizationService, PermitKeyPair
from packages.contracts import ActionCandidate
from packages.tool_gateway import ToolGateway
from services.api.app.application.conversation_models import ArtifactDraft, ConversationPlan
from services.api.app.application.conversations import (
    ConversationService,
    _strip_repeated_risk,
)
from services.api.app.application.runs import RunService
from services.api.app.application.storage import InMemoryWorkspaceStore


class FakeAgent:
    async def parse(self, message: str) -> ActionCandidate:
        raise AssertionError("conversation test should use plan")

    async def plan(self, message: str, history: list[dict], trusted_context: dict) -> ConversationPlan:
        assert history[-1]["content"] == message
        assert trusted_context["notice"]
        assert trusted_context["active_workspace"]["view"] == "expense"
        assert trusted_context["active_workspace"]["artifact"]["content"]["case_id"] == "BX-LOCAL"
        return ConversationPlan(
            assistant_response="已完成报销单核查。",
            focus_view="expense",
            action=ActionCandidate(
                action_type="expense_inspect",
                capability="expense.read",
                target_scope="internal_member",
                resources=["BX-0412"],
                data_classes=["financial"],
                state_change_type="read_only",
                reversibility="high",
            ),
            artifact=ArtifactDraft(
                kind="expense",
                title="BX-0412 核查结果",
                content={"status": "核查完成"},
            ),
        )

    async def answer_general(
        self, message: str, history: list[dict], current_datetime: str
    ) -> str:
        assert history[-1]["content"] == message
        assert current_datetime
        return "今天是 2026 年 7 月 13 日。"


async def test_conversation_streams_model_content_and_artifact() -> None:
    keys = PermitKeyPair.generate()
    run_service = RunService(
        parser=FakeAgent(),  # type: ignore[arg-type]
        policy_version="test-v1",
        authorization_service=AuthorizationService(keys),
        tool_gateway=ToolGateway(keys.public_key, "test-v1"),
    )
    service = ConversationService(FakeAgent(), run_service)  # type: ignore[arg-type]
    thread = await service.create_thread("user_1")
    events = [
        event
        async for event in service.stream_message(
            thread.thread_id,
            "核查报销单 BX-0412",
            "user_1",
            active_view="expense",
            workspace_context={"case_id": "BX-LOCAL"},
        )
    ]

    event_types = [event["type"] for event in events]
    assert "artifact.stream.started" in event_types
    assert "artifact.delta" in event_types
    assert "artifact.updated" in event_types
    assert "assistant.delta" in event_types
    assert events[-1] == {"type": "ui.focus", "view": "expense"}
    restored = await service.get_thread(thread.thread_id, "user_1")
    assert restored.messages[-1].content.startswith("已完成报销单核查。")
    assert "风险等级：L1" in restored.messages[-1].content
    assert restored.artifacts[-1].kind == "expense"


async def test_workspace_is_seeded_and_persists_independently_of_threads() -> None:
    keys = PermitKeyPair.generate()
    run_service = RunService(
        parser=FakeAgent(),  # type: ignore[arg-type]
        policy_version="test-v1",
        authorization_service=AuthorizationService(keys),
        tool_gateway=ToolGateway(keys.public_key, "test-v1"),
    )
    store = InMemoryWorkspaceStore()
    first = ConversationService(FakeAgent(), run_service, store)  # type: ignore[arg-type]
    workspace = await first.get_workspace("user_1")

    assert {artifact.kind for artifact in workspace} == {
        "mail", "document", "quote", "tasks", "calendar", "expense", "crm"
    }
    mail = await first.save_workspace_artifact(
        "mail", {"subject": "持久保存的主题"}, "user_1"
    )

    second = ConversationService(FakeAgent(), run_service, store)  # type: ignore[arg-type]
    restored = {artifact.kind: artifact for artifact in await second.get_workspace("user_1")}
    assert restored["mail"].artifact_id == mail.artifact_id
    assert restored["mail"].content["subject"] == "持久保存的主题"
    assert restored["mail"].change_history[0]["actor"] == "当前用户"
    assert restored["calendar"].title == "我的日历"
    assert restored["calendar"].content["events"]

    blank = await second.start_new_mail("user_1")
    assert blank.artifact_id != mail.artifact_id
    assert blank.title == "新邮件"
    assert blank.content == {
        "to": [], "cc": [], "subject": "", "body": "", "attachments": []
    }
    assert blank.linked_action_id is None
    third = ConversationService(FakeAgent(), run_service, store)  # type: ignore[arg-type]
    persisted = {item.kind: item for item in await third.get_workspace("user_1")}
    assert persisted["mail"].artifact_id == blank.artifact_id


async def test_general_question_does_not_repeat_previous_office_action() -> None:
    keys = PermitKeyPair.generate()
    agent = FakeAgent()
    service = ConversationService(
        agent,  # type: ignore[arg-type]
        RunService(
            parser=agent,  # type: ignore[arg-type]
            policy_version="test-v1",
            authorization_service=AuthorizationService(keys),
            tool_gateway=ToolGateway(keys.public_key, "test-v1"),
        ),
    )
    thread = await service.create_thread("user_1")
    events = [
        event
        async for event in service.stream_message(
            thread.thread_id, "今天是几号？", "user_1", active_view="mail"
        )
    ]

    assert not any(event["type"] == "action.proposed" for event in events)
    restored = await service.get_thread(thread.thread_id, "user_1")
    assert restored.messages[-1].content == "今天是 2026 年 7 月 13 日。"


def test_final_action_response_removes_repeated_risk_summary() -> None:
    response = (
        "邮件已成功发送至 example@123.com。\n"
        "风险等级：L4。判断依据：收件人为外部客户，邮件涉及报价数据。"
    )

    assert _strip_repeated_risk(response) == "邮件已成功发送至 example@123.com。"
