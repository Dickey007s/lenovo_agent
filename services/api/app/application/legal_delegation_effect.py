"""Source-derived legal delegation review for the fixed FORTE Legal-020 set.

The adapter parses only the seven allowlisted inputs supplied by the caller. It
does not read benchmark task instructions, infer a hidden draft exception, or
make a legal-validity decision. Every output row is recomputed from the source
rule table and the frozen DOCX bytes.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import date
from typing import Literal
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from packages.contracts.harness_models import (
    AgentControlLoopBusinessGate,
    AgentControlLoopBusinessGateOutcome,
    AgentControlLoopLegalDocumentReview,
    AgentControlLoopLegalReviewOutcome,
    AgentControlLoopLegalRuleAssessment,
)


class LegalDelegationValidationError(ValueError):
    """The fixed Legal-020 source or output contract is not trustworthy."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class LegalSourceInput:
    logical_id: str
    file_name: str
    display_path: str
    file_ref: str
    content: bytes
    declared_size: int
    allowlist_verified: bool


@dataclass(frozen=True)
class LegalRule:
    rule_id: str
    name: str
    level: Literal["high", "medium", "low"]
    trigger: str
    description: str
    line_number: int


@dataclass(frozen=True)
class SourceParagraph:
    index: int
    text: str
    has_drawing: bool
    has_pict: bool


@dataclass(frozen=True)
class SourceTable:
    index: int
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class ParsedDelegationDocument:
    source: LegalSourceInput
    paragraphs: tuple[SourceParagraph, ...]
    tables: tuple[SourceTable, ...]
    text: str
    principal_name: str
    principal_identity: str
    agent_name: str
    agent_identity: str
    agent_license: str
    principal_locator: str
    agent_locator: str
    is_enterprise: bool
    is_litigation: bool
    case_number_present: bool
    counterparty_present: bool
    scope_text: str
    scope_locator: str
    authorization_kind: Literal["general", "special", "unclear"]
    authorization_actions: tuple[str, ...]
    start_date: date | None
    end_date: date | None
    signed_date: date | None
    date_locator: str
    transfer_text: str
    liability_text: str
    signature_locator: str
    signature_excerpt: str
    signature_text_evidence: bool
    signature_visual_evidence: bool
    representative_signature_evidence: bool
    stamp_evidence: bool
    has_media: bool
    has_drawing: bool
    has_pict: bool
    has_embedding: bool
    has_digital_signature: bool

    @property
    def signing_evidence_status(self) -> Literal[
        "present", "absent", "unverifiable"
    ]:
        if (
            self.signature_text_evidence
            or self.signature_visual_evidence
            or self.has_digital_signature
        ):
            return "present"
        if self.has_media or self.has_drawing or self.has_pict or self.has_embedding:
            return "unverifiable"
        return "absent"


@dataclass(frozen=True)
class LegalDelegationAnalysis:
    rules: tuple[LegalRule, ...]
    documents: tuple[ParsedDelegationDocument, ...]
    reviews: tuple[AgentControlLoopLegalDocumentReview, ...]
    legal_outcome: AgentControlLoopLegalReviewOutcome
    business_outcome: AgentControlLoopBusinessGateOutcome


@dataclass(frozen=True)
class LegalVerifierCheck:
    check_id: str
    label: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class LegalDelegationBuild:
    report_docx: bytes
    ledger_csv: bytes
    analysis: LegalDelegationAnalysis
    checks: tuple[LegalVerifierCheck, ...]
    docx_table_count: int


RULE_LOGICAL_ID = "RULES"
DOCUMENT_LOGICAL_IDS = tuple(f"DOC-{index:02d}" for index in range(1, 7))
EXPECTED_FILE_NAMES = {
    RULE_LOGICAL_ID: "授权委托书风控校验规则.md",
    **{
        logical_id: f"委托书{index}.docx"
        for index, logical_id in enumerate(DOCUMENT_LOGICAL_IDS, start=1)
    },
}
EXPECTED_DISPLAY_PATHS = {
    RULE_LOGICAL_ID: "法务/授权委托书风控校验规则.md",
    **{
        logical_id: f"法务/委托书/委托书{index}.docx"
        for index, logical_id in enumerate(DOCUMENT_LOGICAL_IDS, start=1)
    },
}
EXPECTED_RULE_CODES = frozenset(
    [*(f"R{index:02d}" for index in range(1, 7))]
    + [*(f"M{index:02d}" for index in range(1, 10))]
    + [*(f"L{index:02d}" for index in range(1, 7))]
)
LEVEL_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}
LEVEL_LABELS = {"none": "无已触发项", "low": "低", "medium": "中", "high": "高"}
STATUS_LABELS = {
    "triggered": "已触发",
    "not_triggered": "未触发",
    "unverifiable": "资料不足",
}

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"

LEDGER_HEADERS = (
    "文档ID",
    "文档",
    "综合等级",
    "规则ID",
    "规则名称",
    "规则等级",
    "状态",
    "来源文件Ref",
    "来源位置",
    "原文摘录",
    "事实",
    "规则判断",
    "原因",
    "责任人",
    "处置建议",
    "退出条件",
)

REMEDIATION = {
    "R01": (
        "业务经办人、法务负责人",
        "补充并核验委托人的身份证明或统一社会信用代码。",
        "委托人身份字段与证明材料一致，法务复核留痕完成。",
    ),
    "R02": (
        "业务经办人、法务负责人",
        "补充并核验受托人身份证明或律师执业证号。",
        "受托人身份或执业证号可由批准材料核验。",
    ),
    "M02": (
        "业务经办人、法务负责人",
        "补充合同、诉状或业务主体证明，核对委托人与业务主体。",
        "关联材料中的业务主体与委托人一致，或差异已有书面依据。",
    ),
    "M03": (
        "受托人、法务负责人",
        "补充律师执业证、亲属或员工关系证明，或法院许可材料。",
        "受托人代理资格可由批准材料独立核验。",
    ),
    "L01": (
        "业务经办人",
        "补齐案号和明确的对方当事人信息。",
        "案件信息可唯一对应本次授权事项。",
    ),
    "R03": (
        "委托人、法务负责人",
        "将模糊的全权表述改为一般授权或逐项列明的特别授权。",
        "授权类型明确，具体事项和边界可逐项核对。",
    ),
    "M01": (
        "委托人、法务负责人",
        "收窄特别授权，并为重大处分事项增加书面确认条件。",
        "承认、放弃等重大事项的权限与确认机制明确。",
    ),
    "M04": (
        "委托人、法务负责人",
        "删除无边界表述并列明可执行事项。",
        "授权事项可枚举且不存在一切事宜等开放表述。",
    ),
    "L02": (
        "业务经办人、法务负责人",
        "补充业务场景说明并核对授权事项与案件类型。",
        "授权事项与业务场景能够由同一组批准材料核对。",
    ),
    "R04": (
        "委托人、法务负责人",
        "补充授权起始日和截止日。",
        "起止日期完整、格式有效且起始日不晚于截止日。",
    ),
    "M05": (
        "委托人、法务负责人",
        "缩短授权期限或增加到期复核与续签条件。",
        "期限未超过来源规则阈值，且不存在长期或永久授权。",
    ),
    "M06": (
        "委托人、法务负责人",
        "补齐缺失的授权起始日或截止日。",
        "授权起止日期均存在且格式、顺序有效。",
    ),
    "L03": (
        "委托人、法务负责人",
        "补充可核验的委托日期。",
        "委托日期完整且格式有效。",
    ),
    "M07": (
        "委托人、法务负责人",
        "明确是否允许转委托，并写明批准方式。",
        "转委托允许或禁止状态在正文中明确。",
    ),
    "L04": (
        "委托人、法务负责人",
        "补齐转委托范围、次数和转受托人资质限制。",
        "允许转委托时三类限制均可核对。",
    ),
    "M08": (
        "委托人、受托人、法务负责人",
        "明确受托人行为后果归属及故意或重大过失责任。",
        "责任承担条款具体且可由双方复核。",
    ),
    "L05": (
        "委托人、法务负责人",
        "删除绝对免责表述并限定合理免责范围。",
        "免责条款不再免除全部责任，适用条件明确。",
    ),
    "R05": (
        "委托人、法务负责人",
        "完成可核验的签字或盖章并保留签署对象。",
        "签署栏存在可审查的签字、盖章或数字签署证据。",
    ),
    "R06": (
        "业务经办人、法务负责人",
        "补充受托人姓名或机构名称。",
        "正文能够唯一识别受托人。",
    ),
    "M09": (
        "法定代表人、法务负责人",
        "为企业委托书补充单位公章并核验签署权限。",
        "企业公章对象可审查，签署主体权限已由法务复核。",
    ),
    "L06": (
        "业务经办人",
        "列明附件清单并绑定对应证明材料。",
        "正文提及的附件与批准材料逐项对应。",
    ),
}


