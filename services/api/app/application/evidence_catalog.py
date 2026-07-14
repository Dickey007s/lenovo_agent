from pydantic import BaseModel, ConfigDict, Field


class EvidenceOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str
    label: str


class EvidenceRequirementDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement: str
    label: str
    description: str
    resolved_by: str
    user_action: str
    input_type: str = "none"
    options: list[EvidenceOption] = Field(default_factory=list)


EVIDENCE_CATALOG = {
    "recipient_identity": EvidenceRequirementDefinition(
        requirement="recipient_identity",
        label="收件人企业身份",
        description="由企业通讯录自动确认收件人属于内部成员还是外部客户。",
        resolved_by="企业通讯录",
        user_action="无需填写",
    ),
    "attachment_hash": EvidenceRequirementDefinition(
        requirement="attachment_hash",
        label="附件完整性校验",
        description="由文件服务读取附件并自动计算哈希，防止授权后替换文件。",
        resolved_by="文件服务",
        user_action="无需填写；请先在请求中选择附件",
    ),
    "dlp_result": EvidenceRequirementDefinition(
        requirement="dlp_result",
        label="数据防泄漏扫描",
        description="由 DLP 服务自动扫描附件和正文，不接受人工填写扫描结论。",
        resolved_by="DLP 服务",
        user_action="无需填写",
    ),
    "pricing_source": EvidenceRequirementDefinition(
        requirement="pricing_source",
        label="已批准报价来源",
        description="请选择 CRM 中已经审批通过的报价版本；系统将校验引用和内容摘要。",
        resolved_by="CRM 报价库",
        user_action="选择一条已批准报价",
        input_type="select",
        options=[
            EvidenceOption(value="crm:quote/991:v3", label="客户 991 · 报价 V3（已批准）"),
            EvidenceOption(
                value="crm:quote/2026-demo:v1", label="Demo 客户 · 2026 标准报价 V1（已批准）"
            ),
        ],
    ),
    "project_write_access": EvidenceRequirementDefinition(
        requirement="project_write_access",
        label="项目任务写入权限",
        description="由项目系统确认当前用户可以创建和分派任务。",
        resolved_by="项目管理系统",
        user_action="系统已自动校验",
    ),
    "calendar_availability": EvidenceRequirementDefinition(
        requirement="calendar_availability",
        label="日历可用性",
        description="检查与会人空闲时间与当前用户的日历写入权限。",
        resolved_by="企业日历",
        user_action="系统已自动校验",
    ),
    "crm_write_access": EvidenceRequirementDefinition(
        requirement="crm_write_access",
        label="CRM 写入权限",
        description="由 CRM 确认当前用户对目标商机的写入范围。",
        resolved_by="CRM",
        user_action="系统已自动校验",
    ),
    "expense_case_access": EvidenceRequirementDefinition(
        requirement="expense_case_access",
        label="报销单访问权限",
        description="确认用户可以查看该报销单并向申请人发起补件请求。",
        resolved_by="OA 报销系统",
        user_action="系统已自动校验",
    ),
}


def list_evidence_requirements() -> list[EvidenceRequirementDefinition]:
    return list(EVIDENCE_CATALOG.values())
