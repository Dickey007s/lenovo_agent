"""Source-derived Sales-020 cleaning, segmentation, and draft-strategy artifacts.

The fixed adapter reads only the approved survey CSV and Markdown rule source.
It keeps every raw row and transformation, treats duplicate matching as an
explicit policy assumption, and never turns a label into CRM or sales action.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

from packages.contracts.harness_models import (
    AgentControlLoopCustomerSampleDecision,
    AgentControlLoopCustomerSegmentationOutcome,
    AgentControlLoopCustomerSegmentationParameters,
    AgentControlLoopCustomerSegmentationRule,
)


SURVEY_LOGICAL_ID = "sales-020-survey"
RULES_LOGICAL_ID = "sales-020-rules"
SOURCE_ORDER = (SURVEY_LOGICAL_ID, RULES_LOGICAL_ID)
EXPECTED_FILE_NAMES = {
    SURVEY_LOGICAL_ID: "客户画像调研问卷.csv",
    RULES_LOGICAL_ID: "客户分类画像与差异化销售策略生成规则.md",
}
EXPECTED_DISPLAY_PATHS = {
    SURVEY_LOGICAL_ID: "销售运营/客户画像调研问卷.csv",
    RULES_LOGICAL_ID: "销售运营/客户分类画像与差异化销售策略生成规则.md",
}
EXPECTED_FILE_REFS = {
    SURVEY_LOGICAL_ID: "forte-30f5e044f5d7a199",
    RULES_LOGICAL_ID: "forte-8d86fcca3891dabb",
}

SURVEY_HEADERS = (
    "样本ID",
    "企业所在行业",
    "企业规模",
    "填写人职位",
    "专业 (Stech)",
    "安全 (Ssafe)",
    "预算 (Sbudget)",
    "易用 (Seasy)",
)
SCORE_FIELDS = {
    "tech": "专业 (Stech)",
    "safe": "安全 (Ssafe)",
    "budget": "预算 (Sbudget)",
    "easy": "易用 (Seasy)",
}
PROFILE_FIELDS = {
    "技术型": ("tech",),
    "安全型": ("safe", "budget"),
    "敏捷型": ("easy",),
}
CHINESE_NUMBERS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}
LEDGER_HEADERS = (
    "原始行号",
    "来源位置",
    "样本ID",
    "企业所在行业",
    "企业规模",
    "填写人职位",
    "原始专业",
    "原始安全",
    "原始预算",
    "原始易用",
    "清洗专业",
    "清洗安全",
    "清洗预算",
    "清洗易用",
    "转换记录",
    "命中画像",
    "是否应用优先级",
    "最终画像",
    "排除原因",
    "duplicate_of",
    "规则Refs",
)
STRATEGY_EVIDENCE_STATUS = "no_approved_strategy_source"
STRATEGY_PLACEHOLDER = "待销售负责人基于已批准产品资料补充并确认。"
DUPLICATE_POLICY = "exact_non_id_payload"
DUPLICATE_POLICY_NOTE = (
    "规则来源未定义重复键；固定适配器保守采用 exact_non_id_payload："
    "除样本 ID 外所有原始字段完全相同才视为重复，并保留 CSV 中第一条。"
)
BOUNDARY = (
    "这是公开样本的画像清洗与策略草案，不是真实客户研究、销售效果证明或 CRM 执行。"
    "没有联系客户、写 CRM、创建商机或触发营销动作。"
)


class CustomerSegmentationValidationError(ValueError):
    """The fixed Sales-020 source or generated artifact contract is invalid."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class CustomerSourceInput:
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
    text: str

    @property
    def locator(self) -> str:
        return f"客户分类画像与差异化销售策略生成规则.md:L{self.number}"


@dataclass(frozen=True)
class ParsedSegmentationRules:
    source_file_ref: str
    rules: tuple[AgentControlLoopCustomerSegmentationRule, ...]
    missing_default: int
    thresholds: dict[str, int]
    priority: tuple[str, ...]
    output_columns: tuple[str, ...]
    strategy_subitems: tuple[str, ...]
    analysis_subitems: tuple[str, ...]


@dataclass(frozen=True)
class CustomerSegmentationAnalysis:
    rules: ParsedSegmentationRules
    encoding: str
    outcome: AgentControlLoopCustomerSegmentationOutcome


@dataclass(frozen=True)
class CustomerArtifactCheck:
    check_id: str
    label: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class CustomerSegmentationBuild:
    report_markdown: bytes
    ledger_csv: bytes
    analysis: CustomerSegmentationAnalysis
    checks: tuple[CustomerArtifactCheck, ...]