def build_legal_delegation_review(
    sources: tuple[LegalSourceInput, ...],
) -> LegalDelegationBuild:
    analysis = analyze_legal_delegation_sources(sources)
    ledger_csv = _ledger_csv(analysis)
    report_docx, table_count = _report_docx(analysis)
    checks = verify_legal_delegation_artifacts(
        sources,
        report_docx=report_docx,
        ledger_csv=ledger_csv,
    )
    return LegalDelegationBuild(
        report_docx=report_docx,
        ledger_csv=ledger_csv,
        analysis=analysis,
        checks=checks,
        docx_table_count=table_count,
    )


def analyze_legal_delegation_sources(
    sources: tuple[LegalSourceInput, ...],
) -> LegalDelegationAnalysis:
    by_id = _validate_source_contract(sources)
    rules = _parse_rules(by_id[RULE_LOGICAL_ID].content)
    documents = tuple(
        _parse_docx(by_id[logical_id]) for logical_id in DOCUMENT_LOGICAL_IDS
    )
    reviews = tuple(_review_document(document, rules) for document in documents)
    legal_outcome = _legal_outcome(reviews, len(rules))
    business_outcome = _business_outcome(legal_outcome)
    return LegalDelegationAnalysis(
        rules=rules,
        documents=documents,
        reviews=reviews,
        legal_outcome=legal_outcome,
        business_outcome=business_outcome,
    )


def verify_legal_delegation_artifacts(
    sources: tuple[LegalSourceInput, ...],
    *,
    report_docx: bytes,
    ledger_csv: bytes,
) -> tuple[LegalVerifierCheck, ...]:
    expected = analyze_legal_delegation_sources(sources)
    expected_rows = _ledger_rows(expected)
    csv_valid, csv_rows, csv_detail = _parse_ledger(ledger_csv)
    csv_pairs = [
        (row.get("文档ID", ""), row.get("规则ID", "")) for row in csv_rows
    ]
    row_map = {
        (row.get("文档ID", ""), row.get("规则ID", "")): row for row in csv_rows
    }
    expected_map = {
        (row["文档ID"], row["规则ID"]): row for row in expected_rows
    }
    exact_ledger = csv_valid and row_map == expected_map

    docx_valid, docx_text, docx_tables, docx_detail = _parse_generated_docx(
        report_docx
    )
    assessment_rows = [
        row
        for table in docx_tables
        for row in table[1:]
        if len(row) == 8 and re.fullmatch(r"DOC-[0-9]{2}", row[0])
    ]
    expected_docx_rows = {
        (
            review.document_id,
            assessment.rule_id,
            assessment.rule_name,
            LEVEL_LABELS[assessment.rule_level],
            STATUS_LABELS[assessment.status],
            assessment.source_locator,
            assessment.fact,
            assessment.judgment,
        )
        for review in expected.reviews
        for assessment in review.assessments
    }
    actual_docx_rows = {tuple(row) for row in assessment_rows}
    dynamic_summary = _summary_sentence(expected.legal_outcome)
    boundary_markers = (
        "不是正式法律意见",
        "没有签署任何文件",
        "不代表授权有效",
        "必须由法务人员复核",
    )
    locator_check = all(
        assessment.source_locator
        and assessment.excerpt
        and assessment.excerpt in document.text
        for review, document in zip(expected.reviews, expected.documents, strict=True)
        for assessment in review.assessments
    )
    highest_check = all(
        review.highest_triggered_level
        == _highest_triggered_level(review.assessments)
        for review in expected.reviews
    )
    checks = (
        LegalVerifierCheck(
            "check-legal-source-contract",
            "七份固定来源合同",
            len(expected.documents) == 6 and len(expected.rules) == 21,
            "1 份规则与 6 份委托书来自 allowlist 校验后的冻结字节；逻辑 ID、文件名、路径、大小和内容唯一性已复核。",
        ),
        LegalVerifierCheck(
            "check-legal-rule-contract",
            "21 条规则结构",
            len({rule.rule_id for rule in expected.rules}) == 21,
            "规则代码唯一，等级只使用高/中/低，名称、触发条件和说明均非空。",
        ),
        LegalVerifierCheck(
            "check-legal-assessment-coverage",
            "126 条逐项核查",
            len(expected_rows) == 126
            and len(set((row["文档ID"], row["规则ID"]) for row in expected_rows))
            == 126,
            "6 份文件 × 21 条规则完整展开，文档与规则组合没有漏项或重复。",
        ),
        LegalVerifierCheck(
            "check-legal-source-locators",
            "来源位置与原文",
            locator_check,
            "每条判断保留批准文件 Ref、段落或表格位置及真实原文摘录；不存在由报告反推来源的定位。",
        ),
        LegalVerifierCheck(
            "check-legal-dynamic-highest-risk",
            "动态最高风险等级",
            highest_check,
            "每份文件的综合等级由已触发规则的来源等级动态取最高，资料不足项单独保留。",
        ),
        LegalVerifierCheck(
            "check-legal-ledger-structure",
            "CSV 台账结构",
            csv_valid and len(csv_rows) == 126 and len(set(csv_pairs)) == 126,
            csv_detail,
        ),
        LegalVerifierCheck(
            "check-legal-ledger-content",
            "CSV 与来源重算一致",
            exact_ledger,
            "CSV 的状态、等级、位置、事实、判断、责任人与退出条件逐字段等于服务端从来源字节重新计算的台账。",
        ),
        LegalVerifierCheck(
            "check-legal-report-structure",
            "DOCX 报告结构",
            docx_valid
            and len(docx_tables) >= 8
            and len(assessment_rows) == 126
            and actual_docx_rows == expected_docx_rows,
            docx_detail,
        ),
        LegalVerifierCheck(
            "check-legal-report-summary",
            "DOCX 汇总与台账一致",
            docx_valid
            and dynamic_summary in docx_text
            and all(
                f"{review.document_name}：{LEVEL_LABELS[review.highest_triggered_level]}风险"
                in docx_text
                for review in expected.reviews
            ),
            "报告风险数量、每份最高等级和不可验证数量均来自同一份 126 行重算台账。",
        ),
        LegalVerifierCheck(
            "check-legal-boundary",
            "法律与外部动作边界",
            docx_valid and all(marker in docx_text for marker in boundary_markers),
            "报告明确是辅助核查，不构成法律意见，不签署文件，也不判断授权已经生效。",
        ),
    )
    return checks


