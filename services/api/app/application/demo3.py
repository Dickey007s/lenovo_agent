from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from packages.contracts import ActionCandidate


class Demo3Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    title: str
    description: str
    expected_status: str
    demonstrates: list[str]
    candidate: ActionCandidate
    trusted_context: dict


SCENARIOS = {
    "self": Demo3Scenario(
        scenario_id="self",
        title="发送给本人",
        description="受管设备上把普通材料发送给自己，允许进入最终预览。",
        expected_status="READY_TO_AUTHORIZE",
        demonstrates=["低风险", "最小审批", "一次性 Permit"],
        candidate=ActionCandidate(
            action_type="send_email",
            capability="email.send",
            target_scope="self",
            recipients=["demo_user@company.local"],
            resources=["meeting_notes.pdf"],
            data_classes=["internal"],
            state_change_type="internal_effect",
            reversibility="high",
        ),
        trusted_context={"device": {"managed": True, "name": "managed_pc"}},
    ),
    "internal": Demo3Scenario(
        scenario_id="internal",
        title="内部成员（非受管设备）",
        description="从非受管设备向内部成员发送材料，发送 capability 被降级为 deny。",
        expected_status="DENIED",
        demonstrates=["设备可信度", "capability 降级", "安全拒绝"],
        candidate=ActionCandidate(
            action_type="send_email",
            capability="email.send",
            target_scope="internal_member",
            recipients=["colleague@company.local"],
            resources=["project_notes.pdf"],
            data_classes=["internal"],
            state_change_type="internal_effect",
            reversibility="medium",
        ),
        trusted_context={"device": {"managed": False, "name": "personal_mobile"}},
    ),
    "external": Demo3Scenario(
        scenario_id="external",
        title="外部客户",
        description="通讯录、附件哈希和 DLP 自动完成，只需要当前用户确认外发。",
        expected_status="WAITING_APPROVAL",
        demonstrates=["系统自动取证", "人工确认", "外发约束"],
        candidate=ActionCandidate(
            action_type="send_email",
            capability="email.send",
            target_scope="external_customer",
            recipients=["client@example.com"],
            resources=["proposal.pdf"],
            data_classes=["customer_data"],
            state_change_type="external_effect",
            reversibility="low",
        ),
        trusted_context={"device": {"managed": True, "name": "managed_pc"}},
    ),
    "pricing": Demo3Scenario(
        scenario_id="pricing",
        title="未经授权价格承诺",
        description="外发报价缺少批准来源和价格权限，必须补证据并由销售经理审批。",
        expected_status="WAITING_EVIDENCE",
        demonstrates=["L4 风险", "选择批准报价", "经理审批", "参数篡改拦截"],
        candidate=ActionCandidate(
            action_type="send_email",
            capability="email.send",
            target_scope="external_customer",
            recipients=["buyer@example.com"],
            resources=["unapproved_quote.pdf"],
            data_classes=["customer_data", "pricing"],
            state_change_type="external_effect",
            reversibility="low",
        ),
        trusted_context={"device": {"managed": True, "name": "managed_pc"}},
    ),
}


def list_scenarios() -> list[Demo3Scenario]:
    return list(SCENARIOS.values())


def get_scenario(scenario_id: str) -> Demo3Scenario:
    try:
        return SCENARIOS[scenario_id]
    except KeyError as exc:
        raise LookupError(scenario_id) from exc
