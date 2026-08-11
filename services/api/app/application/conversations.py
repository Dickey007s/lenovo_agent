from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Any, AsyncIterator
from uuid import uuid4

from packages.contracts import ActionCandidate, ProposedActionSpec, RiskAssessment
from packages.risk_core import assess_risk
from services.api.app.application.conversation_models import (
    ArtifactDraft,
    ChatMessage,
    ConversationPlan,
    ConversationThread,
    SourceReference,
    WorkspaceArtifact,
)
from services.api.app.application.llm import AutoDLActionParser
from services.api.app.application.quote_calculator import (
    QuoteCalculationError,
    merge_quote_workspace_context,
    quote_question_intent,
    render_quote_answer,
)
from services.api.app.application.runs import RunService
from services.api.app.application.storage import InMemoryWorkspaceStore, WorkspaceStore


class ConversationNotFoundError(LookupError):
    pass


class WorkspaceChangedError(RuntimeError):
    pass


class ActionArtifactMismatchError(RuntimeError):
    pass


_EXECUTABLE_SIDE_EFFECT_CAPABILITIES = {
    "email.send",
    "task.create",
    "calendar.invite",
    "crm.opportunity.update",
    "expense.request_evidence",
}

_WORKSPACE_TITLES = {
    "mail": "新邮件",
    "document": "项目 Alpha 会议纪要",
    "quote": "客户 A · 报价工作簿",
    "tasks": "我的任务",
    "calendar": "我的日历",
    "expense": "报销核查工作台",
    "crm": "客户 A · 续约商机",
}

_ROLE_LABELS = {
    "current_user": "当前用户确认",
    "sales_manager": "销售经理审批",
}

_RISK_REASON_LABELS = {
    "EXTERNAL_RECIPIENT": "目标包含企业外部联系人",
    "PUBLIC_SCOPE": "影响范围为公开发布",
    "SENSITIVE_DATA": "内容包含敏感业务数据",
    "PRICING_DATA": "内容涉及报价或定价",
    "LOW_REVERSIBILITY": "执行后不易撤回",
    "ACTION_INFORMATION_MISSING": "动作关键信息仍不完整",
    "CREDENTIAL_EXPOSURE": "存在凭据暴露风险",
    "RESTRICTED_OPERATION": "属于受限操作",
    "RESTRICTED_EXECUTION": "属于受限执行",
}


def _describe_risk(risk: RiskAssessment) -> str:
    reasons = [
        _RISK_REASON_LABELS.get(code, code)
        for code in risk.reason_codes
        if code != "PRICING_DATA" or "SENSITIVE_DATA" not in risk.reason_codes
    ]
    if not reasons:
        reasons = ["仅草稿、只读或当前用户范围内操作，未命中额外风险因子"]
    return f"风险等级：{risk.risk_level}。判断规则：{'；'.join(reasons)}。"


def _workspace_artifact_matches_snapshot(
    artifact: WorkspaceArtifact | None,
    snapshot: dict[str, Any] | None,
) -> bool:
    if snapshot is None:
        return artifact is None
    return artifact is not None and artifact.model_dump(mode="json") == snapshot


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


_EMAIL_ADDRESS_PATTERN = re.compile(
    r"^(?=.{3,254}$)(?!.*\.\.)"
    r"[a-z0-9!#$%&'*+/=?^_`{|}~-]+"
    r"(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@"
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$",
    flags=re.IGNORECASE,
)


def _recipient_scope(values: list[str]) -> tuple[str, bool]:
    internal_domains = {"lenovo.com", "internal.example"}
    external = False
    uncertain = False
    for value in values:
        normalized = value.strip().lower()
        if not normalized:
            continue
        if _EMAIL_ADDRESS_PATTERN.fullmatch(normalized) is None:
            uncertain = True
            continue
        domain = normalized.rsplit("@", maxsplit=1)[1]
        if domain not in internal_domains:
            external = True
    if external or uncertain:
        return "external_customer", uncertain
    return "internal_member", False


def _is_pricing_text(value: str) -> bool:
    return bool(
        re.search(
            r"报价|价格|折扣|金额|¥|￥|\bquote\b|\bpricing\b|\bdiscount\b|\bamount\b|\bQ-\d+",
            value,
            flags=re.IGNORECASE,
        )
    )


def _mail_data_classes(content: dict[str, Any]) -> tuple[list[str], list[str]]:
    message_text = " ".join(
        [str(content.get("subject", "")), str(content.get("body", ""))]
    )
    attachments = _string_list(content.get("attachments"))
    classes = ["customer_data"]
    if _is_pricing_text(message_text):
        classes.append("pricing")

    unknown_attachments: list[str] = []
    for attachment in attachments:
        # Attachment classification is deliberately independent from the mail
        # body. A pricing subject must never make an opaque file look classified.
        if _is_pricing_text(attachment):
            if "pricing" not in classes:
                classes.append("pricing")
        else:
            unknown_attachments.append(attachment)
    return classes, unknown_attachments