def build_customer_segmentation(
    sources: tuple[CustomerSourceInput, ...],
) -> CustomerSegmentationBuild:
    """Build both artifacts and independently reparse source and output bytes."""

    analysis = analyze_customer_sources(sources)
    report = _render_markdown(analysis)
    ledger = _render_ledger(analysis.outcome.samples)
    checks = verify_customer_artifacts(sources, report_markdown=report, ledger_csv=ledger)
    return CustomerSegmentationBuild(
        report_markdown=report,
        ledger_csv=ledger,
        analysis=analysis,
        checks=checks,
    )


def analyze_customer_sources(
    sources: tuple[CustomerSourceInput, ...],
) -> CustomerSegmentationAnalysis:
    by_id = _validate_source_bundle(sources)
    parsed_rules = _parse_rules(by_id[RULES_LOGICAL_ID])
    encoding, raw_rows = _parse_survey(by_id[SURVEY_LOGICAL_ID])
    samples = _decide_samples(raw_rows, by_id[SURVEY_LOGICAL_ID], parsed_rules)
    duplicate_count = sum(bool(sample.duplicate_of) for sample in samples)
    classified_count = sum(sample.final_label is not None for sample in samples)
    unclassified_count = sum(sample.exclusion_reason == "unclassified" for sample in samples)
    profile_counts = {
        profile: sum(sample.final_label == profile for sample in samples)
        for profile in parsed_rules.thresholds
    }
    witness_count = sum(sample.priority_applied for sample in samples)
    outcome = AgentControlLoopCustomerSegmentationOutcome(
        outcome_id="customer-segmentation-outcome-sales-020",
        status="sales_review_required",
        decision=(
            "来源规则、清洗与画像台账已由服务端重算；重复口径和策略草案仍需销售负责人批准，"
            "客户联系、CRM、商机和营销动作均未发生。"
        ),
        summary=(
            f"公开问卷 {len(samples)} 行，唯一业务载荷 {len(samples) - duplicate_count} 条；"
            f"分类 {classified_count} 条、无法归类 {unclassified_count} 条、"
            f"精确重复 {duplicate_count} 条。多标签优先级 witness {witness_count} 个。"
        ),
        source_row_count=len(samples),
        unique_payload_count=len(samples) - duplicate_count,
        duplicate_count=duplicate_count,
        classified_count=classified_count,
        unclassified_count=unclassified_count,
        excluded_count=duplicate_count + unclassified_count,
        profile_counts=profile_counts,
        parameters=AgentControlLoopCustomerSegmentationParameters(
            parsing_encoding=encoding,
            missing_score_default=parsed_rules.missing_default,
            chinese_number_domain="零至十，对应整数 0..10",
            profile_thresholds=parsed_rules.thresholds,
            profile_priority=list(parsed_rules.priority),
        ),
        rules=list(parsed_rules.rules),
        samples=list(samples),
        priority_witness_count=witness_count,
    )
    return CustomerSegmentationAnalysis(rules=parsed_rules, encoding=encoding, outcome=outcome)


