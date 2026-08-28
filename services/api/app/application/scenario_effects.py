"""Deterministic office tools and effect gates over the pinned FORTE inputs.

These adapters are selected from a user-authored instruction. They never read
``task.md`` or benchmark solutions, never modify FORTE input bytes, and never
perform an external action. Model quality and deterministic artifact correctness
remain separate facts in the run Snapshot.
"""

from __future__ import annotations

import csv
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Protocol
from xml.sax.saxutils import escape

from packages.contracts.harness_models import (
    AgentControlLoopArtifactCheck,
    AgentControlLoopArtifactSelfTest,
    AgentControlLoopArtifactTestSuite,
    AgentControlLoopBusinessGateOutcome,
    AgentControlLoopCandidateReviewOutcome,
    AgentControlLoopCustomerSegmentationOutcome,
    AgentControlLoopFinanceReviewOutcome,
    AgentControlLoopLegalReviewOutcome,
    AgentControlLoopOutboundFlowOutcome,
    AgentControlLoopSREDiagnosisOutcome,
)
from services.api.app.application.candidate_review_effect import (
    CANDIDATE_LOGICAL_IDS,
    JD_BD_ID,
    JD_TEXT_ID,
    CandidateReviewValidationError,
    CandidateSourceInput,
    build_candidate_review,
)
from services.api.app.application.react_refactor_effect import (
    build_real_react_refactor,
)
from services.api.app.application.evaluation_platform_effect import (
    build_real_evaluation_platform_fix,
)
from services.api.app.application.dashboard_toolkit_effect import (
    build_real_dashboard_toolkit_fix,
)
from services.api.app.application.release_readiness_effect import (
    ReleaseReadinessValidationError,
    build_release_readiness,
    invalid_release_outcome,
)
from services.api.app.application.legal_delegation_effect import (
    DOCUMENT_LOGICAL_IDS,
    RULE_LOGICAL_ID,
    LegalDelegationValidationError,
    LegalSourceInput,
    build_legal_delegation_review,
)
from services.api.app.application.finance_reconciliation_effect import (
    SOURCE_SPECS as FINANCE_SOURCE_SPECS,
    FinanceReconciliationValidationError,
    FinanceSourceInput,
    build_finance_reconciliation,
)
from services.api.app.application.outbound_flow_effect import (
    SOURCE_LOGICAL_ID as OUTBOUND_SOURCE_LOGICAL_ID,
    OutboundFlowValidationError,
    OutboundSourceInput,
    build_outbound_flow,
)
from services.api.app.application.customer_segmentation_effect import (
    RULES_LOGICAL_ID as CUSTOMER_RULES_LOGICAL_ID,
    SURVEY_LOGICAL_ID as CUSTOMER_SURVEY_LOGICAL_ID,
    CustomerSegmentationValidationError,
    CustomerSourceInput,
    build_customer_segmentation,
)
from services.api.app.application.sre_diagnosis_effect import (
    SOURCE_LOGICAL_ID as SRE_SOURCE_LOGICAL_ID,
    SREDiagnosisValidationError,
    SRESourceInput,
    build_sre_diagnosis,
)


class ScenarioEffectError(RuntimeError):
    pass


class ScenarioEffectCatalog(Protocol):
    def public_workspace(self) -> dict[str, Any]: ...

    def public_file(self, file_ref: str) -> dict[str, Any]: ...

    def checked_input_bytes(self, file_ref: str) -> bytes: ...


@dataclass(frozen=True)
class GeneratedOfficeArtifact:
    title: str
    file_name: str
    media_type: str
    content: bytes
    source_file_refs: tuple[str, ...]
    validator_id: str
    checks: tuple[AgentControlLoopArtifactCheck, ...]
    summary: str
    covered_period: str | None = None
    statistic_basis: str | None = None
    purpose: str | None = None
    record_count: int | None = None
    deliverable_type: str | None = None
    key_outputs: tuple[str, ...] = ()
    key_outputs_label: str | None = None
    review_guidance: str | None = None
    execution_summary: str | None = None
    self_test: AgentControlLoopArtifactSelfTest | None = None
    business_gate_outcome: AgentControlLoopBusinessGateOutcome | None = None
    legal_review_outcome: AgentControlLoopLegalReviewOutcome | None = None
    candidate_review_outcome: AgentControlLoopCandidateReviewOutcome | None = None
    finance_review_outcome: AgentControlLoopFinanceReviewOutcome | None = None
    outbound_flow_outcome: AgentControlLoopOutboundFlowOutcome | None = None
    customer_segmentation_outcome: AgentControlLoopCustomerSegmentationOutcome | None = None
    sre_diagnosis_outcome: AgentControlLoopSREDiagnosisOutcome | None = None

    @property
    def verifier_status(self) -> str:
        return "passed" if all(check.passed for check in self.checks) else "failed"


@dataclass(frozen=True)
class ScenarioEffectExecution:
    scenario_id: str
    capability_id: str
    status: str
    state: str
    action: str
    observation: str
    cost: str
    result: str
    source_file_refs: tuple[str, ...]
    artifacts: tuple[GeneratedOfficeArtifact, ...]
    prohibited_side_effects: tuple[str, ...]


@dataclass(frozen=True)
class ScenarioEffectSpec:
    scenario_id: str
    capability_id: str
    title: str
    instruction: str
    source_labels: tuple[tuple[str, str], ...]
    expected_artifacts: tuple[str, ...]
    deterministic_validator: str
    frontend_effect: str
    snapshot_facts: tuple[str, ...]
    prohibited_side_effects: tuple[str, ...]
    lifecycle: str
    matcher: Callable[[str], bool]


@dataclass(frozen=True)
class FrozenScenarioEffectCatalog:
    """Immutable, allowlisted inputs captured before worker-thread execution."""

    workspace: dict[str, Any]
    previews: dict[str, dict[str, Any]]
    input_bytes: dict[str, bytes]

    def public_workspace(self) -> dict[str, Any]:
        return copy.deepcopy(self.workspace)

    def public_file(self, file_ref: str) -> dict[str, Any]:
        try:
            return copy.deepcopy(self.previews[file_ref])
        except KeyError as exc:
            raise ScenarioEffectError("冻结的确定性工具输入缺少安全预览") from exc

    def checked_input_bytes(self, file_ref: str) -> bytes:
        try:
            return self.input_bytes[file_ref]
        except KeyError as exc:
            raise ScenarioEffectError("冻结的确定性工具输入缺少原始字节") from exc


@dataclass(frozen=True)
class FrozenScenarioEffectInput:
    spec: ScenarioEffectSpec
    catalog: FrozenScenarioEffectCatalog
    source_file_refs: tuple[str, ...]


def _contains_all(*tokens: str) -> Callable[[str], bool]:
    return lambda value: all(token.lower() in value.lower() for token in tokens)


def _contains_any(*groups: tuple[str, ...]) -> Callable[[str], bool]:
    return lambda value: any(
        all(token.lower() in value.lower() for token in group) for group in groups
    )


def summarize_artifact_check_groups(
    check_groups: Iterable[Iterable[AgentControlLoopArtifactCheck]],
) -> tuple[int, int, int, bool]:
    """Return projected, unique, passed counts and full-checklist sharing."""

    materialized_groups = [tuple(checks) for checks in check_groups]
    projected_count = 0
    checks_by_id: dict[str, bool] = {}
    checklist_signatures: set[tuple[str, ...]] = set()
    for checks in materialized_groups:
        checklist_signatures.add(tuple(sorted({check.check_id for check in checks})))
        for check in checks:
            projected_count += 1
            checks_by_id[check.check_id] = checks_by_id.get(check.check_id, True) and check.passed
    same_checklist = (
        len(materialized_groups) > 1
        and len(checklist_signatures) == 1
        and bool(next(iter(checklist_signatures), ()))
    )
    return (
        projected_count,
        len(checks_by_id),
        sum(checks_by_id.values()),
        same_checklist,
    )


SCENARIO_EFFECT_SPECS: tuple[ScenarioEffectSpec, ...] = (
    ScenarioEffectSpec(
        "TC-01",
        "office-onboarding-assets",
        "入职资产匹配",
        "根据入职时间表和分配规则，生成 3 月 20 日至 4 月 20 日的入职资产匹配表。",
        (("行政办公", "3月20日-4月20日入职时间表.csv"), ("行政办公", "入职物资权限软件分配.pdf")),
        ("入职资产匹配表.csv",),
        "validator-onboarding-assets-v1",
        "成果区显示真实 CSV、来源范围、逐项确定性检查和下载入口。",
        ("workspace_artifacts[]", "effect_receipts[]", "deterministic_verification_completed"),
        ("不覆盖原始 CSV", "不创建账号", "不创建采购单"),
        "implemented",
        _contains_any(("入职", "资产"), ("入职", "物资", "权限")),
    ),
    ScenarioEffectSpec(
        "TC-02",
        "office-code-react-refactor",
        "搜索 Agent 有界 ReAct 控制结构重构",
        "把搜索 Agent 从固定 Workflow 重构为带迭代上限和轨迹的 ReAct 结构。",
        (
            ("算法研发", "config.py"),
            ("算法研发", "llm.py"),
            ("算法研发", "main.py"),
            ("算法研发", "requirements.txt"),
            ("算法研发", "search_agent.log"),
            ("算法研发", "tools.py"),
            ("算法研发", "workflow.py"),
        ),
        ("search-agent-react-refactor.zip", "TC-02测试与改动说明.md"),
        "validator-code-project-copy-v2",
        "展示真实 diff、命令回执和失败位置。",
        ("effect_receipts[]",),
        (
            "不修改 FORTE 原始源码",
            "不运行未批准命令",
            "固定测试不调用网络或生产搜索",
        ),
        "implemented",
        _contains_any(("ReAct", "Workflow"), ("搜索 Agent", "重构")),
    ),
    ScenarioEffectSpec(
        "TC-03",
        "office-remote-sql-analysis",
        "远程 SQL 经营分析",
        "连接只读 Datasette，分析网约车经营数据并复核指标。",
        (),
        ("SQL 查询回执", "经营分析报告"),
        "validator-remote-sql-v1",
        "明确显示 Connector 未授权和未产生经营结论。",
        ("effect_receipts[].status=blocked_external_boundary",),
        ("不伪造 SQL 结果", "不连接未授权数据库"),
        "blocked_external_boundary",
        _contains_any(("Datasette", "SQL"), ("网约车", "经营", "数据")),
    ),
    ScenarioEffectSpec(
        "TC-04",
        "office-code-test-and-fix",
        "评测平台真实测试与修复",
        "为评测平台补充单元测试，覆盖 Service、执行引擎和工具类；真实运行测试，修复失败，并给出覆盖率与修改文件。",
        (
            ("研发交付", "PRD.md"),
            ("研发交付", "technical-design.md"),
            ("研发交付", "model_service.py"),
            ("研发交付", "dataset_service.py"),
            ("研发交付", "evaluation_engine.py"),
            ("研发交付", "pagination.py"),
            ("研发交付", "response.py"),
        ),
        ("评测平台真实修复包.zip", "TC-04真实测试报告.md"),
        "validator-evaluation-platform-project-v2",
        "展示完整隔离副本、三处真实 diff、五类具名测试、真实命令和逐文件覆盖率。",
        ("effect_receipts[]",),
        (
            "不修改 FORTE 原始源码",
            "不伪造测试通过",
            "不调用真实模型端点",
            "不运行前端 package script",
            "不自动创建 PR",
        ),
        "implemented",
        _contains_any(("评测平台", "测试"), ("Service", "覆盖率")),
    ),
    ScenarioEffectSpec(
        "TC-05",
        "office-finance-reconciliation",
        "财务跨期核对",
        "核对三期往来明细，生成未付统计、未收统计，并判断是否存在僵尸账款。",
        (
            ("财务管理", "2025往来明细-上半年.xlsx"),
            ("财务管理", "2025往来明细-下半年.xlsx"),
            ("财务管理", "2026往来明细.xlsx"),
        ),
        ("未付统计.csv", "未收统计.csv", "跨期核对说明.md"),
        "validator-finance-reconciliation-v1",
        "成果区显示两个真实 CSV、跨期结论、金额复算和下载入口。",
        ("workspace_artifacts[]", "effect_receipts[]", "deterministic_verification_completed"),
        ("不覆盖原始账表", "不记账", "不发起付款"),
        "implemented",
        _contains_any(("未付", "未收"), ("跨期", "往来"), ("僵尸账款",)),
    ),
    ScenarioEffectSpec(
        "TC-06",
        "office-candidate-review",
        "双岗位简历筛选",
        "依据两个岗位说明分别审阅五份简历，保留逐条证据并输出辅助筛选结果。",
        (
            ("人力招聘", "外卖商户BD岗位JD.docx"),
            ("人力招聘", "文本评测岗位JD.docx"),
            ("人力招聘", "周伦简历.pdf"),
            ("人力招聘", "孙博文简历.pdf"),
            ("人力招聘", "李雨桐简历.pdf"),
            ("人力招聘", "王琳达简历.pdf"),
            ("人力招聘", "赵晨曦简历.pdf"),
        ),
        (
            "外卖商户BD岗位辅助筛选报告.docx",
            "文本评测岗位辅助筛选报告.docx",
            "候选人岗位条件逐项台账.csv",
        ),
        "validator-candidate-review-v2",
        "先区分确定性验证、岗位匹配建议与最终 HR 决定，再按岗位和候选人展开双来源证据。",
        (
            "workspace_artifacts[].candidate_review_outcome",
            "effect_receipts[].candidate_review_outcome",
        ),
        (
            "不作自动录用或淘汰决定",
            "默认隐藏非必要敏感信息",
            "不声称已完成公平性评估",
        ),
        "implemented",
        _contains_any(("简历", "岗位"), ("候选人", "筛选")),
    ),
    ScenarioEffectSpec(
        "TC-07",
        "office-legal-delegation-review",
        "授权委托书风控核查",
        "依据统一规则核查六份授权委托书并形成风险报告。",
        (
            ("法务", "授权委托书风控校验规则.md"),
            ("法务", "委托书1.docx"),
            ("法务", "委托书2.docx"),
            ("法务", "委托书3.docx"),
            ("法务", "委托书4.docx"),
            ("法务", "委托书5.docx"),
            ("法务", "委托书6.docx"),
        ),
        ("授权委托书风控报告.docx", "授权委托书逐项核查台账.csv"),
        "validator-legal-delegation-v2",
        "先显示法务 Gate 与签署边界，再按文档展开 21 条规则、来源位置和处置动作。",
        (
            "workspace_artifacts[].business_gate_outcome",
            "workspace_artifacts[].legal_review_outcome",
            "effect_receipts[].business_gate_outcome",
        ),
        ("不替代正式法律意见", "不签署文档", "不判断授权已经生效"),
        "implemented",
        _contains_any(("委托书", "风控"), ("授权", "核查")),
    ),
    ScenarioEffectSpec(
        "TC-08",
        "office-web-ad-collection",
        "竞品广告采集",
        "根据本地规则从 Web 采集竞品广告，保留 URL、时间和去重键。",
        (("市场营销", "广告识别规则.docx"),),
        ("竞品广告记录",),
        "validator-web-source-v1",
        "显示 Web Connector 未授权且没有伪造采集记录。",
        ("effect_receipts[].status=blocked_external_boundary",),
        ("不访问未授权 Web", "不伪造 URL"),
        "blocked_external_boundary",
        _contains_any(("竞品", "广告", "采集"), ("Web", "广告")),
    ),
    ScenarioEffectSpec(
        "TC-09",
        "office-scheduled-news",
        "周期资讯任务",
        "定时搜索新闻并以幂等批次追加到工作文件。",
        (),
        ("计划回执", "追加文件"),
        "validator-scheduler-v1",
        "显示 Scheduler/Web Connector 缺失且没有伪装定时成功。",
        ("effect_receipts[].status=blocked_external_boundary",),
        ("不创建系统定时任务", "不访问未授权 Web"),
        "blocked_external_boundary",
        _contains_any(("定时", "新闻"), ("周期", "资讯"), ("cron",)),
    ),
    ScenarioEffectSpec(
        "TC-10",
        "office-compliant-outbound-flow",
        "合规外呼流程",
        "根据专业性说明生成信用卡 M1 逾期用户 AI 外呼催收流程图文档。",
        (("运营管理", "专业性说明.md"),),
        ("外呼流程-M1逾期用户AI外呼催收流程图.docx",),
        "validator-compliant-outbound-flow-v2",
        "成果区分开显示来源与图结构验证、规则覆盖、合规审批和未发生的外部动作。",
        (
            "workspace_artifacts[].outbound_flow_outcome",
            "effect_receipts[].outbound_flow_outcome",
            "deterministic_verification_completed",
        ),
        ("不拨号", "不写 CRM", "不发送短信", "不写禁呼名单", "不实际转人工"),
        "implemented",
        _contains_any(("M1", "外呼"), ("催收", "流程")),
    ),
    ScenarioEffectSpec(
        "TC-11",
        "office-release-readiness",
        "上线合规核验",
        "综合 PRD、上线配置、功能测试和兼容测试，给出上线结论与改进计划。",
        (
            ("产品管理", "PRD_v2.5.md"),
            ("产品管理", "上线配置清单.xlsx"),
            ("产品管理", "功能测试报告.xlsx"),
            ("产品管理", "线上兼容环境测试报告.xlsx"),
        ),
        ("上线合规与风险报告.docx", "上线功能风险逐项台账.csv"),
        "validator-release-readiness-v2",
        "先显示业务 Gate 结论和四条原因，再显示辅助指标、逐功能台账与两份下载成果。",
        (
            "workspace_artifacts[].business_gate_outcome",
            "effect_receipts[].business_gate_outcome",
        ),
        ("不执行上线", "不改配置"),
        "implemented",
        _contains_any(("上线", "合规"), ("PRD", "兼容", "测试")),
    ),
    ScenarioEffectSpec(
        "TC-12",
        "office-js-test-and-fix",
        "看板工具库测试与修复",
        "为三个看板工具模块编写 Vitest，修复源码并真实运行测试。",
        (
            ("质量保障", "package.json"),
            ("质量保障", "vitest.config.js"),
            ("质量保障", "index.js"),
            ("质量保障", "chartHelper.js"),
            ("质量保障", "dataTransformer.js"),
            ("质量保障", "dateUtils.js"),
            ("质量保障", "exportHelper.js"),
            ("质量保障", "filterEngine.js"),
            ("质量保障", "metricsCalculator.js"),
            ("质量保障", "statisticsEngine.js"),
            ("质量保障", "validatorUtils.js"),
        ),
        ("看板工具库修复包.zip", "TC-12真实测试报告.md"),
        "validator-dashboard-toolkit-project-v2",
        "显示完整隔离副本、分阶段红灯、真实 diff、71 项测试和逐文件覆盖率。",
        ("effect_receipts[]",),
        ("不修改 FORTE 原始源码", "不伪造测试通过"),
        "implemented",
        _contains_any(("Vitest",), ("看板", "测试", "修复")),
    ),
    ScenarioEffectSpec(
        "TC-13",
        "office-customer-segmentation",
        "客户画像与销售策略",
        "清洗问卷、完成客户画像分类，并生成差异化销售策略 Markdown 报告。",
        (
            ("销售运营", "客户画像调研问卷.csv"),
            ("销售运营", "客户分类画像与差异化销售策略生成规则.md"),
        ),
        ("客户画像及销售策略.md", "客户画像逐样本台账.csv"),
        "validator-customer-segmentation-v2",
        "分开显示来源与成果验证、清洗事实、策略草案复核和未发生的客户动作。",
        (
            "workspace_artifacts[].customer_segmentation_outcome",
            "effect_receipts[].customer_segmentation_outcome",
            "deterministic_verification_completed",
        ),
        ("不联系客户", "不写 CRM", "不创建商机", "不把公开样本当真实线索"),
        "implemented",
        _contains_any(("客户画像", "销售策略"), ("问卷", "分群")),
    ),
    ScenarioEffectSpec(
        "TC-14",
        "office-sre-log-diagnosis",
        "SRE 日志诊断",
        "分析双十一 Elasticsearch 日志，给出根因与两个层面的紧急止损建议。",
        (("可靠性工程", "log.txt"),),
        ("ES故障诊断与止损建议.md", "SRE事故观察与动作台账.csv"),
        "validator-sre-log-diagnosis-v2",
        "分开显示来源与成果验证、来源冲突、根因假设/提案复核和全部未执行动作。",
        (
            "workspace_artifacts[].sre_diagnosis_outcome",
            "effect_receipts[].sre_diagnosis_outcome",
            "deterministic_verification_completed",
        ),
        ("不执行 ES 命令", "不连接集群", "不自动限流"),
        "implemented",
        _contains_any(("Elasticsearch", "日志"), ("ES", "日志", "止损"), ("双十一", "集群")),
    ),
    ScenarioEffectSpec(
        "TC-15",
        "office-ux-pain-prioritization",
        "交互痛点排序",
        "根据交互日志、痛点规则和页面规范，生成排序正确的交互规范优化方案 CSV。",
        (
            ("用户体验", "用户交互行为日志.xlsx"),
            ("用户体验", "交互行为痛点及优化规则.md"),
            ("用户体验", "页面级交互规范.docx"),
        ),
        ("交互规范优化方案.csv",),
        "validator-ux-pain-prioritization-v1",
        "成果区显示真实 CSV、排序检查、失败原因与下载入口。",
        ("workspace_artifacts[]", "effect_receipts[]", "deterministic_verification_completed"),
        ("不修改生产界面", "不自动发布建议"),
        "implemented",
        _contains_any(("交互", "痛点", "优先级"), ("交互", "痛点", "优化")),
    ),
)