def _bind_action_to_artifact(
    action: ActionCandidate,
    artifact: WorkspaceArtifact,
) -> ActionCandidate:
    requested_parameters = dict(action.parameters)
    parameters: dict[str, Any] = {}
    recipients: list[str] = []
    resources: list[str] = []
    action_type = action.action_type
    target_scope = action.target_scope
    data_classes = list(action.data_classes)
    state_change_type = action.state_change_type
    reversibility = action.reversibility
    missing_slots: list[str] = []
    content = artifact.content

    if action.capability == "email.send":
        if artifact.kind != "mail":
            raise ActionArtifactMismatchError
        recipients = [*_string_list(content.get("to")), *_string_list(content.get("cc"))]
        subject = str(content.get("subject", "")).strip()
        body = str(content.get("body", "")).strip()
        if not recipients or not subject or not body:
            raise ActionArtifactMismatchError
        attachments = _string_list(content.get("attachments"))
        parameters = {"subject": subject, "body": body}
        resources = attachments
        action_type = "send_email"
        target_scope, uncertain_recipient = _recipient_scope(recipients)
        data_classes, unknown_attachments = _mail_data_classes(content)
        state_change_type = "external_effect"
        reversibility = "low"
        if uncertain_recipient:
            missing_slots.append("recipient_identity")
        missing_slots.extend(
            f"attachment_data_class:{attachment}"
            for attachment in unknown_attachments
        )
    elif action.capability == "calendar.invite":
        if artifact.kind != "calendar":
            raise ActionArtifactMismatchError
        events = content.get("events")
        if not isinstance(events, list):
            raise ActionArtifactMismatchError
        event_id = str(requested_parameters.get("event_id", ""))
        title = str(requested_parameters.get("title", ""))
        matches = [
            event
            for event in events if isinstance(event, dict)
            and (
                (event_id and str(event.get("id", "")) == event_id)
                or (title and str(event.get("title", "")) == title)
            )
        ]
        if len(matches) != 1:
            raise ActionArtifactMismatchError
        event = matches[0]
        recipients = _string_list(event.get("attendees"))
        parameters = {
            "title": event.get("title"),
            "start_at": f"{event.get('date')}T{event.get('start')}:00",
            "end_at": f"{event.get('date')}T{event.get('end')}:00",
            "location": event.get("location"),
            "agenda": event.get("agenda"),
        }
        recipient_scope, uncertain_recipient = _recipient_scope(recipients)
        external = recipient_scope == "external_customer"
        action_type = "create_calendar_invite"
        target_scope = "external_customer" if external else "internal_team"
        data_classes = ["customer_data" if external else "internal"]
        state_change_type = "external_effect" if external else "internal_system_write"
        reversibility = "medium"
        if not recipients:
            missing_slots.append("attendees")
        elif uncertain_recipient:
            missing_slots.append("recipient_identity")
    elif action.capability == "task.create":
        if artifact.kind != "tasks":
            raise ActionArtifactMismatchError
        tasks = content.get("tasks")
        if not isinstance(tasks, list):
            raise ActionArtifactMismatchError
        task_id = str(requested_parameters.get("task_id", ""))
        title = str(requested_parameters.get("title", ""))
        matches = [
            task
            for task in tasks if isinstance(task, dict)
            and (
                (task_id and str(task.get("id", "")) == task_id)
                or (title and str(task.get("title", "")) == title)
            )
        ]
        if len(matches) != 1:
            raise ActionArtifactMismatchError
        task = matches[0]
        parameters = {
            "title": task.get("title"),
            "assignee": task.get("assignee"),
            "due_at": task.get("due_at"),
        }
        action_type = "create_internal_task"
        target_scope = "internal_member"
        data_classes = ["internal"]
        state_change_type = "internal_system_write"
        reversibility = "high"
        if not task.get("assignee"):
            missing_slots.append("assignee")
    elif action.capability == "crm.opportunity.update":
        if artifact.kind != "crm":
            raise ActionArtifactMismatchError
        parameters = {
            "opportunity_id": content.get("opportunity_id"),
            "before": content.get("before"),
            "after": content.get("suggested_stage"),
        }
        action_type = "update_crm_stage"
        target_scope = "internal_team"
        data_classes = ["customer_data"]
        state_change_type = "internal_system_write"
        reversibility = "medium"
    elif action.capability == "expense.request_evidence":
        if artifact.kind != "expense":
            raise ActionArtifactMismatchError
        parameters = {
            "case_id": content.get("case_id"),
            "owner": content.get("owner"),
            "missing_items": content.get("anomalies", []),
        }
        action_type = "expense_request_evidence"
        target_scope = "internal_member"
        data_classes = ["financial"]
        state_change_type = "internal_system_write"
        reversibility = "medium"
    else:
        raise ActionArtifactMismatchError

    parameters.update(
        {
            "artifact_id": artifact.artifact_id,
            "artifact_revision": artifact.revision,
            "artifact_content": artifact.content,
        }
    )
    return action.model_copy(
        update={
            "action_type": action_type,
            "recipients": recipients,
            "resources": resources,
            "target_scope": target_scope,
            "data_classes": data_classes,
            "state_change_type": state_change_type,
            "reversibility": reversibility,
            "source_refs": [],
            "missing_slots": missing_slots,
            "parameters": parameters,
        }
    )


def _is_side_effect_action(action: ActionCandidate | None) -> bool:
    return bool(
        action and action.capability in _EXECUTABLE_SIDE_EFFECT_CAPABILITIES
    )


def _describe_candidate_risk(action: ActionCandidate) -> str:
    spec = ProposedActionSpec(
        **action.model_dump(),
        trace_id="preview",
        action_id="preview",
        actor_id="current_user",
        payload_digest="preview",
        idempotency_key="preview",
    )
    return _describe_risk(assess_risk(spec))


def _strip_repeated_risk(text: str) -> str:
    """Risk is already shown before confirmation; final replies report outcome only."""
    cleaned = re.sub(
        r"(?:风险等级|风险判断|判断规则|判断依据)[^。\n]*。?",
        "",
        text,
    )
    return "\n".join(line.strip() for line in cleaned.splitlines() if line.strip())


def _quote_needs_review(content: dict[str, Any]) -> bool:
    approval = content.get("approval")
    return isinstance(approval, dict) and approval.get("status") == "needs_review"


def _describe_action_gate(run: Any) -> str:
    capability = run.action.capability
    status = run.control_plan.status
    risk = _describe_risk(run.risk)
    if status == "WAITING_EVIDENCE":
        requirements = "、".join(run.control_plan.missing_requirements)
        return f"{risk}\n执行前需要取得 `{capability}` 权限，并补充可信依据：{requirements}。"
    if status == "WAITING_APPROVAL":
        roles = "、".join(
            _ROLE_LABELS.get(role, role)
            for role in run.control_plan.required_approvals
        )
        return f"{risk}\n执行前需要取得 `{capability}` 权限，并完成：{roles}。请在下方确认卡片中处理。"
    if status == "READY_TO_AUTHORIZE":
        return f"{risk}\n`{capability}` 的前置条件已经满足，仍需要你确认最终执行。"
    if status == "DENIED":
        return f"{risk}\n当前策略不允许 Agent 使用 `{capability}`，我不会继续执行。"
    return f"{risk}\n我已按策略检查 `{capability}` 的执行条件。"