def verify_customer_artifacts(
    sources: tuple[CustomerSourceInput, ...],
    *,
    report_markdown: bytes,
    ledger_csv: bytes,
) -> tuple[CustomerArtifactCheck, ...]:
    """Recompute expected facts, then parse and compare both generated artifacts."""

    expected = analyze_customer_sources(sources)
    expected_report = _render_markdown(expected)
    expected_ledger_rows = _ledger_rows(expected.outcome.samples)
    ledger_valid, ledger_rows, ledger_detail = _parse_ledger(ledger_csv)
    markdown_valid, markdown_facts, markdown_detail = _parse_markdown(report_markdown)
    expected_profile_rows = [
        (profile, str(expected.outcome.profile_counts.get(profile, 0)))
        for profile in expected.rules.priority
    ]
    expected_portrait_rows = [
        (sample.sample_id, sample.industry, sample.company_size, sample.final_label or "")
        for sample in expected.outcome.samples
        if sample.final_label is not None
    ]
    ledger_exact = ledger_valid and ledger_rows == expected_ledger_rows
    markdown_counts_ok = markdown_valid and markdown_facts.get("counts") == {
        "source": expected.outcome.source_row_count,
        "unique": expected.outcome.unique_payload_count,
        "duplicate": expected.outcome.duplicate_count,
        "classified": expected.outcome.classified_count,
        "unclassified": expected.outcome.unclassified_count,
        "excluded": expected.outcome.excluded_count,
        "witness": expected.outcome.priority_witness_count,
    }
    markdown_tables_ok = (
        markdown_valid
        and markdown_facts.get("profiles") == expected_profile_rows
        and markdown_facts.get("portraits") == expected_portrait_rows
    )
    rule_ids = [rule.rule_id for rule in expected.rules.rules]
    markdown_rules_ok = markdown_valid and markdown_facts.get("rule_ids") == rule_ids
    boundary_ok = markdown_valid and all(
        token in str(markdown_facts.get("text") or "")
        for token in (
            BOUNDARY,
            DUPLICATE_POLICY_NOTE,
            STRATEGY_EVIDENCE_STATUS,
            STRATEGY_PLACEHOLDER,
            "不能从标签冲突优先级推导销售跟进优先级",
            "原始 Sales-020 输入未修改",
        )
    )
    checks = (
        _check(
            "check-customer-source-contract-v2",
            "两份批准来源合同",
            all(source.allowlist_verified for source in sources),
            "问卷 CSV 与规则 MD 的逻辑 ID、文件名、展示路径、file_ref、声明大小、冻结字节和角色唯一性已校验。",
        ),
        _check(
            "check-customer-rule-ledger-v2",
            "规则账本由 Markdown 动态解析",
            markdown_rules_ok,
            f"{len(rule_ids)} 条清洗、分类、优先级、排除和报告规则必须逐条保留来源行；{markdown_detail}",
        ),
        _check(
            "check-customer-ledger-csv-v2",
            "逐样本台账可独立复算",
            ledger_exact,
            f"CSV 必须逐字段覆盖 {expected.outcome.source_row_count} 个原始行且无缺行、重复行或状态漂移；{ledger_detail}",
        ),
        _check(
            "check-customer-markdown-facts-v2",
            "画像表与动态分布一致",
            markdown_counts_ok and markdown_tables_ok,
            "Markdown 中的清洗计数、画像行、动态分布和多标签 witness 必须与来源重算一致。",
        ),
        _check(
            "check-customer-conservation-v2",
            "原始行、唯一载荷、分类与排除守恒",
            (
                expected.outcome.unique_payload_count + expected.outcome.duplicate_count
                == expected.outcome.source_row_count
                and expected.outcome.classified_count + expected.outcome.unclassified_count
                == expected.outcome.unique_payload_count
                and expected.outcome.unclassified_count + expected.outcome.duplicate_count
                == expected.outcome.excluded_count
            ),
            (
                f"{expected.outcome.source_row_count} 原始行 = {expected.outcome.unique_payload_count} 唯一载荷 + "
                f"{expected.outcome.duplicate_count} 重复；{expected.outcome.unique_payload_count} 唯一载荷 = "
                f"{expected.outcome.classified_count} 分类 + {expected.outcome.unclassified_count} 无法归类。"
            ),
        ),
        _check(
            "check-customer-strategy-boundary-v2",
            "策略草案与销售动作边界",
            boundary_ok,
            "没有批准的策略内容来源；话术、功能与销售优先级只显示待负责人补充，未联系客户、写 CRM、创建商机或营销。",
        ),
        _check(
            "check-customer-canonical-bytes-v2",
            "两份成果为来源重算后的规范字节",
            report_markdown == expected_report and ledger_exact,
            "Verifier 重新读取批准来源并解析最终 Markdown/CSV；任一内容、行、locator、rule ref 或边界变化均转红。",
        ),
    )
    return checks


def _validate_source_bundle(
    sources: tuple[CustomerSourceInput, ...],
) -> dict[str, CustomerSourceInput]:
    if len(sources) != 2:
        raise CustomerSegmentationValidationError(
            "source-count", "Sales-020 必须恰好包含问卷 CSV 与规则 Markdown。"
        )
    by_id: dict[str, CustomerSourceInput] = {}
    for source in sources:
        if source.logical_id in by_id:
            raise CustomerSegmentationValidationError(
                "duplicate-logical-id", f"来源逻辑 ID 重复：{source.logical_id}"
            )
        by_id[source.logical_id] = source
    if tuple(source.logical_id for source in sources) != SOURCE_ORDER:
        raise CustomerSegmentationValidationError(
            "source-order", "Sales-020 两份来源的逻辑角色或顺序不正确。"
        )
    if set(by_id) != set(SOURCE_ORDER):
        raise CustomerSegmentationValidationError("source-role", "Sales-020 来源角色不完整。")
    for logical_id in SOURCE_ORDER:
        source = by_id[logical_id]
        if not source.allowlist_verified:
            raise CustomerSegmentationValidationError(
                "allowlist", f"{source.file_name} 未通过服务端 allowlist。"
            )
        if source.file_name != EXPECTED_FILE_NAMES[logical_id]:
            raise CustomerSegmentationValidationError(
                "file-name", f"{logical_id} 文件名不符合固定来源合同。"
            )
        if source.display_path != EXPECTED_DISPLAY_PATHS[logical_id]:
            raise CustomerSegmentationValidationError(
                "display-path", f"{logical_id} 展示路径不符合固定来源合同。"
            )
        if source.file_ref != EXPECTED_FILE_REFS[logical_id]:
            raise CustomerSegmentationValidationError(
                "file-ref", f"{logical_id} file_ref 不符合固定来源合同。"
            )
        if not source.content:
            raise CustomerSegmentationValidationError("empty-source", f"{source.file_name} 为空。")
        if source.declared_size != len(source.content):
            raise CustomerSegmentationValidationError(
                "declared-size", f"{source.file_name} 声明大小与冻结字节不一致。"
            )
    if by_id[SURVEY_LOGICAL_ID].content == by_id[RULES_LOGICAL_ID].content:
        raise CustomerSegmentationValidationError(
            "same-content", "问卷与规则文件不能由同一份字节冒充不同来源。"
        )
    return by_id