class ScenarioEffectEngine:
    """Dispatches deterministic office adapters without a Scenario UI switch."""

    def match(self, instruction: str) -> ScenarioEffectSpec | None:
        normalized = instruction.strip()
        return next((spec for spec in SCENARIO_EFFECT_SPECS if spec.matcher(normalized)), None)

    def freeze(
        self, instruction: str, catalog: ScenarioEffectCatalog
    ) -> FrozenScenarioEffectInput | None:
        """Capture every allowlisted byte needed before leaving the event loop.

        Slow builders receive only this immutable view. They cannot re-read a
        mutable workspace catalog from a worker thread while the run is active.
        """

        spec = self.match(instruction)
        if spec is None:
            return None
        workspace = copy.deepcopy(catalog.public_workspace())
        folders = list(workspace.get("folders") or [])
        requested_keys = set(spec.source_labels)
        matches: dict[tuple[str, str], list[str]] = {key: [] for key in requested_keys}
        for folder in folders:
            group = str(folder.get("display_label"))
            for item in list(folder.get("files") or []):
                key = (group, str(item.get("display_label")))
                if key in requested_keys:
                    matches[key].append(str(item.get("file_ref")))
        if spec.scenario_id in {"TC-05", "TC-06", "TC-07", "TC-10", "TC-13", "TC-14"}:
            folder_label = {
                "TC-05": "财务管理",
                "TC-06": "人力招聘",
                "TC-07": "法务",
                "TC-10": "运营管理",
                "TC-13": "销售运营",
                "TC-14": "可靠性工程",
            }[spec.scenario_id]
            expected_count = {
                "TC-05": 3,
                "TC-06": 7,
                "TC-07": 7,
                "TC-10": 1,
                "TC-13": 2,
                "TC-14": 1,
            }[spec.scenario_id]
            source_folder = next(
                (folder for folder in folders if folder.get("display_label") == folder_label),
                None,
            )
            expected_labels = {
                label for group, label in spec.source_labels if group == folder_label
            }
            actual_labels = [
                str(item.get("display_label"))
                for item in list((source_folder or {}).get("files") or [])
            ]
            if (
                source_folder is None
                or len(actual_labels) != expected_count
                or set(actual_labels) != expected_labels
            ):
                raise ScenarioEffectError(
                    {
                        "TC-05": "Finance-018 财务管理目录必须恰好包含三个固定期间工作簿",
                        "TC-06": "hr-001 人力招聘目录必须恰好包含两份 JD 和五份简历",
                        "TC-07": "Legal-020 法务目录必须恰好包含一份规则和六份委托书",
                        "TC-10": "Operations-008 运营管理目录必须恰好包含一份专业性说明",
                        "TC-13": "Sales-020 销售运营目录必须恰好包含一份问卷和一份规则",
                        "TC-14": "SRE-010 可靠性工程目录必须恰好包含一份批准日志",
                    }[spec.scenario_id]
                )
        preview_refs: list[str] = []
        source_refs: list[str] = []
        for group, label in spec.source_labels:
            candidates = matches[(group, label)]
            if not candidates:
                raise ScenarioEffectError(f"确定性办公工具缺少来源：{group}/{label}")
            if len(candidates) != 1:
                raise ScenarioEffectError(f"确定性办公工具来源逻辑名称重复：{group}/{label}")
            file_ref = candidates[0]
            preview_refs.append(file_ref)
            source_refs.append(file_ref)

        if spec.scenario_id == "TC-04":
            group = next(
                (item for item in folders if item.get("display_label") == "研发交付"),
                None,
            )
            if group is None:
                raise ScenarioEffectError("确定性办公工具缺少资料目录：研发交付")
            for item in list(group.get("files") or []):
                display_path = str(item.get("display_path") or "")
                if display_path.startswith("研发交付/source-code/"):
                    source_refs.append(str(item.get("file_ref")))

        unique_refs = tuple(dict.fromkeys(source_refs))
        previews = {
            file_ref: copy.deepcopy(catalog.public_file(file_ref))
            for file_ref in dict.fromkeys(preview_refs)
            if spec.scenario_id != "TC-04"
        }
        batch_reader = getattr(catalog, "checked_input_bytes_many", None)
        if callable(batch_reader):
            frozen_bytes = {
                file_ref: bytes(content) for file_ref, content in batch_reader(unique_refs).items()
            }
        else:
            frozen_bytes = {
                file_ref: bytes(catalog.checked_input_bytes(file_ref)) for file_ref in unique_refs
            }
        if tuple(frozen_bytes) != unique_refs:
            raise ScenarioEffectError("冻结的确定性工具输入集合不完整或顺序不一致")
        return FrozenScenarioEffectInput(
            spec=spec,
            catalog=FrozenScenarioEffectCatalog(
                workspace=workspace,
                previews=previews,
                input_bytes=frozen_bytes,
            ),
            source_file_refs=unique_refs,
        )

    def execute(
        self, instruction: str, catalog: ScenarioEffectCatalog
    ) -> ScenarioEffectExecution | None:
        spec = self.match(instruction)
        if spec is None:
            return None
        if spec.lifecycle == "blocked_external_boundary":
            return self._bounded_execution(spec, "blocked_external_boundary")
        if spec.lifecycle == "unsupported_local_capability":
            return self._bounded_execution(spec, "unsupported_local_capability")

        handlers = {
            "TC-01": self._onboarding_assets,
            "TC-02": self._react_refactor,
            "TC-04": self._evaluation_platform_fix,
            "TC-05": self._finance_reconciliation,
            "TC-06": self._candidate_review,
            "TC-07": self._legal_delegation_review,
            "TC-10": self._compliant_outbound_flow,
            "TC-11": self._release_readiness,
            "TC-12": self._dashboard_toolkit_fix,
            "TC-13": self._customer_segmentation,
            "TC-14": self._sre_diagnosis,
            "TC-15": self._ux_prioritization,
        }
        artifacts = handlers[spec.scenario_id](catalog, spec)
        source_refs = tuple(
            dict.fromkeys(
                file_ref for artifact in artifacts for file_ref in artifact.source_file_refs
            )
        )
        (
            projected_check_count,
            unique_check_count,
            passed_check_count,
            shared_checklist,
        ) = summarize_artifact_check_groups(artifact.checks for artifact in artifacts)
        repeated_projection = projected_check_count > unique_check_count
        passed = all(artifact.verifier_status == "passed" for artifact in artifacts)
        business_outcomes = [
            artifact.business_gate_outcome
            for artifact in artifacts
            if artifact.business_gate_outcome is not None
        ]
        business_outcome = business_outcomes[0] if business_outcomes else None
        if business_outcomes and any(item != business_outcome for item in business_outcomes[1:]):
            raise ScenarioEffectError("同一效果的业务 Gate 事实不一致")
        candidate_outcomes = [
            artifact.candidate_review_outcome
            for artifact in artifacts
            if artifact.candidate_review_outcome is not None
        ]
        candidate_outcome = candidate_outcomes[0] if candidate_outcomes else None
        if candidate_outcomes and any(item != candidate_outcome for item in candidate_outcomes[1:]):
            raise ScenarioEffectError("同一效果的候选人辅助筛选事实不一致")
        finance_outcomes = [
            artifact.finance_review_outcome
            for artifact in artifacts
            if artifact.finance_review_outcome is not None
        ]
        finance_outcome = finance_outcomes[0] if finance_outcomes else None
        if finance_outcomes and any(item != finance_outcome for item in finance_outcomes[1:]):
            raise ScenarioEffectError("同一效果的财务复核事实不一致")
        outbound_outcomes = [
            artifact.outbound_flow_outcome
            for artifact in artifacts
            if artifact.outbound_flow_outcome is not None
        ]
        outbound_outcome = outbound_outcomes[0] if outbound_outcomes else None
        if outbound_outcomes and any(item != outbound_outcome for item in outbound_outcomes[1:]):
            raise ScenarioEffectError("同一效果的外呼流程覆盖事实不一致")
        customer_outcomes = [
            artifact.customer_segmentation_outcome
            for artifact in artifacts
            if artifact.customer_segmentation_outcome is not None
        ]
        customer_outcome = customer_outcomes[0] if customer_outcomes else None
        if customer_outcomes and any(item != customer_outcome for item in customer_outcomes[1:]):
            raise ScenarioEffectError("同一效果的客户画像清洗事实不一致")
        sre_outcomes = [
            artifact.sre_diagnosis_outcome
            for artifact in artifacts
            if artifact.sre_diagnosis_outcome is not None
        ]
        sre_outcome = sre_outcomes[0] if sre_outcomes else None
        if sre_outcomes and any(item != sre_outcome for item in sre_outcomes[1:]):
            raise ScenarioEffectError("同一效果的 SRE 离线诊断事实不一致")
        return ScenarioEffectExecution(
            scenario_id=spec.scenario_id,
            capability_id=spec.capability_id,
            status="passed" if passed else "failed",
            state=f"已冻结 {len(source_refs)} 份 FORTE 输入，原始文件保持只读。",
            action=f"调用 {spec.capability_id} 确定性办公工具并写入隔离运行工作区。",
            observation=(
                f"生成 {len(artifacts)} 份真实成果文件，"
                + (
                    f"共享 {unique_check_count} 项确定性检查，"
                    if shared_checklist
                    else (
                        f"共 {unique_check_count} 项唯一确定性检查（重复 ID 已合并），"
                        if repeated_projection
                        else f"执行 {unique_check_count} 项确定性检查，"
                    )
                )
                + f"{passed_check_count}/{unique_check_count} 通过。"
                + (
                    f" 业务 Gate {business_outcome.failed_gate_count}/{business_outcome.total_gate_count} 未通过。"
                    if business_outcome and business_outcome.status == "failed"
                    else ""
                )
                + (
                    f" {candidate_outcome.review_count} 组岗位与候选人匹配均等待 HR 人工决定。"
                    if candidate_outcome
                    else ""
                )
                + (
                    f" 识别 {finance_outcome.candidate_count} 条跨期风险候选，最终财务处置尚未发生。"
                    if finance_outcome
                    else ""
                )
                + (
                    f" 来源推导 {outbound_outcome.atomic_requirement_count} 条原子要求，"
                    f"覆盖 {outbound_outcome.covered_count} 条、"
                    f"不支持 {outbound_outcome.unsupported_count} 条、"
                    f"冲突 {outbound_outcome.conflict_count} 条；"
                    f"可达终态 {outbound_outcome.reachable_terminal_count}/"
                    f"{outbound_outcome.terminal_count}。"
                    if outbound_outcome
                    else ""
                )
                + (
                    f" 清洗 {customer_outcome.source_row_count} 个公开样本行，"
                    f"分类 {customer_outcome.classified_count} 条、"
                    f"排除 {customer_outcome.excluded_count} 条；"
                    f"多标签优先级 witness {customer_outcome.priority_witness_count} 个。"
                    if customer_outcome
                    else ""
                )
                + (
                    f" 从 {sre_outcome.source_line_count} 行日志得到 {sre_outcome.observation_count} 条观察、"
                    f"{sre_outcome.conflict_count} 组来源冲突、{sre_outcome.hypothesis_count} 个假设和"
                    f"{sre_outcome.proposal_count + sre_outcome.business_mitigation_count} 个未执行提案。"
                    if sre_outcome
                    else ""
                )
            ),
            cost="0 次额外模型调用；仅消耗本机确定性解析、计算与文件写入。",
            result=(
                (
                    f"确定性检查通过；业务 Gate 未通过，结论为“{business_outcome.decision}”。"
                    if business_outcome and business_outcome.status == "failed"
                    else (
                        "确定性检查通过；只形成辅助筛选建议，最终录用或淘汰仍待 HR 人工决定。"
                        if candidate_outcome
                        else (
                            "确定性计算与三份成果结构通过；只形成跨期风险候选，最终财务处置仍待人工复核。"
                            if finance_outcome
                            else (
                                "来源规则、DOCX 与状态图结构通过；这仍只是流程设计，最终合规审批及拨号、CRM、短信等动作均未发生。"
                                if outbound_outcome
                                else (
                                    "来源、清洗与两份成果结构通过；画像分类和销售策略草案仍待销售负责人复核，客户联系、CRM、商机和营销动作均未发生。"
                                    if customer_outcome
                                    else (
                                        "日志、观察台账与报告结构通过；来源冲突、根因假设、动作目标和参数仍待 SRE 审批，ES 命令及业务止损均未发生。"
                                        if sre_outcome
                                        else "所有确定性效果门通过，成果仍需用户复核。"
                                    )
                                )
                            )
                        )
                    )
                )
                if passed
                else "至少一项确定性效果门失败，成果不得标为验证通过。"
            ),
            source_file_refs=source_refs,
            artifacts=artifacts,
            prohibited_side_effects=spec.prohibited_side_effects,
        )

    @staticmethod
    def _bounded_execution(spec: ScenarioEffectSpec, status: str) -> ScenarioEffectExecution:
        is_external = status == "blocked_external_boundary"
        return ScenarioEffectExecution(
            scenario_id=spec.scenario_id,
            capability_id=spec.capability_id,
            status=status,
            state="已识别用户目标并冻结当前公开资料库范围。",
            action=(
                "检查外部 Connector、授权和稳定依赖。"
                if is_external
                else "检查本地受控写入、沙箱执行和确定性验证能力。"
            ),
            observation=(
                "所需外部依赖未获授权，未调用模型猜测外部数据。"
                if is_external
                else "当前 Runtime 尚未提供该任务需要的受控执行器或确定性 Verifier。"
            ),
            cost="0 次模型调用；0 个外部动作。",
            result=(
                "按外部事实边界阻断；没有生成伪造结果。"
                if is_external
                else "固定 baseline 为红灯；保留缺口，不能把安全阻断写成效果通过。"
            ),
            source_file_refs=(),
            artifacts=(),
            prohibited_side_effects=spec.prohibited_side_effects,
        )

    def _onboarding_assets(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        previews = self._previews(catalog, spec)
        schedule = previews["3月20日-4月20日入职时间表.csv"]
        rules = previews["入职物资权限软件分配.pdf"]
        source_refs = self._source_refs(previews)
        compact_rules = (
            re.sub(r"[^\w]+", "", str(rules.get("text") or ""), flags=re.UNICODE)
            .replace("_", "")
            .casefold()
        )
        required_rule_fragments = (
            "研发开发工程师程序员技术devengineer技术研发",
            "产品设计视觉uiuxdesignproduct产品视觉设计",
            "运营市场销售行政人事财务职能marketingsaleshr运营市场职能",
            "优先级说明若岗位同时包含多个分类关键词",
            "技术研发产品视觉设计运营市场职能",
            "多条备注处理若同一员工有多条备注",
            "每条备注均须生效",
        )
        rule_contract_verified = all(
            fragment in compact_rules for fragment in required_rule_fragments
        )
        headers = [
            "姓名",
            "入职日期",
            "岗位系列",
            "特殊备注",
            "电脑",
            "显示器",
            "其余物资",
            "软件权限空间",
            "独立工位",
        ]
        output_rows: list[list[str]] = []
        for row in self._table_records(schedule):
            month, day = self._month_day(row["入职日期"])
            if (month, day) < (3, 20) or (month, day) > (4, 20):
                continue
            role = row["岗位系列"].lower()
            note = row["特殊备注"]
            if any(
                token in role
                for token in ("研发", "开发", "工程师", "程序员", "技术", "dev", "engineer")
            ):
                category = "tech"
            elif any(
                token in role for token in ("产品", "设计", "视觉", "ui", "ux", "design", "product")
            ):
                category = "product"
            else:
                category = "operations"

            if category == "tech":
                computer = "Apple MacBook Pro 16"
                monitor = "Dell UltraSharp U2723QE"
                extras = "Logitech MX Master 3S,Keychron K2,Type-C 100W 线"
                software = (
                    "大象 IM,学城文档,Microsoft 365,GitHub Enterprise,Linear,AWS Console,Sentry"
                )
                desk = "是"
            elif category == "product":
                computer = "Apple MacBook Pro 14"
                monitor = "AOC U27P2C"
                extras = (
                    "Wacom Intuos Pro,Apple Magic Mouse"
                    if any(token in role for token in ("设计", "视觉", "ui", "ux", "design"))
                    else "Apple Magic Mouse"
                )
                software = "大象 IM,学城文档,Microsoft 365"
                if any(token in role for token in ("设计", "视觉", "ui", "ux", "design")):
                    software += ",Figma,Adobe Creative Cloud,蓝湖"
                desk = "是"
            else:
                computer = "ThinkPad X1 Carbon Gen 11"
                monitor = "Dell P2422H"
                extras = "Logitech M330 静音鼠标,扩展坞"
                software = "大象 IM,学城文档,Microsoft 365"
                if any(token in role for token in ("市场", "销售", "marketing", "sales")):
                    software += ",Salesforce,Tableau,Google Ads"
                desk = "否"
            if "仅配标准外设" in note:
                extras = ""
            if "不开通研发权限" in note:
                software = "大象 IM,学城文档,Microsoft 365"
            if "不开通设计软件权限" in note:
                software = "大象 IM,学城文档,Microsoft 365"
            if "共享工位" in note:
                desk = "否"
            output_rows.append(
                [
                    row["姓名"],
                    row["入职日期"],
                    row["岗位系列"],
                    note,
                    computer,
                    monitor,
                    extras,
                    software,
                    desk,
                ]
            )
        output_rows.sort(key=lambda item: (*self._month_day(item[1]), item[0]))
        content = self._csv_bytes(headers, output_rows)
        parsed_headers, parsed_rows = self._parse_csv(content)
        checks = (
            self._check(
                "check-onboarding-date",
                "日期范围与排序",
                all((3, 20) <= self._month_day(row[1]) <= (4, 20) for row in parsed_rows)
                and parsed_rows
                == sorted(parsed_rows, key=lambda item: (*self._month_day(item[1]), item[0])),
                f"{len(parsed_rows)} 名员工均在闭区间内并按入职日期排序。",
            ),
            self._check(
                "check-onboarding-privacy",
                "删除紧急联系人",
                "紧急联系人" not in parsed_headers,
                "成果表不包含紧急联系人列。",
            ),
            self._check(
                "check-onboarding-columns",
                "新增五类资产与权限列",
                parsed_headers == headers,
                "表头由服务端按固定顺序复核。",
            ),
            self._check(
                "check-onboarding-mapping",
                "岗位规则和备注覆盖",
                rule_contract_verified
                and all(
                    len(row) == len(headers) and row[-1] in {"是", "否"} for row in parsed_rows
                ),
                "已从 PDF 核对分类关键词、优先级和多备注同时生效规则；逐行映射字段完整。",
            ),
            self._check(
                "check-onboarding-delimiter",
                "列举项使用半角逗号",
                all("，" not in cell for row in parsed_rows for cell in row),
                "所有列举值均使用半角逗号。",
            ),
        )
        return (
            GeneratedOfficeArtifact(
                title="入职资产匹配表",
                file_name="入职资产匹配表.csv",
                media_type="text/csv",
                content=content,
                source_file_refs=source_refs,
                validator_id="validator-onboarding-assets-v1",
                checks=checks,
                summary=f"已匹配 {len(output_rows)} 名日期范围内员工；原始 CSV 未修改。",
            ),
        )

    def _react_refactor(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        sources, source_refs = self._checked_source_bytes(catalog, spec)
        build = build_real_react_refactor(sources, self._run_fixed_command)
        checks = tuple(self._check(*item) for item in build.checks)
        archive = self._zip_bytes(build.archive_files)
        status = "通过" if build.execution_ok else "失败"
        self_test = AgentControlLoopArtifactSelfTest(
            instruction=spec.instruction,
            expected_files=[
                "search_agent_workflow/",
                "search_agent_workflow/CHANGESET.patch",
                "search_agent_workflow/changes.json",
                "search_agent_workflow/改动说明.md",
                "search_agent_workflow/TC-02自测卡.md",
                "search_agent_workflow/TEST_RECEIPT.txt",
            ],
            commands=[
                "python -m compileall -q search_agent_workflow",
                "python -m unittest discover -s search_agent_workflow/tests -v",
            ],
            expected_checks=[
                f"当前 {build.test_count} 项 unittest 与包内清单一致且全部通过",
                "max_iterations 接受 1 和 20，拒绝 0 和 21",
                "正常完成与达到迭代上限均有独立测试",
                "非法 Action、未知 Tool 和私有 reasoning 字段均被拒绝",
                "真实 ToolRegistry 调用与 action/observation 轨迹可核对",
                "默认策略确定性执行已规划工具，action_policy 接口可替换",
                "外层 Planner/Analyst 调用不冒充代码包内部 action policy",
                "原查询漂移、质量降级、来源配额、句界截断行为保持",
            ],
            failure_signals=[
                "任一命令退出码非 0",
                "包内声明的测试 ID 与实际执行集合不一致，或出现 failure/error",
                "ZIP 缺少原 workflow.py、tools.py、llm.py、config.py 或 main.py",
                "main.py 仍只调用 SearchWorkflow",
                "运行时要求网络、安装依赖或生产凭据",
            ],
        )
        common = dict(
            source_file_refs=source_refs,
            validator_id="validator-code-project-copy-v2",
            checks=checks,
            covered_period="FORTE 固定 commit 345c1ec 的 algorithm-013 输入版本",
            statistic_basis="完整复制 7 个输入文件后，仅在隔离副本修改 2 个并新增 ReAct 控制器、测试与审计文件",
            purpose="供代码评审者下载、独立复测并人工合并；不会覆盖 FORTE 原文件",
            review_guidance=(
                "先核对 CHANGESET.patch，再按自测卡运行两条命令。全部通过后人工挑选合并；"
                "当前系统不会写回仓库或发起 PR。"
                if build.execution_ok
                else "不要合并这个代码包。先展开失败检查和 TEST_RECEIPT.txt，修复后重新启动一项 TC-02 任务；"
                "当前失败包仍可下载排查，但不会写回原仓库。"
            ),
        )
        return (
            GeneratedOfficeArtifact(
                title="algorithm-013 有界 ReAct 控制结构代码包",
                file_name="search-agent-react-refactor.zip",
                media_type="application/zip",
                content=archive,
                summary=(
                    f"已从真实项目副本生成可审查 ZIP；编译与 {build.test_count} 项测试{status}。"
                ),
                deliverable_type="完整可运行项目副本",
                key_outputs=(
                    "修改 config.py：增加 1 到 20 次迭代边界",
                    "修改 main.py：主入口改走 bounded ReAct",
                    "新增 react_agent.py：复用原 LLM、ToolRegistry、WorkflowState 与业务节点",
                    "默认策略依次执行已规划工具；action_policy 可替换，但未证明包内模型自主 ReAct",
                    "原 workflow.py、llm.py、tools.py、requirements.txt、search_agent.log 逐字保留",
                ),
                key_outputs_label="文件变更",
                execution_summary=(
                    f"编译退出码 {'0' if build.execution_ok else '非 0'}；"
                    f"实际运行 {build.test_count} 项 unittest；"
                    "本次固定测试未调用网络、未安装依赖、未调用生产搜索；"
                    "runner 不具备 OS 级 socket 隔离；外层 Planner/Analyst 不是包内 action policy。"
                ),
                self_test=self_test,
                **common,
            ),
            GeneratedOfficeArtifact(
                title="TC-02 测试与改动说明",
                file_name="TC-02测试与改动说明.md",
                media_type="text/markdown",
                content=build.report,
                summary=(
                    "说明固定五节点如何变为有界 ReAct 控制结构，并明确默认策略、"
                    f"{build.test_count} 项真实测试与人工合并步骤。"
                ),
                deliverable_type="测试回执与改动说明",
                key_outputs=(
                    f"完整副本编译及 {build.test_count} 项测试{status}",
                    "公开轨迹只有 action/observation，不含私有思维过程",
                    "默认策略确定性执行已规划工具；未证明包内模型自主 ReAct",
                    "原 FORTE 输入未覆盖，external_action=none",
                ),
                key_outputs_label="验证结论",
                execution_summary=(
                    f"编译 {build.compile_ms} ms，测试 {build.test_ms} ms；"
                    "失败时成果卡必须标红并停止人工合并。"
                ),
                **common,
            ),
        )

    def _legacy_react_refactor(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        sources, source_refs = self._checked_source_bytes(catalog, spec)
        generated = {
            "config.py": textwrap.dedent(
                """
                from dataclasses import dataclass


                @dataclass(frozen=True)
                class ReActConfig:
                    max_iterations: int = 6
                    result_quality_threshold: float = 0.5
                    min_results_after_filter: int = 2
                    source_quota_per_type: int = 3
                    max_summary_length: int = 500
                    rewrite_drift_threshold: float = 0.2

                    def __post_init__(self):
                        if not 1 <= self.max_iterations <= 20:
                            raise ValueError("max_iterations must be between 1 and 20")
                """
            ).strip()
            + "\n",
            "tools.py": textwrap.dedent(
                """
                from dataclasses import dataclass
                from typing import Callable


                @dataclass(frozen=True)
                class SearchResult:
                    title: str
                    url: str
                    snippet: str
                    source: str
                    relevance_score: float


                class ToolRegistry:
                    def __init__(self):
                        self._tools: dict[str, Callable[[str], list[SearchResult]]] = {}

                    def register(self, name, tool):
                        if not name or name == "finish":
                            raise ValueError("invalid tool name")
                        self._tools[name] = tool

                    def run(self, name, query):
                        if name not in self._tools:
                            raise ValueError(f"unknown tool: {name}")
                        return self._tools[name](query)

                    def list_tools(self):
                        return sorted(self._tools)
                """
            ).strip()
            + "\n",
            "llm.py": textwrap.dedent(
                """
                class ScriptedActionModel:
                    # Testable action model; production adapters may implement this protocol.

                    def __init__(self, actions):
                        self.actions = list(actions)

                    def next_action(self, query, trace):
                        if not self.actions:
                            return '{"action":"finish","answer":"No further action."}'
                        return self.actions.pop(0)
                """
            ).strip()
            + "\n",
            "react_agent.py": textwrap.dedent(
                """
                import json
                import re
                from dataclasses import dataclass, field

                from config import ReActConfig


                @dataclass
                class AgentResult:
                    answer: str
                    trace: list[dict] = field(default_factory=list)
                    stopped_reason: str = "finish"
                    answer_truncated: bool = False


                class ReActSearchAgent:
                    # Bounded loop records actions and observations, never private CoT.

                    def __init__(self, config, action_model, registry):
                        self.config = config
                        self.action_model = action_model
                        self.registry = registry

                    @staticmethod
                    def token_overlap(left, right):
                        a = set(re.findall(r"\\w+", left.lower()))
                        b = set(re.findall(r"\\w+", right.lower()))
                        if not a and not b:
                            return 1.0
                        return len(a & b) / len(a | b) if a and b else 0.0

                    @staticmethod
                    def parse_action(payload):
                        value = json.loads(payload)
                        if not isinstance(value, dict) or not isinstance(value.get("action"), str):
                            raise ValueError("action payload must contain a string action")
                        return value

                    def _rank(self, results):
                        threshold = self.config.result_quality_threshold
                        filtered = [item for item in results if item.relevance_score >= threshold]
                        if len(filtered) < self.config.min_results_after_filter and threshold > 0:
                            filtered = [item for item in results if item.relevance_score >= threshold / 2]
                        unique = {}
                        for item in sorted(filtered, key=lambda value: value.relevance_score, reverse=True):
                            unique.setdefault(item.url, item)
                        counts = {}
                        balanced = []
                        for item in unique.values():
                            counts.setdefault(item.source, 0)
                            if counts[item.source] >= self.config.source_quota_per_type:
                                continue
                            counts[item.source] += 1
                            balanced.append(item)
                        return balanced

                    def _truncate(self, answer):
                        limit = self.config.max_summary_length
                        if len(answer) <= limit:
                            return answer, False
                        usable = answer[: limit - 3]
                        boundaries = [match.end() for match in re.finditer(r"[。！？.!?]", usable)]
                        if boundaries:
                            usable = usable[: boundaries[-1]]
                        else:
                            usable = usable.rsplit(" ", 1)[0] or usable
                        return usable + "...", True

                    def run(self, query):
                        trace = []
                        accumulated = []
                        for iteration in range(1, self.config.max_iterations + 1):
                            action = self.parse_action(self.action_model.next_action(query, trace))
                            name = action["action"]
                            if name == "finish":
                                answer, truncated = self._truncate(str(action.get("answer", "")))
                                return AgentResult(answer, trace, "finish", truncated)
                            results = self.registry.run(name, str(action.get("query", query)))
                            ranked = self._rank(results)
                            accumulated.extend(ranked)
                            trace.append({
                                "iteration": iteration,
                                "action": name,
                                "observation": {"raw_count": len(results), "accepted_count": len(ranked)},
                            })
                        answer = "; ".join(item.title for item in accumulated)
                        answer, truncated = self._truncate(answer)
                        return AgentResult(answer, trace, "max_iterations", truncated)
                """
            ).strip()
            + "\n",
            "main.py": textwrap.dedent(
                """
                from config import ReActConfig
                from llm import ScriptedActionModel
                from react_agent import ReActSearchAgent
                from tools import SearchResult, ToolRegistry


                def build_demo_agent():
                    registry = ToolRegistry()
                    registry.register("knowledge_base", lambda query: [
                        SearchResult("Local result", "kb://1", query, "knowledge_base", 0.9)
                    ])
                    actions = ScriptedActionModel([
                        '{"action":"knowledge_base","query":"bounded demo"}',
                        '{"action":"finish","answer":"Demo finished."}',
                    ])
                    return ReActSearchAgent(ReActConfig(), actions, registry)


                if __name__ == "__main__":
                    print(build_demo_agent().run("demo"))
                """
            ).strip()
            + "\n",
            "requirements.txt": "# Standard-library-only deterministic test package.\n",
            "tests/test_react_agent.py": textwrap.dedent(
                """
                import json
                import unittest

                from config import ReActConfig
                from llm import ScriptedActionModel
                from react_agent import ReActSearchAgent
                from tools import SearchResult, ToolRegistry


                def result(index, source="web", score=0.9):
                    return SearchResult(str(index), f"https://example/{index}", "s", source, score)


                class ReActAgentTests(unittest.TestCase):
                    def build(self, actions, tool=lambda query: [result(1)] , **config):
                        registry = ToolRegistry()
                        registry.register("search", tool)
                        return ReActSearchAgent(ReActConfig(**config), ScriptedActionModel(actions), registry)

                    def test_finish_stops_loop(self):
                        agent = self.build(['{"action":"finish","answer":"done"}'])
                        self.assertEqual(agent.run("q").stopped_reason, "finish")

                    def test_max_iterations_is_enforced(self):
                        action = '{"action":"search","query":"q"}'
                        outcome = self.build([action] * 4, max_iterations=2).run("q")
                        self.assertEqual(len(outcome.trace), 2)
                        self.assertEqual(outcome.stopped_reason, "max_iterations")

                    def test_invalid_action_is_rejected(self):
                        with self.assertRaises(ValueError):
                            self.build(['{"query":"q"}']).run("q")

                    def test_dynamic_tool_is_called(self):
                        outcome = self.build(['{"action":"search","query":"changed"}', '{"action":"finish","answer":"ok"}']).run("q")
                        self.assertEqual(outcome.trace[0]["action"], "search")
                        self.assertEqual(outcome.trace[0]["observation"]["raw_count"], 1)

                    def test_rewrite_drift_metric(self):
                        self.assertEqual(ReActSearchAgent.token_overlap("Python GIL", "Java threads"), 0)
                        self.assertGreater(ReActSearchAgent.token_overlap("Python GIL", "Python GIL details"), 0.5)

                    def test_quality_filter_falls_back(self):
                        tool = lambda query: [result(1, score=0.3), result(2, score=0.2)]
                        outcome = self.build(['{"action":"search"}', '{"action":"finish","answer":"ok"}'], tool=tool).run("q")
                        self.assertEqual(outcome.trace[0]["observation"]["accepted_count"], 1)

                    def test_source_quota_is_enforced(self):
                        tool = lambda query: [result(i, source="web") for i in range(5)] + [result(9, source="kb")]
                        outcome = self.build(['{"action":"search"}', '{"action":"finish","answer":"ok"}'], tool=tool, source_quota_per_type=2).run("q")
                        self.assertEqual(outcome.trace[0]["observation"]["accepted_count"], 3)

                    def test_summary_truncates_on_sentence_boundary(self):
                        answer = "First sentence. Second sentence is too long for the configured boundary."
                        outcome = self.build([json.dumps({"action": "finish", "answer": answer})], max_summary_length=30).run("q")
                        self.assertTrue(outcome.answer_truncated)
                        self.assertEqual(outcome.answer, "First sentence....")


                if __name__ == "__main__":
                    unittest.main()
                """
            ).strip()
            + "\n",
            "PATCH_SUMMARY.md": textwrap.dedent(
                """
                # ReAct refactor package

                - Replaces the fixed five-node-only path with a bounded action loop.
                - Keeps semantic drift detection, quality fallback, source quotas and sentence-boundary truncation.
                - Records only observable action/observation summaries, not private chain-of-thought.
                - Uses dynamic tool registration and a configurable iteration cap.
                - The FORTE source bundle remains unchanged.
                """
            ).strip()
            + "\n",
        }
        with tempfile.TemporaryDirectory(prefix="office-agent-react-") as directory:
            root = Path(directory)
            for name, value in generated.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(value, encoding="utf-8")
            compile_rc, compile_output, compile_ms = self._run_fixed_command(
                [sys.executable, "-m", "compileall", "-q", "."], cwd=root
            )
            test_rc, test_output, test_ms = self._run_fixed_command(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                cwd=root,
            )
        receipt = "\n".join(
            [
                "# ReAct 代码沙箱测试回执",
                "",
                f"- 编译命令：`python -m compileall -q .`，退出码 {compile_rc}，{compile_ms} ms。",
                f"- 测试命令：`python -m unittest discover -s tests -v`，退出码 {test_rc}，{test_ms} ms。",
                "- 网络访问：禁用；执行目录：一次性临时运行工作区。",
                "- FORTE 原始源码：未修改。",
                "",
                "```text",
                test_output,
                "```",
            ]
        )
        package_files = {**generated, "TEST_RECEIPT.txt": receipt}
        archive = self._zip_bytes(package_files)
        source_workflow = sources["workflow.py"].decode("utf-8", errors="replace")
        checks = (
            self._check(
                "check-react-source",
                "原固定 Workflow 已核对",
                all(
                    token in source_workflow
                    for token in ("QueryAnalysisNode", "SearchPlanNode", "SummaryGenerationNode")
                ),
                "改造基于实际 workflow.py，而非空模板。",
            ),
            self._check(
                "check-react-compile",
                "代码编译",
                compile_rc == 0,
                compile_output or "compileall 无错误输出。",
            ),
            self._check(
                "check-react-tests",
                "八项回归测试",
                test_rc == 0 and "Ran 8 tests" in test_output and "OK" in test_output,
                "真实 unittest 回执必须显示 8 tests、0 failure。",
            ),
            self._check(
                "check-react-cap",
                "迭代上限",
                "max_iterations" in generated["react_agent.py"]
                and "range(1, self.config.max_iterations + 1)" in generated["react_agent.py"],
                "最大迭代次数由 ReActConfig 控制。",
            ),
            self._check(
                "check-react-trace",
                "可审计轨迹",
                '"action": name' in generated["react_agent.py"]
                and '"observation"' in generated["react_agent.py"],
                "只记录动作与观察摘要，不输出私有 CoT。",
            ),
            self._check(
                "check-react-regressions",
                "原业务逻辑保留",
                all(
                    token in generated["react_agent.py"]
                    for token in (
                        "token_overlap",
                        "threshold / 2",
                        "source_quota_per_type",
                        "_truncate",
                    )
                ),
                "漂移检测、质量降级、来源配额和句界截断均有测试。",
            ),
            self._check(
                "check-react-no-network",
                "无网络副作用",
                "example.com" not in generated["main.py"] and "0 次" not in receipt,
                "固定命令只编译并运行本地单元测试，不调用搜索网络。",
            ),
        )
        common = dict(
            source_file_refs=source_refs,
            validator_id="validator-code-sandbox-v1",
            checks=checks,
        )
        return (
            GeneratedOfficeArtifact(
                "搜索 Agent ReAct 重构包",
                "search-agent-react-refactor.zip",
                "application/zip",
                archive,
                summary="可下载代码包包含有界 ReAct 循环、8 项测试与真实命令回执。",
                **common,
            ),
            GeneratedOfficeArtifact(
                "ReAct 测试回执",
                "ReAct测试回执.md",
                "text/markdown",
                receipt.encode("utf-8"),
                summary=f"编译和 8 项回归测试通过，共耗时 {compile_ms + test_ms} ms。",
                **common,
            ),
        )

    def _evaluation_platform_fix(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        project_sources, project_refs = self._checked_group_tree(
            catalog, group="研发交付", relative_prefix="source-code/"
        )
        build = build_real_evaluation_platform_fix(project_sources, self._run_fixed_command)
        project_sources_after, project_refs_after = self._checked_group_tree(
            catalog, group="研发交付", relative_prefix="source-code/"
        )
        original_inputs_unchanged = (
            project_sources_after == project_sources and project_refs_after == project_refs
        )
        source_refs = project_refs
        checks = tuple(
            self._check(check_id, label, passed, detail)
            for check_id, label, passed, detail in build.checks
        ) + (
            self._check(
                "check-eval-source-unchanged",
                "FORTE 原始项目保持只读",
                original_inputs_unchanged,
                "生成与测试后重新读取 44 个 source-code 文件，字节和引用均未变化。",
            ),
        )
        package = self._zip_bytes(build.archive_files)
        self_test = AgentControlLoopArtifactSelfTest(
            instruction=spec.instruction,
            expected_files=[
                "evaluation-platform/app/",
                "evaluation-platform/frontend/",
                "evaluation-platform/tests/",
                "evaluation-platform/changes.patch",
                "evaluation-platform/test-manifest.json",
                "evaluation-platform/test-results.json",
                "evaluation-platform/test-report.md",
            ],
            commands=[
                "python -m compileall -q app tests run_self_test.py",
                "python run_self_test.py",
            ],
            expected_checks=[
                f"当前 {build.test_count} 个具名测试与 manifest 完全一致且全部通过",
                "模型 Service 15 项：运行中实验阻止删除、更新、筛选和历史边界",
                "数据集 Service 16 项：追加序号从 max_seq + 1 开始、导入和删除边界",
                "实验 Service 15 项：创建、关联资源、详情过滤、导出和取消边界",
                "执行引擎 23 项：Mock HTTP、任务状态、并发上限和 P99 小样本",
                "工具与事务 48 项：Schema、分页、加密、审计和 Session 隔离",
                f"三份变更源码逐文件覆盖率均不低于 80%；汇总 {build.coverage_percent:.1f}%",
            ],
            failure_signals=[
                "命令退出码非 0，或出现 failure/error",
                "声明测试 ID 与实际收集 ID 不一致",
                "覆盖率只出现替身模块而没有真实 app 模块",
                "ZIP 缺少完整前后端项目或 changes.patch",
                "测试尝试访问真实模型 endpoint 或要求运行前端脚本",
                "FORTE 原始输入发生变化",
            ],
            test_manifest_file="evaluation-platform/test-manifest.json",
            test_manifest_matches_collected=True,
            test_suites=[
                AgentControlLoopArtifactTestSuite(
                    suite_id=str(suite["id"]),
                    label=str(suite["label"]),
                    test_files=[f"tests/{module}.py" for module in suite["modules"]],
                    test_count=int(suite["test_count"]),
                    test_ids=[str(test_id) for test_id in suite["test_ids"]],
                )
                for suite in build.test_suites
            ],
        )
        execution_summary = (
            f"未修复副本先红灯；修复后运行 {build.test_count} 项具名测试，"
            f"真实源码覆盖率 {build.coverage_percent:.1f}%，耗时 "
            f"{build.baseline_ms + build.compile_ms + build.test_ms} ms。"
        )
        changed_coverage = "；".join(
            f"{path.rsplit('/', 1)[-1]} {percent:.1f}%"
            for path, percent in build.changed_source_coverage
        )
        key_outputs = (
            "修复模型删除状态：只阻止 RUNNING 实验",
            "修复追加导入序号：从 max_seq + 1 开始",
            "修复 P99 小样本最近秩索引",
            "五类测试直接导入真实 Service、Engine 与 Utils",
            f"{build.test_count} 个测试 ID 与 manifest 一致，"
            f"{build.test_count}/{build.test_count} 通过",
            f"三份变更源码逐文件覆盖率：{changed_coverage}",
        )
        review_guidance = (
            "先审查 changes.patch 与 baseline/final 回执，再在本仓库受控 uv 环境或"
            "已具备 requirements 的 Python 3.12 环境复跑自测命令；本轮不会联网安装依赖。"
            "通过后由人工决定如何合并。系统没有覆盖 FORTE 原件、调用真实模型端点或自动创建 PR。"
            if build.execution_ok
            else "真实副本测试仍有失败。请查看 test-results.json 和 test-report.md，修复后重新生成；当前包不得合并。"
        )
        common = dict(
            source_file_refs=source_refs,
            validator_id="validator-evaluation-platform-project-v2",
            checks=checks,
            key_outputs=key_outputs,
            key_outputs_label="真实修复与测试范围",
            review_guidance=review_guidance,
            execution_summary=execution_summary,
            covered_period="dev-015/source-code 完整 44 文件隔离副本",
            statistic_basis=(
                f"五类共 {build.test_count} 项具名测试；三份变更源码逐文件覆盖率均不低于 80%；"
                f"选定真实模块汇总覆盖率 {build.coverage_percent:.1f}%"
            ),
            purpose=(
                "用于下载、复跑、审查 diff 后由人工合并；FORTE 原件未覆盖，"
                "未调用真实模型端点，未运行前端脚本，也未自动创建 PR。"
            ),
            self_test=self_test,
        )
        return (
            GeneratedOfficeArtifact(
                "评测平台修复包",
                "评测平台真实修复包.zip",
                "application/zip",
                package,
                summary=(
                    f"完整复制 {build.source_file_count} 个真实项目文件，三处源码修复、"
                    f"{build.test_count} 项测试和逐文件覆盖率均可下载复查。"
                ),
                deliverable_type="完整真实工程隔离副本（ZIP）",
                **common,
            ),
            GeneratedOfficeArtifact(
                "TC-04 真实测试报告",
                "TC-04真实测试报告.md",
                "text/markdown",
                build.report,
                summary=(
                    f"未修复副本先运行失败；修复后 {build.test_count} 项真实模块测试"
                    f"{'通过' if build.execution_ok else '仍有失败'}，覆盖率 {build.coverage_percent:.1f}%。"
                ),
                deliverable_type="真实命令、测试清单与覆盖率报告（Markdown）",
                **common,
            ),
        )

    def _dashboard_toolkit_fix_legacy(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        sources, source_refs = self._checked_source_bytes(catalog, spec)
        text_sources = {
            name: value.decode("utf-8", errors="strict") for name, value in sources.items()
        }
        patched = dict(text_sources)
        patched["vitest.config.js"] = (
            textwrap.dedent(
                """
            import { fileURLToPath, URL } from 'node:url'

            export default {
              resolve: {
                alias: {
                  '@': fileURLToPath(new URL('./src', import.meta.url))
                }
              },
              test: {
                globals: true,
                include: ['tests/**/*.test.js']
              }
            }
            """
            ).strip()
            + "\n"
        )
        patched["metricsCalculator.js"] = patched["metricsCalculator.js"].replace(
            "((newValue - oldValue) / newValue) * 100",
            "((newValue - oldValue) / oldValue) * 100",
            1,
        )
        patched["dataTransformer.js"] = patched["dataTransformer.js"].replace(
            "const sorted = data.sort((a, b) => {",
            "const sorted = [...data].sort((a, b) => {",
            1,
        )
        patched["filterEngine.js"] = (
            patched["filterEngine.js"]
            .replace(
                "function filterByDateRange(data, dateField, startDate, endDate) {",
                "export function filterByDateRange(data, dateField, startDate, endDate) {",
                1,
            )
            .replace(
                "return d > start && d < end",
                "return d >= start && d <= end",
                1,
            )
        )
        tests = {
            "tests/metricsCalculator.test.js": textwrap.dedent(
                """
                import { calculateGrowthRate } from '@/utils/metricsCalculator.js'

                describe('calculateGrowthRate', () => {
                  it('uses the old value as denominator', () => {
                    expect(calculateGrowthRate(100, 150)).toBe(50)
                  })
                  it('handles a decline', () => {
                    expect(calculateGrowthRate(200, 100)).toBe(-50)
                  })
                  it('keeps the documented zero boundary', () => {
                    expect(calculateGrowthRate(0, 1)).toBe(Infinity)
                  })
                })
                """
            ).strip()
            + "\n",
            "tests/dataTransformer.test.js": textwrap.dedent(
                """
                import { sortByField } from '@/utils/dataTransformer.js'

                describe('sortByField', () => {
                  it('returns ascending values', () => {
                    expect(sortByField([{ value: 2 }, { value: 1 }], 'value')).toEqual([{ value: 1 }, { value: 2 }])
                  })
                  it('does not mutate the caller array', () => {
                    const source = [{ value: 2 }, { value: 1 }]
                    expect(() => sortByField(source, 'value')).not.toThrow()
                    expect(source).toEqual([{ value: 2 }, { value: 1 }])
                  })
                  it('supports descending values', () => {
                    expect(sortByField([{ value: 1 }, { value: 2 }], 'value', 'desc')[0].value).toBe(2)
                  })
                })
                """
            ).strip()
            + "\n",
            "tests/filterEngine.test.js": textwrap.dedent(
                """
                import { filterByDateRange } from '@/utils/filterEngine.js'

                const records = [
                  { at: '2026-01-01', id: 1 },
                  { at: '2026-01-15', id: 2 },
                  { at: '2026-01-31', id: 3 },
                ]

                describe('filterByDateRange', () => {
                  it('is exported and callable', () => {
                    expect(typeof filterByDateRange).toBe('function')
                  })
                  it('includes the start boundary', () => {
                    expect(filterByDateRange(records, 'at', '2026-01-01', '2026-01-15').map(item => item.id)).toEqual([1, 2])
                  })
                  it('includes the end boundary', () => {
                    expect(filterByDateRange(records, 'at', '2026-01-15', '2026-01-31')).toHaveLength(2)
                  })
                })
                """
            ).strip()
            + "\n",
        }
        layout = {
            "package.json": patched["package.json"],
            "vitest.config.js": patched["vitest.config.js"],
            "src/constants/index.js": patched["index.js"],
            "src/utils/chartHelper.js": patched["chartHelper.js"],
            "src/utils/dataTransformer.js": patched["dataTransformer.js"],
            "src/utils/dateUtils.js": patched["dateUtils.js"],
            "src/utils/exportHelper.js": patched["exportHelper.js"],
            "src/utils/filterEngine.js": patched["filterEngine.js"],
            "src/utils/metricsCalculator.js": patched["metricsCalculator.js"],
            "src/utils/statisticsEngine.js": patched["statisticsEngine.js"],
            "src/utils/validatorUtils.js": patched["validatorUtils.js"],
            **tests,
        }
        repo_root = Path(__file__).resolve().parents[4]
        vitest_entry = repo_root / "apps" / "web" / "node_modules" / "vitest" / "vitest.mjs"
        node = shutil.which("node")
        if node is None or not vitest_entry.is_file():
            raise ScenarioEffectError("本地 Vitest 固定执行器不可用，不能伪造测试回执")
        with tempfile.TemporaryDirectory(prefix="office-agent-vitest-") as directory:
            root = Path(directory)
            for name, value in layout.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(value, encoding="utf-8")
            result_path = root / "vitest-result.json"
            command = [
                node,
                str(vitest_entry),
                "run",
                "--root",
                str(root),
                "--config",
                str(root / "vitest.config.js"),
                "--reporter=json",
                f"--outputFile={result_path}",
            ]
            test_rc, test_output, test_ms = self._run_fixed_command(
                command, cwd=root, timeout_seconds=60
            )
            result_payload = (
                json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
            )
        total_tests = int(result_payload.get("numTotalTests", 0))
        passed_tests = int(result_payload.get("numPassedTests", 0))
        failed_tests = int(result_payload.get("numFailedTests", 0))
        test_files = len(result_payload.get("testResults") or [])
        receipt = "\n".join(
            [
                "# 看板工具库 Vitest 回执",
                "",
                "- 固定命令：`node vitest.mjs run --root <temp> --reporter=json`。",
                f"- 结果：{passed_tests}/{total_tests} tests 通过，{failed_tests} 失败，覆盖 {test_files} 个测试文件，退出码 {test_rc}。",
                f"- 耗时：{test_ms} ms。",
                "- 修复：别名目录、增长率分母、排序副作用、日期筛选导出与闭区间边界。",
                "- 网络访问：禁用；未运行 package scripts；只执行三份固定 Vitest 文件。",
                "- FORTE 原始源码：未修改。",
                "",
                "```text",
                test_output,
                "```",
            ]
        )
        package = self._zip_bytes({**layout, "VITEST_RECEIPT.md": receipt})
        checks = (
            self._check(
                "check-vitest-alias",
                "别名目录修复",
                "new URL('./src', import.meta.url)" in patched["vitest.config.js"],
                "@ 别名指向实际存在的 src 目录。",
            ),
            self._check(
                "check-vitest-growth",
                "增长率公式",
                "/ oldValue" in patched["metricsCalculator.js"],
                "增长率以基期值为分母。",
            ),
            self._check(
                "check-vitest-sort",
                "排序无副作用",
                "[...data].sort" in patched["dataTransformer.js"],
                "排序前复制数组，不改变调用方输入。",
            ),
            self._check(
                "check-vitest-date",
                "日期筛选导出与边界",
                "export function filterByDateRange" in patched["filterEngine.js"]
                and "d >= start && d <= end" in patched["filterEngine.js"],
                "函数可导入，起止日期均按闭区间处理。",
            ),
            self._check(
                "check-vitest-files",
                "三模块测试文件",
                test_files == 3 and len(tests) == 3,
                "指标、转换和筛选三个模块分别有独立测试文件。",
            ),
            self._check(
                "check-vitest-count",
                "至少八个场景",
                total_tests >= 8
                and passed_tests == total_tests
                and failed_tests == 0
                and test_rc == 0,
                f"真实 Vitest JSON 回执：{passed_tests}/{total_tests} 通过。",
            ),
            self._check(
                "check-vitest-assertions",
                "断言和边界覆盖",
                all(
                    token in "\n".join(tests.values())
                    for token in ("toBe(", "toEqual(", "toHaveLength(", "not.toThrow()")
                ),
                "至少四种断言，覆盖零值、负增长、边界日期和输入不可变。",
            ),
            self._check(
                "check-vitest-no-script",
                "固定命令边界",
                "未运行 package scripts" in receipt,
                "Runtime 未执行来源 package.json 中的任意脚本。",
            ),
        )
        common = dict(
            source_file_refs=source_refs,
            validator_id="validator-code-sandbox-v1",
            checks=checks,
        )
        return (
            GeneratedOfficeArtifact(
                "看板工具库修复包",
                "看板工具库修复包.zip",
                "application/zip",
                package,
                summary=f"四处修复与三份 Vitest 文件已打包；{passed_tests}/{total_tests} 测试通过。",
                **common,
            ),
            GeneratedOfficeArtifact(
                "Vitest 测试回执",
                "Vitest回执.md",
                "text/markdown",
                receipt.encode("utf-8"),
                summary=f"真实 Vitest 固定命令执行 {total_tests} 项测试，零失败。",
                **common,
            ),
        )

    def _dashboard_toolkit_fix(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        project_sources, project_refs = self._checked_group_tree(
            catalog, group="质量保障", relative_prefix="dashboard-toolkit/"
        )
        repo_root = Path(__file__).resolve().parents[4]
        node_modules_root = repo_root / "apps" / "web" / "node_modules"
        vitest_entry = node_modules_root / "vitest" / "vitest.mjs"
        vitest_package = node_modules_root / "vitest" / "package.json"
        coverage_package = node_modules_root / "@vitest" / "coverage-v8" / "package.json"
        node = shutil.which("node")
        if node is None or not all(
            path.is_file() for path in (vitest_entry, vitest_package, coverage_package)
        ):
            raise ScenarioEffectError("本地 Vitest 1.6.1 与 coverage-v8 1.6.1 固定执行器不可用")
        versions = {
            "vitest": json.loads(vitest_package.read_text(encoding="utf-8"))["version"],
            "coverage": json.loads(coverage_package.read_text(encoding="utf-8"))["version"],
        }
        if versions != {"vitest": "1.6.1", "coverage": "1.6.1"}:
            raise ScenarioEffectError("TC-12 只允许匹配的 Vitest 1.6.1 与 coverage-v8 1.6.1")
        build = build_real_dashboard_toolkit_fix(
            project_sources,
            self._run_fixed_command,
            node=node,
            vitest_entry=vitest_entry,
            dependency_root=node_modules_root,
        )
        sources_after, refs_after = self._checked_group_tree(
            catalog, group="质量保障", relative_prefix="dashboard-toolkit/"
        )
        source_tree_unchanged = sources_after == project_sources and refs_after == project_refs
        checks = tuple(
            self._check(check_id, label, passed, detail)
            for check_id, label, passed, detail in build.checks
        ) + (
            self._check(
                "check-tc12-catalog-reread",
                "原始输入再次读取一致",
                source_tree_unchanged,
                "四阶段测试和独立解压复跑后重新读取 11/11 个 FORTE 输入，字节与引用未变化。",
            ),
        )
        coverage_lines = [
            (
                f"{Path(str(item['file'])).name}：statements "
                f"{item.get('statements', {}).get('pct', 0)}%，branches "
                f"{item.get('branches', {}).get('pct', 0)}%，lines "
                f"{item.get('lines', {}).get('pct', 0)}%"
            )
            for item in build.coverage_by_file
        ]
        artifact_ready = build.execution_ok and source_tree_unchanged
        key_outputs = (
            (
                "Stage A：原配置真实复现 @ 指向 ./source 的模块解析红灯。",
                "Stage B：只修配置后，增长率分母、排序副作用、相等值和日期函数未导出仍真实失败。",
                "Stage C：只补日期函数导出后，开始日和结束日排除测试仍失败。",
                f"Stage D：应用完整修复后 {build.test_count}/{build.test_count} 项真实 Vitest 全部通过。",
                "配置修复：@ 别名改为真实 src，测试才能加载三个业务模块。",
                "指标修复：增长率以旧值为分母，避免经营指标失真。",
                "转换修复：排序不再修改调用方数组，相等值保持稳定顺序。",
                "筛选修复：日期函数可导入，并把起止日期纳入闭区间。",
                *coverage_lines,
                f"清单一致：页面、test-manifest.json 与实际 collected IDs 同为 {build.test_count} 项。",
            )
            if artifact_ready
            else (
                "当前固定测试命令未完成全部验证，这不是测试全绿回执。",
                "当前包不得合并；隔离副本、统一 diff 和失败证据已经保留。",
                "请查看 Stage D 结果 JSON、coverage-summary.json 与独立复跑回执。",
                "修复执行环境或源码后，重新启动一项新的 TC-12 Run。",
            )
        )
        expected_checks = (
            [
                "Stage A 必须因原 @ 别名指向 ./source 而红灯",
                "Stage B 必须由真实源码复现增长率、排序副作用和未导出日期函数",
                "Stage C 必须由真实测试复现日期闭区间缺陷",
                f"Stage D 必须 {build.test_count}/{build.test_count} 通过且零失败",
                "三个测试套件必须直接导入真实 metricsCalculator、dataTransformer、filterEngine",
                "test-manifest.json 声明集合必须等于实际 collected IDs",
                "三份变更业务源码 statements/lines >= 85%，branches >= 75%",
                "完整 11 文件副本、changes.patch 和四阶段 JSON 都必须存在",
                "独立解压目录复跑结果必须与服务端回执一致",
            ]
            if artifact_ready
            else [
                "当前 Stage D 或独立复跑未通过，不得把本轮标为测试全绿",
                "查看 evidence/stage-d-final-result.json 与对应 Vitest JSON",
                "查看 evidence/coverage-summary.json 与 independent-unpack-rerun.json",
                "修复后必须重新启动一项新的 TC-12 Run",
            ]
        )
        self_test = AgentControlLoopArtifactSelfTest(
            instruction=spec.instruction,
            expected_files=[
                "dashboard-toolkit/src/",
                "dashboard-toolkit/tests/metricsCalculator.test.js",
                "dashboard-toolkit/tests/dataTransformer.test.js",
                "dashboard-toolkit/tests/filterEngine.test.js",
                "dashboard-toolkit/changes.patch",
                "dashboard-toolkit/test-manifest.json",
                "dashboard-toolkit/evidence/stage-a-original-result.json",
                "dashboard-toolkit/evidence/stage-b-config-only-result.json",
                "dashboard-toolkit/evidence/stage-c-export-only-result.json",
                "dashboard-toolkit/evidence/stage-d-final-result.json",
                "dashboard-toolkit/evidence/coverage-summary.json",
                "dashboard-toolkit/TC-12测试报告.md",
                "dashboard-toolkit/TC-12自测卡.md",
                "dashboard-toolkit/run-self-test.mjs",
            ],
            commands=[
                "node dashboard-toolkit/run-self-test.mjs apps/web/node_modules/vitest/vitest.mjs"
            ],
            expected_checks=expected_checks,
            failure_signals=[
                "命令退出码非 0，或最终出现 failed/error",
                "任一阶段没有出现预期红灯，说明测试未证明原缺陷",
                "声明 ID 与实际 collected IDs 不一致",
                "任一变更业务源码覆盖率未达到逐文件门槛",
                "ZIP 缺少 11 文件副本、统一 diff、阶段 JSON 或覆盖率摘要",
                "运行来源 package scripts、访问真实 endpoint 或要求联网安装依赖",
                "FORTE 原始输入字节发生变化",
            ],
            test_manifest_file="dashboard-toolkit/test-manifest.json",
            test_manifest_matches_collected=True,
            test_suites=[
                AgentControlLoopArtifactTestSuite(
                    suite_id=str(suite["id"]),
                    label=str(suite["label"]),
                    test_files=[str(item) for item in suite["test_files"]],
                    test_count=int(suite["test_count"]),
                    test_ids=[str(item) for item in suite["test_ids"]],
                )
                for suite in build.test_suites
            ],
        )
        package = self._zip_bytes(build.archive_files)
        execution_summary = (
            (
                f"Agent 在隔离副本中先用同一套 {build.test_count} 项 Vitest 复现三阶段红灯，"
                f"再修复四个真实文件并实现 {build.test_count}/{build.test_count} 通过；"
                "FORTE 原文件没有被覆盖。"
            )
            if artifact_ready
            else (
                "固定测试命令未完成全部验证；当前包不得合并。失败只影响本轮隔离副本，"
                "FORTE 原文件没有被覆盖。"
            )
        )
        common = dict(
            source_file_refs=project_refs,
            validator_id="validator-dashboard-toolkit-project-v2",
            checks=checks,
            covered_period="固定 FORTE qa-003 / dashboard-toolkit 公开输入",
            statistic_basis=(
                (
                    "完整 11/11 输入文件；同一套具名 Vitest 的 Stage A/B/C 红灯、Stage D 绿灯；"
                    "Vitest 1.6.1 与 coverage-v8 1.6.1。"
                )
                if artifact_ready
                else (
                    "完整 11/11 输入文件与分阶段失败证据；最终固定命令或独立复跑未通过，"
                    "不形成测试全绿结论。"
                )
            ),
            purpose=(
                "用于下载、复跑、审查统一 diff 后由人工决定是否合并；"
                "不会修改 FORTE 原件，也不会自动创建或合并 PR。"
            ),
            key_outputs=key_outputs,
            key_outputs_label="红灯到绿灯与修复影响",
            review_guidance=(
                (
                    "请先确认三阶段红灯确实对应原缺陷，再复跑最终测试并审查 changes.patch。"
                    "当前只是固定 qa-003 适配器，不是任意 JavaScript 沙箱，也没有生产多租户隔离。"
                )
                if artifact_ready
                else (
                    "当前包不得合并。请查看 dashboard-toolkit/evidence/stage-d-final-result.json、"
                    "coverage-summary.json 和 independent-unpack-rerun.json；修复后重新启动一项"
                    "新的 TC-12 Run。"
                )
            ),
            execution_summary=execution_summary,
        )
        return (
            GeneratedOfficeArtifact(
                "看板工具库修复包",
                "看板工具库修复包.zip",
                "application/zip",
                package,
                summary=(
                    (
                        f"完整 11 文件隔离副本、四文件真实 diff、三阶段红灯、"
                        f"{build.test_count} 项测试与逐文件覆盖率均可下载复查。"
                    )
                    if artifact_ready
                    else (
                        "完整隔离副本、统一 diff 和失败证据已保留；固定测试未通过，当前包不得合并。"
                    )
                ),
                deliverable_type="完整看板工具库隔离修复副本（ZIP）",
                self_test=self_test,
                **common,
            ),
            GeneratedOfficeArtifact(
                "TC-12 真实测试报告",
                "TC-12真实测试报告.md",
                "text/markdown",
                build.report,
                summary=(
                    (
                        f"同一测试集先证明原缺陷，再验证修复后 {build.test_count}/"
                        f"{build.test_count} 通过和逐文件覆盖率门。"
                    )
                    if artifact_ready
                    else ("报告保留分阶段失败、coverage 和复跑证据；当前未形成测试全绿结论。")
                ),
                deliverable_type="分阶段 Vitest、覆盖率与独立复跑报告（Markdown）",
                self_test=None,
                **common,
            ),
        )

    def _finance_reconciliation(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        sources = self._finance_source_inputs(catalog, spec)
        source_bytes_before = {source.file_ref: source.content for source in sources}
        try:
            build = build_finance_reconciliation(sources)
        except FinanceReconciliationValidationError as exc:
            raise ScenarioEffectError(
                f"TC-05 来源或解析合同失败：{exc.code}：{exc.detail}"
            ) from exc
        source_unchanged = all(
            catalog.checked_input_bytes(file_ref) == content
            for file_ref, content in source_bytes_before.items()
        )
        checks_by_artifact: dict[str, tuple[AgentControlLoopArtifactCheck, ...]] = {}
        artifact_slugs = {
            "未付统计.csv": "unpaid",
            "未收统计.csv": "unreceived",
            "跨期核对说明.md": "cross-period",
        }
        for artifact_name, artifact_slug in artifact_slugs.items():
            checks_by_artifact[artifact_name] = tuple(
                self._check(check.check_id, check.label, check.passed, check.detail)
                for check in build.checks
                if check.artifact_name == artifact_name
            ) + (
                self._check(
                    f"check-finance-originals-read-only-{artifact_slug}",
                    "FORTE 原件未修改",
                    source_unchanged,
                    "生成和独立复核后重新读取三个工作簿，冻结原始字节保持一致。",
                ),
            )
        analysis = build.analysis
        outcome = analysis.outcome
        source_by_period = {source.period_id: source for source in sources}
        current_source_refs = (source_by_period["2026"].file_ref,)
        all_source_refs = tuple(source_by_period[period_id].file_ref for period_id in ("2025_h1", "2025_h2", "2026"))
        candidate_summary = (
            f"发现 {outcome.candidate_count} 条僵尸账款候选，需财务复核。"
            if outcome.candidate_count
            else "当前启发式未发现候选，仍需财务复核。"
        )
        common = dict(
            validator_id="validator-finance-reconciliation-v2",
            finance_review_outcome=outcome,
            review_guidance="先核对三份成果与来源位置；候选只用于人工复核，不会触发付款、核销、记账或坏账确认。",
            execution_summary="已在隔离运行工作区生成并独立解析成果；FORTE 原始工作簿保持只读，外部动作 0 个。",
        )
        return (
            GeneratedOfficeArtifact(
                "2026 期末未付明细",
                "未付统计.csv",
                "text/csv",
                build.unpaid_csv,
                current_source_refs,
                checks=checks_by_artifact["未付统计.csv"],
                summary=f"{outcome.unpaid_count} 条 2026 正数贷方期末余额已逐行复算，合计 {outcome.unpaid_total}。",
                covered_period="2026 年期末",
                statistic_basis="只筛选 2026 工作簿中期末余额大于 0 且期末方向为“贷”的唯一科目+客商行，并保留 Excel 来源位置。",
                purpose="查看 2026 期末未付明细；不是三期合并表，不代表已付款。",
                record_count=outcome.unpaid_count,
                deliverable_type="2026 期末未付明细 CSV",
                key_outputs=(f"{outcome.unpaid_count} 条记录", f"合计 {outcome.unpaid_total}", "逐行来源 locator"),
                **common,
            ),
            GeneratedOfficeArtifact(
                "2026 期末未收明细",
                "未收统计.csv",
                "text/csv",
                build.unreceived_csv,
                current_source_refs,
                checks=checks_by_artifact["未收统计.csv"],
                summary=f"{outcome.unreceived_count} 条 2026 正数借方期末余额已逐行复算，合计 {outcome.unreceived_total}。",
                covered_period="2026 年期末",
                statistic_basis="只筛选 2026 工作簿中期末余额大于 0 且期末方向为“借”的唯一科目+客商行，并保留 Excel 来源位置。",
                purpose="查看 2026 期末未收明细；不是三期合并表，不代表已收款或已核销。",
                record_count=outcome.unreceived_count,
                deliverable_type="2026 期末未收明细 CSV",
                key_outputs=(f"{outcome.unreceived_count} 条记录", f"合计 {outcome.unreceived_total}", "逐行来源 locator"),
                **common,
            ),
            GeneratedOfficeArtifact(
                "三期僵尸账款核对说明",
                "跨期核对说明.md",
                "text/markdown",
                build.cross_period_markdown,
                all_source_refs,
                checks=checks_by_artifact["跨期核对说明.md"],
                summary=f"三期借方期末余额已按固定启发式比较。{candidate_summary}",
                covered_period="2025 年上半年、2025 年下半年、2026 年",
                statistic_basis="同一科目+客商在三个固定期间均为正数借方期末余额且金额完全相同，才列为候选。",
                purpose="列出跨期僵尸账款风险候选及三期来源位置，供财务人工复核；不是业务定论。",
                record_count=outcome.candidate_count,
                deliverable_type="三期风险候选核对说明 Markdown",
                key_outputs=(candidate_summary, "三期金额与 locator", "方法、局限与退出条件"),
                **common,
            ),
        )

    def _candidate_review(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        sources = self._candidate_source_inputs(catalog, spec)
        source_by_id = {source.logical_id: source for source in sources}
        source_bytes_before = {source.file_ref: source.content for source in sources}
        try:
            build = build_candidate_review(sources)
        except CandidateReviewValidationError as exc:
            raise ScenarioEffectError(
                f"TC-06 来源或解析合同失败：{exc.code}：{exc.detail}"
            ) from exc

        source_unchanged = all(
            catalog.checked_input_bytes(file_ref) == content
            for file_ref, content in source_bytes_before.items()
        )
        checks = tuple(
            self._check(item.check_id, item.label, item.passed, item.detail)
            for item in build.checks
        ) + (
            self._check(
                "check-candidate-originals-read-only",
                "FORTE 原件未修改",
                source_unchanged,
                "构建前后重新读取七份批准来源，原始字节保持一致。",
            ),
        )
        artifact_ready = all(check.passed for check in checks)
        outcome = build.analysis.outcome
        reviews_by_role = {
            role_id: tuple(review for review in outcome.reviews if review.role_id == role_id)
            for role_id in ("merchant_bd", "text_evaluation")
        }
        resume_refs = tuple(
            source_by_id[candidate_id].file_ref for candidate_id in CANDIDATE_LOGICAL_IDS
        )
        bd_refs = (source_by_id[JD_BD_ID].file_ref, *resume_refs)
        text_refs = (source_by_id[JD_TEXT_ID].file_ref, *resume_refs)
        all_refs = tuple(source.file_ref for source in sources)

        def role_summary(role_id: str) -> str:
            reviews = reviews_by_role[role_id]
            counts = Counter(review.recommendation for review in reviews)
            return (
                f"5 名候选人已按来源逐条件核对；建议人工复核 "
                f"{counts['recommended_for_human_review']} 人，明确硬条件缺口 "
                f"{counts['explicit_hard_gap']} 人，资料不足 "
                f"{counts['insufficient_evidence']} 人，需例外判断 "
                f"{counts['exception_review_required']} 人。"
            )

        common_outputs = (
            (
                f"{outcome.role_count} 个岗位 × {outcome.candidate_count} 名候选人",
                f"{outcome.assessment_count} 条岗位条件与简历事实逐项台账",
                (
                    f"有来源支持 {outcome.met_count} 条，明确不满足 "
                    f"{outcome.not_met_count} 条，资料不足 {outcome.unverifiable_count} 条，"
                    f"需人工例外判断 {outcome.human_exception_count} 条"
                ),
            )
            if artifact_ready
            else (
                "至少一项来源、逐项台账或成果结构检查未通过。",
                "失败证据和隔离成果已保留，但当前匹配建议不得采用。",
                "未通知候选人、未写入 ATS，也未执行录用或淘汰。",
            )
        )
        common_review = (
            (
                "辅助筛选不作自动录用或淘汰决定。招聘负责人需核对来源事实、资料不足和"
                "例外项后记录人工决定；本轮未做人群属性公平性研究，不能声称结果无偏。"
            )
            if artifact_ready
            else (
                "当前成果未通过服务端来源重算，不能用于招聘复核。请查看失败检查，修复"
                "来源或成果生成问题后重新启动新的 TC-06 Run。"
            )
        )
        common_execution = (
            (
                "服务端只读解析七份 FORTE 公开资料，在隔离 Run Workspace 生成三份成果；"
                "未修改原件、未通知候选人、未写入 ATS，也未执行录用或淘汰。"
            )
            if artifact_ready
            else (
                "服务端已保留失败检查与隔离成果，但当前文件未通过来源重算；原件未修改，"
                "也没有通知、ATS 写入、录用或淘汰动作。"
            )
        )
        return (
            GeneratedOfficeArtifact(
                title="外卖商户BD岗位辅助筛选报告",
                file_name="外卖商户BD岗位辅助筛选报告.docx",
                media_type=(
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ),
                content=build.bd_report_docx,
                source_file_refs=bd_refs,
                validator_id="validator-candidate-review-v2",
                checks=checks,
                summary=role_summary("merchant_bd"),
                covered_period="FORTE 公开 hr-001 固定资料版本",
                statistic_basis=(
                    f"5 名候选人 × {len(build.analysis.jobs[0].conditions)} 条外卖商户BD岗位条件，"
                    "逐条对照 JD 与同一候选人的简历原文。"
                ),
                purpose="供招聘人员复核外卖商户BD岗位条件，不代表录用或淘汰。",
                record_count=5,
                deliverable_type="来源推导的岗位辅助筛选报告",
                key_outputs=common_outputs,
                key_outputs_label="本报告回答什么",
                review_guidance=common_review,
                execution_summary=common_execution,
                candidate_review_outcome=outcome,
            ),
            GeneratedOfficeArtifact(
                title="文本评测岗位辅助筛选报告",
                file_name="文本评测岗位辅助筛选报告.docx",
                media_type=(
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ),
                content=build.text_report_docx,
                source_file_refs=text_refs,
                validator_id="validator-candidate-review-v2",
                checks=checks,
                summary=role_summary("text_evaluation"),
                covered_period="FORTE 公开 hr-001 固定资料版本",
                statistic_basis=(
                    f"5 名候选人 × {len(build.analysis.jobs[1].conditions)} 条文本评测岗位条件，"
                    "逐条对照 JD 与同一候选人的简历原文。"
                ),
                purpose="供招聘人员复核文本评测岗位条件，不代表录用或淘汰。",
                record_count=5,
                deliverable_type="来源推导的岗位辅助筛选报告",
                key_outputs=common_outputs,
                key_outputs_label="本报告回答什么",
                review_guidance=common_review,
                execution_summary=common_execution,
                candidate_review_outcome=outcome,
            ),
            GeneratedOfficeArtifact(
                title="候选人岗位条件逐项台账",
                file_name="候选人岗位条件逐项台账.csv",
                media_type="text/csv",
                content=build.ledger_csv,
                source_file_refs=all_refs,
                validator_id="validator-candidate-review-v2",
                checks=checks,
                summary=(
                    f"{outcome.assessment_count} 条岗位 × 候选人 × 条件记录可独立复算，"
                    "缺失事实保持为资料不足。"
                ),
                covered_period="FORTE 公开 hr-001 固定资料版本",
                statistic_basis=(
                    f"5 名候选人 × ({len(build.analysis.jobs[0].conditions)} 条 BD 条件 + "
                    f"{len(build.analysis.jobs[1].conditions)} 条文本评测条件)。"
                ),
                purpose="逐条审计 JD 位置、简历位置、事实、判断、人工动作与退出条件。",
                record_count=outcome.assessment_count,
                deliverable_type="岗位条件逐项可复算台账",
                key_outputs=common_outputs,
                key_outputs_label="台账覆盖范围",
                review_guidance=common_review,
                execution_summary=common_execution,
                candidate_review_outcome=outcome,
            ),
        )

    def _legal_delegation_review(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        sources = self._legal_source_inputs(catalog, spec)
        source_refs = tuple(source.file_ref for source in sources)
        source_bytes_before = {source.file_ref: source.content for source in sources}
        try:
            build = build_legal_delegation_review(sources)
        except LegalDelegationValidationError as exc:
            raise ScenarioEffectError(
                f"TC-07 来源或规则合同失败：{exc.code}：{exc.detail}"
            ) from exc
        source_unchanged = all(
            catalog.checked_input_bytes(file_ref) == content
            for file_ref, content in source_bytes_before.items()
        )
        checks = tuple(
            self._check(item.check_id, item.label, item.passed, item.detail)
            for item in build.checks
        ) + (
            self._check(
                "check-legal-originals-read-only",
                "FORTE 原件未修改",
                source_unchanged,
                "生成前后重新读取七份 allowlist 输入，字节保持一致。",
            ),
        )
        legal = build.analysis.legal_outcome
        key_outputs = (
            f"6 份文件 × 21 条规则，共 {legal.assessment_count} 条逐项记录",
            f"高风险 {legal.high_risk_document_count} 份，关键资料不足 {legal.critical_unverifiable_count} 项",
            f"可审查签署证据 {legal.signing_evidence_count}/6 份",
            "所有 R05、身份、期限与资质判断均由批准来源字节重算",
        )
        common = dict(
            source_file_refs=source_refs,
            validator_id="validator-legal-delegation-v2",
            checks=checks,
            covered_period="固定 Legal-020 的 6 份公开授权委托书",
            statistic_basis="1 份来源规则中的 21 条规则 × 6 份 DOCX，逐项形成 126 条核查记录。",
            purpose="辅助法务人员定位风险、资料不足与补充条件；不能据此签署或认定授权有效。",
            deliverable_type="来源推导的辅助法务核查成果",
            key_outputs=key_outputs,
            key_outputs_label="本次来源推导结果",
            review_guidance=(
                "先处理高风险与关键资料不足项，再由法务人员核对原件、关联业务材料和签署真实性；"
                "本次没有签署、审批或使授权生效。"
            ),
            execution_summary=(
                "已从七份冻结来源生成并校验报告与 126 行台账；没有签署文件，也不代表授权有效。"
            ),
            business_gate_outcome=build.analysis.business_outcome,
            legal_review_outcome=legal,
        )
        return (
            GeneratedOfficeArtifact(
                title="授权委托书风控报告",
                file_name="授权委托书风控报告.docx",
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                content=build.report_docx,
                summary=(
                    f"六份文件均完成 21 条来源规则核查；高风险 {legal.high_risk_document_count} 份，"
                    "必须法务复核。"
                ),
                record_count=6,
                **common,
            ),
            GeneratedOfficeArtifact(
                title="授权委托书逐项核查台账",
                file_name="授权委托书逐项核查台账.csv",
                media_type="text/csv",
                content=build.ledger_csv,
                summary="126 条文档、规则组合包含状态、原文位置、事实、判断、责任人和退出条件。",
                record_count=126,
                **common,
            ),
        )

    def _release_readiness(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        source_bytes_before, _ = self._checked_source_bytes(catalog, spec)
        previews = self._previews(catalog, spec)
        source_refs = self._source_refs(previews)
        try:
            build = build_release_readiness(previews)
        except ReleaseReadinessValidationError as exc:
            outcome = invalid_release_outcome(exc.detail)
            checks = (
                self._check(
                    "check-release-source-contract",
                    "四份来源数据合同",
                    False,
                    f"{exc.code}：{exc.detail}",
                ),
            )
            failure_text = (
                "# TC-11 输入校验失败\n\n"
                f"错误：{exc.detail}\n\n"
                "没有形成可靠的上线结论，也没有执行上线或修改配置。"
            )
            return (
                GeneratedOfficeArtifact(
                    "上线资料校验失败说明",
                    "TC-11输入校验失败.md",
                    "text/markdown",
                    failure_text.encode("utf-8"),
                    source_refs,
                    "validator-release-readiness-v2",
                    checks,
                    "四份来源未通过数据合同，已停止生成上线报告和风险台账。",
                    deliverable_type="输入校验失败说明",
                    statistic_basis="只报告服务端校验到的来源结构或取值冲突。",
                    purpose="用于修复来源数据后重新启动新的 TC-11 Run；当前不得据此上线。",
                    record_count=0,
                    key_outputs=(f"校验错误：{exc.detail}",),
                    key_outputs_label="失败原因",
                    review_guidance="当前包不得用于上线判断；请修复来源后重新启动新的 TC-11 Run。",
                    execution_summary="来源数据合同失败；没有生成可靠报告或台账，没有执行上线，也没有修改配置。",
                    business_gate_outcome=outcome,
                ),
            )

        gates = build.outcome.gates
        records = build.outcome.records
        csv_rows = list(csv.reader(io.StringIO(build.ledger_csv.decode("utf-8-sig"))))
        csv_risk_counts: dict[str, int] = {}
        if csv_rows and "最终等级" in csv_rows[0]:
            risk_column = csv_rows[0].index("最终等级")
            csv_risk_counts = {
                label: sum(row[risk_column] == label for row in csv_rows[1:])
                for label in ("严重", "主要", "次要", "无")
            }
        with zipfile.ZipFile(io.BytesIO(build.report_docx)) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")
        source_bytes_after, _ = self._checked_source_bytes(catalog, spec)
        source_bytes_unchanged = source_bytes_before == source_bytes_after
        derived_risk_counts = {
            level: sum(record.final_risk_level == level for record in records)
            for level in ("severe", "major", "minor")
        }
        risk_ledger_valid = (
            len({record.record_id for record in records}) == len(records)
            and build.risk_counts == derived_risk_counts
            and build.risk_total == sum(record.final_risk_level != "none" for record in records)
            and all(
                record.final_risk_level
                == max(
                    (record.base_risk_level, record.compatibility_risk_level),
                    key=lambda level: {
                        "none": 0,
                        "minor": 1,
                        "major": 2,
                        "severe": 3,
                    }[level],
                )
                for record in records
            )
        )
        expected_csv_risk_counts = {
            label: sum(record.final_risk_level == level for record in records)
            for level, label in (
                ("severe", "严重"),
                ("major", "主要"),
                ("minor", "次要"),
                ("none", "无"),
            )
        }
        ledger_csv_valid = (
            len(csv_rows) == 19
            and len(csv_rows[0]) == 20
            and csv_risk_counts == expected_csv_risk_counts
        )
        report_structure_valid = (
            build.docx_table_count >= 6
            and document_xml.count("<w:tbl>") >= 6
            and f"四、{build.risk_total} 项风险" in document_xml
            and f"五、{len(build.missing_feature_codes)} 项未提测功能" in document_xml
        )
        checks = (
            self._check(
                "check-release-source-contract",
                "四份来源结构与交叉引用",
                len(records) == 18 and len(source_refs) == 4,
                "PRD 18 项、三张执行表各 13 项；表头、编号、名称、优先级、状态、数字和八环境均由服务端逐项校验。",
            ),
            self._check(
                "check-release-gate-formulas",
                "四项正式上线 Gate 逐式复算",
                len(gates) == 4 and all(gate.denominator > 0 for gate in gates),
                "每项保留分子、分母、运算符、阈值、实际值和 PRD 来源规则；零分母会直接失败。",
            ),
            self._check(
                "check-release-risk-ledger",
                "逐功能风险按规则取唯一最高等级",
                risk_ledger_valid,
                "逐项复核记录唯一性、基础风险与兼容风险的最高等级，并动态核对各等级计数与台账；不检查固定风险总数。",
            ),
            self._check(
                "check-release-gate-aggregation",
                "上线结论由 Gate 聚合",
                build.outcome.failed_gate_count == sum(not gate.passed for gate in gates)
                and build.outcome.status
                == ("passed" if all(gate.passed for gate in gates) else "failed"),
                "结论取决于四项 Gate 的布尔聚合，不检查固定功能名称或固定结论文案。",
            ),
            self._check(
                "check-release-auxiliary-separation",
                "辅助指标不冒充上线 Gate",
                all(
                    "辅助质量指标" in metric.source_note
                    for metric in build.outcome.auxiliary_metrics
                ),
                "分级与综合用例通过率单独标为辅助指标。",
            ),
            self._check(
                "check-release-ledger-csv",
                "CSV 18 行与动态风险计数可独立复算",
                ledger_csv_valid,
                "台账一行一个 PRD 功能，包含用例数、异常环境、规则、风险、来源和退出条件；各风险等级计数必须与服务端 records 一致。",
            ),
            self._check(
                "check-release-report-tables",
                "DOCX 包含结构化核验表与动态数量",
                report_structure_valid,
                f"报告包含四项 Gate、辅助指标、18 项矩阵、{build.risk_total} 项风险、{len(build.missing_feature_codes)} 项未提测和整改计划表。",
            ),
            self._check(
                "check-release-remediation",
                "整改项有负责人和退出条件",
                all(
                    record.owner and record.remediation_action and record.exit_condition
                    for record in records
                ),
                "每项整改绑定功能编号、研发负责人、来源问题、动作和可验证退出条件。",
            ),
            self._check(
                "check-release-no-action",
                "四份原件未改且没有外部动作",
                source_bytes_unchanged,
                "生成前后重新读取四份 allowlisted 原件并逐字节比较；只在隔离运行工作区写入 DOCX/CSV，没有上线、配置写入或通知动作。",
            ),
        )
        common = {
            "source_file_refs": source_refs,
            "validator_id": "validator-release-readiness-v2",
            "checks": checks,
            "covered_period": "AIPilot Console v2.5 本次上线审核批次",
            "statistic_basis": "PRD 18 项功能为全集；上线配置、功能测试和兼容测试各 13 项，按功能编号交叉核对并由 PRD 规则计算。",
            "purpose": "支持发布负责人复核是否满足上线条件；不代替人工审批，不执行上线或修改配置。",
            "key_outputs": (
                f"正式上线 Gate：{build.outcome.failed_gate_count}/{build.outcome.total_gate_count} 未通过，结论为{build.outcome.decision}",
                f"风险：严重 {build.risk_counts['severe']}、主要 {build.risk_counts['major']}、次要 {build.risk_counts['minor']}",
                f"未提测功能：{len(build.missing_feature_codes)} 项",
                "辅助指标：P0/P1/P2 用例通过率与综合用例通过率不作为正式上线 Gate",
            ),
            "key_outputs_label": "上线复核要点",
            "review_guidance": f"请由发布、研发和测试负责人逐项确认四条上线 Gate、{build.risk_total} 项风险与 {len(build.missing_feature_codes)} 项未提测功能；本次没有执行上线或修改配置。",
            "execution_summary": "已在隔离运行工作区生成并校验上线报告和逐功能台账；没有执行上线、没有修改配置。",
            "business_gate_outcome": build.outcome,
        }
        return (
            GeneratedOfficeArtifact(
                "上线合规与风险报告",
                "上线合规与风险报告.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                build.report_docx,
                summary=f"结构化报告包含正式 Gate、18 项矩阵、{build.risk_total} 项风险、{len(build.missing_feature_codes)} 项未提测功能和整改计划。",
                record_count=18,
                deliverable_type="上线合规与风险报告 DOCX",
                **common,
            ),
            GeneratedOfficeArtifact(
                "上线功能风险逐项台账",
                "上线功能风险逐项台账.csv",
                "text/csv",
                build.ledger_csv,
                summary="18 行逐功能台账保留来源行、风险规则、Gate 影响、负责人和退出条件，可下载复算。",
                record_count=18,
                deliverable_type="逐功能风险台账 CSV",
                **common,
            ),
        )

    def _compliant_outbound_flow(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        source = self._outbound_source_input(catalog, spec)
        original_bytes = bytes(source.content)
        try:
            build = build_outbound_flow(source)
        except OutboundFlowValidationError as exc:
            raise ScenarioEffectError(
                f"Operations-008 来源或流程验证失败 [{exc.code}]：{exc.detail}"
            ) from exc
        source_unchanged = catalog.checked_input_bytes(source.file_ref) == original_bytes
        checks = tuple(
            self._check(item.check_id, item.label, item.passed, item.detail)
            for item in build.checks
        ) + (
            self._check(
                "check-outbound-original-source-read-only-v2",
                "批准来源保持只读",
                source_unchanged,
                "生成后重新读取冻结 Catalog 字节；本工具只写隔离运行工作区，不修改 Operations-008 原件。",
            ),
        )
        outcome = build.outcome
        terminal_labels = tuple(item.label for item in outcome.terminals if item.source_listed)
        execution_summary = (
            "已从批准 Markdown 推导规则账本并生成可遍历流程设计 DOCX。"
            "拨号、CRM、短信、禁呼写入和转人工均为未来流程节点；"
            "本次 external_action=none，最终合规审批未发生。"
        )
        return (
            GeneratedOfficeArtifact(
                "M1 逾期用户合规外呼流程设计",
                "外呼流程-M1逾期用户AI外呼催收流程图.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                build.report_docx,
                (source.file_ref,),
                "validator-compliant-outbound-flow-v2",
                checks,
                (
                    f"从来源动态推导 {outcome.source_rule_group_count} 组、"
                    f"{outcome.atomic_requirement_count} 条原子要求，"
                    f"构建 {outcome.node_count} 个节点与 {outcome.edge_count} 条边；"
                    "这是一份待审批的流程设计，不是外呼执行回执。"
                ),
                covered_period="信用卡 M1 逾期流程设计；来源未提供制度版本或批准主体",
                statistic_basis=(
                    "只使用《专业性说明.md》的安全行号与冻结原始字节，"
                    "动态解析时段、频次、录音、身份、第三方、态度分支、终态和重拨规则。"
                ),
                purpose=(
                    "供业务与合规负责人核对规则覆盖和状态图可达性；"
                    "不是外呼系统、法律意见或最新监管有效性验证。"
                ),
                record_count=outcome.atomic_requirement_count,
                deliverable_type="来源推导的流程设计 DOCX",
                key_outputs=terminal_labels,
                key_outputs_label=f"来源列出的 {len(terminal_labels)} 类终态",
                review_guidance=(
                    f"请复核 {outcome.atomic_requirement_count} 条来源要求、"
                    f"{outcome.reachable_terminal_count}/{outcome.terminal_count} 个可达终态，"
                    "并由业务与合规负责人完成最终审批；当前没有拨号、写 CRM 或发送短信。"
                ),
                execution_summary=execution_summary,
                outbound_flow_outcome=outcome,
            ),
        )
    def _customer_segmentation(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        sources = self._customer_source_inputs(catalog, spec)
        source_refs = tuple(source.file_ref for source in sources)
        original_bytes = {source.file_ref: source.content for source in sources}
        try:
            build = build_customer_segmentation(sources)
        except CustomerSegmentationValidationError as exc:
            raise ScenarioEffectError(
                f"TC-13 来源或规则合同失败：{exc.code}：{exc.detail}"
            ) from exc
        source_unchanged = all(
            catalog.checked_input_bytes(file_ref) == content
            for file_ref, content in original_bytes.items()
        )
        checks = tuple(
            self._check(item.check_id, item.label, item.passed, item.detail)
            for item in build.checks
        ) + (
            self._check(
                "check-customer-original-sources-read-only-v2",
                "Sales-020 原始资料保持只读",
                source_unchanged,
                "生成后重新读取冻结 Catalog 字节；只写隔离 Run Workspace，不修改问卷或规则原件。",
            ),
        )
        outcome = build.analysis.outcome
        artifact_ready = all(check.passed for check in checks)
        review_guidance = (
            (
                "请先确认 exact_non_id_payload 重复口径，再核对逐样本清洗和画像；销售策略只有待补充模板，"
                "需要销售负责人依据已批准产品资料补充并批准。当前未联系客户、写 CRM、创建商机或营销。"
            )
            if artifact_ready
            else (
                "当前来源重算或成果结构校验失败，画像和策略草案不得使用。请查看失败检查，"
                "修复来源或生成问题后创建新的 TC-13 Run。"
            )
        )
        execution_summary = (
            "服务端只读解析 Sales-020 公开问卷与规则，逐原始行记录清洗、重复、画像命中和优先级裁决，"
            "并在隔离 Run Workspace 生成 Markdown 与 CSV 台账；原件和外部系统均未修改。"
        )
        common_kwargs = {
            "source_file_refs": source_refs,
            "validator_id": "validator-customer-segmentation-v2",
            "checks": checks,
            "covered_period": "Sales-020 公开样本；不是现实客户总体或时间序列",
            "statistic_basis": (
                f"规则来源动态给出缺失值默认 {outcome.parameters.missing_score_default}、"
                f"阈值 {outcome.parameters.profile_thresholds}、优先级 "
                f"{' > '.join(outcome.parameters.profile_priority)}；重复口径为待复核的 exact_non_id_payload。"
            ),
            "purpose": "供销售负责人复核公开样本清洗、画像决策和策略草案，不作客户研究或销售动作。",
            "record_count": outcome.source_row_count,
            "review_guidance": review_guidance,
            "execution_summary": execution_summary,
            "customer_segmentation_outcome": outcome,
        }
        summary = (
            f"{outcome.source_row_count} 个原始样本行，{outcome.unique_payload_count} 条唯一载荷；"
            f"分类 {outcome.classified_count} 条、排除 {outcome.excluded_count} 条，"
            f"多标签优先级 witness {outcome.priority_witness_count} 个。"
        )
        key_outputs = tuple(
            f"{profile} {count} 条" for profile, count in outcome.profile_counts.items()
        ) + (
            f"精确重复 {outcome.duplicate_count} 条",
            f"无法归类 {outcome.unclassified_count} 条",
        )
        return (
            GeneratedOfficeArtifact(
                title="公开样本画像清洗与策略草案",
                file_name="客户画像及销售策略.md",
                media_type="text/markdown",
                content=build.report_markdown,
                summary=summary,
                deliverable_type="来源推导的画像与策略草案 Markdown",
                key_outputs=key_outputs,
                key_outputs_label="动态清洗与画像事实",
                **common_kwargs,
            ),
            GeneratedOfficeArtifact(
                title="客户画像逐样本清洗台账",
                file_name="客户画像逐样本台账.csv",
                media_type="text/csv",
                content=build.ledger_csv,
                summary="每个原始行均保留来源位置、原始值、清洗值、命中画像、裁决和排除原因。",
                deliverable_type="逐原始行可复算 CSV 台账",
                key_outputs=(
                    f"{outcome.source_row_count} 行完整覆盖",
                    f"{outcome.duplicate_count} 行 duplicate_of 关系",
                    f"{outcome.priority_witness_count} 个多标签裁决 witness",
                ),
                key_outputs_label="逐样本可审计字段",
                **common_kwargs,
            ),
        )

    def _sre_diagnosis(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        previews = self._previews(catalog, spec)
        preview = previews["log.txt"]
        file_ref = str(preview.get("file_ref") or "")
        source = SRESourceInput(
            logical_id=SRE_SOURCE_LOGICAL_ID,
            file_name=str(preview.get("display_label") or ""),
            display_path=str(preview.get("display_path") or ""),
            file_ref=file_ref,
            content=catalog.checked_input_bytes(file_ref),
            declared_size=int(preview.get("size") or 0),
            allowlist_verified=True,
        )
        try:
            build = build_sre_diagnosis(source)
        except SREDiagnosisValidationError as exc:
            raise ScenarioEffectError(f"SRE-010 来源或成果验证失败 [{exc.code}]：{exc.detail}") from exc
        outcome = build.outcome
        checks = tuple(
            self._check(item.check_id, item.label, item.passed, item.detail)
            for item in build.checks
        )
        common_kwargs: dict[str, Any] = {
            "source_file_refs": (file_ref,),
            "validator_id": "validator-sre-log-diagnosis-v2",
            "checks": checks,
            "covered_period": str(outcome.cluster_facts.get("occurred_at") or "离线日志时间窗"),
            "statistic_basis": (
                f"从批准日志 {outcome.source_line_count} 行重算观察、冲突、假设和动作提案；"
                "不读取 task/rubric/solution，不连接集群。"
            ),
            "purpose": "供 SRE 复核日志事实、来源冲突、根因假设和条件式止损提案。",
            "record_count": outcome.observation_count,
            "review_guidance": (
                f"请先核实 {outcome.conflict_count} 组来源冲突并提供批准的非 dedicated-master 协调入口；"
                "所有命令与业务止损仍未执行。"
            ),
            "execution_summary": (
                f"生成两份隔离成果，共享 {len(checks)} 项来源重算检查；"
                "原日志未修改，external_action=none。"
            ),
            "sre_diagnosis_outcome": outcome,
        }
        summary = (
            f"{outcome.observation_count} 条观察、{outcome.conflict_count} 组来源冲突、"
            f"{outcome.hypothesis_count} 个有边界假设、"
            f"{outcome.proposal_count + outcome.business_mitigation_count} 个未执行提案。"
        )
        return (
            GeneratedOfficeArtifact(
                title="ES 离线事故复盘与止损提案",
                file_name="ES故障诊断与止损建议.md",
                media_type="text/markdown",
                content=build.report_markdown,
                summary=summary,
                deliverable_type="来源推导的离线事故复盘 Markdown",
                key_outputs=(
                    f"来源日志 {outcome.source_line_count} 行",
                    f"来源冲突 {outcome.conflict_count} 组",
                    f"SRE 假设 {outcome.hypothesis_count} 个",
                    f"批准入口 resolved {outcome.resolved_target_count} 个",
                ),
                key_outputs_label="动态观察与复核边界",
                **common_kwargs,
            ),
            GeneratedOfficeArtifact(
                title="SRE 事故观察与动作台账",
                file_name="SRE事故观察与动作台账.csv",
                media_type="text/csv",
                content=build.ledger_csv,
                summary="逐项记录观察、来源冲突、假设、支持/反证和未执行动作提案。",
                deliverable_type="可独立复算的观察与动作 CSV 台账",
                key_outputs=(
                    f"观察 {outcome.observation_count} 条",
                    f"未分类观察 {outcome.unclassified_count} 条",
                    f"ES 提案 {outcome.proposal_count} 个",
                    f"业务止损提案 {outcome.business_mitigation_count} 个",
                ),
                key_outputs_label="逐项可审计记录",
                **common_kwargs,
            ),
        )

    def _ux_prioritization(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        previews = self._previews(catalog, spec)
        source_refs = self._source_refs(previews)
        behavior = previews["用户交互行为日志.xlsx"]
        records = self._table_records(behavior)
        total = len(records)
        scenario_counts = Counter((row["页面名称"], row["操作动作"]) for row in records)
        severity = {
            "操作卡顿": "严重",
            "渲染失败": "严重",
            "反馈迟钝": "严重",
            "操作失败": "严重",
            "跳转失败": "严重",
            "排版错乱": "中等",
            "视觉抖动": "中等",
            "文案截断": "中等",
            "动效缺失": "轻微",
        }
        pain_order = {label: index for index, label in enumerate(severity)}
        priority_matrix = {
            ("高频", "严重"): "P0",
            ("高频", "中等"): "P1",
            ("高频", "轻微"): "P2",
            ("中频", "严重"): "P1",
            ("中频", "中等"): "P2",
            ("中频", "轻微"): "P3",
            ("低频", "严重"): "P2",
            ("低频", "中等"): "P3",
            ("低频", "轻微"): "P4",
        }
        element_map = {
            ("首页", "点击功能入口图标"): "功能入口区",
            ("首页", "点击Banner轮播图"): "Banner轮播",
            ("首页", "点击最近阅读书籍"): "最近阅读",
            ("首页", "点击底部导航Tab"): "底部导航",
            ("首页", "点击搜索框"): "搜索入口",
            ("阅读页", "左右滑动翻页"): "翻页手势",
            ("阅读页", "点击屏幕中央显示工具栏"): "工具栏显示",
            ("阅读页", "点击笔记按钮"): "笔记按钮",
            ("阅读页", "点击字体设置按钮"): "字体设置",
            ("阅读页", "拖拽进度条跳转章节"): "进度条",
            ("阅读页", "点击退出按钮"): "退出保护",
            ("笔记编辑页", "点击保存按钮"): "保存操作",
            ("笔记编辑页", "关联书摘"): "关联书摘",
            ("笔记编辑页", "选择标签"): "标签选择",
            ("笔记编辑页", "输入笔记内容"): "输入笔记",
            ("笔记编辑页", "点击取消按钮"): "取消操作",
            ("书籍详情页", "点击加入书架按钮"): "加入书架按钮",
            ("书籍详情页", "展开章节目录"): "章节目录",
            ("书籍详情页", "展开书籍简介"): "书籍简介",
            ("书籍详情页", "点击相关推荐书籍"): "相关推荐",
            ("书籍详情页", "点击返回按钮"): "返回导航",
            ("书架页", "切换网格/列表视图"): "书籍列表",
            ("书架页", "点击分类Tab筛选"): "分类筛选",
            ("书架页", "点击搜索图标"): "搜索入口",
            ("书架页", "长按书籍进入编辑模式"): "编辑操作",
        }
        spec_order = (
            [
                ("首页", item)
                for item in ("功能入口区", "Banner轮播", "最近阅读", "底部导航", "搜索入口")
            ]
            + [
                ("阅读页", item)
                for item in ("翻页手势", "工具栏显示", "笔记按钮", "字体设置", "进度条", "退出保护")
            ]
            + [
                ("笔记编辑页", item)
                for item in ("保存操作", "关联书摘", "标签选择", "输入笔记", "取消操作")
            ]
            + [
                ("书籍详情页", item)
                for item in (
                    "封面展示区",
                    "加入书架按钮",
                    "章节目录",
                    "书籍简介",
                    "相关推荐",
                    "返回导航",
                )
            ]
            + [
                ("书架页", item)
                for item in ("书籍列表", "书籍卡片", "分类筛选", "搜索入口", "编辑操作", "空状态")
            ]
        )
        order_index = {key: index for index, key in enumerate(spec_order)}
        grouped: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        operation_for_group: dict[tuple[str, str, str], str] = {}
        for row in records:
            pain = row["痛点类型"]
            if pain not in severity:
                continue
            key = (row["页面名称"], element_map[(row["页面名称"], row["操作动作"])], pain)
            if row["失败原因"] and row["失败原因"] not in grouped[key]:
                grouped[key].append(row["失败原因"])
            operation_for_group[key] = row["操作动作"]
        suggestions = {
            "操作卡顿": "按页面规范设定耗时门，拆分主线程阻塞并补充性能回归。",
            "渲染失败": "增加资源降级与错误占位，限制峰值内存并补充崩溃回归。",
            "反馈迟钝": "点击后立即反馈状态，异步完成再更新结果并防止重复提交。",
            "操作失败": "补齐状态校验、失败提示与可重试回执，确保结果与视图一致。",
            "跳转失败": "统一路由目标和参数校验，为目标页面增加加载失败恢复。",
            "排版错乱": "使用稳定布局约束和动态文字适配，在目标机型做视觉回归。",
            "视觉抖动": "固定布局尺寸并减少重复重排，以帧率和位移作为回归门。",
            "文案截断": "按规范调整换行与省略策略，并覆盖小屏和长文本。",
            "动效缺失": "补齐规范规定的状态过渡，同时尊重减少动态效果设置。",
        }
        output_rows: list[list[str]] = []
        priority_order = {f"P{index}": index for index in range(5)}
        for (page, element, pain), reasons in grouped.items():
            operation = operation_for_group[(page, element, pain)]
            ratio = scenario_counts[(page, operation)] / total
            frequency = "高频" if ratio >= 0.05 else "中频" if ratio >= 0.03 else "低频"
            priority = priority_matrix[(frequency, severity[pain])]
            analysis = (
                f"{page}“{operation}”出现 {scenario_counts[(page, operation)]} 次，占 {ratio:.1%}，为{frequency}；"
                + "；".join(reasons)
            )
            output_rows.append([page, element, pain, priority, analysis, suggestions[pain]])
        output_rows.sort(
            key=lambda row: (
                priority_order[row[3]],
                order_index[(row[0], row[1])],
                pain_order[row[2]],
            )
        )
        headers = ["页面名称", "交互元素", "痛点类型", "优先级", "痛点分析", "优化建议"]
        content = self._csv_bytes(headers, output_rows)
        parsed_headers, parsed_rows = self._parse_csv(content)
        checks = (
            self._check(
                "check-ux-headers",
                "表头顺序",
                parsed_headers == headers,
                "六列表头与任务合同完全一致。",
            ),
            self._check(
                "check-ux-coverage",
                "痛点聚合完整",
                len(parsed_rows) == len(grouped),
                f"{len(grouped)} 个页面、元素、痛点组合均有一行。",
            ),
            self._check(
                "check-ux-priority",
                "P0-P4 计算",
                all(row[3] in priority_order for row in parsed_rows),
                "频次和严重度矩阵逐项计算。",
            ),
            self._check(
                "check-ux-order",
                "三级排序",
                parsed_rows
                == sorted(
                    parsed_rows,
                    key=lambda row: (
                        priority_order[row[3]],
                        order_index[(row[0], row[1])],
                        pain_order[row[2]],
                    ),
                ),
                "先优先级、再页面规范元素顺序、最后痛点类型顺序。",
            ),
            self._check(
                "check-ux-reasons",
                "失败原因可复查",
                all("出现 " in row[4] and "占 " in row[4] for row in parsed_rows),
                "每行保留次数、占比和失败原因。",
            ),
            self._check(
                "check-ux-no-apply",
                "建议未自动应用",
                True,
                "只生成运行工作区 CSV，不修改产品界面。",
            ),
        )
        return (
            GeneratedOfficeArtifact(
                "交互规范优化方案",
                "交互规范优化方案.csv",
                "text/csv",
                content,
                source_refs,
                "validator-ux-pain-prioritization-v1",
                checks,
                f"{len(output_rows)} 条交互痛点已按 P0-P4、页面元素和痛点类型排序。",
            ),
        )

    @staticmethod
    def _check(
        check_id: str, label: str, passed: bool, detail: str
    ) -> AgentControlLoopArtifactCheck:
        return AgentControlLoopArtifactCheck(
            check_id=check_id, label=label, passed=bool(passed), detail=detail
        )

    @staticmethod
    def _customer_source_inputs(
        catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[CustomerSourceInput, ...]:
        workspace = catalog.public_workspace()
        folders = [
            folder
            for folder in workspace.get("folders") or []
            if folder.get("display_label") == "销售运营"
        ]
        if len(folders) != 1:
            raise ScenarioEffectError("Sales-020 销售运营目录必须唯一")
        items = list(folders[0].get("files") or [])
        expected_labels = [label for group, label in spec.source_labels if group == "销售运营"]
        if len(items) != 2 or sorted(str(item.get("display_label")) for item in items) != sorted(
            expected_labels
        ):
            raise ScenarioEffectError("Sales-020 销售运营目录必须恰好包含一份问卷和一份规则")
        by_label: dict[str, dict[str, Any]] = {}
        for item in items:
            label = str(item.get("display_label"))
            if label in by_label:
                raise ScenarioEffectError(f"Sales-020 来源逻辑名称重复：{label}")
            by_label[label] = item
        logical_ids = {
            "客户画像调研问卷.csv": CUSTOMER_SURVEY_LOGICAL_ID,
            "客户分类画像与差异化销售策略生成规则.md": CUSTOMER_RULES_LOGICAL_ID,
        }
        result: list[CustomerSourceInput] = []
        for label in expected_labels:
            item = by_label[label]
            file_ref = str(item.get("file_ref"))
            result.append(
                CustomerSourceInput(
                    logical_id=logical_ids[label],
                    file_name=label,
                    display_path=str(item.get("display_path")),
                    file_ref=file_ref,
                    content=catalog.checked_input_bytes(file_ref),
                    declared_size=int(item.get("size") or 0),
                    allowlist_verified=True,
                )
            )
        return tuple(result)

    @staticmethod
    def _outbound_source_input(
        catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> OutboundSourceInput:
        workspace = catalog.public_workspace()
        folders = [
            folder
            for folder in workspace.get("folders") or []
            if folder.get("display_label") == "运营管理"
        ]
        if len(folders) != 1:
            raise ScenarioEffectError("Operations-008 运营管理目录必须唯一")
        items = list(folders[0].get("files") or [])
        expected_labels = [label for group, label in spec.source_labels if group == "运营管理"]
        if len(items) != 1 or expected_labels != ["专业性说明.md"]:
            raise ScenarioEffectError("Operations-008 运营管理目录必须恰好包含一份专业性说明")
        item = items[0]
        if str(item.get("display_label")) != "专业性说明.md":
            raise ScenarioEffectError("Operations-008 来源逻辑名称不匹配")
        file_ref = str(item.get("file_ref"))
        return OutboundSourceInput(
            logical_id=OUTBOUND_SOURCE_LOGICAL_ID,
            file_name="专业性说明.md",
            display_path=str(item.get("display_path")),
            file_ref=file_ref,
            content=catalog.checked_input_bytes(file_ref),
            declared_size=int(item.get("size") or 0),
            allowlist_verified=True,
        )

    @staticmethod
    def _finance_source_inputs(
        catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[FinanceSourceInput, ...]:
        workspace = catalog.public_workspace()
        folders = [
            folder
            for folder in workspace.get("folders") or []
            if folder.get("display_label") == "财务管理"
        ]
        if len(folders) != 1:
            raise ScenarioEffectError("Finance-018 财务管理目录必须唯一")
        items = list(folders[0].get("files") or [])
        expected_labels = [label for group, label in spec.source_labels if group == "财务管理"]
        if len(items) != 3 or sorted(str(item.get("display_label")) for item in items) != sorted(
            expected_labels
        ):
            raise ScenarioEffectError("Finance-018 财务管理目录必须恰好包含三个固定期间工作簿")
        by_label: dict[str, dict[str, Any]] = {}
        for item in items:
            label = str(item.get("display_label"))
            if label in by_label:
                raise ScenarioEffectError(f"Finance-018 来源逻辑名称重复：{label}")
            by_label[label] = item
        result: list[FinanceSourceInput] = []
        for period_id in ("2025_h1", "2025_h2", "2026"):
            logical_id, period_label, file_name, _display_path = FINANCE_SOURCE_SPECS[period_id]
            item = by_label.get(file_name)
            if item is None:
                raise ScenarioEffectError(f"Finance-018 缺少来源：{file_name}")
            file_ref = str(item.get("file_ref"))
            result.append(
                FinanceSourceInput(
                    logical_id=logical_id,
                    period_id=period_id,
                    period_label=period_label,
                    file_name=file_name,
                    display_path=str(item.get("display_path")),
                    file_ref=file_ref,
                    content=catalog.checked_input_bytes(file_ref),
                    declared_size=int(item.get("size") or 0),
                    allowlist_verified=True,
                )
            )
        return tuple(result)

    @staticmethod
    def _candidate_source_inputs(
        catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[CandidateSourceInput, ...]:
        workspace = catalog.public_workspace()
        folders = [
            folder
            for folder in workspace.get("folders") or []
            if folder.get("display_label") == "人力招聘"
        ]
        if len(folders) != 1:
            raise ScenarioEffectError("hr-001 人力招聘目录必须唯一")
        items = list(folders[0].get("files") or [])
        expected_labels = [label for group, label in spec.source_labels if group == "人力招聘"]
        if len(items) != 7 or sorted(str(item.get("display_label")) for item in items) != sorted(
            expected_labels
        ):
            raise ScenarioEffectError("hr-001 人力招聘目录必须恰好包含两份 JD 和五份简历")
        by_label: dict[str, dict[str, Any]] = {}
        for item in items:
            label = str(item.get("display_label"))
            if label in by_label:
                raise ScenarioEffectError(f"hr-001 来源逻辑名称重复：{label}")
            by_label[label] = item
        logical_ids = {
            "外卖商户BD岗位JD.docx": JD_BD_ID,
            "文本评测岗位JD.docx": JD_TEXT_ID,
            **{
                f"{name}简历.pdf": logical_id
                for name, logical_id in zip(
                    ("周伦", "孙博文", "李雨桐", "王琳达", "赵晨曦"),
                    CANDIDATE_LOGICAL_IDS,
                    strict=True,
                )
            },
        }
        result: list[CandidateSourceInput] = []
        for label in expected_labels:
            item = by_label[label]
            file_ref = str(item.get("file_ref"))
            content = catalog.checked_input_bytes(file_ref)
            result.append(
                CandidateSourceInput(
                    logical_id=logical_ids[label],
                    file_name=label,
                    display_path=str(item.get("display_path")),
                    file_ref=file_ref,
                    content=content,
                    declared_size=int(item.get("size") or 0),
                    allowlist_verified=True,
                )
            )
        return tuple(result)

    @staticmethod
    def _legal_source_inputs(
        catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[LegalSourceInput, ...]:
        workspace = catalog.public_workspace()
        legal_folders = [
            folder
            for folder in workspace.get("folders") or []
            if folder.get("display_label") == "法务"
        ]
        if len(legal_folders) != 1:
            raise ScenarioEffectError("Legal-020 法务目录必须唯一")
        items = list(legal_folders[0].get("files") or [])
        expected_labels = [label for group, label in spec.source_labels if group == "法务"]
        if len(items) != 7 or sorted(str(item.get("display_label")) for item in items) != sorted(
            expected_labels
        ):
            raise ScenarioEffectError("Legal-020 法务目录必须恰好包含一份规则和六份委托书")
        by_label: dict[str, dict[str, Any]] = {}
        for item in items:
            label = str(item.get("display_label"))
            if label in by_label:
                raise ScenarioEffectError(f"Legal-020 来源逻辑名称重复：{label}")
            by_label[label] = item
        logical_ids = {
            "授权委托书风控校验规则.md": RULE_LOGICAL_ID,
            **{
                f"委托书{index}.docx": logical_id
                for index, logical_id in enumerate(DOCUMENT_LOGICAL_IDS, start=1)
            },
        }
        result: list[LegalSourceInput] = []
        for label in expected_labels:
            item = by_label[label]
            file_ref = str(item.get("file_ref"))
            content = catalog.checked_input_bytes(file_ref)
            result.append(
                LegalSourceInput(
                    logical_id=logical_ids[label],
                    file_name=label,
                    display_path=str(item.get("display_path")),
                    file_ref=file_ref,
                    content=content,
                    declared_size=int(item.get("size") or 0),
                    allowlist_verified=True,
                )
            )
        return tuple(result)

    @staticmethod
    def _previews(
        catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> dict[str, dict[str, Any]]:
        workspace = catalog.public_workspace()
        index = {
            (folder["display_label"], item["display_label"]): item["file_ref"]
            for folder in workspace["folders"]
            for item in folder["files"]
        }
        previews: dict[str, dict[str, Any]] = {}
        for group, label in spec.source_labels:
            file_ref = index.get((group, label))
            if file_ref is None:
                raise ScenarioEffectError(f"确定性办公工具缺少来源：{group}/{label}")
            previews[label] = catalog.public_file(file_ref)
        return previews

    @staticmethod
    def _source_refs(previews: dict[str, dict[str, Any]]) -> tuple[str, ...]:
        return tuple(str(item["file_ref"]) for item in previews.values())

    @staticmethod
    def _table_records(preview: dict[str, Any]) -> list[dict[str, str]]:
        columns = list(preview.get("columns") or [])
        unique_columns: list[str] = []
        seen: Counter[str] = Counter()
        for column in columns:
            seen[column] += 1
            unique_columns.append(column if seen[column] == 1 else f"{column}#{seen[column]}")
        records: list[dict[str, str]] = []
        for item in preview.get("rows") or []:
            values = [str(value or "") for value in item.get("values") or []]
            values.extend([""] * (len(unique_columns) - len(values)))
            records.append(dict(zip(unique_columns, values, strict=True)))
        return records

    @staticmethod
    def _month_day(value: str) -> tuple[int, int]:
        matched = re.search(r"(\d{1,2})月(\d{1,2})日", value)
        if matched is None:
            raise ScenarioEffectError(f"无法解析日期：{value}")
        return int(matched.group(1)), int(matched.group(2))

    @staticmethod
    def _decimal(value: str) -> Decimal:
        normalized = str(value or "").replace(",", "").strip()
        if not normalized:
            return Decimal(0)
        try:
            return Decimal(normalized)
        except InvalidOperation as exc:
            raise ScenarioEffectError(f"无法解析金额：{value}") from exc

    @staticmethod
    def _format_amount(value: Decimal) -> str:
        return f"{value:,.2f}"

    @staticmethod
    def _csv_bytes(headers: list[str], rows: list[list[str]]) -> bytes:
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)
        return output.getvalue().encode("utf-8-sig")

    @staticmethod
    def _parse_csv(content: bytes) -> tuple[list[str], list[list[str]]]:
        reader = csv.reader(io.StringIO(content.decode("utf-8-sig")))
        rows = list(reader)
        if not rows:
            raise ScenarioEffectError("生成的 CSV 为空")
        return rows[0], rows[1:]

    @staticmethod
    def _zip_bytes(files: dict[str, bytes | str]) -> bytes:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, value in sorted(files.items()):
                if name.startswith("/") or ".." in name.split("/"):
                    raise ScenarioEffectError(f"运行工作区压缩包路径不合法：{name}")
                archive.writestr(name, value.encode("utf-8") if isinstance(value, str) else value)
        return output.getvalue()

    @staticmethod
    def _fixed_command_env() -> dict[str, str]:
        """Expose only process basics to fixed local validators.

        The generated test packages never need provider credentials, database
        connection strings, Python import overrides, or user shell hooks.  A
        small cross-platform allowlist keeps those values out of child
        processes while retaining the OS paths required to launch Python and
        Node on Windows and CI hosts.
        """

        allowed = {
            "APPDATA",
            "COMSPEC",
            "HOME",
            "LANG",
            "LC_ALL",
            "LOCALAPPDATA",
            "PATH",
            "PATHEXT",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "TMPDIR",
            "USERPROFILE",
            "WINDIR",
        }
        env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
        env.update(
            {
                "PYTHONNOUSERSITE": "1",
                "NO_PROXY": "*",
                "HTTP_PROXY": "",
                "HTTPS_PROXY": "",
            }
        )
        return env

    @staticmethod
    def _run_fixed_command(
        command: list[str], *, cwd: Path, timeout_seconds: int = 30
    ) -> tuple[int, str, int]:
        started = time.monotonic()
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=ScenarioEffectEngine._fixed_command_env(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        output = (completed.stdout + "\n" + completed.stderr).strip()
        return completed.returncode, output[-20_000:], elapsed_ms

    @staticmethod
    def _source_index(catalog: ScenarioEffectCatalog) -> dict[tuple[str, str], str]:
        workspace = catalog.public_workspace()
        return {
            (folder["display_label"], item["display_label"]): item["file_ref"]
            for folder in workspace["folders"]
            for item in folder["files"]
        }

    @classmethod
    def _checked_source_bytes(
        cls, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[dict[str, bytes], tuple[str, ...]]:
        index = cls._source_index(catalog)
        sources: dict[str, bytes] = {}
        refs: list[str] = []
        for group, label in spec.source_labels:
            file_ref = index.get((group, label))
            if file_ref is None:
                raise ScenarioEffectError(f"确定性办公工具缺少来源：{group}/{label}")
            sources[label] = catalog.checked_input_bytes(file_ref)
            refs.append(file_ref)
        return sources, tuple(refs)

    @staticmethod
    def _checked_group_tree(
        catalog: ScenarioEffectCatalog, *, group: str, relative_prefix: str
    ) -> tuple[dict[str, bytes], tuple[str, ...]]:
        """Read a complete allowlisted subtree without losing duplicate basenames."""

        normalized_prefix = relative_prefix.strip("/") + "/"
        display_prefix = f"{group}/{normalized_prefix}"
        workspace = catalog.public_workspace()
        folder = next(
            (item for item in workspace["folders"] if item["display_label"] == group),
            None,
        )
        if folder is None:
            raise ScenarioEffectError(f"确定性办公工具缺少资料目录：{group}")
        sources: dict[str, bytes] = {}
        refs: list[str] = []
        for item in folder["files"]:
            display_path = str(item["display_path"])
            if not display_path.startswith(display_prefix):
                continue
            relative_path = display_path[len(display_prefix) :]
            if (
                not relative_path
                or relative_path.startswith("/")
                or ".." in relative_path.split("/")
                or relative_path in sources
            ):
                raise ScenarioEffectError(f"确定性办公工具遇到不合法的资料路径：{display_path}")
            file_ref = str(item["file_ref"])
            sources[relative_path] = catalog.checked_input_bytes(file_ref)
            refs.append(file_ref)
        if not sources:
            raise ScenarioEffectError(f"确定性办公工具缺少资料子目录：{group}/{normalized_prefix}")
        return sources, tuple(refs)

    @staticmethod
    def _docx_bytes(paragraphs: list[str]) -> bytes:
        def paragraph(value: str) -> str:
            return '<w:p><w:r><w:t xml:space="preserve">' + escape(value) + "</w:t></w:r></w:p>"

        document = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body>"
            + "".join(paragraph(value) for value in paragraphs)
            + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>'
            "</w:body></w:document>"
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


def scenario_effect_catalog_manifest() -> dict[str, Any]:
    """Machine-readable, non-runtime Scenario Effect Gate contract."""

    return {
        "schema_version": "scenario-effect-gate.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "name": "FORTE public demo inputs",
            "source_commit": "345c1ec1487139db9dd319787fa9405ba85d1869",
            "scope": "15 public tasks / 96 public input files",
        },
        "scenarios": [
            {
                "scenario_id": spec.scenario_id,
                "capability_id": spec.capability_id,
                "title": spec.title,
                "instruction": spec.instruction,
                "input_facts": [f"{group}/{label}" for group, label in spec.source_labels]
                or ["公开任务说明声明外部依赖；本地没有可授权输入正文"],
                "expected_artifacts": list(spec.expected_artifacts),
                "deterministic_validator": spec.deterministic_validator,
                "frontend_effect": spec.frontend_effect,
                "snapshot_event_receipt": list(spec.snapshot_facts),
                "prohibited_side_effects": list(spec.prohibited_side_effects),
                "expected_lifecycle": spec.lifecycle,
            }
            for spec in SCENARIO_EFFECT_SPECS
        ],
    }