def _validate_source_contract(
    sources: tuple[LegalSourceInput, ...],
) -> dict[str, LegalSourceInput]:
    if len(sources) != 7:
        raise LegalDelegationValidationError(
            "source-count", f"Legal-020 必须恰好包含 7 份输入，实际为 {len(sources)} 份。"
        )
    result: dict[str, LegalSourceInput] = {}
    seen_refs: set[str] = set()
    for source in sources:
        if source.logical_id in result:
            raise LegalDelegationValidationError(
                "duplicate-logical-id", f"来源逻辑 ID 重复：{source.logical_id}。"
            )
        if source.logical_id not in EXPECTED_FILE_NAMES:
            raise LegalDelegationValidationError(
                "unknown-source", f"出现未批准来源：{source.logical_id}。"
            )
        if source.file_name != EXPECTED_FILE_NAMES[source.logical_id]:
            raise LegalDelegationValidationError(
                "source-file-name",
                f"{source.logical_id} 文件名应为 {EXPECTED_FILE_NAMES[source.logical_id]}。",
            )
        if source.display_path != EXPECTED_DISPLAY_PATHS[source.logical_id]:
            raise LegalDelegationValidationError(
                "source-display-path",
                f"{source.logical_id} 安全展示路径不符合固定合同。",
            )
        if not source.allowlist_verified:
            raise LegalDelegationValidationError(
                "source-not-allowlisted", f"{source.file_name} 未通过 allowlist 完整性校验。"
            )
        if not source.content or len(source.content) != source.declared_size:
            raise LegalDelegationValidationError(
                "source-size", f"{source.file_name} 为空或与冻结大小不一致。"
            )
        if source.file_ref in seen_refs:
            raise LegalDelegationValidationError(
                "duplicate-file-ref", "两个逻辑来源指向同一个 file_ref。"
            )
        seen_refs.add(source.file_ref)
        result[source.logical_id] = source
    if set(result) != set(EXPECTED_FILE_NAMES):
        missing = sorted(set(EXPECTED_FILE_NAMES) - set(result))
        raise LegalDelegationValidationError(
            "source-set", "缺少固定来源：" + "、".join(missing)
        )
    document_hashes = [
        hashlib.sha256(result[logical_id].content).hexdigest()
        for logical_id in DOCUMENT_LOGICAL_IDS
    ]
    if len(set(document_hashes)) != len(document_hashes):
        raise LegalDelegationValidationError(
            "duplicate-document-content", "两份逻辑委托书使用了相同内容，禁止冒充独立来源。"
        )
    return result


def _parse_rules(content: bytes) -> tuple[LegalRule, ...]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise LegalDelegationValidationError(
            "rule-encoding", "规则 Markdown 不是 UTF-8 文本。"
        ) from exc
    if not text.strip():
        raise LegalDelegationValidationError("rule-empty", "规则 Markdown 为空。")
    lines = text.splitlines()
    blocks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for line_number, raw_line in enumerate(lines, start=1):
        if raw_line.strip().startswith("|"):
            current.append((line_number, raw_line.strip()))
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)

    rules: list[LegalRule] = []
    seen_rule_lines: set[int] = set()
    for block in blocks:
        header = _markdown_cells(block[0][1])
        code_rows = [
            (line_number, _markdown_cells(raw_line))
            for line_number, raw_line in block
            if re.match(r"^\|\s*[A-Z][0-9]{2}\s*\|", raw_line)
        ]
        if not code_rows:
            continue
        if header != ("编号", "风险项", "风险等级", "触发条件", "风险说明"):
            raise LegalDelegationValidationError(
                "rule-table-header", f"规则表第 {block[0][0]} 行表头损坏。"
            )
        if len(block) < 3 or not all(
            re.fullmatch(r":?-{3,}:?", cell.replace(" ", ""))
            for cell in _markdown_cells(block[1][1])
        ):
            raise LegalDelegationValidationError(
                "rule-table-separator", f"规则表第 {block[1][0]} 行分隔符损坏。"
            )
        for line_number, cells in code_rows:
            seen_rule_lines.add(line_number)
            if len(cells) != 5:
                raise LegalDelegationValidationError(
                    "rule-row-shape", f"规则第 {line_number} 行列数不是 5。"
                )
            rule_id, name, level_text, trigger, description = cells
            level = _parse_rule_level(level_text, line_number)
            if not name or not trigger or not description:
                raise LegalDelegationValidationError(
                    "rule-required", f"规则第 {line_number} 行缺少名称、触发条件或说明。"
                )
            rules.append(
                LegalRule(rule_id, name, level, trigger, description, line_number)
            )

    all_code_lines = {
        line_number
        for line_number, raw_line in enumerate(lines, start=1)
        if re.match(r"^\|\s*[A-Z][0-9]{2}\s*\|", raw_line.strip())
    }
    if seen_rule_lines != all_code_lines:
        raise LegalDelegationValidationError(
            "rule-table-coverage", "存在未被合法规则表覆盖的规则行。"
        )
    if len(rules) != 21:
        raise LegalDelegationValidationError(
            "rule-count", f"规则应为 21 条，实际解析到 {len(rules)} 条。"
        )
    by_code: dict[str, LegalRule] = {}
    for rule in rules:
        if rule.rule_id in by_code:
            raise LegalDelegationValidationError(
                "duplicate-rule", f"规则代码重复：{rule.rule_id}。"
            )
        by_code[rule.rule_id] = rule
    unknown = sorted(set(by_code) - EXPECTED_RULE_CODES)
    missing = sorted(EXPECTED_RULE_CODES - set(by_code))
    if unknown or missing:
        raise LegalDelegationValidationError(
            "rule-set",
            "规则代码集合不符合固定合同。"
            + (f" 未知：{'、'.join(unknown)}。" if unknown else "")
            + (f" 缺少：{'、'.join(missing)}。" if missing else ""),
        )
    return tuple(sorted(rules, key=lambda item: item.line_number))


def _markdown_cells(line: str) -> tuple[str, ...]:
    return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))


def _parse_rule_level(
    value: str, line_number: int
) -> Literal["high", "medium", "low"]:
    matches = [
        level
        for token, level in (("高", "high"), ("中", "medium"), ("低", "low"))
        if token in value
    ]
    if len(matches) != 1:
        raise LegalDelegationValidationError(
            "rule-level", f"规则第 {line_number} 行等级未知或含糊：{value}。"
        )
    return matches[0]  # type: ignore[return-value]