def _parse_rules(source: CustomerSourceInput) -> ParsedSegmentationRules:
    try:
        text = source.content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CustomerSegmentationValidationError(
            "rule-encoding", "规则 Markdown 必须是有效 UTF-8 文本。"
        ) from exc
    if "\x00" in text:
        raise CustomerSegmentationValidationError("rule-nul", "规则 Markdown 包含 NUL。")
    lines = tuple(SourceLine(index, value.strip()) for index, value in enumerate(text.splitlines(), 1))
    nonempty = tuple(line for line in lines if line.text)
    allowed_headings = {
        "# 客户画像与差异化销售策略生成规则",
        "## 业务背景",
        "## 一、前置数据清洗规则",
        "## 二、客户画像分类逻辑",
        "### 分类标准",
        "### 标签优先级规则",
        "## 三、输出报告规范",
    }
    allowed_prose = {
        "我司主营产品为「企业级低代码开发平台」，本次基于客户偏好调研问卷的多维度评分数据，完成客户分类画像，并输出定制化差异化销售策略。",
        "处理问卷数据前需完成以下清洗操作：",
    }
    matched: dict[str, tuple[SourceLine, re.Match[str]]] = {}

    patterns: tuple[tuple[str, str], ...] = (
        ("duplicate", r"1\. 剔除重复样本，仅保留重复样本中的第一条"),
        ("chinese", r"2\. 将非数字格式的评分字段转换为对应数字（例如将「一」转换为「1」）"),
        ("missing", r"3\. 缺失的评分字段统一按数值([0-9]+)处理"),
        ("technical", r"1\. 技术型：专业\(Stech\)字段数值≥([0-9]+)的客户"),
        ("safety", r"2\. 安全型：安全\(Ssafe\)字段 \*\*和\*\* 预算\(Sbudget\)字段数值同时≥([0-9]+)的客户"),
        ("agile", r"3\. 敏捷型：易用\(Seasy\)字段数值≥([0-9]+)的客户"),
        ("priority", r"若某客户同时满足多个画像条件，按以下优先级取唯一标签：`([^`]+)`，最终输出剔除所有无法归类的样本数据"),
        ("report-parts", r"最终Markdown报告必须包含以下([0-9]+)个部分，格式严格符合要求："),
        ("portrait-module", r"1\. \*\*客户画像表格\*\*"),
        ("portrait-title", r"- 表格核心名称为「客户画像」"),
        ("portrait-columns", r"- 列名严格设定为：(.+)"),
        ("strategy-module", r"2\. \*\*销售策略模块\*\*"),
        ("strategy-title", r"- 模块标题为「销售策略」"),
        ("strategy-items", r"- 分别为([0-9]+)类客户定制差异化建议，每类客户的策略必须包含两个子项，子项标题严格使用：(.+)"),
        ("analysis-module", r"3\. \*\*客户分析模块\*\*"),
        ("analysis-title", r"- 模块标题为「客户分析」"),
        ("analysis-items", r"- 必须包含三个子项，子项标题严格使用：(.+)"),
    )
    consumed: set[int] = set()
    for line in nonempty:
        if line.text in allowed_headings or line.text in allowed_prose:
            consumed.add(line.number)
            continue
        hits = [(key, re.fullmatch(pattern, line.text)) for key, pattern in patterns]
        hits = [(key, hit) for key, hit in hits if hit is not None]
        if len(hits) != 1:
            raise CustomerSegmentationValidationError(
                "unknown-rule", f"规则 Markdown L{line.number} 存在未知、含糊或未完整消费的规范：{line.text}"
            )
        key, hit = hits[0]
        if key in matched:
            raise CustomerSegmentationValidationError(
                "duplicate-rule", f"规则 {key} 在 Markdown 中重复。"
            )
        matched[key] = (line, hit)
        consumed.add(line.number)
    required = {key for key, _ in patterns}
    if set(matched) != required or len(consumed) != len(nonempty):
        missing = sorted(required - set(matched))
        raise CustomerSegmentationValidationError(
            "missing-rule", f"规则 Markdown 缺少固定适配器要求的规范：{','.join(missing)}"
        )

    def integer(key: str, group: int = 1) -> int:
        value = int(matched[key][1].group(group))
        if not 0 <= value <= 10:
            raise CustomerSegmentationValidationError(
                "rule-number", f"规则 {key} 的评分参数必须在 0..10。"
            )
        return value

    missing_default = integer("missing")
    thresholds = {
        "技术型": integer("technical"),
        "安全型": integer("safety"),
        "敏捷型": integer("agile"),
    }
    priority = tuple(
        item.strip() for item in matched["priority"][1].group(1).split(">") if item.strip()
    )
    if len(priority) != 3 or set(priority) != set(thresholds):
        raise CustomerSegmentationValidationError(
            "priority", "标签优先级必须恰好包含三个已定义画像且不得重复。"
        )
    report_parts = int(matched["report-parts"][1].group(1))
    strategy_profile_count = int(matched["strategy-items"][1].group(1))
    if report_parts != 3 or strategy_profile_count != len(thresholds):
        raise CustomerSegmentationValidationError(
            "report-count", "固定适配器只支持来源定义的三模块与三个画像。"
        )
    output_columns = tuple(re.findall(r"`([^`]+)`", matched["portrait-columns"][1].group(1)))
    strategy_subitems = tuple(re.findall(r"`([^`]+)`", matched["strategy-items"][1].group(2)))
    analysis_subitems = tuple(re.findall(r"`([^`]+)`", matched["analysis-items"][1].group(1)))
    if len(output_columns) != 4 or set(output_columns) != {"样本ID", "企业所在行业", "企业规模", "客户画像"}:
        raise CustomerSegmentationValidationError(
            "report-columns", "客户画像表必须恰好使用来源批准的四个已知列。"
        )
    if strategy_subitems != ("推荐话术", "主推功能"):
        raise CustomerSegmentationValidationError(
            "strategy-items", "销售策略只能使用来源批准的两个待补充子项。"
        )
    if analysis_subitems != ("画像分布", "行业与规模特征", "销售优先级建议"):
        raise CustomerSegmentationValidationError(
            "analysis-items", "客户分析只能使用来源批准的三个子项。"
        )

    def public_rule(
        rule_id: str,
        category: str,
        key: str,
        *parameters: str,
    ) -> AgentControlLoopCustomerSegmentationRule:
        line = matched[key][0]
        return AgentControlLoopCustomerSegmentationRule(
            rule_id=rule_id,
            category=category,
            source_file_ref=source.file_ref,
            locator=line.locator,
            excerpt=line.text,
            parameters=list(parameters),
        )

    rules = (
        public_rule("SEG-CLEAN-DUPLICATE", "cleaning", "duplicate", "policy_assumption=exact_non_id_payload"),
        public_rule("SEG-CLEAN-CHINESE", "cleaning", "chinese", "mapping=零..十", "range=0..10"),
        public_rule("SEG-CLEAN-MISSING", "cleaning", "missing", f"default={missing_default}"),
        public_rule("SEG-PROFILE-TECH", "classification", "technical", f"threshold={thresholds['技术型']}"),
        public_rule("SEG-PROFILE-SAFE", "classification", "safety", f"threshold={thresholds['安全型']}", "fields=safe+budget"),
        public_rule("SEG-PROFILE-AGILE", "classification", "agile", f"threshold={thresholds['敏捷型']}"),
        public_rule("SEG-PRIORITY", "priority", "priority", f"order={' > '.join(priority)}"),
        public_rule("SEG-EXCLUDE", "exclusion", "priority", "unclassified=exclude"),
        public_rule("SEG-REPORT-PARTS", "report", "report-parts", f"count={report_parts}"),
        public_rule("SEG-REPORT-PORTRAIT", "report", "portrait-module", "title=客户画像"),
        public_rule("SEG-REPORT-COLUMNS", "report", "portrait-columns", *output_columns),
        public_rule("SEG-REPORT-STRATEGY", "report", "strategy-module", "title=销售策略"),
        public_rule("SEG-REPORT-STRATEGY-ITEMS", "report", "strategy-items", *strategy_subitems),
        public_rule("SEG-REPORT-ANALYSIS", "report", "analysis-module", "title=客户分析"),
        public_rule("SEG-REPORT-ANALYSIS-ITEMS", "report", "analysis-items", *analysis_subitems),
    )
    return ParsedSegmentationRules(
        source_file_ref=source.file_ref,
        rules=rules,
        missing_default=missing_default,
        thresholds=thresholds,
        priority=priority,
        output_columns=output_columns,
        strategy_subitems=strategy_subitems,
        analysis_subitems=analysis_subitems,
    )