def _default_sources(kind: str) -> list[SourceReference]:
    catalog = {
        "mail": [
            SourceReference(
                source_id="mail:customer-a/latest",
                label="客户 A 最新来信",
                system="企业邮箱",
                excerpt="客户关注交付时间、报价有效期与技术支持范围。",
                permission="当前用户可读",
                updated_at="刚刚",
            ),
            SourceReference(
                source_id="crm:customer-a/profile",
                label="客户 A 商机档案",
                system="CRM",
                excerpt="A 类客户，当前阶段：方案沟通。",
                permission="销售团队可读",
                updated_at="10 分钟前",
            ),
            SourceReference(
                source_id="crm:quote/991:v3",
                label="客户 991 · 报价 V3",
                system="CRM 报价库",
                excerpt="已批准版本，有效期至 2026-07-31。",
                permission="销售可读 · 经理批准",
                updated_at="昨天 17:40",
            ),
        ],
        "document": [
            SourceReference(
                source_id="kb:meeting/alpha-0713",
                label="项目 Alpha 会议纪要",
                system="内部知识库",
                excerpt="记录交付节点、技术方案待办与客户风险。",
                permission="项目组可读",
                updated_at="今天 14:20",
            ),
            SourceReference(
                source_id="kb:template/weekly-report",
                label="项目周报模板",
                system="内部知识库",
                excerpt="进展、风险、下周计划三段式结构。",
                permission="全员可读",
                updated_at="2026-07-01",
            ),
        ],
        "quote": [
            SourceReference(
                source_id="crm:quote/991:v3",
                label="客户 A · 报价 V3（演示数据）",
                system="演示 CRM 报价库",
                excerpt="演示基线版本已批准，有效期至 2026-07-31；修改后需要重新复核。",
                permission="销售可读 · 基线经经理批准",
                updated_at="昨天 17:40",
            ),
            SourceReference(
                source_id="kb:pricing/floor-2026",
                label="2026 报价与折扣政策（演示数据）",
                system="演示制度库",
                excerpt="标准服务最低折后比例为 88%（8.8 折）。",
                permission="销售团队可读",
                updated_at="2026-07-01",
            ),
        ],
        "tasks": [
            SourceReference(
                source_id="project:alpha/board",
                label="项目 Alpha 任务板",
                system="项目系统",
                excerpt="3 项即将到期，1 项等待用户确认。",
                permission="项目组可读",
                updated_at="2 分钟前",
            )
        ],
        "calendar": [
            SourceReference(
                source_id="calendar:freebusy/team",
                label="与会人空闲时间",
                system="企业日历",
                excerpt="明天 10:00-10:45 所有内部与会人均可用。",
                permission="仅读忙闲状态",
                updated_at="刚刚",
            )
        ],
        "expense": [
            SourceReference(
                source_id="oa:expense/BX-0412",
                label="报销单 BX-0412",
                system="OA 报销",
                excerpt="差旅报销 12,860 元，包含 4 张发票。",
                permission="财务与申请人可读",
                updated_at="今天 09:18",
            ),
            SourceReference(
                source_id="kb:expense/policy-2026",
                label="2026 差旅报销制度",
                system="内部制度库",
                excerpt="同一发票代码和号码不得重复报销。",
                permission="全员可读",
                updated_at="2026-01-01",
            ),
        ],
        "crm": [
            SourceReference(
                source_id="crm:opportunity/A-2026",
                label="客户 A · 2026 续约商机",
                system="CRM",
                excerpt="当前阶段：方案沟通；预计金额：86 万元。",
                permission="销售团队可读",
                updated_at="今天 11:05",
            )
        ],
    }
    return catalog.get(kind, [])


def _default_content(kind: str) -> dict[str, Any]:
    defaults: dict[str, dict[str, Any]] = {
        "mail": {
            "to": [],
            "cc": [],
            "subject": "",
            "body": "",
            "attachments": [],
        },
        "document": {
            "document_type": "会议纪要",
            "sections": [
                {"heading": "关键结论", "body": "项目交付节点保持不变，技术方案需在本周内完成补充。"},
                {"heading": "风险与待核实", "body": "客户测试环境资源尚未最终确认，可能影响联调日期。"},
                {"heading": "下一步", "body": "王工补充技术方案；李经理确认客户评审时间。"},
            ],
        },
        "quote": {
            "quote_id": "Q-991-V3",
            "customer": "客户 A",
            "currency": "CNY",
            "valid_until": "2026-07-31",
            "approved_floor": 0.88,
            "items": [
                {"name": "企业办公 Agent 平台许可", "qty": 100, "unit_price": 1680, "discount": 0.9, "subtotal": 151200},
                {"name": "实施与知识库集成", "qty": 1, "unit_price": 68000, "discount": 1, "subtotal": 68000},
                {"name": "年度技术支持", "qty": 1, "unit_price": 36000, "discount": 0.95, "subtotal": 34200},
            ],
            "total": 253400,
            "approval": {"status": "approved", "approver": "销售经理 B", "approved_at": "2026-07-12 17:40"},
        },
        "tasks": {
            "tasks": [
                {"id": "T-101", "title": "回复客户 A 方案问题", "source": "邮件", "priority": "高", "status": "待确认", "reason": "SLA 剩余 45 分钟"},
                {"id": "T-102", "title": "核查报销单 BX-0412", "source": "OA", "priority": "高", "status": "异常挂起", "reason": "疑似重复发票"},
                {"id": "T-103", "title": "生成项目 Alpha 风险页", "source": "项目", "priority": "中", "status": "准备中", "reason": "明日 10:00 汇报"},
            ]
        },
        "calendar": {
            "month": "2026-07",
            "selected_date": "2026-07-13",
            "events": [
                {
                    "id": "CAL-0713-01",
                    "title": "项目 Alpha 晨会",
                    "date": "2026-07-13",
                    "start": "09:30",
                    "end": "10:00",
                    "attendees": ["项目组"],
                    "location": "Teams 会议",
                    "agenda": "同步本周交付与阻塞事项",
                },
                {
                    "id": "CAL-0714-01",
                    "title": "客户 A 方案评审",
                    "date": "2026-07-14",
                    "start": "10:00",
                    "end": "10:45",
                    "attendees": ["李经理", "王工", "客户 A"],
                    "location": "Teams 会议",
                    "agenda": "方案变更、交付节点与报价有效期",
                },
                {
                    "id": "CAL-0714-02",
                    "title": "报价内部复核",
                    "date": "2026-07-14",
                    "start": "15:30",
                    "end": "16:00",
                    "attendees": ["销售经理 B", "李经理"],
                    "location": "3F-06 会议室",
                    "agenda": "复核折扣底线与附件版本",
                },
                {
                    "id": "CAL-0718-01",
                    "title": "周度项目回顾",
                    "date": "2026-07-18",
                    "start": "14:00",
                    "end": "15:00",
                    "attendees": ["项目组"],
                    "location": "Teams 会议",
                    "agenda": "进展、风险和下周计划",
                },
                {
                    "id": "CAL-0722-01",
                    "title": "客户交付检查点",
                    "date": "2026-07-22",
                    "start": "11:00",
                    "end": "11:30",
                    "attendees": ["交付组", "客户 A"],
                    "location": "线上会议",
                    "agenda": "确认联调准备状态",
                },
            ],
        },
        "expense": {
            "case_id": "BX-0412",
            "owner": "陈晶",
            "amount": 12860,
            "status": "待核查",
            "invoices": [
                {"number": "INV-88421", "vendor": "某酒店", "amount": 4280, "result": "通过"},
                {"number": "INV-88422", "vendor": "某航空", "amount": 6380, "result": "疑似重复"},
                {"number": "INV-88422", "vendor": "某航空", "amount": 2200, "result": "疑似重复"},
            ],
            "anomalies": ["发票 INV-88422 号码重复", "第 3 张发票缺少行程单"],
        },
        "crm": {
            "customer": "客户 A",
            "opportunity_id": "OPP-A-2026",
            "amount": 860000,
            "before": "方案沟通",
            "suggested_stage": "合同谈判",
            "next_step": "完成方案评审并确认商务条款",
        },
    }
    return defaults.get(kind, {})