def _parse_docx(source: LegalSourceInput) -> ParsedDelegationDocument:
    try:
        archive = zipfile.ZipFile(io.BytesIO(source.content))
    except zipfile.BadZipFile as exc:
        raise LegalDelegationValidationError(
            "docx-package", f"{source.file_name} 不是有效 DOCX 包。"
        ) from exc
    with archive:
        names = archive.namelist()
        if (
            len(names) > 300
            or any(name.startswith(("/", "\\")) or ".." in name.split("/") for name in names)
            or sum(item.file_size for item in archive.infolist()) > 30 * 1024 * 1024
        ):
            raise LegalDelegationValidationError(
                "docx-package-boundary", f"{source.file_name} DOCX 包超出解析边界。"
            )
        if "word/document.xml" not in names:
            raise LegalDelegationValidationError(
                "docx-document-missing", f"{source.file_name} 缺少 word/document.xml。"
            )
        try:
            root = ET.fromstring(archive.read("word/document.xml"))
        except ET.ParseError as exc:
            raise LegalDelegationValidationError(
                "docx-xml", f"{source.file_name} document.xml 损坏。"
            ) from exc
        body = root.find(f"{W}body")
        if body is None:
            raise LegalDelegationValidationError(
                "docx-body", f"{source.file_name} 缺少正文。"
            )
        paragraphs: list[SourceParagraph] = []
        tables: list[SourceTable] = []
        paragraph_index = 0
        table_index = 0
        for child in body:
            if child.tag == f"{W}p":
                paragraph_index += 1
                text = "".join(node.text or "" for node in child.iter(f"{W}t")).strip()
                paragraphs.append(
                    SourceParagraph(
                        paragraph_index,
                        text,
                        child.find(f".//{W}drawing") is not None,
                        child.find(f".//{W}pict") is not None,
                    )
                )
            elif child.tag == f"{W}tbl":
                table_index += 1
                rows: list[tuple[str, ...]] = []
                for row in child.findall(f"{W}tr"):
                    rows.append(
                        tuple(
                            "".join(
                                node.text or "" for node in cell.iter(f"{W}t")
                            ).strip()
                            for cell in row.findall(f"{W}tc")
                        )
                    )
                tables.append(SourceTable(table_index, tuple(rows)))
        nonempty = [paragraph for paragraph in paragraphs if paragraph.text]
        table_texts = [cell for table in tables for row in table.rows for cell in row if cell]
        if not nonempty and not table_texts:
            raise LegalDelegationValidationError(
                "docx-empty", f"{source.file_name} 正文为空。"
            )
        text = "\n".join(
            [*(paragraph.text for paragraph in nonempty), *table_texts]
        )
        has_media = any(name.startswith("word/media/") for name in names)
        has_embedding = any(name.startswith("word/embeddings/") for name in names)
        has_digital_signature = any(
            name.startswith("_xmlsignatures/")
            or name.endswith("origin.sigs")
            or "digitalsignature" in name.casefold()
            for name in names
        )

    principal = _unique_field(paragraphs, "委托人", source.file_name)
    agent = _unique_field(paragraphs, "受托人", source.file_name)
    principal_name = _field_name(principal[1]) if principal else ""
    agent_name = _field_name(agent[1]) if agent else ""
    principal_line = principal[1] if principal else ""
    agent_line = agent[1] if agent else ""
    principal_identity = _first_match(
        principal_line, r"身份证号\s*[：:]\s*([0-9Xx]{15,18})"
    )
    credit_code = _first_match(
        principal_line, r"统一社会信用代码\s*[：:]\s*([0-9A-Za-z]{18})"
    )
    agent_identity = _first_match(
        agent_line, r"身份证号\s*[：:]\s*([0-9Xx]{15,18})"
    )
    agent_license = _first_match(
        agent_line, r"执业证号\s*[：:]\s*([0-9A-Za-z]{8,30})"
    )
    scope_paragraphs = [
        paragraph
        for paragraph in paragraphs
        if "授权范围" in paragraph.text or "全权委托" in paragraph.text
    ]
    scope_text = "；".join(paragraph.text for paragraph in scope_paragraphs)
    if "一般授权" in scope_text and "特别授权" in scope_text:
        raise LegalDelegationValidationError(
            "scope-conflict", f"{source.file_name} 同时声明一般授权与特别授权。"
        )
    authorization_kind: Literal["general", "special", "unclear"]
    if "一般授权" in scope_text:
        authorization_kind = "general"
    elif "特别授权" in scope_text:
        authorization_kind = "special"
    else:
        authorization_kind = "unclear"
    action_terms = ("承认", "放弃", "变更", "和解", "上诉", "强制执行", "签收")
    actions = tuple(term for term in action_terms if term in scope_text)
    start_date, end_date, date_locator = _authorization_dates(
        paragraphs, source.file_name
    )
    signed_date = _signed_date(paragraphs, source.file_name)
    signature_paragraphs = [
        paragraph
        for paragraph in paragraphs
        if any(
            label in paragraph.text
            for label in ("委托人签名", "委托人盖章", "法定代表人签名")
        )
    ]
    signature_values = [
        re.split(r"[：:]", paragraph.text, maxsplit=1)[1].strip()
        for paragraph in signature_paragraphs
        if re.search(r"[：:]", paragraph.text)
    ]
    signature_text_evidence = any(signature_values)
    signature_visual_evidence = any(
        paragraph.has_drawing or paragraph.has_pict
        for paragraph in signature_paragraphs
    )
    stamp_evidence = any(
        "盖章" in paragraph.text
        and (
            bool(re.split(r"[：:]", paragraph.text, maxsplit=1)[-1].strip())
            or paragraph.has_drawing
            or paragraph.has_pict
        )
        for paragraph in signature_paragraphs
    )
    representative_signature_evidence = any(
        "法定代表人签名" in paragraph.text
        and (
            bool(re.split(r"[：:]", paragraph.text, maxsplit=1)[-1].strip())
            or paragraph.has_drawing
            or paragraph.has_pict
        )
        for paragraph in signature_paragraphs
    )
    transfer_text = "；".join(
        paragraph.text
        for paragraph in paragraphs
        if "转委托" in paragraph.text or "转授权" in paragraph.text
    )
    liability_text = "；".join(
        paragraph.text
        for paragraph in paragraphs
        if "责任" in paragraph.text or "赔偿" in paragraph.text
    )
    signature_locator, signature_excerpt = _evidence(
        paragraphs,
        ("委托人签名", "委托人盖章", "法定代表人签名"),
    )
    return ParsedDelegationDocument(
        source=source,
        paragraphs=tuple(paragraphs),
        tables=tuple(tables),
        text=text,
        principal_name=principal_name,
        principal_identity=principal_identity or credit_code,
        agent_name=agent_name,
        agent_identity=agent_identity,
        agent_license=agent_license,
        principal_locator=f"P{principal[0]}" if principal else "全文",
        agent_locator=f"P{agent[0]}" if agent else "全文",
        is_enterprise=bool(credit_code or "公司" in principal_name or "企业" in principal_name),
        is_litigation="诉讼代理人" in text or "案号" in text,
        case_number_present=bool(re.search(r"案号\s*[：:]", text)),
        counterparty_present=bool(re.search(r"(?:我|本公司)与.+?之间", text)),
        scope_text=scope_text,
        scope_locator=(
            "、".join(f"P{paragraph.index}" for paragraph in scope_paragraphs)
            if scope_paragraphs
            else "全文"
        ),
        authorization_kind=authorization_kind,
        authorization_actions=actions,
        start_date=start_date,
        end_date=end_date,
        signed_date=signed_date,
        date_locator=date_locator,
        transfer_text=transfer_text,
        liability_text=liability_text,
        signature_locator=signature_locator,
        signature_excerpt=signature_excerpt,
        signature_text_evidence=signature_text_evidence,
        signature_visual_evidence=signature_visual_evidence,
        representative_signature_evidence=representative_signature_evidence,
        stamp_evidence=stamp_evidence,
        has_media=has_media,
        has_drawing=any(paragraph.has_drawing for paragraph in paragraphs),
        has_pict=any(paragraph.has_pict for paragraph in paragraphs),
        has_embedding=has_embedding,
        has_digital_signature=has_digital_signature,
    )


def _unique_field(
    paragraphs: list[SourceParagraph], label: str, file_name: str
) -> tuple[int, str] | None:
    matches = [
        (paragraph.index, paragraph.text)
        for paragraph in paragraphs
        if re.match(rf"^{re.escape(label)}\s*[：:]", paragraph.text)
    ]
    if not matches:
        return None
    values = {value for _, value in matches}
    if len(values) != 1:
        raise LegalDelegationValidationError(
            "field-conflict", f"{file_name} 的{label}字段存在冲突。"
        )
    return matches[0]


def _field_name(line: str) -> str:
    value = re.split(r"[：:]", line, maxsplit=1)[-1]
    return re.split(r"[，,]", value, maxsplit=1)[0].strip()