def _parse_survey(source: CustomerSourceInput) -> tuple[str, tuple[tuple[int, tuple[str, ...]], ...]]:
    text = ""
    encoding = ""
    for candidate in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = source.content.decode(candidate)
            encoding = candidate
            break
        except UnicodeDecodeError:
            continue
    if not encoding:
        raise CustomerSegmentationValidationError("csv-encoding", "问卷 CSV 编码不受支持。")
    if "\x00" in text:
        raise CustomerSegmentationValidationError("csv-nul", "问卷 CSV 包含 NUL。")
    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except (csv.Error, UnicodeError) as exc:
        raise CustomerSegmentationValidationError("csv-parse", "问卷 CSV 结构损坏或截断。") from exc
    if len(rows) < 2:
        raise CustomerSegmentationValidationError("csv-empty", "问卷 CSV 必须包含表头和业务行。")
    if len(rows) > 20_001:
        raise CustomerSegmentationValidationError("csv-row-limit", "问卷 CSV 超过固定适配器行数上限。")
    header = tuple(rows[0])
    if header != SURVEY_HEADERS or len(header) != len(set(header)):
        raise CustomerSegmentationValidationError(
            "csv-header", "问卷 CSV 必须使用精确且唯一的八个批准表头。"
        )
    parsed: list[tuple[int, tuple[str, ...]]] = []
    seen_ids: set[str] = set()
    for row_number, values in enumerate(rows[1:], start=2):
        if len(values) != len(SURVEY_HEADERS):
            raise CustomerSegmentationValidationError(
                "csv-column-count", f"问卷 CSV 第 {row_number} 行列数不一致。"
            )
        normalized = tuple(value.strip() for value in values)
        if any(value and value[0] in "=+-@" for value in normalized):
            raise CustomerSegmentationValidationError(
                "csv-injection", f"问卷 CSV 第 {row_number} 行包含公式或 CSV 注入前缀。"
            )
        sample_id, industry, company_size, respondent_role = normalized[:4]
        if not sample_id or not industry or not company_size or not respondent_role:
            raise CustomerSegmentationValidationError(
                "csv-required-field", f"问卷 CSV 第 {row_number} 行缺少身份或业务字段。"
            )
        if sample_id in seen_ids:
            raise CustomerSegmentationValidationError(
                "duplicate-sample-id", f"问卷 CSV 样本 ID 重复：{sample_id}。"
            )
        seen_ids.add(sample_id)
        parsed.append((row_number, normalized))
    return encoding, tuple(parsed)