def _merge_artifact(draft: ArtifactDraft) -> WorkspaceArtifact:
    defaults = _default_content(draft.kind)
    # Records that pretend to come from CRM/OA must stay connector-owned. Text
    # drafts remain model-authored but are grounded by the same connector context.
    content = (
        draft.content | defaults
        if draft.kind in {"quote", "tasks", "expense", "crm"}
        else defaults | draft.content
    )
    return WorkspaceArtifact(
        artifact_id=f"artifact_{uuid4().hex}",
        kind=draft.kind,
        title=draft.title,
        content=content,
        sources=_default_sources(draft.kind),
        change_history=[
            {
                "actor": "Office Agent",
                "action": "根据对话更新工作区",
                "time": datetime.now(UTC).isoformat(),
            }
        ],
    )


def _seed_workspace_artifact(kind: str) -> WorkspaceArtifact:
    return WorkspaceArtifact(
        artifact_id=f"workspace_{kind}_{uuid4().hex}",
        kind=kind,  # type: ignore[arg-type]
        title=_WORKSPACE_TITLES[kind],
        content=_default_content(kind),
        sources=_default_sources(kind),
        change_history=[
            {
                "actor": "系统",
                "action": "初始化办公工作区",
                "time": datetime.now(UTC).isoformat(),
            }
        ],
    )


def _retrieve_trusted_context(text: str) -> dict[str, Any]:
    normalized = text.lower()
    rules = [
        (("报销", "发票", "bx-"), "expense"),
        (("报价", "折扣", "价格"), "quote"),
        (("今天重点", "任务驾驶舱", "待办"), "tasks"),
        (("会议纪要", "周报", "文档"), "document"),
        (("日历", "会议邀请", "空闲时间"), "calendar"),
        (("crm", "商机", "客户跟进"), "crm"),
        (("邮件", "回复客户", "发给客户"), "mail"),
    ]
    kinds = [kind for keywords, kind in rules if any(keyword in normalized for keyword in keywords)]
    if "quote" in kinds and "mail" in kinds:
        kinds = ["quote", "mail"]
    return {
        "records": {kind: _default_content(kind) for kind in kinds},
        "sources": {
            kind: [source.model_dump(mode="json") for source in _default_sources(kind)]
            for kind in kinds
        },
        "notice": "以上为 Demo 专用模拟企业数据，不是真实企业记录。",
        "current_datetime": datetime.now().astimezone().isoformat(),
    }


def _is_general_question(text: str) -> bool:
    """Route public-knowledge questions away from the structured office planner."""
    normalized = text.strip().lower()
    enterprise_specific_terms = (
        "当前工作区", "数据库中", "内部库", "公司里", "我们的", "本公司", "客户",
        "报价单", "报销单", "发票", "商机", "审批", "权限", "刚刚这个操作",
        "上一个操作", "风险等级",
    )
    imperative_terms = (
        "请帮", "帮我", "替我", "给我", "发给", "发送", "创建", "新增", "添加",
        "删除", "更新", "修改", "保存到", "安排到", "导入", "起草一", "写一封",
    )
    question_terms = (
        "什么", "为什么", "怎么", "如何", "谁", "哪里", "几号", "几点",
        "多少", "区别", "介绍", "解释", "是否", "能否", "吗", "？", "?",
    )
    return (
        len(normalized) <= 180
        and any(term in normalized for term in question_terms)
        and not any(term in normalized for term in enterprise_specific_terms)
        and not any(term in normalized for term in imperative_terms)
    )


