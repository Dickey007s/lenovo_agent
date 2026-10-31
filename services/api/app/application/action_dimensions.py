"""Risk level and eight-dimension explanation for one Agent action.

The tables follow ``docs/design/submission/人机共驾设计指导手册_v1.0.md``:

* section 1: eight things to establish for every action;
* section 3: L0-L5 risk levels and the default collaboration / takeover point;
* section 3: AL0-AL5 autonomy levels, recorded separately from risk.

Everything here is deterministic.  The level comes from the operation kind (a
product convention, as the manual stresses), not from a score computed over the
dimensions.  ``drives_level`` only marks which dimensions explain that level so a
reader can see *why* an action sits where it does.  No model is called.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["L0", "L1", "L2", "L3", "L4", "L5"]
AutonomyLevel = Literal["AL0", "AL1", "AL2", "AL3", "AL4", "AL5"]

DimensionKey = Literal[
    "action_object",
    "data_flow",
    "state_change",
    "blast_radius",
    "recoverability",
    "intent_evidence",
    "authority",
    "environment",
]

# Order and wording match the manual's section-1 table.
DIMENSION_LABELS: dict[str, str] = {
    "action_object": "动作和对象",
    "data_flow": "数据流向",
    "state_change": "状态变化",
    "blast_radius": "影响范围",
    "recoverability": "恢复能力",
    "intent_evidence": "意图和证据",
    "authority": "权限和制度",
    "environment": "使用环境",
}

# level -> (title, default collaboration, takeover point, design focus)
RISK_LEVELS: dict[str, tuple[str, str, str, str]] = {
    "L0": ("无业务影响", "静默处理，状态可查", "用户主动查看或关闭维护时", "不占用注意力，不扩大读取范围"),
    "L1": ("个人、低风险且可逆", "自动完成，提供撤销", "结果不合意或操作范围变化时", "改动可见，撤销可用"),
    "L2": ("内容准备", "展示草稿与来源", "需要修订或准备正式提交时", "编辑方便，保留不确定项"),
    "L3": ("有限内部变更", "普通确认后执行", "改变协作记录之前", "对象、字段和影响可检查"),
    "L4": ("外发或敏感高后果动作", "准备或强确认；按制度取得审批", "敏感处理或正式实施之前", "内容、依据、权限和影响一起核对"),
    "L5": ("极高风险或受限动作", "停止自动实施，交给有权人员或正式流程", "发现受限条件时", "解释限制，保留允许的准备工作"),
}

AUTONOMY_LEVELS: dict[str, tuple[str, str]] = {
    "AL0": ("观察", "展示允许查看的状态"),
    "AL1": ("建议", "提醒和处理选项"),
    "AL2": ("草稿或模拟", "准备内容，供用户检查"),
    "AL3": ("确认后执行", "对当前动作取得有效确认后实施"),
    "AL4": ("可撤销自动执行", "在获准范围内完成低风险操作"),
    "AL5": ("静默后台", "无业务影响的维护"),
}


class DimensionFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: DimensionKey
    label: str
    finding: str = Field(min_length=1, max_length=400)
    # True when this dimension is one of the reasons the action sits at its level.
    drives_level: bool = False


class RiskAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_level: RiskLevel
    risk_title: str
    autonomy_level: AutonomyLevel
    autonomy_title: str
    collaboration: str
    takeover_point: str
    design_focus: str
    dimensions: list[DimensionFinding] = Field(min_length=8, max_length=8)
    rules: list[str] = Field(default_factory=list, max_length=8)
    # The level is looked up from the operation kind, not computed from the dimensions.
    basis: Literal["operation_default"] = "operation_default"


def _assessment(
    risk: str,
    autonomy: str,
    findings: dict[str, str],
    drivers: set[str],
    rules: list[str],
) -> RiskAssessment:
    title, collaboration, takeover, focus = RISK_LEVELS[risk]
    autonomy_title, _ = AUTONOMY_LEVELS[autonomy]
    return RiskAssessment(
        risk_level=risk,  # type: ignore[arg-type]
        risk_title=title,
        autonomy_level=autonomy,  # type: ignore[arg-type]
        autonomy_title=autonomy_title,
        collaboration=collaboration,
        takeover_point=takeover,
        design_focus=focus,
        dimensions=[
            DimensionFinding(
                key=key,  # type: ignore[arg-type]
                label=label,
                finding=findings[key],
                drives_level=key in drivers,
            )
            for key, label in DIMENSION_LABELS.items()
        ],
        rules=rules,
    )


# --------------------------------------------------------------------------
# Single office actions (Demo 3).  One entry per operation kind.
# --------------------------------------------------------------------------

def assess_office_action(
    operation: str,
    *,
    target_label: str = "",
    due_date: str | None = None,
    source_label: str | None = None,
    risk_level: str | None = None,
    autonomy_level: str | None = None,
    restricted_reason: str | None = None,
) -> RiskAssessment:
    """Eight-dimension explanation for one office action.

    ``risk_level`` / ``autonomy_level`` come from the policy that already ran;
    they are passed in so this explanation can never disagree with the policy.
    """

    target = target_label or "尚未指定"
    env = "桌面与手机都能看到关键预览；系统不检测用户所处场合，也不启用录音或摄像。"
    table: dict[str, tuple[str, str, dict[str, str], set[str], list[str]]] = {
        "format_text": (
            "L1",
            "AL4",
            {
                "action_object": "把你给出的个人文本重新排版，对象只有这一段文字。",
                "data_flow": "只用你提交的文字，在本地规则中处理，不交给其他人，也不传给模型。",
                "state_change": "只生成一份整理后的副本，原文保留。",
                "blast_radius": "仅你本人。",
                "recoverability": "可以撤销，撤销后恢复为整理前的文字。",
                "intent_evidence": "目标明确：按所选格式整理，没有要核对的外部事实。",
                "authority": "个人文本，不涉及审批或受限事项。",
                "environment": env,
            },
            {"state_change", "blast_radius", "recoverability"},
            ["R01", "R11", "R14"],
        ),
        "extract_excerpt": (
            "L2",
            "AL2",
            {
                "action_object": f"从{source_label or '所选资料'}中摘录要点，形成内部草稿。",
                "data_flow": "读取你选定的资料，结果只留在草稿里，不外发。",
                "state_change": "只生成草稿，不修改任何业务记录。",
                "blast_radius": "仅你本人，草稿经你核对后才会被使用。",
                "recoverability": "丢弃草稿不影响原资料。",
                "intent_evidence": "摘录与原文并排展示，便于你核对出处；原文没有的内容不会补写。",
                "authority": "读取范围限于你选定的资料；起草权限不包含外发权限。",
                "environment": env,
            },
            {"state_change", "intent_evidence"},
            ["R05", "R06"],
        ),
        "create_task": (
            "L3",
            "AL3",
            {
                "action_object": f"为{target}创建一条协作任务"
                + (f"，截止 {due_date}。" if due_date else "。"),
                "data_flow": "任务标题和说明会交给内部同事，不含外部联系人。",
                "state_change": "会新增一条协作记录，这是业务提交，不是草稿。",
                "blast_radius": "指定的一位内部同事，以及这条任务所在的协作记录。",
                "recoverability": "创建前可修改、暂缓或取消；创建后只能由对方处理，当前演示只写入隔离的测试记录。",
                "intent_evidence": "需要联系人和截止日期都明确，缺任何一项就先停下来问你。",
                "authority": "仅限测试通讯录中的内部成员。",
                "environment": env,
            },
            {"state_change", "blast_radius", "intent_evidence"},
            ["R04", "R05", "R07", "R08"],
        ),
        "send_message": (
            "L4",
            "AL3",
            {
                "action_object": f"把一段消息发给{target}。",
                "data_flow": "消息正文会交给收件人，发出后无法完全收回。",
                "state_change": "产生一次正式发送，这是业务提交，不是草稿。",
                "blast_radius": "收件人本人；如果被转发，范围会继续扩大。",
                "recoverability": "发送前可修改或取消；发送后不能当作已撤回，只能补救。",
                "intent_evidence": "收件人、正文和影响三项都要你逐项核对，改动任何一项都要重新核对。",
                "authority": "涉及价格、薪资等承诺时需要有权人员批准；没有批准则不能发出。",
                "environment": env,
            },
            {"data_flow", "recoverability", "authority"},
            ["R02", "R07", "R08", "R09"],
        ),
        "restricted_action": (
            "L5",
            "AL1",
            {
                "action_object": "这是一项被组织规则限制的动作。",
                "data_flow": "不读取也不传送任何资料来实施它。",
                "state_change": "不会产生任何变化，系统停在准备阶段。",
                "blast_radius": "如果实施，影响会超出你个人可决定的范围，所以不实施。",
                "recoverability": "不执行，也就没有需要恢复的内容。",
                "intent_evidence": "意图清楚，但缺少授权依据。",
                "authority": restricted_reason or "没有权限，需要交给有权人员或走正式流程。",
                "environment": env,
            },
            {"authority", "blast_radius"},
            ["R03", "R15"],
        ),
        "compare_materials": (
            "L2",
            "AL1",
            {
                "action_object": "把两份材料并排对照，找出差异。",
                "data_flow": "只在两份材料之间比较，不外发。",
                "state_change": "不修改任何材料，只给出对照和你的判断记录。",
                "blast_radius": "仅你本人。",
                "recoverability": "判断记录可以重做，材料本身不变。",
                "intent_evidence": "材料可能冲突，系统不替你选，把依据并列后由你判断。",
                "authority": "选哪份材料属于业务判断，由你决定。",
                "environment": env,
            },
            {"intent_evidence", "authority"},
            ["R04", "R06"],
        ),
    }
    # A message that trips the restricted-content rule is explained as a
    # restricted action, whatever operation the user picked.
    key = "restricted_action" if risk_level == "L5" else operation
    default_risk, default_autonomy, findings, drivers, rules = table[key]
    return _assessment(risk_level or default_risk, autonomy_level or default_autonomy, findings, drivers, rules)


# --------------------------------------------------------------------------
# Workflow nodes of an Agent Control Loop run (Demo 1 / Demo 2 rows).
# --------------------------------------------------------------------------

_ENV_NOTE = "界面在桌面和手机上都保留关键信息；系统不检测用户所处场合。"


def assess_intake(*, file_count: int) -> RiskAssessment:
    return _assessment(
        "L0",
        "AL4",
        {
            "action_object": "理解任务要求，并在资料库里确定要读哪些文件。",
            "data_flow": f"只读取已获准的公开办公资料库，本次涉及 {file_count} 份文件。",
            "state_change": "不修改任何文件或记录。",
            "blast_radius": "不对任何人产生影响。",
            "recoverability": "没有需要恢复的内容。",
            "intent_evidence": "目标来自你输入的任务描述。",
            "authority": "读取范围受资料库白名单约束。",
            "environment": _ENV_NOTE,
        },
        {"state_change", "blast_radius"},
        ["R01", "R02"],
    )


def assess_analysis_unit(
    *,
    tool: str,
    side_effect: str,
    requires_human_gate: bool,
    file_count: int,
    depends_on_count: int,
    artifact_name: str | None = None,
) -> RiskAssessment:
    """Assess one planned work unit from facts the server already validated."""

    upstream = f"，并使用前序 {depends_on_count} 项工作的结果" if depends_on_count else ""
    if side_effect == "external_action":
        return _assessment(
            "L4",
            "AL3",
            {
                "action_object": "准备一个对外动作的预览，不会真正发出。",
                "data_flow": "预览内容可能包含需要外发的信息，发出前要核对。",
                "state_change": "当前运行不会产生外部变化。",
                "blast_radius": "如果实施，影响到外部对象。",
                "recoverability": "外发后无法完全收回，所以必须先经过你确认。",
                "intent_evidence": "收件对象、正文和依据要一起核对。",
                "authority": "必须有人工确认，按制度可能还要审批。",
                "environment": _ENV_NOTE,
            },
            {"data_flow", "recoverability", "authority"},
            ["R07", "R09", "R15"],
        )
    if requires_human_gate:
        return _assessment(
            "L3",
            "AL3",
            {
                "action_object": "这一步需要你作出决定后才能继续。",
                "data_flow": f"读取 {file_count} 份已获准文件{upstream}。",
                "state_change": "你确认之前，不会写入任何结果。",
                "blast_radius": "取决于你的决定，范围限于本次任务。",
                "recoverability": "你可以暂缓、拒绝或要求重新核对。",
                "intent_evidence": "系统把依据放在决定旁边，由你判断。",
                "authority": "需要用户在场，不能自动越过。",
                "environment": _ENV_NOTE,
            },
            {"authority", "intent_evidence"},
            ["R04", "R07", "R10"],
        )
    if side_effect == "run_workspace_write":
        return _assessment(
            "L2",
            "AL2",
            {
                "action_object": f"生成交付文件{('「' + artifact_name + '」') if artifact_name else ''}，供你检查。",
                "data_flow": f"读取 {file_count} 份已获准文件{upstream}，结果只写入本次运行的工作区。",
                "state_change": "只新增一个版本化的草稿文件，不修改资料库原文件。",
                "blast_radius": "仅本次任务，不对外发送。",
                "recoverability": "每个版本都保留，可以回退到上一个版本。",
                "intent_evidence": "结论带原文位置，便于你核对。",
                "authority": "只写运行工作区，不写业务系统。",
                "environment": _ENV_NOTE,
            },
            {"state_change", "recoverability"},
            ["R05", "R06", "R11"],
        )
    return _assessment(
        "L2",
        "AL2",
        {
            "action_object": f"阅读并分析 {file_count} 份文件，形成可核对的发现。",
            "data_flow": f"只读取已获准文件{upstream}，不外发。",
            "state_change": "只产生分析结果，不修改任何文件。",
            "blast_radius": "仅本次任务。",
            "recoverability": "分析结果可以重做，原文件不变。",
            "intent_evidence": "每条发现都要能回到原文位置；找不到就标为证据缺口。",
            "authority": "读取范围受资料库白名单约束。",
            "environment": _ENV_NOTE,
        },
        {"state_change", "intent_evidence"},
        ["R05", "R06"],
    )


def assess_delivery(*, artifact_count: int) -> RiskAssessment:
    return _assessment(
        "L2",
        "AL2",
        {
            "action_object": "把各项工作的结果汇总成交付摘要，并核对依据。",
            "data_flow": "只使用前面各项工作已验证的结果，不引入新资料。",
            "state_change": f"形成 {artifact_count} 个版本的交付物，需要你确认后才算采纳。",
            "blast_radius": "仅本次任务。",
            "recoverability": "交付物按版本保留，可以回退。",
            "intent_evidence": "结论和原文并排，缺口会单独列出。",
            "authority": "采纳与否由你决定。",
            "environment": _ENV_NOTE,
        },
        {"intent_evidence", "authority"},
        ["R05", "R06", "R16"],
    )


_GATE_TEXT = {
    "judgment": (
        "L3",
        "AL3",
        "分析发现了需要你拍板的事：系统不替你选。",
        "你选定之前，这一项不会被当作结论写入。",
        "你可以接受、拒绝、暂缓，或要求重新核对。",
        "系统把问题、选项和原文依据放在一起，由你判断。",
        "业务取舍属于有权限的人，系统不能自动越过。",
        {"authority", "intent_evidence"},
        ["R04", "R07", "R10"],
    ),
    "source_choice": (
        "L2",
        "AL2",
        "同一处引用有多个候选位置，需要你对照原文挑出正确的一处。",
        "你选定之前，这一项不会被当作已核对的依据。",
        "可以重新选择，原文件不变。",
        "候选位置并排展示，由你对照。这不是业务批准。",
        "只决定引用位置，不授予任何业务权限。",
        {"intent_evidence"},
        ["R05", "R06"],
    ),
    "missing": (
        "L2",
        "AL2",
        "资料库里没有找到这一项要求的来源，需要你补充真实材料。",
        "补充之前，这一项保持空缺，其他已完成的工作不受影响。",
        "补充材料后可以只重做这一项。",
        "系统不会用相近的资料代替所需凭证，也不会猜测答案。",
        "补充什么材料由你决定，系统不自行联网或向外索取。",
        {"intent_evidence", "authority"},
        ["R05", "R06", "R10"],
    ),
    "start": (
        "L1",
        "AL1",
        "系统已经把任务拆成几项可以同时做的只读工作，等你同意后才分头启动。",
        "你同意之前不会调用任何分析模型；同意后只读取资料，不改任何文件。",
        "启动后可以中断任务；已读取的资料和原文件都不变。",
        "拆分依据和每项工作要读的资料列在节点里，可以逐项查看。",
        "是否花费模型调用与时间属于你的授权，系统不自行放大并行数量。",
        {"authority"},
        ["R04", "R09"],
    ),
}


def assess_human_gate(*, kind: str, reason: str = "") -> RiskAssessment:
    """A step that waits for a person. The level is the gate kind's convention, not a score."""

    risk, autonomy, action, state, recover, evidence, authority, drivers, rules = _GATE_TEXT.get(
        kind, _GATE_TEXT["judgment"]
    )
    return _assessment(
        risk,
        autonomy,
        {
            "action_object": action,
            "data_flow": "只涉及本次任务已读取的资料，不外发。",
            "state_change": state,
            "blast_radius": "仅本次任务；其他并行工作继续推进。",
            "recoverability": recover,
            "intent_evidence": (reason + " " if reason else "") + evidence,
            "authority": authority,
            "environment": _ENV_NOTE,
        },
        drivers,
        rules,
    )