def _decide_samples(
    raw_rows: tuple[tuple[int, tuple[str, ...]], ...],
    survey_source: CustomerSourceInput,
    rules: ParsedSegmentationRules,
) -> tuple[AgentControlLoopCustomerSampleDecision, ...]:
    first_payload: dict[tuple[str, ...], str] = {}
    decisions: list[AgentControlLoopCustomerSampleDecision] = []
    for row_number, values in raw_rows:
        sample_id, industry, company_size, respondent_role = values[:4]
        raw_by_key = dict(zip(SCORE_FIELDS, values[4:], strict=True))
        cleaned: dict[str, int] = {}
        transformations: list[str] = []
        for key, raw in raw_by_key.items():
            if raw == "":
                value = rules.missing_default
                transformations.append(f"{key}:空→{value}")
            elif re.fullmatch(r"[0-9]+", raw):
                value = int(raw)
            elif raw in CHINESE_NUMBERS:
                value = CHINESE_NUMBERS[raw]
                transformations.append(f"{key}:{raw}→{value}")
            else:
                raise CustomerSegmentationValidationError(
                    "score-format", f"问卷 CSV 第 {row_number} 行 {SCORE_FIELDS[key]} 不是受支持的 0..10 整数或中文数字。"
                )
            if not 0 <= value <= 10:
                raise CustomerSegmentationValidationError(
                    "score-range", f"问卷 CSV 第 {row_number} 行 {SCORE_FIELDS[key]} 超出 0..10。"
                )
            cleaned[key] = value
        matches = [
            profile
            for profile in rules.priority
            if all(cleaned[field] >= rules.thresholds[profile] for field in PROFILE_FIELDS[profile])
        ]
        payload = values[1:]
        duplicate_of = first_payload.get(payload)
        if duplicate_of is None:
            first_payload[payload] = sample_id
        priority_applied = duplicate_of is None and len(matches) > 1
        final_label = matches[0] if duplicate_of is None and matches else None
        exclusion_reason = (
            "exact_duplicate" if duplicate_of is not None else "unclassified" if not matches else None
        )
        rule_refs = ["SEG-CLEAN-DUPLICATE", "SEG-CLEAN-CHINESE", "SEG-CLEAN-MISSING"]
        rule_refs.extend(
            {
                "技术型": "SEG-PROFILE-TECH",
                "安全型": "SEG-PROFILE-SAFE",
                "敏捷型": "SEG-PROFILE-AGILE",
            }[profile]
            for profile in matches
        )
        if priority_applied:
            rule_refs.append("SEG-PRIORITY")
        if exclusion_reason == "unclassified":
            rule_refs.append("SEG-EXCLUDE")
        decisions.append(
            AgentControlLoopCustomerSampleDecision(
                sample_id=sample_id,
                source_file_ref=survey_source.file_ref,
                source_row=row_number,
                source_locator=f"客户画像调研问卷.csv:row={row_number}",
                industry=industry,
                company_size=company_size,
                respondent_role=respondent_role,
                raw_scores=raw_by_key,
                cleaned_scores=cleaned,
                transformations=transformations,
                matched_profiles=matches,
                priority_applied=priority_applied,
                final_label=final_label,
                exclusion_reason=exclusion_reason,
                duplicate_of=duplicate_of,
                rule_refs=list(dict.fromkeys(rule_refs)),
            )
        )
    return tuple(decisions)