async def _stream_artifact_update(
    previous: WorkspaceArtifact | None,
    artifact: WorkspaceArtifact,
) -> AsyncIterator[dict[str, Any]]:
    """Emit meaningful workspace patches so Agent edits are visible, not a hard refresh."""
    previous_content = previous.content if previous else {}
    changed = {
        key: value
        for key, value in artifact.content.items()
        if previous_content.get(key) != value
    }
    if not changed:
        yield {"type": "artifact.updated", "artifact": artifact.model_dump(mode="json")}
        return

    initial_content = dict(previous_content)
    for key, target in changed.items():
        if isinstance(target, str):
            old = str(previous_content.get(key, ""))
            prefix_length = 0
            for old_char, new_char in zip(old, target):
                if old_char != new_char:
                    break
                prefix_length += 1
            initial_content[key] = target[:prefix_length]
        elif isinstance(target, list):
            initial_content[key] = []

    initial = artifact.model_copy(update={"content": initial_content})
    yield {
        "type": "artifact.stream.started",
        "artifact": initial.model_dump(mode="json"),
        "changed_fields": list(changed),
    }

    for key, target in changed.items():
        if isinstance(target, str):
            start = len(str(initial_content.get(key, "")))
            remaining = max(1, len(target) - start)
            chunk_size = max(2, min(10, remaining // 55 or 2))
            for end in range(start + chunk_size, len(target) + chunk_size, chunk_size):
                yield {
                    "type": "artifact.delta",
                    "kind": artifact.kind,
                    "artifact_id": artifact.artifact_id,
                    "patch": {key: target[: min(end, len(target))]},
                }
                await asyncio.sleep(0.016)
        elif isinstance(target, list):
            for index in range(len(target)):
                yield {
                    "type": "artifact.delta",
                    "kind": artifact.kind,
                    "artifact_id": artifact.artifact_id,
                    "patch": {key: target[: index + 1]},
                }
                await asyncio.sleep(0.08)
        else:
            yield {
                "type": "artifact.delta",
                "kind": artifact.kind,
                "artifact_id": artifact.artifact_id,
                "patch": {key: target},
            }
            await asyncio.sleep(0.05)

    yield {"type": "artifact.updated", "artifact": artifact.model_dump(mode="json")}


class ConversationService:
    def __init__(
        self,
        agent: AutoDLActionParser,
        run_service: RunService,
        workspace_store: WorkspaceStore | None = None,
    ) -> None:
        self.agent = agent
        self.run_service = run_service
        self.workspace_store = workspace_store or InMemoryWorkspaceStore()
        self._threads: dict[str, ConversationThread] = {}
        self._thread_locks: dict[str, asyncio.Lock] = {}
        self._workspace_locks: dict[str, asyncio.Lock] = {}
        self._workspace_cache: dict[str, dict[str, WorkspaceArtifact]] = {}
        self._continued_runs: dict[tuple[str, str], ChatMessage] = {}
        self._lock = asyncio.Lock()

    async def get_workspace(self, user_id: str) -> list[WorkspaceArtifact]:
        cached = self._workspace_cache.get(user_id)
        if cached is None:
            async with self._lock:
                cached = self._workspace_cache.get(user_id)
                if cached is None:
                    stored = await self.workspace_store.load(user_id)
                    cached = {
                        artifact.kind: artifact
                        for item in stored
                        if (artifact := WorkspaceArtifact.model_validate(item))
                    }
                    for kind in _WORKSPACE_TITLES:
                        if kind not in cached:
                            artifact = _seed_workspace_artifact(kind)
                            cached[kind] = artifact
                            await self.workspace_store.save(
                                user_id, artifact.model_dump(mode="json")
                            )
                    calendar = cached.get("calendar")
                    if calendar and not isinstance(
                        calendar.content.get("events"), list
                    ):
                        calendar = calendar.model_copy(
                            update={
                                "title": _WORKSPACE_TITLES["calendar"],
                                "content": _default_content("calendar"),
                                "revision": calendar.revision + 1,
                                "updated_at": datetime.now(UTC),
                            }
                        )
                        cached["calendar"] = calendar
                        await self.workspace_store.save(
                            user_id, calendar.model_dump(mode="json")
                        )
                    quote = cached.get("quote")
                    if quote and quote.content.get("quote_id") == "Q-991-V3":
                        demo_sources = _default_sources("quote")
                        if quote.sources != demo_sources:
                            quote = quote.model_copy(
                                update={
                                    "sources": demo_sources,
                                    "revision": quote.revision + 1,
                                    "updated_at": datetime.now(UTC),
                                }
                            )
                            cached["quote"] = quote
                            await self.workspace_store.save(
                                user_id, quote.model_dump(mode="json")
                            )
                    self._workspace_cache[user_id] = cached
        return list(cached.values())

    async def save_workspace_artifact(
        self,
        kind: str,
        content: dict[str, Any],
        user_id: str,
        *,
        expected_artifact_id: str,
        expected_revision: int,
        title: str | None = None,
        actor: str = "当前用户",
        action: str = "保存工作区内容",
    ) -> WorkspaceArtifact:
        await self.get_workspace(user_id)
        lock = self._workspace_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            artifact = self._workspace_cache[user_id].get(kind)
            if artifact is None:
                raise ConversationNotFoundError(kind)
            if (
                artifact.artifact_id != expected_artifact_id
                or artifact.revision != expected_revision
            ):
                raise WorkspaceChangedError
            next_content = artifact.content | content
            requires_recheck = bool(artifact.linked_action_id)
            if kind == "quote":
                next_content = merge_quote_workspace_context(
                    artifact.content, next_content
                )
                requires_recheck = requires_recheck or _quote_needs_review(
                    next_content
                )
            updated = artifact.model_copy(
                update={
                    "title": title or artifact.title,
                    "content": next_content,
                    "requires_recheck": requires_recheck,
                    "revision": artifact.revision + 1,
                    "change_history": [
                        {
                            "actor": actor,
                            "action": action,
                            "time": datetime.now(UTC).isoformat(),
                        },
                        *artifact.change_history[:19],
                    ],
                    "updated_at": datetime.now(UTC),
                }
            )
            if artifact.linked_action_id:
                await self.run_service.invalidate_action(
                    artifact.linked_action_id, user_id
                )
            await self.workspace_store.save(
                user_id, updated.model_dump(mode="json")
            )
            self._workspace_cache[user_id][kind] = updated
            return updated

    async def start_new_mail(self, user_id: str) -> WorkspaceArtifact:
        await self.get_workspace(user_id)
        lock = self._workspace_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            previous = self._workspace_cache[user_id].get("mail")
            if previous is None:
                raise ConversationNotFoundError("mail")

            if previous.linked_action_id:
                try:
                    await self.run_service.invalidate_action(
                        previous.linked_action_id, user_id
                    )
                except LookupError:
                    # A persisted workspace can outlive an in-memory demo run.
                    pass

            mail = WorkspaceArtifact(
                artifact_id=f"workspace_mail_{uuid4().hex}",
                kind="mail",
                title=_WORKSPACE_TITLES["mail"],
                content=_default_content("mail"),
                sources=_default_sources("mail"),
                change_history=[
                    {
                        "actor": "当前用户",
                        "action": "新建空白邮件",
                        "time": datetime.now(UTC).isoformat(),
                    },
                    *previous.change_history[:19],
                ],
            )
            await self.workspace_store.save(user_id, mail.model_dump(mode="json"))
            self._workspace_cache[user_id]["mail"] = mail
            return mail

    async def create_thread(self, user_id: str) -> ConversationThread:
        thread = ConversationThread(thread_id=f"chat_{uuid4().hex}", user_id=user_id)
        async with self._lock:
            self._threads[thread.thread_id] = thread
        return thread

    async def get_thread(self, thread_id: str, user_id: str) -> ConversationThread:
        thread = self._threads.get(thread_id)
        if thread is None or thread.user_id != user_id:
            raise ConversationNotFoundError(thread_id)
        return thread

    async def _stream_assistant_reply(
        self, thread: ConversationThread, response_text: str
    ) -> AsyncIterator[dict[str, Any]]:
        assistant_message = ChatMessage(
            message_id=f"msg_{uuid4().hex}",
            role="assistant",
            content="",
            status="streaming",
        )
        yield {
            "type": "message.started",
            "message": assistant_message.model_dump(mode="json"),
        }
        for start in range(0, len(response_text), 2):
            yield {
                "type": "assistant.delta",
                "message_id": assistant_message.message_id,
                "delta": response_text[start : start + 2],
            }
            await asyncio.sleep(0.012)
        completed = assistant_message.model_copy(
            update={"content": response_text, "status": "completed"}
        )
        self._threads[thread.thread_id] = thread.model_copy(
            update={
                "messages": [*thread.messages, completed],
                "updated_at": datetime.now(UTC),
            }
        )
        yield {
            "type": "message.completed",
            "message": completed.model_dump(mode="json"),
        }

    async def update_artifact(
        self, thread_id: str, artifact_id: str, content: dict[str, Any], user_id: str
    ) -> WorkspaceArtifact:
        lock = self._thread_locks.setdefault(thread_id, asyncio.Lock())
        async with lock:
            return await self._update_artifact_unlocked(
                thread_id, artifact_id, content, user_id
            )

    async def _update_artifact_unlocked(
        self, thread_id: str, artifact_id: str, content: dict[str, Any], user_id: str
    ) -> WorkspaceArtifact:
        thread = await self.get_thread(thread_id, user_id)
        artifact = next((item for item in thread.artifacts if item.artifact_id == artifact_id), None)
        if artifact is None:
            raise ConversationNotFoundError(artifact_id)
        next_content = artifact.content | content
        if artifact.kind == "quote":
            next_content = merge_quote_workspace_context(
                artifact.content, next_content
            )
        updated = artifact.model_copy(
            update={
                "content": next_content,
                "requires_recheck": (
                    bool(artifact.linked_action_id)
                    or _quote_needs_review(next_content)
                ),
                "revision": artifact.revision + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        artifacts = [updated if item.artifact_id == artifact_id else item for item in thread.artifacts]
        self._threads[thread_id] = thread.model_copy(
            update={"artifacts": artifacts, "updated_at": datetime.now(UTC)}
        )
        if updated.linked_action_id:
            await self.run_service.invalidate_action(updated.linked_action_id, user_id)
        return updated

    async def stream_message(
        self,
        thread_id: str,
        text: str,
        user_id: str,
        active_view: str | None = None,
        workspace_context: dict[str, Any] | None = None,
        expected_artifact_id: str | None = None,
        expected_revision: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        lock = self._thread_locks.setdefault(thread_id, asyncio.Lock())
        async with lock:
            try:
                async for event in self._stream_message_unlocked(
                    thread_id,
                    text,
                    user_id,
                    active_view=active_view,
                    workspace_context=workspace_context,
                    expected_artifact_id=expected_artifact_id,
                    expected_revision=expected_revision,
                ):
                    yield event
            except WorkspaceChangedError:
                current = await self.get_thread(thread_id, user_id)
                latest_workspace = {
                    item.kind: item for item in await self.get_workspace(user_id)
                }
                latest_artifact = latest_workspace.get(active_view or "")
                if latest_artifact is not None:
                    yield {
                        "type": "workspace.conflict",
                        "view": active_view,
                        "latest_artifact": latest_artifact.model_dump(mode="json"),
                    }
                response_text = (
                    "处理期间，当前工作区已被另一个操作更新。"
                    "为避免覆盖新内容，我没有生成或执行动作。"
                    "你的当前草稿仍保留在页面中，请选择查看最新版本或在最新版本上重新应用。"
                )
                async for event in self._stream_assistant_reply(
                    current, response_text
                ):
                    yield event
            except ActionArtifactMismatchError:
                current = await self.get_thread(thread_id, user_id)
                response_text = (
                    "动作参数与当前工作区内容不一致，或当前内容还不完整。"
                    "为避免批准一份内容却执行另一份内容，我没有创建动作。"
                    "请先在对应工作区补全并核对目标、标题和正文后重试。"
                )
                async for event in self._stream_assistant_reply(
                    current, response_text
                ):
                    yield event

    async def _stream_message_unlocked(
        self,
        thread_id: str,
        text: str,
        user_id: str,
        active_view: str | None = None,
        workspace_context: dict[str, Any] | None = None,
        expected_artifact_id: str | None = None,
        expected_revision: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        thread = await self.get_thread(thread_id, user_id)
        user_message = ChatMessage(
            message_id=f"msg_{uuid4().hex}", role="user", content=text
        )
        thread = thread.model_copy(
            update={
                "messages": [*thread.messages, user_message],
                "title": text[:24] if thread.title == "新对话" else thread.title,
                "updated_at": datetime.now(UTC),
            }
        )
        self._threads[thread_id] = thread
        yield {"type": "message.created", "message": user_message.model_dump(mode="json")}
        yield {"type": "assistant.status", "status": "planning", "label": "正在理解任务与检索授权上下文"}

        history = [
            {"role": item.role, "content": item.content}
            for item in thread.messages[-12:]
        ]
        trusted_context = _retrieve_trusted_context(text)
        workspace = {item.kind: item for item in await self.get_workspace(user_id)}
        workspace_snapshot = {
            kind: item.model_dump(mode="json") for kind, item in workspace.items()
        }
        active_artifact = workspace.get(active_view or "")
        active_artifact_snapshot = workspace_snapshot.get(active_view or "")
        if workspace_context is not None:
            if active_artifact is None or expected_artifact_id is None or expected_revision is None:
                raise WorkspaceChangedError
            if (
                active_artifact.artifact_id != expected_artifact_id
                or active_artifact.revision != expected_revision
            ):
                raise WorkspaceChangedError
        active_content = (
            workspace_context
            if workspace_context is not None
            else (active_artifact.content if active_artifact else {})
        )
        quote_context_error: QuoteCalculationError | None = None
        if active_view == "quote" and active_artifact is not None:
            try:
                active_content = (
                    active_artifact.content
                    if workspace_context is None
                    else merge_quote_workspace_context(
                        active_artifact.content, workspace_context
                    )
                )
            except QuoteCalculationError as exc:
                active_content = {}
                quote_context_error = exc
        trusted_context["active_workspace"] = {
            "view": active_view,
            "artifact": (
                {
                    "title": active_artifact.title,
                    "content": active_content,
                    "sources": [
                        source.model_dump(mode="json")
                        for source in active_artifact.sources
                    ],
                }
                if active_artifact
                else None
            ),
            "notice": (
                f"当前工作区数据未通过校验：{quote_context_error}"
                if quote_context_error
                else "这是用户当前正在编辑的工作区，可能包含尚未保存的输入。"
            ),
        }

        quote_intent = quote_question_intent(text) if active_view == "quote" else None
        if quote_intent is not None:
            yield {
                "type": "assistant.status",
                "status": "calculating",
                "label": "正在按当前报价表逐行核算",
            }
            try:
                if active_artifact is None:
                    raise QuoteCalculationError("服务端报价工作区不存在")
                if quote_context_error is not None:
                    raise quote_context_error
                response_text = render_quote_answer(active_content, quote_intent)
            except QuoteCalculationError as exc:
                response_text = (
                    f"当前报价无法完成核算：{exc}。"
                    "我没有使用历史对话中的金额，也不会在字段不完整时猜测结果。"
                )
            async for event in self._stream_assistant_reply(thread, response_text):
                yield event
            return

        if quote_context_error is not None and not _is_general_question(text):
            response_text = (
                f"当前报价无法继续处理：{quote_context_error}。"
                "我不会使用历史金额生成、修改或发送报价；请先修正当前工作区中的字段。"
            )
            async for event in self._stream_assistant_reply(thread, response_text):
                yield event
            return

        if _is_general_question(text):
            response_text = await self.agent.answer_general(
                text,
                history,
                trusted_context["current_datetime"],
            )
            async for event in self._stream_assistant_reply(thread, response_text):
                yield event
            return

        plan: ConversationPlan = await self.agent.plan(text, history, trusted_context)
        artifact = None
        previous_artifact = None
        run = None
        action: ActionCandidate | None = plan.action
        if plan.artifact:
            await self.get_workspace(user_id)
            workspace_lock = self._workspace_locks.setdefault(
                user_id, asyncio.Lock()
            )
            async with workspace_lock:
                current_active = self._workspace_cache[user_id].get(
                    active_view or ""
                )
                if active_artifact_snapshot is not None and not _workspace_artifact_matches_snapshot(
                    current_active, active_artifact_snapshot
                ):
                    raise WorkspaceChangedError
                existing = self._workspace_cache[user_id].get(plan.artifact.kind)
                if not _workspace_artifact_matches_snapshot(
                    existing, workspace_snapshot.get(plan.artifact.kind)
                ):
                    raise WorkspaceChangedError
                previous_artifact = existing
                if existing:
                    current_content = (
                        active_content
                        if existing.kind == active_view
                        and workspace_context is not None
                        and quote_context_error is None
                        else existing.content
                    )
                    next_content = current_content | plan.artifact.content
                    if existing.kind == "quote":
                        next_content = merge_quote_workspace_context(
                            existing.content, next_content
                        )
                    artifact = existing.model_copy(
                        update={
                            "title": (
                                existing.title
                                if existing.kind == "quote"
                                else plan.artifact.title or existing.title
                            ),
                            "content": next_content,
                            "sources": (
                                existing.sources
                            ),
                            "requires_recheck": (
                                bool(existing.linked_action_id)
                                or _quote_needs_review(next_content)
                            ),
                            "revision": existing.revision + 1,
                            "change_history": [
                                {
                                    "actor": "Office Agent",
                                    "action": "根据对话编辑工作区",
                                    "time": datetime.now(UTC).isoformat(),
                                },
                                *existing.change_history[:19],
                            ],
                            "updated_at": datetime.now(UTC),
                        }
                    )
                else:
                    artifact = _merge_artifact(plan.artifact).model_copy(
                        update={"sources": _default_sources(plan.artifact.kind)}
                    )

                replaces_linked_action = _is_side_effect_action(action)
                if (
                    previous_artifact is not None
                    and previous_artifact.linked_action_id
                    and (
                        artifact.content != previous_artifact.content
                        or replaces_linked_action
                    )
                ):
                    try:
                        await self.run_service.invalidate_action(
                            previous_artifact.linked_action_id, user_id
                        )
                    except LookupError:
                        pass

                if _is_side_effect_action(action):
                    action = _bind_action_to_artifact(action, artifact)
                    run = await self.run_service.create_from_candidate(
                        action,
                        message=text,
                        user_id=user_id,
                        thread_id=thread_id,
                        trusted_context={
                            "device": {"managed": True, "name": "managed_pc"},
                            "user": {"id": user_id},
                        },
                    )
                    artifact = artifact.model_copy(
                        update={
                            "linked_action_id": run.action.action_id,
                            "linked_run_id": run.run_id,
                        }
                    )

                await self.workspace_store.save(
                    user_id, artifact.model_dump(mode="json")
                )
                self._workspace_cache[user_id][artifact.kind] = artifact
        elif _is_side_effect_action(action):
            if active_artifact is None:
                raise WorkspaceChangedError
            await self.get_workspace(user_id)
            workspace_lock = self._workspace_locks.setdefault(
                user_id, asyncio.Lock()
            )
            async with workspace_lock:
                existing = self._workspace_cache[user_id].get(active_view or "")
                if active_artifact_snapshot is None or not _workspace_artifact_matches_snapshot(
                    existing, active_artifact_snapshot
                ):
                    raise WorkspaceChangedError
                previous_artifact = existing
                next_content = active_content
                if existing.kind == "quote":
                    next_content = merge_quote_workspace_context(
                        existing.content, active_content
                    )
                artifact = existing.model_copy(
                    update={
                        "content": next_content,
                        "requires_recheck": _quote_needs_review(next_content),
                        "revision": existing.revision + 1,
                        "change_history": [
                            {
                                "actor": "Office Agent",
                                "action": "绑定动作前记录当前工作区",
                                "time": datetime.now(UTC).isoformat(),
                            },
                            *existing.change_history[:19],
                        ],
                        "updated_at": datetime.now(UTC),
                    }
                )
                if existing.linked_action_id:
                    try:
                        await self.run_service.invalidate_action(
                            existing.linked_action_id, user_id
                        )
                    except LookupError:
                        pass
                action = _bind_action_to_artifact(action, artifact)
                run = await self.run_service.create_from_candidate(
                    action,
                    message=text,
                    user_id=user_id,
                    thread_id=thread_id,
                    trusted_context={
                        "device": {"managed": True, "name": "managed_pc"},
                        "user": {"id": user_id},
                    },
                )
                artifact = artifact.model_copy(
                    update={
                        "linked_action_id": run.action.action_id,
                        "linked_run_id": run.run_id,
                    }
                )
                await self.workspace_store.save(
                    user_id, artifact.model_dump(mode="json")
                )
                self._workspace_cache[user_id][artifact.kind] = artifact

        if artifact is not None:
            yield {"type": "ui.focus", "view": artifact.kind}
            async for artifact_event in _stream_artifact_update(
                previous_artifact, artifact
            ):
                yield artifact_event

        if _is_side_effect_action(action):
            if run is None:
                raise RuntimeError("side-effect action was not initialized")
            yield {
                "type": "action.proposed",
                "action": action.model_dump(mode="json"),
                "run": run.model_dump(mode="json"),
            }
            if artifact is not None:
                yield {
                    "type": "artifact.updated",
                    "artifact": artifact.model_dump(mode="json"),
                }
        elif action is not None:
            yield {
                "type": "action.proposed",
                "action": action.model_dump(mode="json"),
                "run": None,
            }

        assistant_message = ChatMessage(
            message_id=f"msg_{uuid4().hex}",
            role="assistant",
            content="",
            status="streaming",
        )
        yield {"type": "message.started", "message": assistant_message.model_dump(mode="json")}
        response_text = plan.assistant_response.strip() or "我已完成当前任务的准备。"
        if run is not None:
            response_text = f"{response_text}\n\n{_describe_action_gate(run)}"
        elif action is not None:
            response_text = f"{response_text}\n\n{_describe_candidate_risk(action)}"
        for start in range(0, len(response_text), 2):
            delta = response_text[start : start + 2]
            yield {"type": "assistant.delta", "message_id": assistant_message.message_id, "delta": delta}
            await asyncio.sleep(0.012)

        completed = assistant_message.model_copy(
            update={"content": response_text, "status": "completed"}
        )
        artifacts = [*thread.artifacts]
        if artifact is not None:
            artifacts.append(artifact)
        thread = thread.model_copy(
            update={
                "messages": [*thread.messages, completed],
                "artifacts": artifacts,
                "updated_at": datetime.now(UTC),
            }
        )
        self._threads[thread_id] = thread
        yield {"type": "message.completed", "message": completed.model_dump(mode="json")}
        yield {"type": "ui.focus", "view": artifact.kind if artifact else plan.focus_view}

    async def stream_action_result(
        self, thread_id: str, run_id: str, user_id: str
    ) -> AsyncIterator[dict[str, Any]]:
        lock = self._thread_locks.setdefault(thread_id, asyncio.Lock())
        async with lock:
            async for event in self._stream_action_result_unlocked(
                thread_id, run_id, user_id
            ):
                yield event

    async def _stream_action_result_unlocked(
        self, thread_id: str, run_id: str, user_id: str
    ) -> AsyncIterator[dict[str, Any]]:
        thread = await self.get_thread(thread_id, user_id)
        run = await self.run_service.get(run_id, user_id)
        if run.thread_id != thread.thread_id:
            raise ValueError("该运行不属于当前对话，不能继续写入结果")
        key = (thread_id, run_id)
        previous_completion = self._continued_runs.get(key)
        if previous_completion is not None:
            yield {
                "type": "message.completed",
                "message": previous_completion.model_dump(mode="json"),
            }
            yield {
                "type": "action.closed",
                "run_id": run_id,
                "status": run.status,
            }
            return
        if run.status not in {"EXECUTED", "DENIED", "FAILED"}:
            raise ValueError("动作尚未结束，不能生成结果回应")
        yield {
            "type": "assistant.status",
            "status": "reflecting",
            "label": "Agent 正在读取执行结果并更新对话",
        }
        response_text = await self.agent.respond_after_action(
            run.user_message,
            [
                {"role": item.role, "content": item.content}
                for item in thread.messages[-12:]
            ],
            {
                "status": run.status,
                "action": run.action.model_dump(mode="json"),
                "tool_result": (
                    run.tool_result.model_dump(mode="json") if run.tool_result else None
                ),
            },
        )
        response_text = _strip_repeated_risk(response_text)
        if not response_text:
            response_text = {
                "EXECUTED": "动作已执行完成。",
                "DENIED": "该动作已被拒绝，未执行。",
                "FAILED": "动作执行失败。",
            }.get(run.status, "动作处理已结束。")
        assistant = ChatMessage(
            message_id=f"msg_{uuid4().hex}",
            role="assistant",
            content="",
            status="streaming",
        )
        yield {"type": "message.started", "message": assistant.model_dump(mode="json")}
        for start in range(0, len(response_text), 2):
            yield {
                "type": "assistant.delta",
                "message_id": assistant.message_id,
                "delta": response_text[start : start + 2],
            }
            await asyncio.sleep(0.012)
        completed = assistant.model_copy(
            update={"content": response_text, "status": "completed"}
        )
        self._threads[thread_id] = thread.model_copy(
            update={
                "messages": [*thread.messages, completed],
                "updated_at": datetime.now(UTC),
            }
        )
        self._continued_runs[key] = completed
        yield {"type": "message.completed", "message": completed.model_dump(mode="json")}
        yield {"type": "action.closed", "run_id": run_id, "status": run.status}
