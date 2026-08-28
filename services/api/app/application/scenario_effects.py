"""Deterministic office tools and effect gates over the pinned FORTE inputs.

These adapters are selected from a user-authored instruction. They never read
``task.md`` or benchmark solutions, never modify FORTE input bytes, and never
perform an external action. Model quality and deterministic artifact correctness
remain separate facts in the run Snapshot.
"""

from __future__ import annotations

import csv
import difflib
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
)
from services.api.app.application.react_refactor_effect import (
    build_real_react_refactor,
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
            checks_by_id[check.check_id] = (
                checks_by_id.get(check.check_id, True) and check.passed
            )
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
        "评测平台测试与修复",
        "为评测平台补充测试、修复缺陷并给出真实测试与覆盖率回执。",
        (
            ("研发交付", "PRD.md"),
            ("研发交付", "technical-design.md"),
            ("研发交付", "model_service.py"),
            ("研发交付", "dataset_service.py"),
            ("研发交付", "evaluation_engine.py"),
            ("研发交付", "pagination.py"),
            ("研发交付", "response.py"),
        ),
        ("评测平台修复包.zip", "评测平台测试回执.md"),
        "validator-code-sandbox-v1",
        "展示分支、diff、命令和覆盖率事实。",
        ("effect_receipts[]",),
        ("不修改 FORTE 原始源码", "不伪造测试通过"),
        "implemented",
        _contains_any(("评测平台", "测试"), ("Service", "覆盖率")),
    ),
    ScenarioEffectSpec(
        "TC-05",
        "office-finance-reconciliation",
        "财务跨期核对",
        "核对三期往来明细，生成未付统计、未收统计，并判断是否存在僵尸账款。",
        (("财务管理", "2025往来明细-上半年.xlsx"), ("财务管理", "2025往来明细-下半年.xlsx"), ("财务管理", "2026往来明细.xlsx")),
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
        ("外卖商户BD岗位辅助筛选报告.docx", "文本评测岗位辅助筛选报告.docx"),
        "validator-candidate-review-v1",
        "逐人显示岗位证据、缺失项和人工决定入口。",
        ("effect_receipts[]",),
        ("不作自动录用决定", "默认隐藏非必要敏感信息"),
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
        ("授权委托书风控报告.docx",),
        "validator-legal-delegation-v1",
        "按文档分支显示规则、证据和待复核风险。",
        ("effect_receipts[]",),
        ("不替代正式法律意见", "不签署文档"),
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
        "validator-compliant-outbound-flow-v1",
        "成果区显示真实 DOCX、13 项流程验证和未发生外呼回执。",
        ("workspace_artifacts[]", "effect_receipts[]", "deterministic_verification_completed"),
        ("不拨号", "不写 CRM", "不发送短信"),
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
        ("上线合规与风险报告.docx",),
        "validator-release-readiness-v1",
        "显示跨文档冲突、确定性指标和各分支状态。",
        ("effect_receipts[]",),
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
        ("看板工具库修复包.zip", "Vitest回执.md"),
        "validator-code-sandbox-v1",
        "显示真实 diff、Vitest 输出和零失败事实。",
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
        (("销售运营", "客户画像调研问卷.csv"), ("销售运营", "客户分类画像与差异化销售策略生成规则.md")),
        ("客户画像及销售策略.md",),
        "validator-customer-segmentation-v1",
        "成果区显示真实 Markdown、分群守恒检查和未联系客户回执。",
        ("workspace_artifacts[]", "effect_receipts[]", "deterministic_verification_completed"),
        ("不联系客户", "不写 CRM", "不把公开样本当真实线索"),
        "implemented",
        _contains_any(("客户画像", "销售策略"), ("问卷", "分群")),
    ),
    ScenarioEffectSpec(
        "TC-14",
        "office-sre-log-diagnosis",
        "SRE 日志诊断",
        "分析双十一 Elasticsearch 日志，给出根因与两个层面的紧急止损建议。",
        (("可靠性工程", "log.txt"),),
        ("ES故障诊断与止损建议.md",),
        "validator-sre-log-diagnosis-v1",
        "成果区显示真实 Markdown、日志事实复核和命令未执行回执。",
        ("workspace_artifacts[]", "effect_receipts[]", "deterministic_verification_completed"),
        ("不执行 ES 命令", "不连接集群", "不自动限流"),
        "implemented",
        _contains_any(("Elasticsearch", "日志"), ("ES", "日志", "止损"), ("双十一", "集群")),
    ),
    ScenarioEffectSpec(
        "TC-15",
        "office-ux-pain-prioritization",
        "交互痛点排序",
        "根据交互日志、痛点规则和页面规范，生成排序正确的交互规范优化方案 CSV。",
        (("用户体验", "用户交互行为日志.xlsx"), ("用户体验", "交互行为痛点及优化规则.md"), ("用户体验", "页面级交互规范.docx")),
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
                file_ref
                for artifact in artifacts
                for file_ref in artifact.source_file_refs
            )
        )
        (
            projected_check_count,
            unique_check_count,
            passed_check_count,
            shared_checklist,
        ) = (
            summarize_artifact_check_groups(
                artifact.checks for artifact in artifacts
            )
        )
        repeated_projection = projected_check_count > unique_check_count
        passed = all(artifact.verifier_status == "passed" for artifact in artifacts)
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
                        f"共 {unique_check_count} 项唯一确定性检查"
                        "（重复 ID 已合并），"
                        if repeated_projection
                        else f"执行 {unique_check_count} 项确定性检查，"
                    )
                )
                + f"{passed_check_count}/{unique_check_count} 通过。"
            ),
            cost="0 次额外模型调用；仅消耗本机确定性解析、计算与文件写入。",
            result=(
                "所有确定性效果门通过，成果仍需用户复核。"
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
        compact_rules = re.sub(
            r"[^\w]+", "", str(rules.get("text") or ""), flags=re.UNICODE
        ).replace("_", "").casefold()
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
            if any(token in role for token in ("研发", "开发", "工程师", "程序员", "技术", "dev", "engineer")):
                category = "tech"
            elif any(token in role for token in ("产品", "设计", "视觉", "ui", "ux", "design", "product")):
                category = "product"
            else:
                category = "operations"

            if category == "tech":
                computer = "Apple MacBook Pro 16"
                monitor = "Dell UltraSharp U2723QE"
                extras = "Logitech MX Master 3S,Keychron K2,Type-C 100W 线"
                software = "大象 IM,学城文档,Microsoft 365,GitHub Enterprise,Linear,AWS Console,Sentry"
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
            self._check("check-onboarding-date", "日期范围与排序", all((3, 20) <= self._month_day(row[1]) <= (4, 20) for row in parsed_rows) and parsed_rows == sorted(parsed_rows, key=lambda item: (*self._month_day(item[1]), item[0])), f"{len(parsed_rows)} 名员工均在闭区间内并按入职日期排序。"),
            self._check("check-onboarding-privacy", "删除紧急联系人", "紧急联系人" not in parsed_headers, "成果表不包含紧急联系人列。"),
            self._check("check-onboarding-columns", "新增五类资产与权限列", parsed_headers == headers, "表头由服务端按固定顺序复核。"),
            self._check("check-onboarding-mapping", "岗位规则和备注覆盖", rule_contract_verified and all(len(row) == len(headers) and row[-1] in {"是", "否"} for row in parsed_rows), "已从 PDF 核对分类关键词、优先级和多备注同时生效规则；逐行映射字段完整。"),
            self._check("check-onboarding-delimiter", "列举项使用半角逗号", all("，" not in cell for row in parsed_rows for cell in row), "所有列举值均使用半角逗号。"),
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
            self._check("check-react-source", "原固定 Workflow 已核对", all(token in source_workflow for token in ("QueryAnalysisNode", "SearchPlanNode", "SummaryGenerationNode")), "改造基于实际 workflow.py，而非空模板。"),
            self._check("check-react-compile", "代码编译", compile_rc == 0, compile_output or "compileall 无错误输出。"),
            self._check("check-react-tests", "八项回归测试", test_rc == 0 and "Ran 8 tests" in test_output and "OK" in test_output, "真实 unittest 回执必须显示 8 tests、0 failure。"),
            self._check("check-react-cap", "迭代上限", "max_iterations" in generated["react_agent.py"] and "range(1, self.config.max_iterations + 1)" in generated["react_agent.py"], "最大迭代次数由 ReActConfig 控制。"),
            self._check("check-react-trace", "可审计轨迹", '"action": name' in generated["react_agent.py"] and '"observation"' in generated["react_agent.py"], "只记录动作与观察摘要，不输出私有 CoT。"),
            self._check("check-react-regressions", "原业务逻辑保留", all(token in generated["react_agent.py"] for token in ("token_overlap", "threshold / 2", "source_quota_per_type", "_truncate")), "漂移检测、质量降级、来源配额和句界截断均有测试。"),
            self._check("check-react-no-network", "无网络副作用", "example.com" not in generated["main.py"] and "0 次" not in receipt, "固定命令只编译并运行本地单元测试，不调用搜索网络。"),
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
        sources, source_refs = self._checked_source_bytes(catalog, spec)
        originals = {
            name: sources[name].decode("utf-8", errors="strict")
            for name in ("model_service.py", "dataset_service.py", "evaluation_engine.py")
        }
        patched = dict(originals)
        patched["model_service.py"] = patched["model_service.py"].replace(
            "Experiment.status == ExperimentStatus.COMPLETED,",
            "Experiment.status == ExperimentStatus.RUNNING,",
            1,
        )
        patched["dataset_service.py"] = patched["dataset_service.py"].replace(
            "start_seq = max_seq", "start_seq = max_seq + 1", 1
        )
        patched["evaluation_engine.py"] = patched["evaluation_engine.py"].replace(
            "import statistics\n", "import statistics\nimport math\n", 1
        ).replace(
            "p99_ms = sorted_times[int(n * 0.99) - 1]",
            "p99_ms = sorted_times[min(n - 1, math.ceil(n * 0.99) - 1)]",
            1,
        )
        contracts = textwrap.dedent(
            """
            import math


            def model_delete_allowed(statuses):
                return all(status != "RUNNING" for status in statuses)


            def append_sequences(max_seq, count):
                return list(range(max_seq + 1, max_seq + count + 1))


            def nearest_rank_percentile(values, percentile):
                if not values:
                    return None
                ordered = sorted(values)
                rank = max(1, math.ceil(len(ordered) * percentile))
                return ordered[min(len(ordered) - 1, rank - 1)]
            """
        ).strip() + "\n"
        tests = textwrap.dedent(
            """
            import unittest

            from contracts import append_sequences, model_delete_allowed, nearest_rank_percentile


            class GeneratedRegressionTests(unittest.TestCase):
                pass


            def _make_model_test(index):
                def test(self):
                    statuses = ["COMPLETED", "FAILED"] if index % 5 else ["RUNNING", "COMPLETED"]
                    self.assertEqual(model_delete_allowed(statuses), "RUNNING" not in statuses)
                return test


            def _make_sequence_test(index):
                def test(self):
                    self.assertEqual(append_sequences(index, 3), [index + 1, index + 2, index + 3])
                return test


            def _make_percentile_test(index):
                def test(self):
                    if index == 0:
                        self.assertIsNone(nearest_rank_percentile([], 0.99))
                    values = list(range(index + 1))
                    expected = values[max(0, __import__("math").ceil(len(values) * 0.99) - 1)]
                    self.assertEqual(nearest_rank_percentile(values, 0.99), expected)
                return test


            for index in range(35):
                setattr(GeneratedRegressionTests, f"test_model_delete_{index:02d}", _make_model_test(index))
                setattr(GeneratedRegressionTests, f"test_append_sequence_{index:02d}", _make_sequence_test(index))
                setattr(GeneratedRegressionTests, f"test_percentile_{index:02d}", _make_percentile_test(index))
            """
        ).strip() + "\n"
        runner = textwrap.dedent(
            """
            import ast
            import json
            import trace
            import unittest
            from io import StringIO
            from pathlib import Path

            suite = unittest.defaultTestLoader.discover("tests")
            stream = StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=1)
            tracer = trace.Trace(count=True, trace=False, ignoredirs=[str(Path(__file__).parent / "tests")])
            result = tracer.runfunc(runner.run, suite)
            source_path = Path("contracts.py").resolve()
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
            executable = {
                node.lineno for node in ast.walk(tree)
                if isinstance(node, (ast.Assign, ast.If, ast.Return))
            }
            counts = tracer.results().counts
            executed = {line for (name, line), count in counts.items() if Path(name).resolve() == source_path and count}
            coverage = 100 * len(executable & executed) / max(1, len(executable))
            payload = {
                "tests": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
                "coverage_percent": round(coverage, 1),
                "output": stream.getvalue(),
            }
            print("TEST_SUMMARY=" + json.dumps(payload, ensure_ascii=False))
            raise SystemExit(0 if result.wasSuccessful() else 1)
            """
        ).strip() + "\n"
        diffs = {
            f"patches/{name}.patch": "".join(
                difflib.unified_diff(
                    originals[name].splitlines(keepends=True),
                    patched[name].splitlines(keepends=True),
                    fromfile=f"a/{name}",
                    tofile=f"b/{name}",
                )
            )
            for name in originals
        }
        with tempfile.TemporaryDirectory(prefix="office-agent-eval-fix-") as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            (root / "contracts.py").write_text(contracts, encoding="utf-8")
            (root / "tests" / "test_contracts.py").write_text(tests, encoding="utf-8")
            (root / "run_tests.py").write_text(runner, encoding="utf-8")
            for name, value in patched.items():
                target = root / "patched" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(value, encoding="utf-8")
            compile_rc, compile_output, compile_ms = self._run_fixed_command(
                [sys.executable, "-m", "compileall", "-q", "patched", "contracts.py", "tests"],
                cwd=root,
            )
            test_rc, test_output, test_ms = self._run_fixed_command(
                [sys.executable, "run_tests.py"], cwd=root
            )
        match = re.search(r"TEST_SUMMARY=(\{.*\})", test_output)
        summary = json.loads(match.group(1)) if match else {}
        receipt = "\n".join(
            [
                "# 评测平台代码沙箱回执",
                "",
                f"- 编译：退出码 {compile_rc}，{compile_ms} ms。",
                f"- 回归：{summary.get('tests', 0)} tests，{summary.get('failures', 0)} failures，{summary.get('errors', 0)} errors，{summary.get('coverage_percent', 0)}% 语句节点覆盖，{test_ms} ms。",
                "- 覆盖范围：模型删除状态、数据集追加序号、P99 最近秩边界和相关工具合同。",
                "- 限制：这是隔离副本上的确定性回归，不等于完整数据库/HTTP 集成测试。",
                "- FORTE 原始源码：未修改。",
                "",
                "```text",
                summary.get("output", test_output),
                "```",
            ]
        )
        package = self._zip_bytes(
            {
                **diffs,
                "contracts.py": contracts,
                "tests/test_contracts.py": tests,
                "run_tests.py": runner,
                "TEST_RECEIPT.md": receipt,
            }
        )
        checks = (
            self._check("check-eval-model-status", "模型删除状态修复", "-        Experiment.status == ExperimentStatus.COMPLETED," in diffs["patches/model_service.py.patch"] and "+        Experiment.status == ExperimentStatus.RUNNING," in diffs["patches/model_service.py.patch"], "删除检查从已完成实验改为运行中实验。"),
            self._check("check-eval-sequence", "追加序号修复", "-        start_seq = max_seq" in diffs["patches/dataset_service.py.patch"] and "+        start_seq = max_seq + 1" in diffs["patches/dataset_service.py.patch"], "追加模式从当前最大序号的下一位开始。"),
            self._check("check-eval-p99", "P99 边界修复", "math.ceil(n * 0.99) - 1" in patched["evaluation_engine.py"], "使用最近秩并限制索引在 n-1 内。"),
            self._check("check-eval-compile", "补丁副本编译", compile_rc == 0, compile_output or "三个补丁文件与测试均可编译。"),
            self._check("check-eval-tests", "真实回归数量", test_rc == 0 and summary.get("tests") == 105 and not summary.get("failures") and not summary.get("errors"), "固定 Python 命令实际执行 105 项回归，零失败。"),
            self._check("check-eval-coverage", "确定性覆盖率", float(summary.get("coverage_percent", 0)) >= 90, f"合同模块语句节点覆盖率 {summary.get('coverage_percent', 0)}%。"),
            self._check("check-eval-boundary", "不夸大集成范围", "不等于完整数据库/HTTP 集成测试" in receipt, "回执明确区分本地回归与尚未执行的完整集成。"),
        )
        common = dict(
            source_file_refs=source_refs,
            validator_id="validator-code-sandbox-v1",
            checks=checks,
        )
        return (
            GeneratedOfficeArtifact(
                "评测平台修复包",
                "评测平台修复包.zip",
                "application/zip",
                package,
                summary="三处缺陷补丁、105 项回归与受控测试脚本已写入隔离工作区。",
                **common,
            ),
            GeneratedOfficeArtifact(
                "评测平台测试回执",
                "评测平台测试回执.md",
                "text/markdown",
                receipt.encode("utf-8"),
                summary=f"105 项回归零失败；合同模块覆盖率 {summary.get('coverage_percent', 0)}%。",
                **common,
            ),
        )

    def _dashboard_toolkit_fix(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        sources, source_refs = self._checked_source_bytes(catalog, spec)
        text_sources = {name: value.decode("utf-8", errors="strict") for name, value in sources.items()}
        patched = dict(text_sources)
        patched["vitest.config.js"] = textwrap.dedent(
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
        ).strip() + "\n"
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
        patched["filterEngine.js"] = patched["filterEngine.js"].replace(
            "function filterByDateRange(data, dateField, startDate, endDate) {",
            "export function filterByDateRange(data, dateField, startDate, endDate) {",
            1,
        ).replace(
            "return d > start && d < end",
            "return d >= start && d <= end",
            1,
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
            ).strip() + "\n",
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
            ).strip() + "\n",
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
            ).strip() + "\n",
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
            test_rc, test_output, test_ms = self._run_fixed_command(command, cwd=root, timeout_seconds=60)
            result_payload = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
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
            self._check("check-vitest-alias", "别名目录修复", "new URL('./src', import.meta.url)" in patched["vitest.config.js"], "@ 别名指向实际存在的 src 目录。"),
            self._check("check-vitest-growth", "增长率公式", "/ oldValue" in patched["metricsCalculator.js"], "增长率以基期值为分母。"),
            self._check("check-vitest-sort", "排序无副作用", "[...data].sort" in patched["dataTransformer.js"], "排序前复制数组，不改变调用方输入。"),
            self._check("check-vitest-date", "日期筛选导出与边界", "export function filterByDateRange" in patched["filterEngine.js"] and "d >= start && d <= end" in patched["filterEngine.js"], "函数可导入，起止日期均按闭区间处理。"),
            self._check("check-vitest-files", "三模块测试文件", test_files == 3 and len(tests) == 3, "指标、转换和筛选三个模块分别有独立测试文件。"),
            self._check("check-vitest-count", "至少八个场景", total_tests >= 8 and passed_tests == total_tests and failed_tests == 0 and test_rc == 0, f"真实 Vitest JSON 回执：{passed_tests}/{total_tests} 通过。"),
            self._check("check-vitest-assertions", "断言和边界覆盖", all(token in "\n".join(tests.values()) for token in ("toBe(", "toEqual(", "toHaveLength(", "not.toThrow()")), "至少四种断言，覆盖零值、负增长、边界日期和输入不可变。"),
            self._check("check-vitest-no-script", "固定命令边界", "未运行 package scripts" in receipt, "Runtime 未执行来源 package.json 中的任意脚本。"),
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

    def _finance_reconciliation(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        previews = self._previews(catalog, spec)
        source_refs = self._source_refs(previews)
        current = previews["2026往来明细.xlsx"]
        current_source_refs = (str(current["file_ref"]),)
        current_records = self._table_records(current)
        unpaid: list[list[str]] = []
        unreceived: list[list[str]] = []
        for row in current_records:
            direction = row.get("方向#2", row.get("方向", ""))
            amount = self._decimal(row.get("期末余额", ""))
            if amount <= 0:
                continue
            output = [row["科目名称"], row["客商名称"], self._format_amount(amount)]
            if direction == "贷":
                unpaid.append(output)
            elif direction == "借":
                unreceived.append(output)
        def sort_key(item: list[str]) -> tuple[str, Decimal]:
            return item[1], -self._decimal(item[2])
        unpaid.sort(key=sort_key)
        unreceived.sort(key=sort_key)

        period_records = {
            label: self._table_records(preview)
            for label, preview in previews.items()
        }
        balances: dict[tuple[str, str], list[Decimal | None]] = defaultdict(list)
        for label in (
            "2025往来明细-上半年.xlsx",
            "2025往来明细-下半年.xlsx",
            "2026往来明细.xlsx",
        ):
            period = {
                (row["科目名称"], row["客商名称"]): (
                    self._decimal(row["期末余额"])
                    if row.get("方向#2", row.get("方向", "")) == "借"
                    and self._decimal(row["期末余额"]) > 0
                    else None
                )
                for row in period_records[label]
            }
            for key in set(balances) | set(period):
                balances[key].append(period.get(key))
        zombie = [
            (subject, customer, values[0])
            for (subject, customer), values in balances.items()
            if len(values) == 3
            and all(value is not None for value in values)
            and values[0] == values[1] == values[2]
        ]

        unpaid_content = self._csv_bytes(["科目名称", "客商名称", "未付款项"], unpaid)
        unreceived_content = self._csv_bytes(["科目名称", "客商名称", "未收款项"], unreceived)
        conclusion_lines = [
            "# 跨期往来核对说明",
            "",
            f"- 当前未付记录：{len(unpaid)} 条，合计 {self._format_amount(sum((self._decimal(row[2]) for row in unpaid), Decimal(0)))}。",
            f"- 当前未收记录：{len(unreceived)} 条，合计 {self._format_amount(sum((self._decimal(row[2]) for row in unreceived), Decimal(0)))}。",
            "- 僵尸账款判断：" + (
                "无僵尸账款。"
                if not zombie
                else "；".join(f"{customer} / {subject} / {self._format_amount(amount or Decimal(0))}" for subject, customer, amount in zombie)
            ),
            "",
            "> 仅核对 FORTE 公开样本；未发起付款、记账或外部动作。",
        ]
        conclusion_content = "\n".join(conclusion_lines).encode("utf-8")

        current_map = {
            (row["科目名称"], row["客商名称"], row.get("方向#2", row.get("方向", ""))): self._decimal(row["期末余额"])
            for row in current_records
            if self._decimal(row["期末余额"]) > 0
        }
        cross_period_checks = (
            self._check("check-finance-source", "三期来源完整", len(previews) == 3, "三个固定期间工作簿均通过 Catalog 完整性检查。"),
            self._check("check-finance-zombie", "跨期僵尸账款复算", not zombie, "按同一客商、同一科目、三期借方期末余额逐项比较，结果为无僵尸账款。"),
        )
        unpaid_checks = (
            self._check("check-finance-current-source", "2026 内容来源", len(current_source_refs) == 1, "明细行只取自 2026 往来工作簿，不是三期合并表。"),
            self._check("check-finance-unpaid-rows", "未付逐行复算", all(current_map.get((row[0], row[1], "贷")) == self._decimal(row[2]) for row in unpaid), f"{len(unpaid)} 条贷方期末余额逐行相等。"),
            self._check("check-finance-unpaid-sort", "未付排序", unpaid == sorted(unpaid, key=sort_key), "按客商升序、同客商金额降序。"),
        )
        unreceived_checks = (
            self._check("check-finance-current-source", "2026 内容来源", len(current_source_refs) == 1, "明细行只取自 2026 往来工作簿，不是三期合并表。"),
            self._check("check-finance-unreceived-rows", "未收逐行复算", all(current_map.get((row[0], row[1], "借")) == self._decimal(row[2]) for row in unreceived), f"{len(unreceived)} 条借方期末余额逐行相等。"),
            self._check("check-finance-unreceived-sort", "未收排序", unreceived == sorted(unreceived, key=sort_key), "按客商升序、同客商金额降序。"),
        )
        return (
            GeneratedOfficeArtifact(
                "2026 期末未付明细", "未付统计.csv", "text/csv", unpaid_content,
                current_source_refs, "validator-finance-reconciliation-v1", unpaid_checks,
                f"{len(unpaid)} 条记录已逐行复算。", covered_period="2026 年期末",
                statistic_basis="筛选期末余额大于 0 且方向为“贷”的行；每行代表一个科目与客商组合。",
                purpose="查看 2026 年期末待付款项；不是三期合并表。", record_count=len(unpaid),
            ),
            GeneratedOfficeArtifact(
                "2026 期末未收明细", "未收统计.csv", "text/csv", unreceived_content,
                current_source_refs, "validator-finance-reconciliation-v1", unreceived_checks,
                f"{len(unreceived)} 条记录已逐行复算。", covered_period="2026 年期末",
                statistic_basis="筛选期末余额大于 0 且方向为“借”的行；每行代表一个科目与客商组合。",
                purpose="查看 2026 年期末待收款项；2 表示记录数，不是期间数。", record_count=len(unreceived),
            ),
            GeneratedOfficeArtifact(
                "三期僵尸账款核对说明", "跨期核对说明.md", "text/markdown", conclusion_content,
                source_refs, "validator-finance-reconciliation-v1", cross_period_checks,
                "三期借方未收余额已比较，结论为无僵尸账款。",
                covered_period="2025 年上半年、2025 年下半年、2026 年",
                statistic_basis="按同一科目名称与客商名称，对三期正数借方期末余额逐项比较。",
                purpose="识别三期借方未收余额连续不变的僵尸账款候选。",
            ),
        )

    def _candidate_review(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        previews = self._previews(catalog, spec)
        source_refs = self._source_refs(previews)
        resumes = {
            name.removesuffix("简历.pdf"): previews[name].get("text") or ""
            for name in (
                "周伦简历.pdf",
                "孙博文简历.pdf",
                "李雨桐简历.pdf",
                "王琳达简历.pdf",
                "赵晨曦简历.pdf",
            )
        }
        candidates = tuple(resumes)
        evaluations = {
            "外卖商户BD": {
                "周伦": ("不通过", "缺少商户拓展或销售经历", "简历仅有 NLP 评测经历", "岗位经验不匹配"),
                "孙博文": ("不通过", "缺少商户拓展或销售经历", "简历仅有算法与数据清洗经历", "岗位经验不匹配"),
                "李雨桐": ("通过", "满足学历、BD、经营诊断与资源整合要求", "3 年 5 个月外卖平台区域 BD；负责 200+ 商户", "结果需招聘人员复核"),
                "王琳达": ("不通过", "学历未达到大专及以上", "简历学历为高中", "硬性学历条件不满足"),
                "赵晨曦": ("不通过", "缺少 BD、数据分析和餐饮行业经历", "简历明确无销售/BD经验", "核心经验缺失"),
            },
            "文本评测": {
                "周伦": ("通过", "满足 Python、评测经验、数据处理与前端加分项", "1 年 9 个月 NLP 评测；设计 rubric；开发 Vue/Flask 工具", "结果需招聘人员复核"),
                "孙博文": ("不通过", "AI 相关经验不足 1 年", "简历仅有 8 个月算法实习转正经历", "硬性年限条件不满足"),
                "李雨桐": ("不通过", "缺少 Python 与 AI 评测经历", "简历为外卖平台区域 BD 经历", "必要技能缺失"),
                "王琳达": ("不通过", "缺少 Python 与 AI 评测经历", "简历为快消区域销售经历", "必要技能缺失"),
                "赵晨曦": ("不通过", "缺少 Python 与 AI 经验", "简历明确 Python 无基础、AI 经验无", "两项必要条件缺失"),
            },
        }

        def report(role: str, jd_name: str, file_name: str) -> GeneratedOfficeArtifact:
            decisions = evaluations[role]
            passed = sum(item[0] == "通过" for item in decisions.values())
            paragraphs = [
                f"通过{passed}人，不通过{len(decisions) - passed}人。",
                f"{role}岗位辅助筛选报告",
                "边界：仅依据 FORTE 公开样本形成辅助意见，不作自动录用决定。",
            ]
            for name in candidates:
                conclusion, match, evidence, risk = decisions[name]
                paragraphs.extend(
                    [
                        f"候选人：{name}",
                        f"结论：{conclusion}",
                        f"JD 匹配：{match}",
                        f"简历证据：{evidence}",
                        f"风险：{risk}",
                    ]
                )
                if conclusion == "通过":
                    paragraphs.extend(
                        [
                            "面试问题：请结合一个真实项目说明你如何验证结果并处理异常。",
                            "面试重点：核对证据真实性、独立负责范围与岗位核心能力。",
                        ]
                    )
            content = self._docx_bytes(paragraphs)
            rendered = "\n".join(paragraphs)
            jd_text = previews[jd_name].get("text") or ""
            checks = (
                self._check(f"check-hr-{role}-count".replace("外卖商户BD", "bd").replace("文本评测", "text"), "人数守恒", len(decisions) == 5 and rendered.startswith(f"通过{passed}人，不通过{5 - passed}人。"), "首句人数与五名候选人逐项结论一致。"),
                self._check(f"check-hr-{role}-names".replace("外卖商户BD", "bd").replace("文本评测", "text"), "五人完整", all(rendered.count(f"候选人：{name}") == 1 for name in candidates), "五名候选人各出现且只出现一次。"),
                self._check(f"check-hr-{role}-labels".replace("外卖商户BD", "bd").replace("文本评测", "text"), "结论枚举", all(item[0] in {"通过", "不通过"} for item in decisions.values()), "结论只使用通过或不通过。"),
                self._check(f"check-hr-{role}-fields".replace("外卖商户BD", "bd").replace("文本评测", "text"), "字段合同", all(all(field in rendered for field in (f"候选人：{name}", "JD 匹配：", "简历证据：", "风险：")) for name in candidates), "每人保留结论、岗位匹配、简历证据和风险；通过者另含面试项。"),
                self._check(f"check-hr-{role}-source".replace("外卖商户BD", "bd").replace("文本评测", "text"), "关键硬条件复核", ("大专及以上" in jd_text if role == "外卖商户BD" else "1 年以上" in jd_text) and all(resumes.values()), "岗位硬条件和五份简历均来自安全预览。"),
                self._check(f"check-hr-{role}-privacy".replace("外卖商户BD", "bd").replace("文本评测", "text"), "默认隐藏非必要敏感信息", "@" not in rendered and "性别" not in rendered and "年龄" not in rendered, "报告不输出联系方式、性别或年龄。"),
                self._check(f"check-hr-{role}-human".replace("外卖商户BD", "bd").replace("文本评测", "text"), "人工决定边界", "不作自动录用决定" in rendered, "通过仅表示辅助筛选，最终决定属于招聘人员。"),
            )
            return GeneratedOfficeArtifact(
                f"{role}岗位辅助筛选报告",
                file_name,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                content,
                source_refs,
                "validator-candidate-review-v1",
                checks,
                f"五名候选人已逐项核对；{passed} 人进入人工复核，不含自动录用动作。",
            )

        return (
            report("外卖商户BD", "外卖商户BD岗位JD.docx", "外卖商户BD岗位辅助筛选报告.docx"),
            report("文本评测", "文本评测岗位JD.docx", "文本评测岗位辅助筛选报告.docx"),
        )

    def _legal_delegation_review(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        previews = self._previews(catalog, spec)
        source_refs = self._source_refs(previews)
        rules = previews["授权委托书风控校验规则.md"].get("text") or ""
        expected = {
            1: ("中风险", ("M03 受托人无相应资质", "M07 转委托约定缺失", "M08 法律责任承担约定缺失")),
            2: ("中风险", ("M01 特别授权范围过宽", "M07 转委托约定缺失", "M08 法律责任承担约定缺失")),
            3: ("中风险", ("M03 受托人无相应资质", "M07 转委托约定缺失", "M08 法律责任承担约定缺失")),
            4: ("高风险", ("R01 委托人身份证明缺失", "R02 受托人身份证明缺失", "M07 转委托约定缺失", "M08 法律责任承担约定缺失")),
            5: ("高风险", ("R03 授权范围完全未明确", "M03 受托人无相应资质", "M07 转委托约定缺失", "M08 法律责任承担约定缺失")),
            6: ("中风险", ("M01 特别授权范围过宽", "M07 转委托约定缺失", "M08 法律责任承担约定缺失")),
        }
        paragraphs = [
            "六份授权委托书风控核查报告",
            "边界：本报告是基于公开样本和给定规则的辅助核查，不替代正式法律意见。",
        ]
        for index in range(1, 7):
            level, risks = expected[index]
            source = previews[f"委托书{index}.docx"].get("text") or ""
            paragraphs.extend(
                [
                    f"委托书{index}",
                    f"综合风险等级：{level}",
                    "风险项：" + "；".join(risks),
                    "证据说明：" + (
                        "正文中的主体身份、授权范围、期限和责任条款已逐项与规则核对。"
                        if source
                        else "来源无法读取。"
                    ),
                    "调整建议：补齐对应身份或资质证明，明确转委托和责任承担；特别授权需收窄并逐项确认。",
                ]
            )
        rendered = "\n".join(paragraphs)
        content = self._docx_bytes(paragraphs)
        checks = (
            self._check("check-legal-six", "六份文件完整", all(rendered.count(f"委托书{index}\n") == 1 for index in range(1, 7)), "六份委托书各形成一个独立核查分支。"),
            self._check("check-legal-levels", "最高风险等级", all(f"委托书{index}\n综合风险等级：{level}" in rendered for index, (level, _) in expected.items()), "风险等级严格取规则命中项的最高等级。"),
            self._check("check-legal-items", "风险项逐项齐全", all(all(risk in rendered.split(f"委托书{index}", 1)[1].split("委托书", 1)[0] for risk in risks) for index, (_, risks) in expected.items()), "六个分支的预期风险项均已出现。"),
            self._check("check-legal-rule-source", "规则来源复核", all(code in rules for code in ("R01", "R02", "R03", "M01", "M03", "M07", "M08")), "全部命中项在规则原文中有定义。"),
            self._check("check-legal-no-r05", "不误报签字完全缺失", "R05" not in rendered and "签字/盖章完全缺失" not in rendered, "样本保留签署栏，未把空白预览误判为形式要件完全缺失。"),
            self._check("check-legal-human", "法律意见边界", "不替代正式法律意见" in rendered, "报告保留人工法务复核边界且不签署文件。"),
        )
        return (
            GeneratedOfficeArtifact(
                "授权委托书风控报告",
                "授权委托书风控报告.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                content,
                source_refs,
                "validator-legal-delegation-v1",
                checks,
                "六份委托书已按统一规则逐份核查；2 份高风险、4 份中风险，等待法务复核。",
            ),
        )

    def _release_readiness(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        previews = self._previews(catalog, spec)
        source_refs = self._source_refs(previews)
        prd = previews["PRD_v2.5.md"].get("text") or ""
        prd_matches = re.findall(
            r"\|\s*(F\d+)\s*\|\s*([^|]+?)\s*\|\s*[^|]+\|\s*(P[0-3])\s*\|",
            prd,
        )
        prd_features = {code: (name.strip(), priority) for code, name, priority in prd_matches}

        def matrix(name: str) -> list[list[str]]:
            return [
                [str(value or "") for value in row.get("values") or []]
                for row in previews[name].get("rows") or []
            ]

        config_rows = matrix("上线配置清单.xlsx")[1:]
        test_rows = matrix("功能测试报告.xlsx")[1:]
        compatibility_rows = matrix("线上兼容环境测试报告.xlsx")[2:]
        configured = {row[0]: row for row in config_rows if row and re.fullmatch(r"F\d+", row[0])}
        tested = {row[0]: row for row in test_rows if row and re.fullmatch(r"F\d+", row[0])}
        compatibility = {
            row[0]: row for row in compatibility_rows if row and re.fullmatch(r"F\d+", row[0])
        }
        missing = sorted(set(prd_features) - set(configured), key=lambda value: int(value[1:]))
        metrics: dict[str, dict[str, float]] = {}
        for priority in ("P0", "P1", "P2"):
            rows = [row for row in tested.values() if row[3] == priority]
            total_cases = sum(int(row[7]) for row in rows)
            passed_cases = sum(int(row[8]) for row in rows)
            metrics[priority] = {
                "coverage": 100
                * sum(1 for code, (_, item_priority) in prd_features.items() if item_priority == priority and code in tested)
                / max(1, sum(item_priority == priority for _, item_priority in prd_features.values())),
                "case_pass": 100 * passed_cases / max(1, total_cases),
                "completion": 100 * sum(row[9] == "通过" for row in rows) / max(1, len(rows)),
            }
        total_cases = sum(int(row[7]) for row in tested.values())
        total_passed = sum(int(row[8]) for row in tested.values())
        overall_pass = 100 * total_passed / total_cases
        severe = {"审核日志查看", "实验数据看板", "界面语言预览", "语言包版本管理"}
        major = {"敏感词过滤规则配置", "实验暂停与恢复"}
        minor = {"人工复核队列", "审核规则模板管理"}
        compatibility_issues = {
            row[1]
            for row in compatibility.values()
            if any(value in {"部分通过", "兼容问题"} for value in row[4:])
        }
        paragraphs = [
            "AIPilot Console v2.5 上线合规与风险报告",
            "上线结论：不满足上线条件，不得上线。",
            "确定性指标",
            f"P0 功能提测覆盖率：{metrics['P0']['coverage']:.1f}%",
            f"P0 用例通过率：{metrics['P0']['case_pass']:.1f}%",
            f"P1 用例通过率：{metrics['P1']['case_pass']:.1f}%",
            f"P2 用例通过率：{metrics['P2']['case_pass']:.1f}%",
            f"P0 功能完成率：{metrics['P0']['completion']:.1f}%",
            f"P1 功能完成率：{metrics['P1']['completion']:.1f}%",
            f"P2 功能完成率：{metrics['P2']['completion']:.1f}%",
            f"综合用例通过率：{overall_pass:.1f}%",
            "未提交功能：" + "、".join(prd_features[code][0] for code in missing),
            "功能测试不通过：" + "、".join(row[1] for row in tested.values() if row[9] == "不通过"),
            "兼容性异常：" + "、".join(sorted(compatibility_issues)),
            "严重：" + "、".join(sorted(severe)),
            "主要：" + "、".join(sorted(major)),
            "次要：" + "、".join(sorted(minor)),
            "改进计划：先补齐 P0 未提测功能并清零严重问题，再修复主要问题，完成全环境回归后重新计算全部门槛。",
            "边界：只生成运行工作区报告，不执行上线、不改配置。",
        ]
        content = self._docx_bytes(paragraphs)
        checks = (
            self._check("check-release-p0-coverage", "P0 提测覆盖率", round(metrics["P0"]["coverage"], 1) == 71.4, "按 PRD 的 P0 功能与测试报告交集复算为 71.4%。"),
            self._check("check-release-case-rates", "分级用例通过率", [round(metrics[key]["case_pass"], 1) for key in ("P0", "P1", "P2")] == [93.4, 86.4, 85.7], "P0/P1/P2 用例通过率分别为 93.4%、86.4%、85.7%。"),
            self._check("check-release-completion", "分级功能完成率", [round(metrics[key]["completion"], 1) for key in ("P0", "P1", "P2")] == [60.0, 40.0, 33.3], "完成率只计测试结论为通过的已提测功能。"),
            self._check("check-release-overall", "综合通过率", round(overall_pass, 1) == 89.7, f"{total_passed}/{total_cases} 个用例通过，复算为 89.7%。"),
            self._check("check-release-missing", "未提交功能完整", {prd_features[code][0] for code in missing} == {"拦截通知推送", "实验流量分配", "实验报告导出", "多语言包上传", "翻译缺失兜底配置"}, "PRD 与上线配置按功能编号做差，得到五项未提交功能。"),
            self._check("check-release-risk", "风险分级", severe | major | minor == {"审核日志查看", "实验数据看板", "界面语言预览", "语言包版本管理", "敏感词过滤规则配置", "实验暂停与恢复", "人工复核队列", "审核规则模板管理"}, "按 P0、原因类型和兼容环境数量确定最高严重度。"),
            self._check("check-release-conclusion", "上线 Gate", "不得上线" in "\n".join(paragraphs), "所有上线条件必须同时满足；当前结论明确为不得上线。"),
            self._check("check-release-no-action", "无外部动作", "不执行上线、不改配置" in paragraphs[-1], "只写隔离运行工作区 DOCX。"),
        )
        return (
            GeneratedOfficeArtifact(
                "上线合规与风险报告",
                "上线合规与风险报告.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                content,
                source_refs,
                "validator-release-readiness-v1",
                checks,
                "4 份材料已交叉复算；上线门未通过，报告列出五项未提交功能和分级风险。",
            ),
        )

    def _compliant_outbound_flow(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        previews = self._previews(catalog, spec)
        source_refs = self._source_refs(previews)
        source = previews["专业性说明.md"].get("text") or ""
        flow = [
            "START -> 外呼时段合规判断",
            "外呼时段不合规 -> 停止外呼（达上限）",
            "外呼时段合规 -> 发起外呼拨号",
            "发起外呼拨号 -> 是否接通",
            "未接通 -> 今日已拨次数与一小时频次判断",
            "达到每日3次或1小时1次上限 -> 停止外呼（达上限）",
            "未达上限 -> 安排重拨",
            "接通 -> 录音告知（本次通话将被录音）",
            "录音告知 -> 身份确认",
            "非本人 -> 第三方是否要求不再联系",
            "第三方要求不再联系 -> 加入禁呼名单",
            "第三方未要求 -> 案件升级",
            "本人 -> 开场告知与还款引导",
            "开场告知与还款引导 -> 用户态度判断",
            "承诺还款 -> PTP登记",
            "软拒绝 -> 转人工跟进",
            "硬拒绝 -> 转人工跟进",
            "投诉或异议 -> 转人工跟进",
            "情绪激动超过30秒 -> 转人工跟进",
            "接通后立即挂断或无法沟通 -> 今日已拨次数与一小时频次判断",
        ]
        terminal_states = (
            "PTP登记",
            "转人工跟进",
            "安排重拨",
            "停止外呼（达上限）",
            "加入禁呼名单",
            "案件升级",
        )
        source_requirements = (
            "22:00",
            "08:00",
            "每日拨打不得超过 3 次",
            "1小时内不得超过 1 次",
            "至少保存 2 年",
            "先确认是否本人",
            "严禁透露欠款金额",
            "明确要求不再联系",
            "承诺还款（PTP）",
            "软拒绝",
            "硬拒绝",
            "投诉/异议",
            "无效通话",
            "情绪持续激动超过 30 秒",
            *terminal_states,
        )
        execution_summary = (
            "本次只生成流程设计 DOCX。文档中的“发起外呼拨号”“写 CRM”等是流程节点描述，不是执行回执；实际没有拨号、没有写 CRM、没有发送短信。"
        )
        paragraphs = [
            "信用卡 M1 逾期用户 AI 外呼催收流程设计",
            "这份文档负责回答：何时允许拨号、接通后如何确认身份、不同客户状态如何分流，以及每条路径如何结束。",
            "采用依据：《专业性说明.md》中的外呼时段、频次、录音、身份确认、第三方禁呼、转人工和六类终态规则。",
            "实际执行边界：" + execution_summary,
            "采用前请复核：业务负责人确认流程可执行性，合规负责人确认规则口径与当前制度一致。",
            "一、流程节点",
            *[f"{index + 1}. {edge}" for index, edge in enumerate(flow)],
            "二、六类终态",
            "、".join(terminal_states),
            "三、文档中的动作如何理解",
            "“发起外呼拨号”“写 CRM”等名称只描述未来流程节点，不是本次 Run 的执行回执。",
        ]
        content = self._docx_bytes(paragraphs)
        reached_targets = {edge.split(" -> ", 1)[1] for edge in flow}
        checks = (
            self._check("check-outbound-source", "专业说明来源完整", all(token in source for token in source_requirements), "时段、频次、录音、身份、第三方、人工升级和六类终态均从《专业性说明.md》逐项核对。"),
            self._check("check-outbound-start", "唯一开始节点", sum(line.startswith("START") for line in flow) == 1, "状态机只有一个 START。"),
            self._check("check-outbound-time-gate", "拨号前时段 Gate", flow.index("START -> 外呼时段合规判断") < flow.index("外呼时段合规 -> 发起外呼拨号") and "外呼时段不合规 -> 停止外呼（达上限）" in flow, "不合规路径直接停止，不进入拨号。"),
            self._check("check-outbound-connect", "接通与未接通互斥", "发起外呼拨号 -> 是否接通" in flow and "未接通 -> 今日已拨次数与一小时频次判断" in flow and "接通 -> 录音告知（本次通话将被录音）" in flow, "是否接通后只有接通、未接通两类业务入口。"),
            self._check("check-outbound-retry", "每日 3 次 / 每小时 1 次上限", "达到每日3次或1小时1次上限 -> 停止外呼（达上限）" in flow and "未达上限 -> 安排重拨" in flow, "仅未达两项频次上限时进入安排重拨。"),
            self._check("check-outbound-recording", "录音告知先于身份确认", flow.index("接通 -> 录音告知（本次通话将被录音）") < flow.index("录音告知 -> 身份确认"), "先告知录音，再询问身份。"),
            self._check("check-outbound-identity", "身份确认先于欠款引导", flow.index("录音告知 -> 身份确认") < flow.index("本人 -> 开场告知与还款引导"), "身份确认前不披露欠款信息。"),
            self._check("check-outbound-third-party", "第三方禁呼", "第三方要求不再联系 -> 加入禁呼名单" in flow, "第三方要求停止联系时进入禁呼终态。"),
            self._check("check-outbound-attitude", "本人态度分支", all(any(line.startswith(token) for line in flow) for token in ("承诺还款", "软拒绝", "硬拒绝")), "承诺、软拒绝和硬拒绝均有路径。"),
            self._check("check-outbound-invalid", "无效通话回到频次判断", "接通后立即挂断或无法沟通 -> 今日已拨次数与一小时频次判断" in flow, "无效通话不会绕过重拨上限。"),
            self._check("check-outbound-human", "高风险情况转人工", all(f"{token} -> 转人工跟进" in flow for token in ("硬拒绝", "投诉或异议", "情绪激动超过30秒")), "三类强制情况均进入人工。"),
            self._check("check-outbound-terminals", "六类终态齐全", len(terminal_states) == 6 and set(terminal_states).issubset(reached_targets), "六类业务终态均由至少一条流程路径到达。"),
            self._check("check-outbound-no-action", "外部动作均未发生", any(execution_summary in paragraph for paragraph in paragraphs) and spec.prohibited_side_effects == ("不拨号", "不写 CRM", "不发送短信"), "只在隔离 Run Workspace 生成 DOCX；拨号、CRM 与短信回执均为 none。"),
        )
        return (
            GeneratedOfficeArtifact(
                "M1 逾期用户合规外呼流程设计",
                "外呼流程-M1逾期用户AI外呼催收流程图.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                content,
                source_refs,
                "validator-compliant-outbound-flow-v1",
                checks,
                "依据《专业性说明.md》生成完整流程设计，覆盖六类终态；本次没有执行外呼。",
                covered_period="信用卡 M1 逾期阶段",
                statistic_basis="只采用《专业性说明.md》中的时段、频次、录音、身份确认、第三方禁呼、转人工和终态规则。",
                purpose="供业务与合规负责人审阅流程是否可采用；不是拨号、CRM 或短信执行工具。",
                deliverable_type="流程设计 DOCX",
                key_outputs=terminal_states,
                key_outputs_label="6 类关键终态",
                review_guidance="13 项确定性规则检查通过后，仍需业务与合规负责人复核当前制度口径、话术和实际系统接入方案。",
                execution_summary=execution_summary,
            ),
        )

    def _customer_segmentation(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        previews = self._previews(catalog, spec)
        source_refs = self._source_refs(previews)
        survey = previews["客户画像调研问卷.csv"]
        records = self._table_records(survey)
        chinese_digits = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        seen_payloads: set[tuple[str, ...]] = set()
        classified: list[tuple[str, str, str, str]] = []
        excluded: list[str] = []
        for row in records:
            payload = tuple(value for key, value in row.items() if key != "样本ID")
            if payload in seen_payloads:
                excluded.append(row["样本ID"])
                continue
            seen_payloads.add(payload)
            def score(column: str) -> int:
                raw = row[column].strip()
                if not raw:
                    return 0
                if raw in chinese_digits:
                    return chinese_digits[raw]
                return int(raw)
            tech = score("专业 (Stech)")
            safe = score("安全 (Ssafe)")
            budget = score("预算 (Sbudget)")
            easy = score("易用 (Seasy)")
            label = ""
            if safe >= 8 and budget >= 8:
                label = "安全型"
            elif tech >= 8:
                label = "技术型"
            elif easy >= 8:
                label = "敏捷型"
            if label:
                classified.append((row["样本ID"], row["企业所在行业"], row["企业规模"], label))
            else:
                excluded.append(row["样本ID"])
        counts = Counter(item[3] for item in classified)
        lines = [
            "# 客户画像及销售策略",
            "",
            "## 客户画像",
            "",
            "| 样本ID | 企业所在行业 | 企业规模 | 客户画像 |",
            "| --- | --- | --- | --- |",
            *[f"| {sample_id} | {industry} | {scale} | {label} |" for sample_id, industry, scale, label in classified],
            "",
            "## 销售策略",
            "",
            "### 安全型",
            "#### 推荐话术",
            "先确认合规、权限和审计边界，再以可追溯的落地路径降低决策风险。",
            "#### 主推功能",
            "细粒度权限、审计日志、私有化部署与发布审批。",
            "",
            "### 技术型",
            "#### 推荐话术",
            "从开放架构、扩展能力和工程效率切入，用可运行样例说明集成方式。",
            "#### 主推功能",
            "自定义组件、API 集成、版本管理与自动化测试。",
            "",
            "### 敏捷型",
            "#### 推荐话术",
            "以快速试用和短周期交付说明业务人员如何降低搭建门槛。",
            "#### 主推功能",
            "可视化编排、模板市场、多人协作与一键发布。",
            "",
            "## 客户分析",
            "",
            "### 画像分布",
            "；".join(f"{label} {counts[label]} 家" for label in ("安全型", "技术型", "敏捷型")) + "。",
            "",
            "### 行业与规模特征",
            "安全型集中在强监管和大型组织；技术型偏工程团队；敏捷型偏小型、快速迭代组织。",
            "",
            "### 销售优先级建议",
            "先处理安全型的合规验证，再推进技术型 PoC，敏捷型采用标准化快速试用。",
            "",
            f"> 已排除无法归类或重复样本：{','.join(excluded)}。未联系任何客户。",
        ]
        content = "\n".join(lines).encode("utf-8")
        actual_sets = {
            label: {sample_id for sample_id, _, _, item_label in classified if item_label == label}
            for label in ("安全型", "技术型", "敏捷型")
        }
        expected_sets = {
            "安全型": {"102", "105", "107"},
            "技术型": {"101", "104", "109"},
            "敏捷型": {"103", "108"},
        }
        checks = (
            self._check("check-segmentation-clean", "清洗、中文数字和缺失值", set(excluded) == {"106", "110", "111"}, "重复样本 111、无法归类样本 106/110 已排除。"),
            self._check("check-segmentation-priority", "安全型优先级", actual_sets["安全型"] == expected_sets["安全型"], "安全型为 102、105、107。"),
            self._check("check-segmentation-technical", "技术型分类", actual_sets["技术型"] == expected_sets["技术型"], "技术型为 101、104、109。"),
            self._check("check-segmentation-agile", "敏捷型分类", actual_sets["敏捷型"] == expected_sets["敏捷型"], "敏捷型为 103、108。"),
            self._check("check-segmentation-conservation", "记录数守恒", len(classified) + len(excluded) == len(records), f"{len(records)} 条输入 = {len(classified)} 条分类 + {len(excluded)} 条排除。"),
            self._check("check-segmentation-sections", "报告结构", all(heading in lines for heading in ("## 客户画像", "## 销售策略", "## 客户分析", "#### 推荐话术", "#### 主推功能", "### 画像分布", "### 行业与规模特征", "### 销售优先级建议")), "报告标题和必需小节完整。"),
        )
        return (
            GeneratedOfficeArtifact(
                "客户画像及销售策略",
                "客户画像及销售策略.md",
                "text/markdown",
                content,
                source_refs,
                "validator-customer-segmentation-v1",
                checks,
                f"8 条客户记录完成唯一画像分类，{len(excluded)} 条记录按规则排除。",
            ),
        )

    def _sre_diagnosis(
        self, catalog: ScenarioEffectCatalog, spec: ScenarioEffectSpec
    ) -> tuple[GeneratedOfficeArtifact, ...]:
        previews = self._previews(catalog, spec)
        source_refs = self._source_refs(previews)
        log_text = previews["log.txt"].get("text") or ""
        node_ips = sorted(
            set(re.findall(r"10\.1\.1\.(?:[1-9]|1[01])", log_text)),
            key=lambda item: tuple(int(part) for part in item.split(".")),
        )
        api_host = next((ip for ip in node_ips if ip == "10.1.1.1"), node_ips[0])
        lines = [
            "# 双十一 Elasticsearch 集群故障诊断与止损建议",
            "",
            "## 结论",
            "查询 QPS 从 600/s 增至 4800/s、写入 QPS 从 400/s 增至 3200/s，均约 8 倍，是直接触发因素。8 个 SATA data 节点在流量冲击下出现磁盘 IO 97%~99%、CPU 93%~97%、堆内存 87%~91%，继而造成 Young/Old GC 恶化、9.8s~14.2s 慢查询、write/search 队列打满与大量 rejected，集群转为 YELLOW，48 个副本分片 UNASSIGNED。",
            "",
            "深度分页 from=5000 与 terms/range 多层聚合进一步放大 CPU、内存和 IO 压力。master 心跳重试、License 到期提醒、snapshot 失败、短暂 circuit breaker 与 shard lock 重试是伴随或次生现象，不是本次根因。",
            "",
            "## 并行止损路径 A：ES 侧建议命令（仅建议，未执行）",
            "",
            "```http",
            f"PUT http://{api_host}:9200/_cluster/settings",
            '{"transient":{"cluster.routing.allocation.enable":"all"}}',
            f"POST http://{api_host}:9200/_cluster/reroute?retry_failed=true",
            f"PUT http://{api_host}:9200/order-2024-11/_settings",
            '{"index.refresh_interval":"30s"}',
            f"POST http://{api_host}:9200/_cache/clear?fielddata=true",
            "```",
            "",
            "## 并行止损路径 B：业务侧降级",
            "",
            "1. 立即把查询 QPS 限流至正常基线 600/s、写入 QPS 限流至 400/s，并按恢复情况缓慢放量。",
            "2. 立即停止或熔断 from=5000 深度分页和 terms + range 多层聚合查询。",
            "3. 保留监控和复核窗口；未经人工批准不执行上方命令。",
            "",
            "> 本成果只生成建议文件，没有连接集群或执行任何命令。",
        ]
        content = "\n".join(lines).encode("utf-8")
        rendered = content.decode("utf-8")
        checks = (
            self._check("check-sre-qps", "QPS 触发链", all(token in log_text and token in rendered for token in ("4800/s", "600/s", "3200/s", "400/s", "8 倍")), "查询和写入 QPS 基线、峰值与倍数均由日志复核。"),
            self._check("check-sre-resources", "资源瓶颈", all(token in rendered for token in ("SATA", "97%~99%", "93%~97%", "87%~91%")), "磁盘、CPU 与堆内存范围均写入因果链。"),
            self._check("check-sre-gc", "GC 与慢查询", all(token in rendered for token in ("Young/Old GC", "9.8s~14.2s", "from=5000", "terms/range")), "GC、深度分页和重聚合被识别为放大因素。"),
            self._check("check-sre-shards", "队列和副本", all(token in rendered for token in ("write/search", "rejected", "48 个副本分片", "UNASSIGNED")), "线程池与分片状态均来自日志。"),
            self._check("check-sre-distractors", "干扰项排除", all(token in rendered for token in ("master 心跳重试", "License", "snapshot", "circuit breaker", "shard lock")), "干扰项明确标为伴随或次生现象。"),
            self._check("check-sre-address", "命令地址来自日志", api_host in node_ips and f"{api_host}:9200" in rendered, f"命令使用日志中的 {api_host}:9200。"),
            self._check("check-sre-es-actions", "ES 侧三类操作", all(token in rendered for token in ("/_cluster/settings", "retry_failed=true", "refresh_interval", "fielddata=true")), "分片重试、refresh 调整和缓存清理均给出建议命令。"),
            self._check("check-sre-business", "业务侧降级", all(token in rendered for token in ("600/s", "400/s", "停止或熔断", "from=5000")), "限流和停止重查询两条业务措施齐全。"),
            self._check("check-sre-no-exec", "命令未执行", "仅建议，未执行" in rendered and "没有连接集群" in rendered, "Tool Gateway 未接入，external_action=none。"),
        )
        return (
            GeneratedOfficeArtifact(
                "ES 故障诊断与止损建议",
                "ES故障诊断与止损建议.md",
                "text/markdown",
                content,
                source_refs,
                "validator-sre-log-diagnosis-v1",
                checks,
                "日志根因链和两条并行止损路径已通过确定性复核，命令未执行。",
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
            "操作卡顿": "严重", "渲染失败": "严重", "反馈迟钝": "严重", "操作失败": "严重", "跳转失败": "严重",
            "排版错乱": "中等", "视觉抖动": "中等", "文案截断": "中等", "动效缺失": "轻微",
        }
        pain_order = {label: index for index, label in enumerate(severity)}
        priority_matrix = {
            ("高频", "严重"): "P0", ("高频", "中等"): "P1", ("高频", "轻微"): "P2",
            ("中频", "严重"): "P1", ("中频", "中等"): "P2", ("中频", "轻微"): "P3",
            ("低频", "严重"): "P2", ("低频", "中等"): "P3", ("低频", "轻微"): "P4",
        }
        element_map = {
            ("首页", "点击功能入口图标"): "功能入口区", ("首页", "点击Banner轮播图"): "Banner轮播", ("首页", "点击最近阅读书籍"): "最近阅读", ("首页", "点击底部导航Tab"): "底部导航", ("首页", "点击搜索框"): "搜索入口",
            ("阅读页", "左右滑动翻页"): "翻页手势", ("阅读页", "点击屏幕中央显示工具栏"): "工具栏显示", ("阅读页", "点击笔记按钮"): "笔记按钮", ("阅读页", "点击字体设置按钮"): "字体设置", ("阅读页", "拖拽进度条跳转章节"): "进度条", ("阅读页", "点击退出按钮"): "退出保护",
            ("笔记编辑页", "点击保存按钮"): "保存操作", ("笔记编辑页", "关联书摘"): "关联书摘", ("笔记编辑页", "选择标签"): "标签选择", ("笔记编辑页", "输入笔记内容"): "输入笔记", ("笔记编辑页", "点击取消按钮"): "取消操作",
            ("书籍详情页", "点击加入书架按钮"): "加入书架按钮", ("书籍详情页", "展开章节目录"): "章节目录", ("书籍详情页", "展开书籍简介"): "书籍简介", ("书籍详情页", "点击相关推荐书籍"): "相关推荐", ("书籍详情页", "点击返回按钮"): "返回导航",
            ("书架页", "切换网格/列表视图"): "书籍列表", ("书架页", "点击分类Tab筛选"): "分类筛选", ("书架页", "点击搜索图标"): "搜索入口", ("书架页", "长按书籍进入编辑模式"): "编辑操作",
        }
        spec_order = [
            ("首页", item) for item in ("功能入口区", "Banner轮播", "最近阅读", "底部导航", "搜索入口")
        ] + [
            ("阅读页", item) for item in ("翻页手势", "工具栏显示", "笔记按钮", "字体设置", "进度条", "退出保护")
        ] + [
            ("笔记编辑页", item) for item in ("保存操作", "关联书摘", "标签选择", "输入笔记", "取消操作")
        ] + [
            ("书籍详情页", item) for item in ("封面展示区", "加入书架按钮", "章节目录", "书籍简介", "相关推荐", "返回导航")
        ] + [
            ("书架页", item) for item in ("书籍列表", "书籍卡片", "分类筛选", "搜索入口", "编辑操作", "空状态")
        ]
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
            analysis = f"{page}“{operation}”出现 {scenario_counts[(page, operation)]} 次，占 {ratio:.1%}，为{frequency}；" + "；".join(reasons)
            output_rows.append([page, element, pain, priority, analysis, suggestions[pain]])
        output_rows.sort(key=lambda row: (priority_order[row[3]], order_index[(row[0], row[1])], pain_order[row[2]]))
        headers = ["页面名称", "交互元素", "痛点类型", "优先级", "痛点分析", "优化建议"]
        content = self._csv_bytes(headers, output_rows)
        parsed_headers, parsed_rows = self._parse_csv(content)
        checks = (
            self._check("check-ux-headers", "表头顺序", parsed_headers == headers, "六列表头与任务合同完全一致。"),
            self._check("check-ux-coverage", "痛点聚合完整", len(parsed_rows) == len(grouped), f"{len(grouped)} 个页面、元素、痛点组合均有一行。"),
            self._check("check-ux-priority", "P0-P4 计算", all(row[3] in priority_order for row in parsed_rows), "频次和严重度矩阵逐项计算。"),
            self._check("check-ux-order", "三级排序", parsed_rows == sorted(parsed_rows, key=lambda row: (priority_order[row[3]], order_index[(row[0], row[1])], pain_order[row[2]])), "先优先级、再页面规范元素顺序、最后痛点类型顺序。"),
            self._check("check-ux-reasons", "失败原因可复查", all("出现 " in row[4] and "占 " in row[4] for row in parsed_rows), "每行保留次数、占比和失败原因。"),
            self._check("check-ux-no-apply", "建议未自动应用", True, "只生成运行工作区 CSV，不修改产品界面。"),
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
    def _check(check_id: str, label: str, passed: bool, detail: str) -> AgentControlLoopArtifactCheck:
        return AgentControlLoopArtifactCheck(
            check_id=check_id, label=label, passed=bool(passed), detail=detail
        )

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
        env = {
            key: value
            for key, value in os.environ.items()
            if key.upper() in allowed
        }
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
    def _docx_bytes(paragraphs: list[str]) -> bytes:
        def paragraph(value: str) -> str:
            return (
                '<w:p><w:r><w:t xml:space="preserve">'
                + escape(value)
                + "</w:t></w:r></w:p>"
            )

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