def _render_ledger(samples: list[AgentControlLoopCustomerSampleDecision]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(LEDGER_HEADERS)
    writer.writerows(_ledger_rows(samples))
    return output.getvalue().encode("utf-8-sig")


def _ledger_rows(samples: list[AgentControlLoopCustomerSampleDecision]) -> list[list[str]]:
    return [
        [
            str(sample.source_row),
            sample.source_locator,
            sample.sample_id,
            sample.industry,
            sample.company_size,
            sample.respondent_role,
            sample.raw_scores["tech"],
            sample.raw_scores["safe"],
            sample.raw_scores["budget"],
            sample.raw_scores["easy"],
            str(sample.cleaned_scores["tech"]),
            str(sample.cleaned_scores["safe"]),
            str(sample.cleaned_scores["budget"]),
            str(sample.cleaned_scores["easy"]),
            "；".join(sample.transformations),
            "、".join(sample.matched_profiles),
            "是" if sample.priority_applied else "否",
            sample.final_label or "",
            sample.exclusion_reason or "",
            sample.duplicate_of or "",
            ",".join(sample.rule_refs),
        ]
        for sample in samples
    ]


def _render_markdown(analysis: CustomerSegmentationAnalysis) -> bytes:
    outcome = analysis.outcome
    rules = analysis.rules
    lines = [
        "# 客户画像及销售策略",
        "",
        BOUNDARY,
        "",
        "## 运行摘要",
        f"- 原始问卷行：{outcome.source_row_count}",
        f"- 唯一业务载荷：{outcome.unique_payload_count}",
        f"- 精确重复：{outcome.duplicate_count}",
        f"- 已分类：{outcome.classified_count}",
        f"- 无法归类：{outcome.unclassified_count}",
        f"- 合计排除：{outcome.excluded_count}",
        f"- 多标签优先级 witness：{outcome.priority_witness_count}",
        f"- CSV 解析编码：{analysis.encoding}",
        f"- 策略证据状态：{STRATEGY_EVIDENCE_STATUS}",
        "",
        "## 规则账本",
        "| 规则ID | 类别 | 来源位置 | 原文 | 参数 |",
        "| --- | --- | --- | --- | --- |",
        *[
            "| " + " | ".join(
                (
                    rule.rule_id,
                    rule.category,
                    rule.locator,
                    _md_cell(rule.excerpt),
                    _md_cell("；".join(rule.parameters)),
                )
            ) + " |"
            for rule in rules.rules
        ],
        "",
        "## 客户画像",
        "| " + " | ".join(rules.output_columns) + " |",
        "| " + " | ".join("---" for _ in rules.output_columns) + " |",
    ]
    column_value = {
        "样本ID": lambda sample: sample.sample_id,
        "企业所在行业": lambda sample: sample.industry,
        "企业规模": lambda sample: sample.company_size,
        "客户画像": lambda sample: sample.final_label or "",
    }
    for sample in outcome.samples:
        if sample.final_label is None:
            continue
        lines.append(
            "| "
            + " | ".join(_md_cell(column_value[column](sample)) for column in rules.output_columns)
            + " |"
        )
    lines.extend(("", "## 销售策略", ""))
    for profile in rules.thresholds:
        lines.extend(
            (
                f"### {profile}",
                f"- 策略证据状态：`{STRATEGY_EVIDENCE_STATUS}`",
                f"#### {rules.strategy_subitems[0]}",
                STRATEGY_PLACEHOLDER,
                f"#### {rules.strategy_subitems[1]}",
                STRATEGY_PLACEHOLDER,
                "",
            )
        )
    lines.extend(
        (
            "## 客户分析",
            "",
            f"### {rules.analysis_subitems[0]}",
            "| 画像 | 数量 |",
            "| --- | ---: |",
            *[
                f"| {profile} | {outcome.profile_counts.get(profile, 0)} |"
                for profile in rules.priority
            ],
            "",
            f"### {rules.analysis_subitems[1]}",
            "以下只列公开样本中的行业与规模，不推断客户群规律或销售效果：",
        )
    )
    for profile in rules.priority:
        facts = [
            f"{sample.sample_id}={sample.industry}/{sample.company_size}"
            for sample in outcome.samples
            if sample.final_label == profile
        ]
        lines.append(f"- {profile}：{'；'.join(facts) if facts else '无已分类样本'}")
    lines.extend(
        (
            "",
            f"### {rules.analysis_subitems[2]}",
            "没有批准的销售优先级来源，不能从标签冲突优先级推导销售跟进优先级；待销售负责人补充并批准。",
            "",
            "## 口径假设与边界",
            f"- {DUPLICATE_POLICY_NOTE}",
            f"- canonical 是否实际触发优先级：{'是' if outcome.priority_witness_count else '否'}；witness={outcome.priority_witness_count}。",
            "- 画像分类只反映固定公开问卷和当前规则，不代表真实客户研究或分类业务适用性。",
            "- 策略部分只是待批准模板，没有批准的话术、功能或销售排序来源。",
            "- 原始 Sales-020 输入未修改；external_action=none。",
            "- 未联系客户、未写 CRM、未创建商机、未发送营销内容。",
        )
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _parse_ledger(content: bytes) -> tuple[bool, list[list[str]], str]:
    try:
        text = content.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except (UnicodeDecodeError, csv.Error) as exc:
        return False, [], f"CSV 无法解析：{exc}"
    if not rows or tuple(rows[0]) != LEDGER_HEADERS:
        return False, [], "CSV 表头与逐样本台账合同不一致。"
    data = rows[1:]
    if any(len(row) != len(LEDGER_HEADERS) for row in data):
        return False, data, "CSV 存在列数不一致的业务行。"
    if len({row[0] for row in data}) != len(data):
        return False, data, "CSV 原始行号重复。"
    return True, data, f"解析 {len(data)} 条逐样本记录。"


def _parse_markdown(content: bytes) -> tuple[bool, dict[str, object], str]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        return False, {}, f"Markdown UTF-8 解码失败：{exc}"
    required_headings = (
        "# 客户画像及销售策略",
        "## 运行摘要",
        "## 规则账本",
        "## 客户画像",
        "## 销售策略",
        "## 客户分析",
        "### 画像分布",
        "### 行业与规模特征",
        "### 销售优先级建议",
        "## 口径假设与边界",
    )
    if any(text.count(heading) != 1 for heading in required_headings):
        return False, {"text": text}, "Markdown 标题缺失、重复或被篡改。"

    def integer(label: str) -> int | None:
        match = re.search(rf"^- {re.escape(label)}：([0-9]+)$", text, re.MULTILINE)
        return int(match.group(1)) if match else None

    tables = _markdown_tables(text)
    rule_table = tables.get("规则账本", [])
    portrait_table = tables.get("客户画像", [])
    profile_table = tables.get("画像分布", [])
    facts = {
        "text": text,
        "counts": {
            "source": integer("原始问卷行"),
            "unique": integer("唯一业务载荷"),
            "duplicate": integer("精确重复"),
            "classified": integer("已分类"),
            "unclassified": integer("无法归类"),
            "excluded": integer("合计排除"),
            "witness": integer("多标签优先级 witness"),
        },
        "rule_ids": [row[0] for row in rule_table[1:]] if rule_table else [],
        "portraits": [tuple(row) for row in portrait_table[1:]] if portrait_table else [],
        "profiles": [tuple(row) for row in profile_table[1:]] if profile_table else [],
    }
    return True, facts, "Markdown 标题、规则账本、画像表和分布表已解析。"


def _markdown_tables(text: str) -> dict[str, list[list[str]]]:
    tables: dict[str, list[list[str]]] = {}
    current_heading = ""
    current_rows: list[list[str]] = []
    for line in text.splitlines():
        if line.startswith("#"):
            if current_heading and current_rows:
                tables[current_heading] = current_rows
            current_heading = line.lstrip("#").strip()
            current_rows = []
            continue
        if line.startswith("| ") and line.endswith(" |"):
            cells = [cell.strip().replace("\\|", "|") for cell in line[2:-2].split(" | ")]
            if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                continue
            current_rows.append(cells)
        elif current_rows:
            tables[current_heading] = current_rows
            current_rows = []
    if current_heading and current_rows:
        tables[current_heading] = current_rows
    return tables


def _md_cell(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _check(check_id: str, label: str, passed: bool, detail: str) -> CustomerArtifactCheck:
    return CustomerArtifactCheck(
        check_id=check_id,
        label=label,
        passed=bool(passed),
        detail=detail,
    )