def _first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _authorization_dates(
    paragraphs: list[SourceParagraph], file_name: str
) -> tuple[date | None, date | None, str]:
    lines = [paragraph for paragraph in paragraphs if "授权期限" in paragraph.text]
    if len({paragraph.text for paragraph in lines}) > 1:
        raise LegalDelegationValidationError(
            "date-conflict", f"{file_name} 存在相互冲突的授权期限。"
        )
    if not lines:
        return None, None, "全文"
    line = lines[0]
    start = _date_match(line.text, r"自\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
    end = _date_match(line.text, r"至\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
    if re.search(r"\d{4}\s*年", line.text) and start is None and end is None:
        raise LegalDelegationValidationError(
            "date-format", f"{file_name} 授权期限日期格式无法解析。"
        )
    if start and end and start > end:
        raise LegalDelegationValidationError(
            "date-order", f"{file_name} 授权起始日晚于截止日。"
        )
    return start, end, f"P{line.index}"


def _signed_date(
    paragraphs: list[SourceParagraph], file_name: str
) -> date | None:
    lines = [paragraph for paragraph in paragraphs if "委托日期" in paragraph.text]
    if len({paragraph.text for paragraph in lines}) > 1:
        raise LegalDelegationValidationError(
            "signed-date-conflict", f"{file_name} 存在相互冲突的委托日期。"
        )
    if not lines:
        return None
    value = _date_match(
        lines[0].text,
        r"委托日期\s*[：:]\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
    )
    if value is None:
        raise LegalDelegationValidationError(
            "signed-date-format", f"{file_name} 委托日期格式无法解析。"
        )
    return value


def _date_match(text: str, pattern: str) -> date | None:
    match = re.search(pattern, text)
    if not match:
        return None
    try:
        return date(*(int(value) for value in match.groups()))
    except ValueError as exc:
        raise LegalDelegationValidationError(
            "date-value", f"日期数值无效：{match.group(0)}。"
        ) from exc


def _review_document(
    document: ParsedDelegationDocument,
    rules: tuple[LegalRule, ...],
) -> AgentControlLoopLegalDocumentReview:
    document_id = document.source.logical_id
    assessments = tuple(
        _evaluate_rule(document_id, document, rule) for rule in rules
    )
    highest = _highest_triggered_level(assessments)
    triggered = sum(item.status == "triggered" for item in assessments)
    unverifiable = sum(item.status == "unverifiable" for item in assessments)
    signing_status = document.signing_evidence_status
    return AgentControlLoopLegalDocumentReview(
        document_id=document_id,
        document_name=document.source.file_name,
        source_file_ref=document.source.file_ref,
        highest_triggered_level=highest,
        triggered_count=triggered,
        unverifiable_count=unverifiable,
        signing_evidence_status=signing_status,
        summary=(
            f"已触发 {triggered} 项，资料不足 {unverifiable} 项；"
            f"最高已触发等级为{LEVEL_LABELS[highest]}。"
        ),
        assessments=list(assessments),
    )


def _evaluate_rule(
    document_id: str,
    document: ParsedDelegationDocument,
    rule: LegalRule,
) -> AgentControlLoopLegalRuleAssessment:
    status: Literal["triggered", "not_triggered", "unverifiable"]
    locator: str
    excerpt: str
    fact: str
    reason: str
    text = document.text

    if rule.rule_id == "R01":
        locator, excerpt = _evidence(document.paragraphs, ("委托人",))
        status = "not_triggered" if document.principal_identity else "triggered"
        fact = (
            "委托人身份证明字段已提取。"
            if document.principal_identity
            else "委托人行未提取到身份证号或统一社会信用代码。"
        )
        reason = "身份字段存在。" if status == "not_triggered" else "满足身份证明缺失条件。"
    elif rule.rule_id == "R02":
        locator, excerpt = _evidence(document.paragraphs, ("受托人",))
        has_identity = bool(document.agent_identity or document.agent_license)
        status = "not_triggered" if has_identity else "triggered"
        fact = (
            "受托人身份证明或律师执业证号已提取。"
            if has_identity
            else "受托人行未提取到身份证号或律师执业证号。"
        )
        reason = "身份字段存在。" if has_identity else "满足受托人身份证明缺失条件。"
    elif rule.rule_id == "M02":
        locator, excerpt = _evidence(document.paragraphs, ("委托人", "一案"))
        status = "unverifiable"
        fact = "批准来源仅含委托书本体，没有合同、诉状或母公司授权证明。"
        reason = "无法用现有来源比较委托人与外部业务主体。"
    elif rule.rule_id == "M03":
        locator, excerpt = _evidence(document.paragraphs, ("受托人", "诉讼代理人"))
        if "律师" in document.agent_name and not document.agent_license:
            status = "triggered"
            fact = "受托人以律师身份出现，但未提取到律师执业证号。"
            reason = "来源直接满足执业证号无法核实条件。"
        elif "律师" in document.agent_name and document.agent_license:
            status = "unverifiable"
            fact = "受托人以律师身份出现且执业证号已提取。"
            reason = "当前没有律师资格 Registry 或 Connector 回执，字段存在不等于资质已核验。"
        elif document.is_litigation:
            status = "unverifiable"
            fact = "受托人为非律师自然人，现有来源未包含近亲属、员工关系或法院许可材料。"
            reason = "代理资格依赖未提供的关联证明，不能猜测。"
        else:
            status = "not_triggered"
            fact = "正文未识别为诉讼代理场景。"
            reason = "当前来源未满足诉讼代理资质规则的适用前提。"
    elif rule.rule_id == "L01":
        locator, excerpt = _evidence(document.paragraphs, ("案号", "纠纷"))
        complete = document.case_number_present and document.counterparty_present
        status = "not_triggered" if complete else "triggered"
        fact = (
            "正文包含案号和明确的对方当事人。"
            if complete
            else "案号或对方当事人信息不完整。"
        )
        reason = "案件可唯一指向。" if complete else "满足案件信息不完整条件。"
    elif rule.rule_id == "R03":
        locator, excerpt = _evidence(document.paragraphs, ("授权范围", "全权委托"))
        authorization_label = {
            "general": "一般授权",
            "special": "特别授权",
        }.get(document.authorization_kind)
        status = (
            "not_triggered"
            if authorization_label is not None
            else "triggered"
        )
        fact = (
            f"授权类型已识别为{authorization_label}。"
            if status == "not_triggered"
            else "正文未出现一般授权或特别授权，存在全权或范围缺失表述。"
        )
        reason = "授权类型明确。" if status == "not_triggered" else "满足范围完全未明确条件。"
    elif rule.rule_id == "M01":
        locator, excerpt = _evidence(document.paragraphs, ("授权范围",))
        broad = (
            document.authorization_kind == "special"
            and len(document.authorization_actions) >= 3
            and {"承认", "放弃"} <= set(document.authorization_actions)
        )
        status = "triggered" if broad else "not_triggered"
        fact = (
            f"特别授权列出 {len(document.authorization_actions)} 项，并同时包含承认和放弃。"
            if broad
            else "未同时满足特别授权、至少三项以及承认和放弃三项条件。"
        )
        reason = "满足特别授权过宽条件。" if broad else "未命中该组合条件。"
    elif rule.rule_id == "M04":
        locator, excerpt = _evidence(document.paragraphs, ("授权范围", "一切事宜", "全部权利"))
        vague = any(term in document.scope_text for term in ("一切事宜", "所有相关事项", "全部权利"))
        status = "triggered" if vague and not document.authorization_actions else "not_triggered"
        fact = "正文存在无边界授权表述。" if status == "triggered" else "未发现该规则列举的无边界表述组合。"
        reason = "满足笼统无边界条件。" if status == "triggered" else "未命中该项。"
    elif rule.rule_id == "L02":
        locator, excerpt = _evidence(document.paragraphs, ("诉讼代理人", "授权范围"))
        if document.authorization_kind == "unclear":
            status = "unverifiable"
            fact = "授权范围未明确，无法进一步判断与业务场景是否匹配。"
            reason = "需先补齐授权范围。"
        else:
            status = "not_triggered"
            fact = "诉讼场景与立案、庭审或诉讼处分事项没有明显类型冲突。"
            reason = "当前文本未出现规则示例中的明显不匹配。"
    elif rule.rule_id == "R04":
        locator, excerpt = _evidence(document.paragraphs, ("授权期限",))
        missing_both = document.start_date is None and document.end_date is None
        status = "triggered" if missing_both else "not_triggered"
        fact = "授权起止日期均缺失。" if missing_both else "至少提取到一个授权期限端点。"
        reason = "满足期限完全缺失条件。" if missing_both else "未命中两端均缺失条件。"
    elif rule.rule_id == "M05":
        locator, excerpt = _evidence(document.paragraphs, ("授权期限", "长期有效", "永久授权"))
        permanent = "长期有效" in text or "永久授权" in text
        if permanent:
            status = "triggered"
            fact = "正文包含长期有效或永久授权表述。"
            reason = "满足无限期授权条件。"
        elif document.end_date and document.signed_date:
            threshold = _add_years(document.signed_date, 3)
            status = "triggered" if document.end_date > threshold else "not_triggered"
            fact = f"委托日期为 {document.signed_date.isoformat()}，截止日为 {document.end_date.isoformat()}。"
            reason = "截止日超过三年阈值。" if status == "triggered" else "未超过三年阈值。"
        else:
            status = "unverifiable"
            fact = "现有日期不足以计算委托日期至截止日的三年阈值。"
            reason = "需要委托日期和截止日，不能使用静默分母或猜测日期。"
    elif rule.rule_id == "M06":
        locator, excerpt = _evidence(document.paragraphs, ("授权期限",))
        exactly_one = (document.start_date is None) != (document.end_date is None)
        status = "triggered" if exactly_one else "not_triggered"
        fact = "授权期限仅有一个端点。" if exactly_one else "授权期限不是单端缺失。"
        reason = "满足起止不完整条件。" if exactly_one else "未命中该项。"
    elif rule.rule_id == "L03":
        locator, excerpt = _evidence(document.paragraphs, ("委托日期",))
        status = "not_triggered" if document.signed_date else "triggered"
        fact = "委托日期已提取。" if document.signed_date else "正文未识别到委托日期。"
        reason = "日期字段存在。" if document.signed_date else "满足委托日期缺失条件。"
    elif rule.rule_id == "M07":
        locator, excerpt = _evidence(document.paragraphs, ("转委托", "转授权"))
        mentioned = bool(document.transfer_text)
        status = "not_triggered" if mentioned else "triggered"
        fact = "正文已提及转委托安排。" if mentioned else "全文未提及是否允许转委托。"
        reason = "已有转委托约定。" if mentioned else "满足转委托约定缺失条件。"
    elif rule.rule_id == "L04":
        locator, excerpt = _evidence(document.paragraphs, ("转委托", "转授权"))
        allowed = bool(re.search(r"允许.{0,6}(?:转委托|转授权)", document.transfer_text))
        restrictions = (
            any(term in document.transfer_text for term in ("范围", "事项")),
            any(term in document.transfer_text for term in ("次数", "一次", "二次")),
            any(term in document.transfer_text for term in ("资质", "资格", "律师")),
        )
        status = "triggered" if allowed and not all(restrictions) else "not_triggered"
        fact = (
            "允许转委托，但范围、次数或资质限制不完整。"
            if status == "triggered"
            else "未出现允许转委托且限制不完整的组合。"
        )
        reason = "满足限制条款不完整条件。" if status == "triggered" else "未命中该项。"
    elif rule.rule_id == "M08":
        locator, excerpt = _evidence(document.paragraphs, ("责任", "赔偿", "后果"))
        present = bool(document.liability_text and re.search(r"承担|赔偿|后果", document.liability_text))
        status = "not_triggered" if present else "triggered"
        fact = "正文存在责任承担条款。" if present else "全文未识别到责任承担或行为后果归属条款。"
        reason = "责任条款存在。" if present else "满足责任承担约定缺失条件。"
    elif rule.rule_id == "L05":
        locator, excerpt = _evidence(document.paragraphs, ("不承担任何责任", "自行承担一切后果"))
        absolute = any(term in text for term in ("受托人不承担任何责任", "委托人自行承担一切后果"))
        status = "triggered" if absolute else "not_triggered"
        fact = "正文包含绝对免责表述。" if absolute else "未发现规则列举的绝对免责表述。"
        reason = "满足免责瑕疵条件。" if absolute else "未命中该项。"
    elif rule.rule_id == "R05":
        locator, excerpt = document.signature_locator, document.signature_excerpt
        signing = document.signing_evidence_status
        if signing == "present":
            status = "not_triggered"
            fact = "签署栏存在文本、签署位置图形或数字签署对象。"
            reason = "未命中完全缺失条件；签署真实性仍需人工核验。"
        elif signing == "absent":
            status = "triggered"
            fact = "签署栏为空，DOCX 包内没有 media、drawing、pict、嵌入或数字签名。"
            reason = "满足签字或盖章完全缺失条件。"
        else:
            status = "unverifiable"
            fact = "DOCX 包含图形或嵌入对象，但无法确定其是否属于签署栏。"
            reason = "不能把任意图片自动当作签名或盖章。"
    elif rule.rule_id == "R06":
        locator, excerpt = _evidence(document.paragraphs, ("受托人",))
        status = "not_triggered" if document.agent_name else "triggered"
        fact = "受托人姓名或名称已提取。" if document.agent_name else "正文未识别受托人姓名或名称。"
        reason = "受托人字段存在。" if document.agent_name else "满足代理主体缺失条件。"
    elif rule.rule_id == "M09":
        locator, excerpt = document.signature_locator, document.signature_excerpt
        only_personal = (
            document.is_enterprise
            and document.representative_signature_evidence
            and not document.stamp_evidence
        )
        status = "triggered" if only_personal else "not_triggered"
        fact = (
            "企业委托书存在法定代表人签名证据，但没有单位公章证据。"
            if only_personal
            else "未出现企业仅有个人签名而无公章的组合；完全未签署由 R05 单独处理。"
        )
        reason = "满足企业仅签字无公章条件。" if only_personal else "未命中该项。"
    elif rule.rule_id == "L06":
        locator, excerpt = _evidence(document.paragraphs, ("附件", "附后"))
        mentions = "附件" in text or "附后" in text
        has_list = "附件清单" in text or bool(document.tables) or document.has_embedding
        status = "triggered" if mentions and not has_list else "not_triggered"
        fact = "正文提及附件但未发现附件清单或嵌入材料。" if status == "triggered" else "未出现附件提及与清单缺失的组合。"
        reason = "满足附件关联缺失条件。" if status == "triggered" else "未命中该项。"
    else:
        raise LegalDelegationValidationError(
            "unsupported-rule", f"没有服务端判定器的规则：{rule.rule_id}。"
        )

    owner, action, exit_condition = REMEDIATION[rule.rule_id]
    if status == "not_triggered":
        action = "保留当前来源位置，并在正式使用前由法务人员复核。"
        exit_condition = "该规则持续未命中，且来源修订后重新执行核查。"
    judgment = (
        f"来源事实满足规则“{rule.trigger}”，该项已触发。"
        if status == "triggered"
        else (
            f"来源事实未满足规则“{rule.trigger}”，当前未触发。"
            if status == "not_triggered"
            else f"现有批准来源不足以判断规则“{rule.trigger}”。"
        )
    )
    return AgentControlLoopLegalRuleAssessment(
        assessment_id=f"legal-assessment-{document_id.casefold()}-{rule.rule_id.casefold()}",
        rule_id=rule.rule_id,
        rule_name=rule.name,
        rule_level=rule.level,
        status=status,
        source_locator=locator,
        excerpt=excerpt,
        fact=fact,
        judgment=judgment,
        reason=reason,
        owner=owner,
        remediation_action=action,
        exit_condition=exit_condition,
    )


def _evidence(
    paragraphs: tuple[SourceParagraph, ...] | list[SourceParagraph],
    keywords: tuple[str, ...],
) -> tuple[str, str]:
    nonempty = [paragraph for paragraph in paragraphs if paragraph.text]
    for paragraph in nonempty:
        if any(keyword in paragraph.text for keyword in keywords):
            return f"P{paragraph.index}", paragraph.text[:1_000]
    if not nonempty:
        raise LegalDelegationValidationError("evidence-empty", "委托书没有可引用正文。")
    return f"全文 P1-P{max(paragraph.index for paragraph in paragraphs)}", nonempty[0].text[:1_000]


def _add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(year=value.year + years, day=28)


def _highest_triggered_level(
    assessments: tuple[AgentControlLoopLegalRuleAssessment, ...]
    | list[AgentControlLoopLegalRuleAssessment],
) -> Literal["none", "low", "medium", "high"]:
    levels = [
        assessment.rule_level
        for assessment in assessments
        if assessment.status == "triggered"
    ]
    if not levels:
        return "none"
    return max(levels, key=lambda value: LEVEL_ORDER[value])  # type: ignore[return-value]


def _legal_outcome(
    reviews: tuple[AgentControlLoopLegalDocumentReview, ...], rule_count: int
) -> AgentControlLoopLegalReviewOutcome:
    counts = {
        level: sum(review.highest_triggered_level == level for review in reviews)
        for level in ("high", "medium", "low", "none")
    }
    critical_unverifiable = sum(
        assessment.status == "unverifiable"
        and assessment.rule_level in {"high", "medium"}
        for review in reviews
        for assessment in review.assessments
    )
    signing_evidence_count = sum(
        review.signing_evidence_status == "present" for review in reviews
    )
    review_required = (
        counts["high"] > 0
        or critical_unverifiable > 0
        or signing_evidence_count < len(reviews)
    )
    decision = (
        "不得据此签署，必须法务复核"
        if review_required
        else "可进入法务人工复核，不代表授权已经有效"
    )
    return AgentControlLoopLegalReviewOutcome(
        outcome_id="legal-review-outcome-delegation",
        status="review_required" if review_required else "cleared",
        decision=decision,
        summary=_summary_sentence_from_counts(
            len(reviews), counts, critical_unverifiable, signing_evidence_count
        ),
        document_count=len(reviews),
        rule_count=rule_count,
        assessment_count=sum(len(review.assessments) for review in reviews),
        high_risk_document_count=counts["high"],
        medium_risk_document_count=counts["medium"],
        low_risk_document_count=counts["low"],
        no_trigger_document_count=counts["none"],
        critical_unverifiable_count=critical_unverifiable,
        signing_evidence_count=signing_evidence_count,
        human_review_required=True,
        signing_status=(
            "evidence_present"
            if signing_evidence_count == len(reviews)
            else "evidence_incomplete"
        ),
        documents=list(reviews),
    )


def _summary_sentence(outcome: AgentControlLoopLegalReviewOutcome) -> str:
    counts = {
        "high": outcome.high_risk_document_count,
        "medium": outcome.medium_risk_document_count,
        "low": outcome.low_risk_document_count,
        "none": outcome.no_trigger_document_count,
    }
    return _summary_sentence_from_counts(
        outcome.document_count,
        counts,
        outcome.critical_unverifiable_count,
        outcome.signing_evidence_count,
    )


def _summary_sentence_from_counts(
    document_count: int,
    counts: dict[str, int],
    critical_unverifiable: int,
    signing_evidence_count: int,
) -> str:
    return (
        f"共 {document_count} 份文件：高风险 {counts['high']} 份、"
        f"中风险 {counts['medium']} 份、低风险 {counts['low']} 份、"
        f"无已触发项 {counts['none']} 份；关键资料不足 {critical_unverifiable} 项；"
        f"可审查签署证据 {signing_evidence_count}/{document_count} 份。"
    )


def _business_outcome(
    legal: AgentControlLoopLegalReviewOutcome,
) -> AgentControlLoopBusinessGateOutcome:
    gates = [
        AgentControlLoopBusinessGate(
            gate_id="business-gate-legal-high-risk-zero",
            label="高风险文件清零",
            passed=legal.high_risk_document_count == 0,
            numerator=float(legal.high_risk_document_count),
            denominator=float(legal.document_count),
            operator="<=",
            threshold=0,
            actual=float(legal.high_risk_document_count),
            unit="count",
            formula="逐文件最高已触发规则等级为高的文件数",
            source_rule="全部 21 条规则逐项判断后，按已触发项的来源等级取最高。",
            result=(
                "没有高风险文件。"
                if legal.high_risk_document_count == 0
                else f"仍有 {legal.high_risk_document_count} 份高风险文件。"
            ),
        ),
        AgentControlLoopBusinessGate(
            gate_id="business-gate-legal-critical-unverifiable-zero",
            label="高、中等级规则无资料不足项",
            passed=legal.critical_unverifiable_count == 0,
            numerator=float(legal.critical_unverifiable_count),
            denominator=float(legal.assessment_count),
            operator="<=",
            threshold=0,
            actual=float(legal.critical_unverifiable_count),
            unit="count",
            formula="状态为 unverifiable 且来源规则等级为高或中的逐项记录数",
            source_rule="资料不足不能自动判为未触发，也不能被报告结论覆盖。",
            result=(
                "高、中等级规则均有足够来源判断。"
                if legal.critical_unverifiable_count == 0
                else f"有 {legal.critical_unverifiable_count} 项关键规则仍缺少关联材料。"
            ),
        ),
        AgentControlLoopBusinessGate(
            gate_id="business-gate-legal-signing-evidence-complete",
            label="六份文件均有可审查签署对象",
            passed=legal.signing_evidence_count == legal.document_count,
            numerator=float(legal.signing_evidence_count),
            denominator=float(legal.document_count),
            operator="==",
            threshold=float(legal.document_count),
            actual=float(legal.signing_evidence_count),
            unit="count",
            formula="存在签署栏文本、签署位置图形或数字签署对象的文件数",
            source_rule="R05 规则；签署对象存在仍不等于签名真实或授权生效。",
            result=(
                "六份文件均有可审查签署对象。"
                if legal.signing_evidence_count == legal.document_count
                else f"仅 {legal.signing_evidence_count}/{legal.document_count} 份存在可审查签署对象。"
            ),
        ),
    ]
    failed = sum(not gate.passed for gate in gates)
    return AgentControlLoopBusinessGateOutcome(
        outcome_id="business-outcome-legal-delegation",
        outcome_kind="legal_delegation_review",
        status="failed" if failed else "passed",
        decision=legal.decision,
        summary=(
            f"{failed}/{len(gates)} 条法务业务 Gate 未通过；"
            "确定性检查通过只证明来源、计算和文件结构可复核。"
            if failed
            else "3 条法务业务 Gate 均满足；仍须法务人员作出最终判断。"
        ),
        total_gate_count=len(gates),
        failed_gate_count=failed,
        gates=gates,
        auxiliary_metrics=[],
        records=[],
    )


def _ledger_rows(analysis: LegalDelegationAnalysis) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for review in analysis.reviews:
        for assessment in review.assessments:
            rows.append(
                dict(
                    zip(
                        LEDGER_HEADERS,
                        (
                            review.document_id,
                            review.document_name,
                            LEVEL_LABELS[review.highest_triggered_level],
                            assessment.rule_id,
                            assessment.rule_name,
                            LEVEL_LABELS[assessment.rule_level],
                            assessment.status,
                            review.source_file_ref,
                            assessment.source_locator,
                            assessment.excerpt,
                            assessment.fact,
                            assessment.judgment,
                            assessment.reason,
                            assessment.owner,
                            assessment.remediation_action,
                            assessment.exit_condition,
                        ),
                        strict=True,
                    )
                )
            )
    return rows


def _ledger_csv(analysis: LegalDelegationAnalysis) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(LEDGER_HEADERS), lineterminator="\n")
    writer.writeheader()
    writer.writerows(_ledger_rows(analysis))
    return output.getvalue().encode("utf-8-sig")


def _parse_ledger(content: bytes) -> tuple[bool, list[dict[str, str]], str]:
    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = [dict(row) for row in reader]
    except (UnicodeDecodeError, csv.Error) as exc:
        return False, [], f"CSV 无法解析：{exc}"
    if tuple(reader.fieldnames or ()) != LEDGER_HEADERS:
        return False, rows, "CSV 表头与 16 列固定输出合同不一致。"
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        return False, rows, "CSV 存在列错位或缺失字段。"
    return True, rows, "CSV 表头、列数和编码可解析。"


def _report_docx(analysis: LegalDelegationAnalysis) -> tuple[bytes, int]:
    legal = analysis.legal_outcome
    summary_rows = [
        [
            review.document_id,
            review.document_name,
            LEVEL_LABELS[review.highest_triggered_level],
            str(review.triggered_count),
            str(review.unverifiable_count),
            {
                "present": "存在可审查对象",
                "absent": "未发现",
                "unverifiable": "位置不可确认",
            }[review.signing_evidence_status],
        ]
        for review in analysis.reviews
    ]
    blocks: list[tuple[str, object]] = [
        ("title", "授权委托书风控报告"),
        ("heading", "一、结论与边界"),
        ("body", legal.decision),
        ("body", _summary_sentence(legal)),
        (
            "body",
            "本报告是固定 Legal-020 公开资料的辅助核查，不是正式法律意见；Agent 没有签署任何文件，不代表授权有效，也没有执行外部动作。所有结论必须由法务人员复核。",
        ),
        ("heading", "二、来源与规则边界"),
        (
            "body",
            "服务端只读取 1 份规则 Markdown 与 6 份 DOCX 的 allowlist 冻结字节；不读取 task.md、rubric 或 solution。规则表解析为 21 条，六份文件逐条形成 126 项判断。",
        ),
        (
            "table",
            (
                ["来源", "数量", "处理方式", "不能证明"],
                [
                    ["风控规则 Markdown", "1", "解析 21 条规则及来源等级", "规则本身的法律充分性"],
                    ["授权委托书 DOCX", "6", "解析正文、表格、段落和包内签署对象", "签名真伪或授权已经生效"],
                ],
            ),
        ),
        ("heading", "三、六份文件摘要"),
        (
            "table",
            (
                ["文档ID", "文件", "最高等级", "已触发", "资料不足", "签署对象"],
                summary_rows,
            ),
        ),
        ("heading", "四、逐文件 21 条规则台账"),
    ]
    for review in analysis.reviews:
        blocks.extend(
            [
                (
                    "heading",
                    f"{review.document_name}：{LEVEL_LABELS[review.highest_triggered_level]}风险",
                ),
                ("body", review.summary),
                (
                    "table",
                    (
                        ["文档ID", "规则ID", "规则名称", "等级", "状态", "来源位置", "事实", "规则判断"],
                        [
                            [
                                review.document_id,
                                item.rule_id,
                                item.rule_name,
                                LEVEL_LABELS[item.rule_level],
                                STATUS_LABELS[item.status],
                                item.source_locator,
                                item.fact,
                                item.judgment,
                            ]
                            for item in review.assessments
                        ],
                    ),
                ),
            ]
        )
    review_rows = [
        [
            review.document_name,
            item.rule_id,
            STATUS_LABELS[item.status],
            item.owner,
            item.remediation_action,
            item.exit_condition,
        ]
        for review in analysis.reviews
        for item in review.assessments
        if item.status != "not_triggered"
    ]
    blocks.extend(
        [
            ("heading", "五、人工复核清单"),
            (
                "table",
                (
                    ["文件", "规则", "状态", "责任人", "处置建议", "退出条件"],
                    review_rows,
                ),
            ),
            ("heading", "六、最终使用边界"),
            (
                "body",
                "确定性检查仅证明来源合同、规则覆盖、状态计算和两个成果文件一致。不得据此自动签署、认定授权有效、替代律师意见或执行任何外部动作。",
            ),
        ]
    )
    return _docx_bytes(blocks), sum(kind == "table" for kind, _ in blocks)


def _docx_bytes(blocks: list[tuple[str, object]]) -> bytes:
    def run(text: str, *, bold: bool = False, size: int = 22) -> str:
        properties = (
            f'<w:rPr>{"<w:b/>" if bold else ""}'
            f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
        )
        return f'<w:r>{properties}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'

    def paragraph(text: str, *, bold: bool = False, size: int = 22) -> str:
        return f"<w:p>{run(text, bold=bold, size=size)}</w:p>"

    def table(headers: list[str], rows: list[list[str]]) -> str:
        def cell(value: str, *, header: bool = False) -> str:
            return (
                "<w:tc><w:tcPr/><w:p>"
                + run(value, bold=header, size=18)
                + "</w:p></w:tc>"
            )

        header_row = "<w:tr>" + "".join(cell(item, header=True) for item in headers) + "</w:tr>"
        body_rows = "".join(
            "<w:tr>" + "".join(cell(str(item)) for item in row) + "</w:tr>"
            for row in rows
        )
        return (
            '<w:tbl><w:tblPr><w:tblBorders>'
            '<w:top w:val="single" w:sz="4" w:color="999999"/>'
            '<w:left w:val="single" w:sz="4" w:color="999999"/>'
            '<w:bottom w:val="single" w:sz="4" w:color="999999"/>'
            '<w:right w:val="single" w:sz="4" w:color="999999"/>'
            '<w:insideH w:val="single" w:sz="4" w:color="BBBBBB"/>'
            '<w:insideV w:val="single" w:sz="4" w:color="BBBBBB"/>'
            "</w:tblBorders></w:tblPr>"
            + header_row
            + body_rows
            + "</w:tbl>"
        )

    body: list[str] = []
    for kind, value in blocks:
        if kind == "title":
            body.append(paragraph(str(value), bold=True, size=34))
        elif kind == "heading":
            body.append(paragraph(str(value), bold=True, size=28))
        elif kind == "body":
            body.append(paragraph(str(value), size=22))
        elif kind == "table":
            headers, rows = value  # type: ignore[misc]
            body.append(table(headers, rows))
        else:
            raise ValueError(f"unknown DOCX block: {kind}")
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}"><w:body>'
        + "".join(body)
        + '<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>'
        '<w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720"/>'
        "</w:sectPr></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)
    return output.getvalue()


def _parse_generated_docx(
    content: bytes,
) -> tuple[bool, str, list[list[list[str]]], str]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        return False, "", [], f"DOCX 无法解析：{exc}"
    text = "\n".join(node.text or "" for node in root.iter(f"{W}t"))
    tables: list[list[list[str]]] = []
    for raw_table in root.iter(f"{W}tbl"):
        table: list[list[str]] = []
        for raw_row in raw_table.findall(f"{W}tr"):
            table.append(
                [
                    "".join(node.text or "" for node in cell.iter(f"{W}t"))
                    for cell in raw_row.findall(f"{W}tc")
                ]
            )
        tables.append(table)
    return True, text, tables, f"DOCX 可解析，包含 {len(tables)} 张表格。"
