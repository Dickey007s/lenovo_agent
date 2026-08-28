"""Source-derived candidate review for the fixed public FORTE hr-001 bundle.

The adapter parses two approved JD DOCX files and five approved resume PDFs from
frozen bytes.  It never reads benchmark tasks or solutions, never makes a hiring
decision, and never uses protected attributes as matching inputs.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from pypdf import PdfReader

from packages.contracts.harness_models import (
    AgentControlLoopCandidateConditionAssessment,
    AgentControlLoopCandidateReviewOutcome,
    AgentControlLoopCandidateRoleReview,
)


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"

JD_BD_ID = "JD-BD"
JD_TEXT_ID = "JD-TEXT"
CANDIDATE_LOGICAL_IDS = tuple(f"CAND-{index:02d}" for index in range(1, 6))
SOURCE_ORDER = (JD_BD_ID, JD_TEXT_ID, *CANDIDATE_LOGICAL_IDS)

EXPECTED_FILE_NAMES = {
    JD_BD_ID: "外卖商户BD岗位JD.docx",
    JD_TEXT_ID: "文本评测岗位JD.docx",
    "CAND-01": "周伦简历.pdf",
    "CAND-02": "孙博文简历.pdf",
    "CAND-03": "李雨桐简历.pdf",
    "CAND-04": "王琳达简历.pdf",
    "CAND-05": "赵晨曦简历.pdf",
}
EXPECTED_DISPLAY_PATHS = {
    logical_id: f"人力招聘/{file_name}" for logical_id, file_name in EXPECTED_FILE_NAMES.items()
}
EXPECTED_CANDIDATE_NAMES = {
    "CAND-01": "周伦",
    "CAND-02": "孙博文",
    "CAND-03": "李雨桐",
    "CAND-04": "王琳达",
    "CAND-05": "赵晨曦",
}
ROLE_NAMES = {
    "merchant_bd": "外卖商户BD",
    "text_evaluation": "文本评测",
}

STATUS_LABELS = {
    "met": "有来源支持",
    "not_met": "明确不满足",
    "unverifiable": "资料不足",
    "human_exception_required": "需人工例外判断",
}
RECOMMENDATION_LABELS = {
    "recommended_for_human_review": "建议进入人工复核",
    "explicit_hard_gap": "存在明确硬条件缺口",
    "insufficient_evidence": "资料不足，需补证",
    "exception_review_required": "需要人工决定是否适用例外",
}
CONDITION_TYPE_LABELS = {
    "responsibility": "岗位职责",
    "default_threshold": "默认门槛",
    "required": "必要项",
    "preferred": "优先项",
    "bonus": "加分项",
}

EDUCATION_RANKS = {
    "高中": 1,
    "中专": 1,
    "大专": 2,
    "本科": 3,
    "硕士": 4,
    "博士": 5,
}

LEDGER_HEADERS = (
    "岗位ID",
    "岗位",
    "候选人ID",
    "候选人",
    "总体建议",
    "条件ID",
    "条件类型",
    "条件名称",
    "JD来源Ref",
    "JD位置",
    "JD原文",
    "简历来源Ref",
    "简历位置",
    "简历原文",
    "状态",
    "事实",
    "判断",
    "原因",
    "责任人",
    "面试或补证动作",
    "退出条件",
)


class CandidateReviewValidationError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class CandidateSourceInput:
    logical_id: str
    file_name: str
    display_path: str
    file_ref: str
    content: bytes
    declared_size: int
    allowlist_verified: bool


@dataclass(frozen=True)
class SourceLine:
    number: int
    locator: str
    text: str


@dataclass(frozen=True)
class JobCondition:
    role_id: str
    condition_id: str
    condition_type: str
    label: str
    semantic_key: str
    source_file_ref: str
    locator: str
    excerpt: str
    required_for_recommendation: bool
    education_threshold_rank: int | None = None
    experience_threshold_months: int | None = None
    exception_allowed: bool = False


@dataclass(frozen=True)
class ParsedJob:
    role_id: str
    role_name: str
    source_file_ref: str
    file_name: str
    lines: tuple[SourceLine, ...]
    conditions: tuple[JobCondition, ...]


@dataclass(frozen=True)
class ParsedCandidate:
    candidate_id: str
    candidate_name: str
    source_file_ref: str
    file_name: str
    lines: tuple[SourceLine, ...]
    education_level: str | None
    education_rank: int | None
    education_in_progress: bool
    education_line: SourceLine | None
    ai_experience_months: int | None
    positive_evidence: dict[str, tuple[SourceLine, ...]]
    negative_evidence: dict[str, tuple[SourceLine, ...]]


@dataclass(frozen=True)
class CandidateReviewAnalysis:
    jobs: tuple[ParsedJob, ...]
    candidates: tuple[ParsedCandidate, ...]
    reviews: tuple[AgentControlLoopCandidateRoleReview, ...]
    outcome: AgentControlLoopCandidateReviewOutcome


@dataclass(frozen=True)
class CandidateVerifierCheck:
    check_id: str
    label: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class CandidateReviewBuild:
    bd_report_docx: bytes
    text_report_docx: bytes
    ledger_csv: bytes
    analysis: CandidateReviewAnalysis
    checks: tuple[CandidateVerifierCheck, ...]
    report_table_counts: tuple[int, int]


@dataclass(frozen=True)
class _ConditionSpec:
    condition_id: str
    condition_type: str
    label: str
    semantic_key: str
    required_for_recommendation: bool
    all_terms: tuple[str, ...]


BD_SPECS = (
    _ConditionSpec(
        "BD-RESP-MERCHANT",
        "responsibility",
        "商户入驻与拓展",
        "merchant_acquisition",
        False,
        ("商户入驻与拓展",),
    ),
    _ConditionSpec(
        "BD-RESP-DIAGNOSIS",
        "responsibility",
        "经营诊断与策略",
        "operations_diagnosis",
        False,
        ("经营诊断与策略",),
    ),
    _ConditionSpec(
        "BD-RESP-RESOURCE",
        "responsibility",
        "资源整合",
        "resource_coordination",
        False,
        ("资源整合",),
    ),
    _ConditionSpec(
        "BD-RESP-RELATIONSHIP",
        "responsibility",
        "客情维护",
        "relationship_management",
        False,
        ("客情维护",),
    ),
    _ConditionSpec(
        "BD-RESP-MARKET", "responsibility", "市场调研", "market_research", False, ("市场调研",)
    ),
    _ConditionSpec(
        "BD-EDUCATION", "default_threshold", "学历默认门槛", "education", True, ("学历背景",)
    ),
    _ConditionSpec(
        "BD-REQ-COMMUNICATION",
        "required",
        "沟通表达与谈判",
        "communication_negotiation",
        True,
        ("核心素质",),
    ),
    _ConditionSpec(
        "BD-REQ-PRESSURE", "required", "抗压与外勤适应", "pressure_fieldwork", True, ("抗压能力",)
    ),
    _ConditionSpec(
        "BD-REQ-DATA", "required", "数据敏感与报表理解", "data_sensitivity", True, ("数据敏感度",)
    ),
    _ConditionSpec(
        "BD-REQ-INDUSTRY",
        "required",
        "餐饮或 O2O 行业理解",
        "industry_understanding",
        True,
        ("行业理解",),
    ),
    _ConditionSpec(
        "BD-PREF-EXPERIENCE",
        "preferred",
        "外卖、快消或互联网地推经验",
        "preferred_sales_experience",
        False,
        ("外卖平台", "经验者优先"),
    ),
    _ConditionSpec(
        "BD-BONUS-RESOURCES",
        "bonus",
        "区域餐饮资源",
        "restaurant_resources",
        False,
        ("自带区域餐饮资源",),
    ),
    _ConditionSpec(
        "BD-BONUS-TRENDS", "bonus", "餐饮趋势敏感度", "food_trends", False, ("餐饮流行趋势",)
    ),
    _ConditionSpec(
        "BD-BONUS-PLAN", "bonus", "简单运营方案能力", "operations_plan", False, ("运营方案",)
    ),
)

TEXT_SPECS = (
    _ConditionSpec(
        "TEXT-RESP-DATASET",
        "responsibility",
        "数据集调研与构建",
        "dataset_work",
        False,
        ("数据集调研及构建",),
    ),
    _ConditionSpec(
        "TEXT-RESP-TOOLS",
        "responsibility",
        "提效工具开发",
        "tool_development",
        False,
        ("提效工具开发",),
    ),
    _ConditionSpec(
        "TEXT-RESP-RUBRIC",
        "responsibility",
        "评测标准构建与执行",
        "rubric_evaluation",
        False,
        ("评测标准构建及执行",),
    ),
    _ConditionSpec(
        "TEXT-REQ-PYTHON",
        "required",
        "Python 与数据处理",
        "python_data",
        True,
        ("必要项", "Python"),
    ),
    _ConditionSpec(
        "TEXT-REQ-AI-EXPERIENCE",
        "required",
        "AI 评测或开发经历",
        "ai_experience",
        True,
        ("必要项", "AI", "工作经验"),
    ),
    _ConditionSpec(
        "TEXT-BONUS-FRONTEND", "bonus", "前端网页开发", "frontend", False, ("加分项", "前端")
    ),
    _ConditionSpec(
        "TEXT-BONUS-LLM", "bonus", "大模型训练及评测", "llm_evaluation", False, ("加分项", "大模型")
    ),
    _ConditionSpec(
        "TEXT-BONUS-ENGLISH", "bonus", "英文论文阅读", "english_reading", False, ("加分项", "英文")
    ),
)


POSITIVE_PATTERNS: dict[str, tuple[tuple[str, ...], ...]] = {
    "merchant_acquisition": (("商户", "拓展"), ("商户", "签约"), ("新签商户",)),
    "operations_diagnosis": (
        ("经营问题", "数据诊断"),
        ("满减", "营销方案"),
        ("经营漏洞", "改善方案"),
    ),
    "resource_coordination": (("Banner", "资源"), ("大促活动",), ("平台资源",)),
    "relationship_management": (("商户", "维护"), ("长期合作",), ("客户", "维护")),
    "market_research": (("市场调研",), ("竞对",), ("市场反馈",)),
    "communication_negotiation": (("沟通", "谈判"), ("客户沟通",), ("说服",)),
    "pressure_fieldwork": (("抗压",), ("外勤",), ("高强度",)),
    "data_sensitivity": (("运营报表",), ("销售报表",), ("数据分析",), ("数据诊断",)),
    "industry_understanding": (("外卖平台",), ("O2O",), ("餐饮市场",)),
    "preferred_sales_experience": (("外卖平台",), ("快消",), ("地推",)),
    "restaurant_resources": (("餐饮资源",), ("连锁品牌", "长期合作")),
    "food_trends": (("餐饮流行趋势",), ("爆品策略",)),
    "operations_plan": (("运营方案",), ("营销方案",), ("销售策略",)),
    "dataset_work": (("评测集",), ("benchmark", "构建"), ("评测数据集",)),
    "tool_development": (("脚本",), ("网页工具",), ("Vue",), ("Flask",)),
    "rubric_evaluation": (("rubric",), ("机标结果校验",), ("评测", "校验")),
    "python_data": (("Python", "数据清洗"), ("Python", "数据处理"), ("Python", "脚本")),
    "frontend": (("前端",), ("Vue",), ("Flask",), ("网页工具",)),
    "llm_evaluation": (("大模型", "评测"), ("大模型训练",), ("benchmark",)),
    "english_reading": (("CET-6",), ("英文论文",), ("英文文献",)),
}

NEGATIVE_PATTERNS: dict[str, tuple[tuple[str, ...], ...]] = {
    "merchant_acquisition": (("销售/BD 经验", "无"), ("BD 经验", "无")),
    "preferred_sales_experience": (("销售/BD 经验", "无"),),
    "python_data": (("Python", "无基础"), ("Python", "无相关经验")),
    "ai_experience": (("AI 经验", "无"), ("AI experience", "none")),
    "frontend": (("前端", "无相关经验"), ("frontend", "none")),
}


def build_candidate_review(
    sources: tuple[CandidateSourceInput, ...],
) -> CandidateReviewBuild:
    analysis = analyze_candidate_review_sources(sources)
    ledger_csv = _ledger_csv(analysis)
    bd_report, bd_tables = _role_report_docx(analysis, "merchant_bd")
    text_report, text_tables = _role_report_docx(analysis, "text_evaluation")
    checks = verify_candidate_review_artifacts(
        sources,
        bd_report_docx=bd_report,
        text_report_docx=text_report,
        ledger_csv=ledger_csv,
    )
    return CandidateReviewBuild(
        bd_report_docx=bd_report,
        text_report_docx=text_report,
        ledger_csv=ledger_csv,
        analysis=analysis,
        checks=checks,
        report_table_counts=(bd_tables, text_tables),
    )


def analyze_candidate_review_sources(
    sources: tuple[CandidateSourceInput, ...],
) -> CandidateReviewAnalysis:
    by_id = _validate_source_contract(sources)
    jobs = (
        _parse_job(by_id[JD_BD_ID], "merchant_bd", BD_SPECS),
        _parse_job(by_id[JD_TEXT_ID], "text_evaluation", TEXT_SPECS),
    )
    candidates = tuple(
        _parse_candidate(by_id[candidate_id]) for candidate_id in CANDIDATE_LOGICAL_IDS
    )
    reviews = tuple(_review_candidate(job, candidate) for job in jobs for candidate in candidates)
    outcome = _candidate_outcome(jobs, candidates, reviews)
    return CandidateReviewAnalysis(
        jobs=jobs,
        candidates=candidates,
        reviews=reviews,
        outcome=outcome,
    )


def _validate_source_contract(
    sources: tuple[CandidateSourceInput, ...],
) -> dict[str, CandidateSourceInput]:
    if len(sources) != 7:
        raise CandidateReviewValidationError(
            "source-count", f"hr-001 必须恰好包含 2 份 JD 与 5 份简历，实际为 {len(sources)} 份。"
        )
    by_id: dict[str, CandidateSourceInput] = {}
    seen_refs: set[str] = set()
    seen_hashes: set[str] = set()
    for source in sources:
        if source.logical_id in by_id:
            raise CandidateReviewValidationError(
                "duplicate-logical-id", f"来源逻辑 ID 重复：{source.logical_id}。"
            )
        if source.logical_id not in EXPECTED_FILE_NAMES:
            raise CandidateReviewValidationError(
                "unknown-source", f"出现未批准来源：{source.logical_id}。"
            )
        if source.file_name != EXPECTED_FILE_NAMES[source.logical_id]:
            raise CandidateReviewValidationError(
                "source-file-name",
                f"{source.logical_id} 文件名应为 {EXPECTED_FILE_NAMES[source.logical_id]}。",
            )
        if source.display_path != EXPECTED_DISPLAY_PATHS[source.logical_id]:
            raise CandidateReviewValidationError(
                "source-display-path", f"{source.logical_id} 安全展示路径不符合固定合同。"
            )
        if not source.allowlist_verified:
            raise CandidateReviewValidationError(
                "source-not-allowlisted", f"{source.file_name} 未通过 allowlist 完整性校验。"
            )
        if not source.content or len(source.content) != source.declared_size:
            raise CandidateReviewValidationError(
                "source-size", f"{source.file_name} 为空或与冻结大小不一致。"
            )
        if source.file_ref in seen_refs:
            raise CandidateReviewValidationError(
                "duplicate-file-ref", "两个逻辑来源指向同一个 file_ref。"
            )
        digest = hashlib.sha256(source.content).hexdigest()
        if digest in seen_hashes:
            raise CandidateReviewValidationError(
                "duplicate-source-content", "两个逻辑来源使用了相同原始字节，禁止冒充独立资料。"
            )
        seen_refs.add(source.file_ref)
        seen_hashes.add(digest)
        by_id[source.logical_id] = source
    if set(by_id) != set(SOURCE_ORDER):
        missing = sorted(set(SOURCE_ORDER) - set(by_id))
        raise CandidateReviewValidationError(
            "source-set", "固定来源集合不完整：" + "、".join(missing)
        )
    return by_id


def _parse_job(
    source: CandidateSourceInput,
    role_id: str,
    specs: tuple[_ConditionSpec, ...],
) -> ParsedJob:
    lines = _extract_docx_lines(source)
    conditions: list[JobCondition] = []
    for spec in specs:
        line = _unique_line(lines, spec.all_terms, f"{role_id}/{spec.condition_id}")
        education_rank = None
        experience_months = None
        exception_allowed = False
        if spec.semantic_key == "education":
            education_rank = _parse_education_threshold(line.text)
            exception_allowed = "放宽" in line.text
        elif spec.semantic_key == "ai_experience":
            experience_months = _parse_experience_threshold(line.text)
        conditions.append(
            JobCondition(
                role_id=role_id,
                condition_id=spec.condition_id,
                condition_type=spec.condition_type,
                label=spec.label,
                semantic_key=spec.semantic_key,
                source_file_ref=source.file_ref,
                locator=line.locator,
                excerpt=_redact_sensitive(line.text),
                required_for_recommendation=spec.required_for_recommendation,
                education_threshold_rank=education_rank,
                experience_threshold_months=experience_months,
                exception_allowed=exception_allowed,
            )
        )
    expected_necessary = 0 if role_id == "merchant_bd" else 2
    actual_necessary = sum(1 for line in lines if line.text.startswith("必要项："))
    if actual_necessary != expected_necessary:
        raise CandidateReviewValidationError(
            "jd-necessary-contract",
            f"{source.file_name} 必要项数量应为 {expected_necessary}，实际为 {actual_necessary}。",
        )
    return ParsedJob(
        role_id=role_id,
        role_name=ROLE_NAMES[role_id],
        source_file_ref=source.file_ref,
        file_name=source.file_name,
        lines=lines,
        conditions=tuple(conditions),
    )


def _parse_candidate(source: CandidateSourceInput) -> ParsedCandidate:
    lines = _extract_pdf_lines(source)
    name_lines = [line for line in lines if re.match(r"^姓名\s*[：:]", line.text)]
    if len(name_lines) != 1:
        raise CandidateReviewValidationError(
            "candidate-name-field", f"{source.file_name} 必须包含唯一姓名字段。"
        )
    candidate_name = re.split(r"[：:]", name_lines[0].text, maxsplit=1)[1].strip()
    expected_name = EXPECTED_CANDIDATE_NAMES[source.logical_id]
    if candidate_name != expected_name:
        raise CandidateReviewValidationError(
            "candidate-name-mismatch",
            f"{source.file_name} 内姓名为 {candidate_name or '空'}，与文件合同 {expected_name} 不一致。",
        )

    education_lines = [line for line in lines if re.match(r"^学历\s*[：:]", line.text)]
    if len(education_lines) > 1:
        levels = {_education_level(line.text) for line in education_lines}
        if len(levels) > 1:
            raise CandidateReviewValidationError(
                "candidate-education-conflict", f"{source.file_name} 出现相互冲突的学历字段。"
            )
    education_line = education_lines[0] if education_lines else None
    education_level = _education_level(education_line.text) if education_line else None
    education_rank = EDUCATION_RANKS.get(education_level or "")
    education_in_progress = bool(
        education_line and any(term in education_line.text for term in ("在读", "预计"))
    )

    positive: dict[str, list[SourceLine]] = {key: [] for key in POSITIVE_PATTERNS}
    negative: dict[str, list[SourceLine]] = {key: [] for key in NEGATIVE_PATTERNS}
    for line in lines:
        for key, patterns in NEGATIVE_PATTERNS.items():
            if any(all(term.lower() in line.text.lower() for term in terms) for terms in patterns):
                negative[key].append(line)
        if _is_negative_statement(line.text):
            continue
        for key, patterns in POSITIVE_PATTERNS.items():
            if any(all(term.lower() in line.text.lower() for term in terms) for terms in patterns):
                positive[key].append(line)

    ai_months = 0
    ai_duration_lines: list[SourceLine] = []
    for line in lines:
        duration = _parse_work_duration(line.text)
        if duration is None:
            continue
        if any(
            term.lower() in line.text.lower() for term in ("ai", "nlp", "大模型", "算法", "评测")
        ):
            ai_months += duration
            ai_duration_lines.append(line)
    if ai_duration_lines:
        positive.setdefault("ai_experience", []).extend(ai_duration_lines)
    if negative.get("ai_experience") and ai_duration_lines:
        raise CandidateReviewValidationError(
            "candidate-ai-experience-conflict",
            f"{source.file_name} 同时声明 AI 经验为无并列出 AI 相关履历。",
        )
    if negative.get("python_data") and positive.get("python_data"):
        raise CandidateReviewValidationError(
            "candidate-python-conflict", f"{source.file_name} 的 Python 能力陈述相互冲突。"
        )
    if negative.get("frontend") and positive.get("frontend"):
        raise CandidateReviewValidationError(
            "candidate-frontend-conflict", f"{source.file_name} 的前端经历陈述相互冲突。"
        )

    return ParsedCandidate(
        candidate_id=source.logical_id,
        candidate_name=candidate_name,
        source_file_ref=source.file_ref,
        file_name=source.file_name,
        lines=lines,
        education_level=education_level,
        education_rank=education_rank,
        education_in_progress=education_in_progress,
        education_line=education_line,
        ai_experience_months=ai_months if ai_duration_lines else None,
        positive_evidence={key: tuple(value) for key, value in positive.items()},
        negative_evidence={key: tuple(value) for key, value in negative.items()},
    )


def _extract_docx_lines(source: CandidateSourceInput) -> tuple[SourceLine, ...]:
    if not zipfile.is_zipfile(io.BytesIO(source.content)):
        raise CandidateReviewValidationError(
            "jd-docx-container", f"{source.file_name} 不是有效 DOCX。"
        )
    try:
        with zipfile.ZipFile(io.BytesIO(source.content)) as archive:
            names = {name.lower() for name in archive.namelist()}
            if "word/document.xml" not in names:
                raise CandidateReviewValidationError(
                    "jd-docx-document", f"{source.file_name} 缺少 word/document.xml。"
                )
            if any("vbaproject.bin" in name for name in names):
                raise CandidateReviewValidationError(
                    "jd-docx-macro", f"{source.file_name} 包含不允许的宏。"
                )
            root = ET.fromstring(archive.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise CandidateReviewValidationError(
            "jd-docx-parse", f"{source.file_name} 无法安全解析。"
        ) from exc
    values: list[str] = []
    for paragraph in root.iter(f"{W}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{W}t")).strip()
        if text:
            values.append(_normalize_space(text))
    if not values:
        raise CandidateReviewValidationError("jd-empty", f"{source.file_name} 没有可用正文。")
    return tuple(
        SourceLine(index, f"非空行 {index}", value) for index, value in enumerate(values, start=1)
    )


def _extract_pdf_lines(source: CandidateSourceInput) -> tuple[SourceLine, ...]:
    try:
        reader = PdfReader(io.BytesIO(source.content), strict=False)
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise CandidateReviewValidationError(
                "resume-pdf-encrypted", f"{source.file_name} 已加密。"
            )
        if not reader.pages or len(reader.pages) > 20:
            raise CandidateReviewValidationError(
                "resume-pdf-pages", f"{source.file_name} 页数不在允许范围。"
            )
        values: list[tuple[int, str]] = []
        for page_number, page in enumerate(reader.pages, start=1):
            for raw_line in (page.extract_text() or "").splitlines():
                text = _normalize_space(raw_line)
                if text:
                    values.append((page_number, text))
    except CandidateReviewValidationError:
        raise
    except Exception as exc:
        raise CandidateReviewValidationError(
            "resume-pdf-parse", f"{source.file_name} 无法安全解析。"
        ) from exc
    if not values:
        raise CandidateReviewValidationError("resume-empty", f"{source.file_name} 没有可用文本层。")
    return tuple(
        SourceLine(index, f"第 {page} 页 · 非空行 {index}", text)
        for index, (page, text) in enumerate(values, start=1)
    )


def _unique_line(lines: tuple[SourceLine, ...], terms: tuple[str, ...], label: str) -> SourceLine:
    matches = [line for line in lines if all(term in line.text for term in terms)]
    if len(matches) != 1:
        raise CandidateReviewValidationError(
            "jd-condition-location",
            f"{label} 应唯一定位，实际匹配 {len(matches)} 处。",
        )
    return matches[0]


def _parse_education_threshold(text: str) -> int:
    matches = [level for level in EDUCATION_RANKS if re.search(rf"{level}\s*(?:及以上|以上)", text)]
    if len(matches) != 1:
        raise CandidateReviewValidationError("jd-education-threshold", "学历门槛缺失或含糊。")
    return EDUCATION_RANKS[matches[0]]


def _parse_experience_threshold(text: str) -> int:
    year_matches = re.findall(r"(?<!\d)(\d+)\s*年\s*以上", text)
    month_matches = re.findall(r"(?<!\d)(\d+)\s*个?月\s*以上", text)
    if len(year_matches) + len(month_matches) != 1:
        raise CandidateReviewValidationError("jd-experience-threshold", "工作年限门槛缺失或含糊。")
    months = int(year_matches[0]) * 12 if year_matches else int(month_matches[0])
    if months < 1 or months > 600:
        raise CandidateReviewValidationError(
            "jd-experience-threshold", "工作年限门槛超出允许范围。"
        )
    return months


def _education_level(text: str) -> str | None:
    levels = [level for level in EDUCATION_RANKS if level in text]
    if not levels:
        return None
    unique = tuple(dict.fromkeys(levels))
    if len(unique) != 1:
        raise CandidateReviewValidationError("candidate-education-value", "学历字段包含多个等级。")
    return unique[0]


def _parse_work_duration(text: str) -> int | None:
    date_match = re.search(
        r"(?P<sy>\d{4})[.年/-](?P<sm>\d{1,2})\s*(?:-|至|—)\s*(?:(?P<ey>\d{4})[.年/-](?P<em>\d{1,2})|至今)",
        text,
    )
    cn_duration = re.search(
        r"(?:（|\()\s*(?:(?P<years>\d+)\s*年)?\s*(?P<months>\d+)?\s*个?月\s*(?:）|\))",
        text,
    )
    en_duration = re.search(r"(?:\(|\b)(?P<en_months>\d+)\s*months?(?:\)|\b)", text, re.I)
    if date_match:
        sm = int(date_match.group("sm"))
        em = int(date_match.group("em")) if date_match.group("em") else None
        if not 1 <= sm <= 12 or (em is not None and not 1 <= em <= 12):
            raise CandidateReviewValidationError("candidate-date-month", "履历月份不合法。")
        if date_match.group("ey"):
            start = int(date_match.group("sy")) * 12 + sm
            end = int(date_match.group("ey")) * 12 + int(date_match.group("em"))
            if start > end:
                raise CandidateReviewValidationError("candidate-date-order", "履历起止日期倒置。")
    if not cn_duration and not en_duration:
        return None
    if cn_duration:
        years = int(cn_duration.group("years") or 0)
        months = int(cn_duration.group("months") or 0)
        duration = years * 12 + months
    else:
        duration = int(en_duration.group("en_months"))
    if duration < 1 or duration > 600:
        raise CandidateReviewValidationError("candidate-duration", "履历年限不合法。")
    if date_match and date_match.group("ey"):
        inclusive = (
            (int(date_match.group("ey")) - int(date_match.group("sy"))) * 12
            + int(date_match.group("em"))
            - int(date_match.group("sm"))
            + 1
        )
        if inclusive != duration:
            raise CandidateReviewValidationError(
                "candidate-duration-conflict", "履历日期与声明时长冲突。"
            )
    return duration


def _is_negative_statement(text: str) -> bool:
    return any(
        all(term.lower() in text.lower() for term in terms)
        for patterns in NEGATIVE_PATTERNS.values()
        for terms in patterns
    )


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _redact_sensitive(text: str) -> str:
    value = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[已隐藏邮箱]", text)
    value = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[已隐藏手机号]", value)
    value = re.sub(
        r"(?:性别|年龄|出生日期|民族|婚姻状况|籍贯|政治面貌|家庭住址|住址)\s*[：:].*$",
        "[已隐藏非岗位必要信息]",
        value,
    )
    value = re.sub(r"预计\s*\d{4}\s*年\s*\d{1,2}\s*月毕业", "本科在读", value)
    return value


def _review_candidate(
    job: ParsedJob, candidate: ParsedCandidate
) -> AgentControlLoopCandidateRoleReview:
    assessments = tuple(
        _assess_condition(job, condition, candidate) for condition in job.conditions
    )
    required = [
        item
        for item, condition in zip(assessments, job.conditions, strict=True)
        if condition.required_for_recommendation
    ]
    if any(item.status == "not_met" for item in required):
        recommendation = "explicit_hard_gap"
    elif any(item.status == "human_exception_required" for item in required):
        recommendation = "exception_review_required"
    elif any(item.status == "unverifiable" for item in required):
        recommendation = "insufficient_evidence"
    else:
        recommendation = "recommended_for_human_review"
    counts = Counter(item.status for item in assessments)
    summary = (
        f"{RECOMMENDATION_LABELS[recommendation]}；有来源支持 {counts['met']} 项，"
        f"明确不满足 {counts['not_met']} 项，资料不足 {counts['unverifiable']} 项，"
        f"需人工例外判断 {counts['human_exception_required']} 项。"
    )
    return AgentControlLoopCandidateRoleReview(
        review_id=f"candidate-review-{job.role_id.replace('_', '-')}-{candidate.candidate_id.lower()}",
        role_id=job.role_id,
        role_name=job.role_name,
        jd_source_file_ref=job.source_file_ref,
        candidate_id=candidate.candidate_id,
        candidate_name=candidate.candidate_name,
        resume_source_file_ref=candidate.source_file_ref,
        recommendation=recommendation,
        condition_count=len(assessments),
        met_count=counts["met"],
        not_met_count=counts["not_met"],
        unverifiable_count=counts["unverifiable"],
        human_exception_count=counts["human_exception_required"],
        summary=summary,
        assessments=list(assessments),
    )


def _assess_condition(
    job: ParsedJob,
    condition: JobCondition,
    candidate: ParsedCandidate,
) -> AgentControlLoopCandidateConditionAssessment:
    positive = candidate.positive_evidence.get(condition.semantic_key, ())
    negative = candidate.negative_evidence.get(condition.semantic_key, ())
    status: str
    evidence: tuple[SourceLine, ...]
    fact: str
    reason: str

    if condition.semantic_key == "education":
        evidence = (candidate.education_line,) if candidate.education_line else ()
        if candidate.education_line is None or candidate.education_rank is None:
            status = "unverifiable"
            fact = "简历未提供可解析的最高学历。"
            reason = "无法将学历与 JD 默认门槛进行比较。"
        elif candidate.education_in_progress:
            status = "unverifiable"
            fact = f"简历写明{candidate.education_level}在读，尚不能据此确认已取得对应学历。"
            reason = "在读状态不等同于已取得学历，需要核验毕业或在读证明。"
        elif candidate.education_rank >= int(condition.education_threshold_rank or 0):
            status = "met"
            fact = f"简历最高学历为{candidate.education_level}。"
            reason = "来源学历达到 JD 当前默认门槛。"
        elif condition.exception_allowed:
            status = "human_exception_required"
            fact = f"简历最高学历为{candidate.education_level}，低于 JD 默认门槛。"
            reason = "JD 明示优秀者可放宽，服务端不得替招聘人员适用例外。"
        else:
            status = "not_met"
            fact = f"简历最高学历为{candidate.education_level}，低于 JD 默认门槛。"
            reason = "JD 当前没有可适用的例外条款。"
    elif condition.semantic_key == "ai_experience":
        evidence = positive or negative
        threshold = int(condition.experience_threshold_months or 0)
        if negative:
            status = "not_met"
            fact = "简历明确写明没有 AI 相关经验。"
            reason = "明确的无经验陈述低于 JD 必要年限。"
        elif candidate.ai_experience_months is None:
            status = "unverifiable"
            fact = "简历未提供可复算的 AI 评测或开发经历年限。"
            reason = "缺失不能推断为不满足，需要补充起止时间与职责。"
        elif candidate.ai_experience_months >= threshold:
            status = "met"
            fact = f"可复算 AI 相关经历为 {candidate.ai_experience_months} 个月。"
            reason = f"达到 JD 的 {threshold} 个月必要门槛。"
        else:
            status = "not_met"
            fact = f"可复算 AI 相关经历为 {candidate.ai_experience_months} 个月。"
            reason = f"低于 JD 的 {threshold} 个月必要门槛。"
    else:
        evidence = positive or negative
        if positive:
            status = "met"
            fact = "简历存在与该条件直接相关的岗位事实。"
            reason = "批准简历中存在可定位的正向陈述。"
        elif negative:
            status = "not_met"
            fact = "简历明确写明没有该项能力或经历。"
            reason = "只有明确的否定陈述才被判为不满足。"
        else:
            status = "unverifiable"
            fact = "简历未提供与该条件直接对应的陈述。"
            reason = "未写到不等于不满足，必须通过面试或补充材料核验。"

    evidence_present = bool(evidence)
    if evidence_present:
        selected = evidence[:3]
        resume_locator = "；".join(item.locator for item in selected)
        resume_excerpt = "；".join(_redact_sensitive(item.text) for item in selected)
    else:
        resume_locator = "安全预览全文"
        resume_excerpt = "（未提供与该条件直接对应的原文）"

    if status == "met":
        judgment = "该条件有来源支持，但仍需核验陈述真实性和实际负责范围。"
        action = f"围绕“{condition.label}”追问一个可验证实例，并核对候选人的实际职责。"
        exit_condition = "招聘人员核验原始经历、职责边界与证明材料后记录人工结论。"
    elif status == "not_met":
        judgment = "来源显示存在明确条件缺口；这仍不是自动淘汰决定。"
        action = f"确认“{condition.label}”是否存在未写入简历的补充事实，并由招聘人员决定。"
        exit_condition = "补充材料仍不能满足该必要条件，或招聘人员记录有依据的人工处置。"
    elif status == "human_exception_required":
        judgment = "默认门槛未满足，但来源 JD 存在显式例外，必须由人决定。"
        action = "核对销售、谈判、报表、外勤等岗位事实，再决定是否适用“优秀者可放宽”。"
        exit_condition = "招聘负责人记录是否适用例外、依据和复核人。"
    else:
        judgment = "现有资料不足，服务端不把缺失推断为否定。"
        action = f"请候选人补充“{condition.label}”的时间、职责、产出或可验证示例。"
        exit_condition = "获得可定位的补充事实，或招聘人员明确接受资料不足风险。"

    return AgentControlLoopCandidateConditionAssessment(
        assessment_id=(
            "candidate-assessment-"
            f"{job.role_id.replace('_', '-')}-{candidate.candidate_id.lower()}-"
            f"{condition.condition_id.lower()}"
        ),
        role_id=job.role_id,
        candidate_id=candidate.candidate_id,
        candidate_name=candidate.candidate_name,
        condition_id=condition.condition_id,
        condition_type=condition.condition_type,
        condition_label=condition.label,
        jd_source_file_ref=condition.source_file_ref,
        jd_locator=condition.locator,
        jd_excerpt=condition.excerpt,
        resume_source_file_ref=candidate.source_file_ref,
        resume_locator=resume_locator,
        resume_excerpt=resume_excerpt,
        resume_evidence_present=evidence_present,
        status=status,
        fact=fact,
        judgment=judgment,
        reason=reason,
        owner="招聘负责人",
        review_action=action,
        exit_condition=exit_condition,
    )


def _candidate_outcome(
    jobs: tuple[ParsedJob, ...],
    candidates: tuple[ParsedCandidate, ...],
    reviews: tuple[AgentControlLoopCandidateRoleReview, ...],
) -> AgentControlLoopCandidateReviewOutcome:
    assessments = [item for review in reviews for item in review.assessments]
    status_counts = Counter(item.status for item in assessments)
    recommendation_counts = Counter(review.recommendation for review in reviews)
    summary = (
        f"{len(jobs)} 个岗位、{len(candidates)} 名候选人、{len(assessments)} 条来源推导条件；"
        f"有来源支持 {status_counts['met']} 条，明确不满足 {status_counts['not_met']} 条，"
        f"资料不足 {status_counts['unverifiable']} 条，需人工例外判断 "
        f"{status_counts['human_exception_required']} 条。"
    )
    return AgentControlLoopCandidateReviewOutcome(
        outcome_id="candidate-review-outcome-hr-001",
        status="review_required",
        decision="这是人工复核建议，不是录用或淘汰决定。",
        summary=summary,
        role_count=len(jobs),
        candidate_count=len(candidates),
        review_count=len(reviews),
        assessment_count=len(assessments),
        met_count=status_counts["met"],
        not_met_count=status_counts["not_met"],
        unverifiable_count=status_counts["unverifiable"],
        human_exception_count=status_counts["human_exception_required"],
        recommended_for_human_review_count=recommendation_counts["recommended_for_human_review"],
        explicit_hard_gap_count=recommendation_counts["explicit_hard_gap"],
        insufficient_evidence_count=recommendation_counts["insufficient_evidence"],
        exception_review_required_count=recommendation_counts["exception_review_required"],
        reviews=list(reviews),
    )


def _ledger_rows(analysis: CandidateReviewAnalysis) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for review in analysis.reviews:
        for item in review.assessments:
            rows.append(
                {
                    "岗位ID": item.role_id,
                    "岗位": review.role_name,
                    "候选人ID": item.candidate_id,
                    "候选人": item.candidate_name,
                    "总体建议": RECOMMENDATION_LABELS[review.recommendation],
                    "条件ID": item.condition_id,
                    "条件类型": CONDITION_TYPE_LABELS[item.condition_type],
                    "条件名称": item.condition_label,
                    "JD来源Ref": item.jd_source_file_ref,
                    "JD位置": item.jd_locator,
                    "JD原文": item.jd_excerpt,
                    "简历来源Ref": item.resume_source_file_ref,
                    "简历位置": item.resume_locator,
                    "简历原文": item.resume_excerpt,
                    "状态": STATUS_LABELS[item.status],
                    "事实": item.fact,
                    "判断": item.judgment,
                    "原因": item.reason,
                    "责任人": item.owner,
                    "面试或补证动作": item.review_action,
                    "退出条件": item.exit_condition,
                }
            )
    return rows


def _ledger_csv(analysis: CandidateReviewAnalysis) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=LEDGER_HEADERS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(_ledger_rows(analysis))
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def _role_report_docx(analysis: CandidateReviewAnalysis, role_id: str) -> tuple[bytes, int]:
    job = next(item for item in analysis.jobs if item.role_id == role_id)
    reviews = [item for item in analysis.reviews if item.role_id == role_id]
    condition_rows = [
        [
            item.condition_id,
            CONDITION_TYPE_LABELS[item.condition_type],
            item.label,
            item.locator,
            item.excerpt,
        ]
        for item in job.conditions
    ]
    summary_rows = [
        [
            review.candidate_id,
            review.candidate_name,
            RECOMMENDATION_LABELS[review.recommendation],
            str(review.met_count),
            str(review.not_met_count),
            str(review.unverifiable_count),
            str(review.human_exception_count),
        ]
        for review in reviews
    ]
    blocks: list[tuple[str, object]] = [
        ("title", f"{job.role_name}岗位辅助筛选报告"),
        ("heading", "一、结论与边界"),
        ("body", "这是人工复核建议，不是录用或淘汰决定。"),
        (
            "body",
            "本报告只处理固定 hr-001 公开 JD 与简历。没有公平性用户研究或人口属性评估，不能声称无偏；没有背景调查、身份核验、外部通知或自动人事动作。",
        ),
        ("heading", "二、岗位条件"),
        (
            "table",
            (["条件ID", "类型", "条件", "JD位置", "JD原文"], condition_rows),
        ),
        ("heading", "三、五名候选人汇总"),
        (
            "table",
            (
                ["候选人ID", "姓名", "人工复核建议", "支持", "不满足", "资料不足", "例外"],
                summary_rows,
            ),
        ),
        ("heading", "四、逐候选条件证据"),
    ]
    for review in reviews:
        blocks.extend(
            [
                (
                    "heading",
                    f"{review.candidate_name}：{RECOMMENDATION_LABELS[review.recommendation]}",
                ),
                ("body", review.summary),
                (
                    "table",
                    (
                        [
                            "候选人ID",
                            "条件ID",
                            "状态",
                            "JD位置",
                            "简历位置",
                            "事实",
                            "判断",
                            "下一步",
                        ],
                        [
                            [
                                item.candidate_id,
                                item.condition_id,
                                STATUS_LABELS[item.status],
                                item.jd_locator,
                                item.resume_locator,
                                item.fact,
                                item.judgment,
                                item.review_action,
                            ]
                            for item in review.assessments
                        ],
                    ),
                ),
            ]
        )
    action_rows = [
        [
            review.candidate_name,
            item.condition_id,
            STATUS_LABELS[item.status],
            item.owner,
            item.review_action,
            item.exit_condition,
        ]
        for review in reviews
        for item in review.assessments
        if item.status != "met"
    ]
    blocks.extend(
        [
            ("heading", "五、资料不足、例外与人工处置"),
            (
                "table",
                (["候选人", "条件", "状态", "责任人", "面试或补证动作", "退出条件"], action_rows),
            ),
            ("heading", "六、最终使用边界"),
            (
                "body",
                "确定性检查只证明来源合同、条件解析、四态计算和成果文件相互一致。招聘人员必须核验原始材料并自行作出最终决定。",
            ),
        ]
    )
    return _docx_bytes(blocks), sum(kind == "table" for kind, _ in blocks)


def verify_candidate_review_artifacts(
    sources: tuple[CandidateSourceInput, ...],
    *,
    bd_report_docx: bytes,
    text_report_docx: bytes,
    ledger_csv: bytes,
) -> tuple[CandidateVerifierCheck, ...]:
    expected = analyze_candidate_review_sources(sources)
    expected_rows = _ledger_rows(expected)
    csv_valid, csv_rows, csv_detail = _parse_ledger(ledger_csv)
    ledger_keys = [
        (row.get("岗位ID", ""), row.get("候选人ID", ""), row.get("条件ID", "")) for row in csv_rows
    ]
    expected_map = {(row["岗位ID"], row["候选人ID"], row["条件ID"]): row for row in expected_rows}
    actual_map = {
        (row.get("岗位ID", ""), row.get("候选人ID", ""), row.get("条件ID", "")): row
        for row in csv_rows
    }

    report_results: dict[str, tuple[bool, str, list[list[list[str]]], str]] = {
        "merchant_bd": _parse_generated_docx(bd_report_docx),
        "text_evaluation": _parse_generated_docx(text_report_docx),
    }
    report_exact: dict[str, bool] = {}
    for role_id, (valid, text, tables, _detail) in report_results.items():
        expected_review_rows = {
            (
                item.candidate_id,
                item.condition_id,
                STATUS_LABELS[item.status],
                item.jd_locator,
                item.resume_locator,
                item.fact,
                item.judgment,
                item.review_action,
            )
            for review in expected.reviews
            if review.role_id == role_id
            for item in review.assessments
        }
        actual_review_rows = {
            tuple(row)
            for table in tables
            for row in table[1:]
            if len(row) == 8 and re.fullmatch(r"CAND-[0-9]{2}", row[0])
        }
        role_reviews = [item for item in expected.reviews if item.role_id == role_id]
        report_exact[role_id] = (
            valid
            and len(tables) >= 8
            and actual_review_rows == expected_review_rows
            and all(review.summary in text for review in role_reviews)
            and "这是人工复核建议，不是录用或淘汰决定" in text
            and "不能声称无偏" in text
        )

    candidate_lines = {
        candidate.source_file_ref: {_redact_sensitive(line.text) for line in candidate.lines}
        for candidate in expected.candidates
    }
    job_lines = {
        job.source_file_ref: {_redact_sensitive(line.text) for line in job.lines}
        for job in expected.jobs
    }
    locators_valid = all(
        item.jd_excerpt in job_lines[item.jd_source_file_ref]
        and (
            not item.resume_evidence_present
            or all(
                excerpt in candidate_lines[item.resume_source_file_ref]
                for excerpt in item.resume_excerpt.split("；")
            )
        )
        for review in expected.reviews
        for item in review.assessments
    )
    all_output_text = "\n".join(
        [
            ledger_csv.decode("utf-8-sig", errors="replace"),
            report_results["merchant_bd"][1],
            report_results["text_evaluation"][1],
        ]
    )
    privacy_valid = not _contains_sensitive_output(all_output_text)
    outcome = expected.outcome
    count_consistency = (
        outcome.assessment_count == len(expected_rows)
        and sum(
            (
                outcome.met_count,
                outcome.not_met_count,
                outcome.unverifiable_count,
                outcome.human_exception_count,
            )
        )
        == outcome.assessment_count
        and sum(
            (
                outcome.recommended_for_human_review_count,
                outcome.explicit_hard_gap_count,
                outcome.insufficient_evidence_count,
                outcome.exception_review_required_count,
            )
        )
        == outcome.review_count
    )
    boundary_valid = all(
        marker in all_output_text
        for marker in (
            "不是录用或淘汰决定",
            "不能声称无偏",
            "招聘人员",
        )
    )
    return (
        CandidateVerifierCheck(
            "check-candidate-source-contract",
            "七份固定来源合同",
            len(expected.jobs) == 2 and len(expected.candidates) == 5,
            "2 份 JD 与 5 份简历的逻辑 ID、文件名、路径、allowlist、大小、字节唯一性和正文均已复核。",
        ),
        CandidateVerifierCheck(
            "check-candidate-jd-conditions",
            "岗位条件来源解析",
            all(job.conditions for job in expected.jobs)
            and len({item.condition_id for job in expected.jobs for item in job.conditions})
            == sum(len(job.conditions) for job in expected.jobs),
            "职责、默认门槛、必要项、优先项、加分项和显式例外均来自 JD 可定位原文。",
        ),
        CandidateVerifierCheck(
            "check-candidate-identity-isolation",
            "候选人身份与岗位隔离",
            len({item.candidate_id for item in expected.candidates}) == 5
            and len({item.source_file_ref for item in expected.candidates}) == 5
            and len(expected.reviews) == 10,
            "五份简历姓名与文件合同一致；两个岗位分别重算，同名、跨主体和跨岗位事实不会串线。",
        ),
        CandidateVerifierCheck(
            "check-candidate-assessment-coverage",
            "逐条件台账完整",
            len(expected_rows) == sum(len(job.conditions) for job in expected.jobs) * 5
            and len(expected_map) == len(expected_rows),
            f"台账由 5 名候选人 × 两份 JD 的全部来源条件动态展开，共 {len(expected_rows)} 条。",
        ),
        CandidateVerifierCheck(
            "check-candidate-source-locators",
            "JD 与简历双来源位置",
            locators_valid,
            "有证据的判断保留 JD 与简历真实位置及脱敏摘录；资料不足明确标记全文未提供，而不伪造引用。",
        ),
        CandidateVerifierCheck(
            "check-candidate-dynamic-outcome",
            "四态与建议动态汇总",
            count_consistency,
            "met、not_met、unverifiable、human_exception_required 与四类人工建议均从逐项台账汇总。",
        ),
        CandidateVerifierCheck(
            "check-candidate-ledger-structure",
            "CSV 台账结构",
            csv_valid
            and len(csv_rows) == len(expected_rows)
            and len(set(ledger_keys)) == len(ledger_keys),
            csv_detail,
        ),
        CandidateVerifierCheck(
            "check-candidate-ledger-content",
            "CSV 与来源重算一致",
            csv_valid and actual_map == expected_map,
            "CSV 的条件、状态、建议、位置、事实、判断、动作和退出条件逐字段等于服务端来源重算。",
        ),
        CandidateVerifierCheck(
            "check-candidate-reports",
            "两份岗位报告与台账一致",
            all(report_exact.values()),
            "每份报告只呈现本岗位的条件、五人摘要、逐候选条件和人工处置，动态数量与 CSV 一致。",
        ),
        CandidateVerifierCheck(
            "check-candidate-privacy-boundary",
            "隐私与人工决定边界",
            privacy_valid and boundary_valid,
            "输出保留姓名核对主键，但不包含邮箱、手机号、地址、性别、年龄、照片等非必要信息；明确不自动录用或淘汰，也不声称无偏。",
        ),
    )


def _parse_ledger(content: bytes) -> tuple[bool, list[dict[str, str]], str]:
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        rows = [dict(row) for row in reader]
    except (UnicodeDecodeError, csv.Error) as exc:
        return False, [], f"CSV 无法解析：{exc}"
    if tuple(reader.fieldnames or ()) != LEDGER_HEADERS:
        return False, rows, f"CSV 表头与 {len(LEDGER_HEADERS)} 列输出合同不一致。"
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        return False, rows, "CSV 存在列错位或缺失字段。"
    return True, rows, "CSV 表头、列数、编码和唯一键均可解析。"


def _contains_sensitive_output(text: str) -> bool:
    patterns = (
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        r"(?<!\d)1[3-9]\d{9}(?!\d)",
        r"(?:性别|年龄|出生日期|民族|婚姻状况|籍贯|政治面貌|家庭住址|住址)\s*[：:]",
        r"(?:候选人照片|证件照|照片附件)",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _docx_bytes(blocks: list[tuple[str, object]]) -> bytes:
    def run(text: str, *, bold: bool = False, size: int = 22) -> str:
        properties = (
            f"<w:rPr>{'<w:b/>' if bold else ''}"
            f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
        )
        return f'<w:r>{properties}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'

    def paragraph(text: str, *, bold: bool = False, size: int = 22) -> str:
        return f"<w:p>{run(text, bold=bold, size=size)}</w:p>"

    def table(headers: list[str], rows: list[list[str]]) -> str:
        def cell(value: str, *, header: bool = False) -> str:
            return "<w:tc><w:tcPr/><w:p>" + run(value, bold=header, size=18) + "</w:p></w:tc>"

        header_row = "<w:tr>" + "".join(cell(item, header=True) for item in headers) + "</w:tr>"
        body_rows = "".join(
            "<w:tr>" + "".join(cell(str(item)) for item in row) + "</w:tr>" for row in rows
        )
        return (
            "<w:tbl><w:tblPr><w:tblBorders>"
            '<w:top w:val="single" w:sz="4" w:color="999999"/>'
            '<w:left w:val="single" w:sz="4" w:color="999999"/>'
            '<w:bottom w:val="single" w:sz="4" w:color="999999"/>'
            '<w:right w:val="single" w:sz="4" w:color="999999"/>'
            '<w:insideH w:val="single" w:sz="4" w:color="BBBBBB"/>'
            '<w:insideV w:val="single" w:sz="4" w:color="BBBBBB"/>'
            "</w:tblBorders></w:tblPr>" + header_row + body_rows + "</w:tbl>"
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
    return True, text, tables, f"DOCX 可解析，共 {len(tables)} 个表格。"
