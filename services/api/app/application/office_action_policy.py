"""Deterministic policy and bounded local records. No connector or model calls."""

from datetime import datetime, timezone
from uuid import uuid4

from packages.contracts.office_actions import (
    ActionDecision, ActionHistory, ActionInput, ActionReceipt, OfficeAction, OfficeActionControl,
)


CONTACTS = {
    "wang-engineering": "王工 · 研发组 · wang.engineering@example.invalid",
    "wang-delivery": "王工 · 交付组 · wang.delivery@example.invalid",
    "client-review": "客户评审联系人 · review@example.invalid",
}


def prepare_action(
    data: ActionInput, source: dict | None = None, *, previous: OfficeAction | None = None
) -> OfficeAction:
    now = datetime.now(timezone.utc)
    operation = data.operation
    risk, autonomy, mode = {
        "format_text": ("L1", "AL4", "自动整理，可撤销"),
        "extract_excerpt": ("L2", "AL2", "摘录草稿"),
        "create_task": ("L3", "AL3", "确认后创建"),
        "send_message": ("L4", "AL3", "核对后提交"),
        "restricted_action": ("L5", "AL1", "受限，转人工办理"),
        "compare_materials": ("L2", "AL1", "材料对照，由你判断"),
    }[operation]
    missing = []
    target_label = CONTACTS.get(data.target, "尚未指定唯一联系人")
    if operation in {"create_task", "send_message"} and data.target not in CONTACTS:
        missing.append("请选择一位具体联系人")
    if operation == "create_task" and data.target == "client-review":
        missing.append("协作任务仅支持测试通讯录中的内部成员")
    if operation == "create_task" and data.due_date is None:
        missing.append("请填写截止日期")
    if not data.title.strip():
        missing.append("请填写标题")
    if not data.content.strip() and operation != "extract_excerpt":
        missing.append("请填写内容")
    if operation == "compare_materials" and not data.alternative_content.strip():
        missing.append("请补充第二份材料，再对照判断")
    source_text = None
    source_label = None
    if source is not None:
        source_label = str(source.get("display_label", "所选资料"))
        source_text = str(source.get("text") or "")
        if not source_text and source.get("rows"):
            columns = " | ".join(str(x) for x in source.get("columns", []))
            source_text = columns + "\n" + "\n".join(
                " | ".join(str(v) for v in row["values"]) for row in source["rows"]
            )
        source_text = source_text[:5000]
    if operation == "extract_excerpt" and not (
        source_text if source is not None else data.content.strip()
    ):
        missing.append("请选择可预览的资料或填入待摘录文字")
    preview = data.content
    if operation == "format_text":
        preview = "\n\n".join(line.strip() for line in data.content.splitlines() if line.strip())
        target_label = "本次个人文本副本"
    elif operation == "extract_excerpt":
        source_text = (source_text or "") if source is not None else data.content
        preview = "\n".join(line for line in source_text.splitlines() if line.strip())[:1200]
        target_label = "本次内部摘录草稿"
    elif operation == "compare_materials":
        target_label = "用户提供的两份对照材料"
    elif operation == "restricted_action":
        target_label = "受限业务内容，仅供人工核对"
    restricted = operation == "restricted_action" or (
        operation == "send_message"
        and any(word in data.title + data.content for word in ("最低折扣", "最低价承诺", "无须审批"))
    )
    if restricted:
        risk, autonomy, mode = "L5", "AL1", "受限，转人工办理"
    status = (
        "denied" if restricted else "needs_input" if missing else
        "executed" if operation == "format_text" else
        "draft_ready" if operation == "extract_excerpt" else
        "awaiting_decision" if operation == "compare_materials" else "awaiting_confirmation"
    )
    impact = {
        "format_text": "整理当前文本副本的段落空白，原始资料不变。",
        "extract_excerpt": "从可见资料中逐字截取最多 1200 字符，供内部编辑；未作语义总结。",
        "create_task": "在本次测试记录中新增一条任务；不会通知真实同事。",
        "send_message": "在本次测试发件记录中登记完整内容；不会连接真实邮箱。",
        "restricted_action": "当前没有该受限动作的执行授权，需要由有权人员办理。",
        "compare_materials": "仅记录你选择的材料和判断理由；不修改原材料，不创建任务或通知他人。",
    }[operation]
    if restricted:
        impact = "受限承诺未提交；当前测试策略没有价格承诺或权限变更的授权路径。"
    reason = {
        "denied": "内容或动作触及本次受限策略，未执行。",
        "needs_input": "缺少办理这件事项所需的信息。",
        "executed": "个人文本副本已经整理，原内容可恢复。",
        "draft_ready": "摘录已准备好，请结合原文检查。",
        "awaiting_confirmation": "请核对当前对象和内容，再决定是否提交。",
        "awaiting_decision": "两份材料已并列保留，尚未选择；请由了解业务的人判断，也可暂缓。",
    }[status]
    action = OfficeAction(
        action_id=previous.action_id if previous else f"action-{uuid4().hex[:12]}",
        revision=previous.revision + 1 if previous else 1,
        input=data, status=status, risk_level=risk, autonomy_level=autonomy, mode=mode,
        reason=reason, missing_fields=missing,
        required_checks=["target", "content", "impact"] if risk == "L4" else [],
        target_label=target_label, before=data.content, preview=preview,
        source_label=source_label, source_excerpt=source_text,
        impact=impact,
        reversibility=("可以恢复整理前的文本副本。" if operation == "format_text" else
                       "可编辑或丢弃当前草稿。" if operation == "extract_excerpt" else
                       "两份材料保持原样，判断记录不改写原文。" if operation == "compare_materials" else
                       "本次仅保存测试记录；真实业务撤回能力须由相应系统提供。"),
        result_message=reason, history=list(previous.history) if previous else [],
    )
    if status in {"executed", "draft_ready"}:
        action.receipt = ActionReceipt(
            record_id=f"record-{uuid4().hex[:12]}",
            kind="text_copy" if operation == "format_text" else "excerpt_draft",
            content=preview, target=target_label, created_at=now,
        )
    action.history.append(ActionHistory(
        revision=action.revision, event="revised" if previous else "prepared",
        message=("内容已更新，按新版本重新核对。" if previous else reason),
        at=now, input=data, content_snapshot=preview,
    ))
    return action


def control_action(action: OfficeAction, request: OfficeActionControl) -> OfficeAction:
    if request.action_revision != action.revision:
        raise ValueError("内容版本已经变化，请重新核对当前版本")
    if len(action.history) >= 59:
        raise ValueError("本次事项记录已达上限，请新建事项")
    if request.replacement is not None and request.command != "revise":
        raise ValueError("只有修改操作可以替换内容")
    updated = action.model_copy(deep=True)
    now = datetime.now(timezone.utc)
    if request.command == "edit_draft":
        if (action.input.operation != "extract_excerpt" or action.status != "draft_ready"
                or action.receipt is None or not request.edited_content):
            raise ValueError("只有已准备的摘录草稿可以编辑")
        updated.revision += 1
        updated.preview = request.edited_content
        updated.receipt.content = request.edited_content
        updated.mode = "人工修订草稿"
        updated.reason = "当前内容包含人工修改，请与保留的原文分别核对。"
        updated.result_message = "你的修改已保存为内部草稿；原始来源保留，未外发或修改源文件。"
    elif request.command == "record_decision":
        if (action.input.operation != "compare_materials"
                or action.status not in {"awaiting_decision", "deferred"}
                or action.missing_fields or request.selected_option is None
                or not request.rationale.strip()):
            raise ValueError("请先核对完整的两份材料，再明确记录判断")
        selected = (action.input.content if request.selected_option == "first"
                    else action.input.alternative_content)
        updated.decision = ActionDecision(
            option=request.selected_option, rationale=request.rationale.strip(),
            selected_content=selected, at=now,
        )
        label = "材料 A" if request.selected_option == "first" else "材料 B"
        updated.receipt = ActionReceipt(
            record_id=f"record-{uuid4().hex[:12]}", kind="decision_note",
            content=f"选择：{label}\n依据：{request.rationale.strip()}\n\n{selected}",
            target=action.target_label, created_at=now,
        )
        updated.status = "decided"
        updated.mode = "人工判断已记录"
        updated.result_message = "已记录你的判断，两份原材料均未修改；没有启动后续任务。"
        updated.reason = updated.result_message
    elif request.command == "undo":
        if (action.input.operation != "format_text" or action.status != "executed"
                or action.receipt is None):
            raise ValueError("当前事项没有可撤销的格式修改")
        updated.preview = action.before
        updated.receipt.content = action.before
        updated.receipt.undone_at = now
        updated.status = "undone"
        updated.result_message = "已恢复整理前的文本副本。"
    else:
        if action.status not in {
            "needs_input", "awaiting_confirmation", "deferred", "stale", "awaiting_decision"
        }:
            raise ValueError("当前事项已经结束，不能再次办理")
        if request.command == "confirm":
            if action.status == "stale" or action.missing_fields:
                raise ValueError("请先补齐信息或更新内容")
            if set(request.reviewed_fields) != set(action.required_checks):
                raise ValueError("请完成当前内容所需的核对")
            if (action.risk_level not in {"L3", "L4"}
                    or action.input.operation not in {"create_task", "send_message"}):
                raise ValueError("当前策略不允许确认执行")
            updated.receipt = ActionReceipt(
                record_id=f"record-{uuid4().hex[:12]}",
                kind="test_task" if action.input.operation == "create_task" else "test_message",
                content=action.preview, target=action.target_label, created_at=now,
            )
            updated.status = "executed"
            updated.result_message = (
                "已创建一条测试任务，未通知真实同事。"
                if action.input.operation == "create_task" else
                "已登记一条测试发件记录，未发送真实邮件。"
            )
        elif request.command == "defer":
            updated.status = "deferred"
            updated.result_message = "已暂缓，可稍后继续核对。"
        elif request.command == "cancel":
            updated.status = "cancelled"
            updated.result_message = "本次事项已取消，未产生业务提交。"
        else:
            raise ValueError("修改需要重新进行策略检查")
    updated.history.append(ActionHistory(
        revision=updated.revision, event=request.command,
        message=updated.result_message, at=now, input=updated.input,
        content_snapshot=updated.receipt.content if updated.receipt else updated.preview,
    ))
    return updated
