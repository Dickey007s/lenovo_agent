from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import threading
import zipfile
from pathlib import Path

import httpx
import pytest

from packages.contracts.harness_models import (
    AgentControlLoopArtifactCheck,
    AgentControlLoopFindingDecisionOption,
    AgentControlLoopFindingReview,
)
from services.api.app.application.benchmark_workspace_catalog import (
    BenchmarkWorkspaceCatalog,
)
from services.api.app.application.harness_runtime import (
    HarnessEvidenceQuote,
    HarnessFinding,
    HarnessModelError,
    HarnessPlanCandidate,
    HarnessPlanCandidateUnit,
    HarnessPlanError,
    HarnessRunStart,
    HarnessRuntime,
    HarnessTaskResult,
)
from services.api.app.application.run_workspace_artifact_store import (
    RunWorkspaceArtifactStore,
)
from services.api.app.api.harness_routes import stream_harness_events
from services.api.app.application.scenario_effects import (
    GeneratedOfficeArtifact,
    ScenarioEffectExecution,
    ScenarioEffectEngine,
    ScenarioEffectError,
)
from services.api.app.main import create_app


FORTE_ROOT = Path(__file__).resolve().parents[2] / "demo-enterprise-data" / "forte"
ONBOARDING_LABEL = "3月20日-4月20日入职时间表.csv"
ONBOARDING_INSTRUCTION = (
    "根据入职时间表和分配规则，生成 3 月 20 日至 4 月 20 日的入职资产匹配表。"
)
TC04_INSTRUCTION = (
    "为评测平台补充单元测试，覆盖 Service、执行引擎和工具类；"
    "真实运行测试，修复失败，并给出覆盖率与修改文件。"
)
TC12_INSTRUCTION = "为三个看板工具模块编写 Vitest，修复源码并真实运行测试。"
TC11_INSTRUCTION = "综合 PRD、上线配置、功能测试和兼容测试，给出上线结论与改进计划。"
TC05_INSTRUCTION = "核对三期往来明细，生成未付统计、未收统计，并判断是否存在僵尸账款。"
TC07_INSTRUCTION = "依据统一规则核查六份授权委托书，逐项说明风险、资料不足和复核动作。"
TC06_INSTRUCTION = "依据两个岗位说明分别审阅五份简历，保留逐条证据并输出辅助筛选结果。"
TC10_INSTRUCTION = "根据专业性说明生成信用卡 M1 逾期用户 AI 外呼催收流程图文档。"
TC13_INSTRUCTION = "清洗问卷、完成客户画像分类，并生成差异化销售策略 Markdown 报告。"
TC14_INSTRUCTION = "分析双十一 Elasticsearch 日志，给出根因与两个层面的紧急止损建议。"


class OnboardingPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        selected = next(item for item in files if item["display_label"] == ONBOARDING_LABEL)
        return HarnessPlanCandidate(
            summary="读取入职名单并形成可复核结果",
            selection_reason="入职时间表直接承载日期、岗位和备注事实。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="onboarding-input",
                    title="核对入职名单",
                    objective="核对日期范围内的入职员工",
                    input_file_refs=[selected["file_ref"]],
                    tool="table.inspect",
                )
            ],
        )


class WaitingPlanner:
    model = "deepseek-v4-pro"

    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def plan(self, *, scenario, files):
        self.started.set()
        await self.release.wait()
        raise AssertionError("the close lifecycle test must cancel the pending plan")


class OnboardingAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        source = files[0]
        assert source["display_label"] == ONBOARDING_LABEL
        return HarnessTaskResult(
            summary="入职时间表已只读核对，确定性工具将生成资产匹配表。",
            findings=[
                HarnessFinding(
                    plan_unit_id=plan.units[0].unit_id,
                    title="日期范围内存在待入职员工",
                    detail="时间表包含需要进行资产匹配的入职记录。",
                    file_refs=[source["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=source["file_ref"],
                            role="observed",
                            label="一条可唯一定位的入职记录",
                            quote="王子涵 | 3月23日 (周一) | 设计",
                        )
                    ],
                )
            ],
            follow_ups=[],
            review_required=True,
        )


class DashboardPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        source = next(
            item
            for item in files
            if str(item["display_path"]).endswith(
                "dashboard-toolkit/src/utils/metricsCalculator.js"
            )
        )
        return HarnessPlanCandidate(
            summary="核对真实看板工具源码并形成隔离修复包",
            selection_reason="增长率源码可用于形成一条可定位的模型分析；确定性效果门另行冻结完整 11 文件项目。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="read-dashboard-source",
                    title="读取看板工具源码",
                    objective="核对增长率实现并为确定性修复提供分析上下文",
                    input_file_refs=[source["file_ref"]],
                    tool="file.read",
                )
            ],
        )


class DashboardAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        source = files[0]
        return HarnessTaskResult(
            summary="已定位增长率实现；真实测试、修复和覆盖率由服务端固定 TC-12 效果门执行。",
            findings=[
                HarnessFinding(
                    plan_unit_id=plan.units[0].unit_id,
                    title="增长率实现使用了报告期值作分母",
                    detail="固定测试将先复现该业务红灯，再在隔离副本中修复。",
                    file_refs=[source["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=source["file_ref"],
                            role="observed",
                            label="增长率原实现",
                            quote="return ((newValue - oldValue) / newValue) * 100",
                        )
                    ],
                )
            ],
            follow_ups=[],
            review_required=True,
        )


class ReleaseReadinessPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        source = next(item for item in files if item["display_label"] == "PRD_v2.5.md")
        return HarnessPlanCandidate(
            summary="读取发布规则并形成可复核的上线判断",
            selection_reason="PRD 定义正式上线条件；固定 TC-11 效果门会另行冻结四份批准资料并逐项复算。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="read-release-rules",
                    title="读取 PRD 上线规则",
                    objective="核对功能全集、优先级和正式上线条件",
                    input_file_refs=[source["file_ref"]],
                    tool="file.read",
                )
            ],
        )


class ReleaseReadinessAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        source = files[0]
        return HarnessTaskResult(
            summary="已读取 PRD 上线规则；四份资料的交叉表校验、风险推导和 Gate 复算由服务端固定 TC-11 效果门完成。",
            findings=[
                HarnessFinding(
                    plan_unit_id=plan.units[0].unit_id,
                    title="本批次处于待上线审核状态",
                    detail="PRD 将当前文档状态标记为待上线审核，需要结合配置、功能测试和兼容测试复核。",
                    file_refs=[source["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=source["file_ref"],
                            role="observed",
                            label="PRD 文档状态",
                            quote="| 文档状态 | 待上线审核 |",
                        )
                    ],
                )
            ],
            follow_ups=[],
            review_required=True,
        )


class LegalDelegationPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        source = next(item for item in files if item["display_label"] == "委托书4.docx")
        return HarnessPlanCandidate(
            summary="读取一份委托书并形成可定位的法务核查上下文",
            selection_reason="固定 TC-07 效果门会另行冻结一份来源规则与六份委托书，并逐项重算。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="read-delegation-document",
                    title="读取授权委托书",
                    objective="核对签署栏和身份字段",
                    input_file_refs=[source["file_ref"]],
                    tool="file.read",
                )
            ],
        )


class LegalDelegationAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        source = files[0]
        return HarnessTaskResult(
            summary="已读取一份委托书；完整 21 条规则核查由服务端固定 TC-07 效果门执行。",
            findings=[
                HarnessFinding(
                    plan_unit_id=plan.units[0].unit_id,
                    title="签署栏没有可见签署对象",
                    detail="委托书4的签署栏为空，确定性效果门将结合 DOCX 包结构复核 R05。",
                    file_refs=[source["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=source["file_ref"],
                            role="observed",
                            label="空签署栏",
                            quote="委托人签名：",
                        )
                    ],
                )
            ],
            follow_ups=[],
            review_required=True,
        )


class CandidateReviewPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        source = next(
            item for item in files if item["display_label"] == "外卖商户BD岗位JD.docx"
        )
        return HarnessPlanCandidate(
            summary="读取一份岗位说明并形成可定位的招聘辅助上下文",
            selection_reason="固定 TC-06 效果门会另行冻结两份 JD 与五份简历，并逐条件重算。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="read-candidate-role",
                    title="读取外卖商户BD岗位说明",
                    objective="核对岗位默认学历门槛与显式例外",
                    input_file_refs=[source["file_ref"]],
                    tool="file.read",
                )
            ],
        )


class CandidateReviewAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        source = files[0]
        return HarnessTaskResult(
            summary="已读取一份岗位说明；完整双岗位逐条件核对由服务端固定 TC-06 效果门执行。",
            findings=[
                HarnessFinding(
                    plan_unit_id=plan.units[0].unit_id,
                    title="学历门槛包含人工例外",
                    detail="招聘负责人必须结合候选人的岗位证据决定是否适用优秀者放宽，服务端不会自动淘汰。",
                    file_refs=[source["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=source["file_ref"],
                            role="expected",
                            label="默认学历门槛与例外",
                            quote="学历背景： 大专及以上学历（优秀者可放宽）。",
                        )
                    ],
                )
            ],
            follow_ups=[],
            review_required=True,
        )


class CustomerSegmentationPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        source = next(item for item in files if item["display_label"] == "客户画像调研问卷.csv")
        return HarnessPlanCandidate(
            summary="读取公开问卷并形成可定位的画像清洗上下文",
            selection_reason="固定 TC-13 效果门会另行冻结问卷与规则，并逐原始行重算清洗和画像。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="read-customer-survey",
                    title="读取客户画像调研问卷",
                    objective="核对一条可回开的公开样本记录",
                    input_file_refs=[source["file_ref"]],
                    tool="table.inspect",
                )
            ],
        )


class CustomerSegmentationAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        source = files[0]
        return HarnessTaskResult(
            summary="已读取一条公开问卷记录；两份成果由服务端固定 TC-13 效果门从批准来源独立重算。",
            findings=[
                HarnessFinding(
                    plan_unit_id=plan.units[0].unit_id,
                    title="公开样本包含可复算的画像评分",
                    detail="这条记录只作为可回开的模型分析证据；清洗、重复和画像裁决由确定性效果门重算。",
                    file_refs=[source["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=source["file_ref"],
                            role="observed",
                            label="一条公开问卷记录",
                            quote="101 | 金融科技 | 500-1000人 | 技术架构师 | 9 | 7 | 6 | 2",
                        )
                    ],
                )
            ],
            follow_ups=[],
            review_required=True,
        )


class SREDiagnosisPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        source = next(
            item for item in files if item["display_path"] == "可靠性工程/log.txt"
        )
        return HarnessPlanCandidate(
            summary="读取固定公开日志并形成可定位的事故复盘上下文",
            selection_reason="固定 TC-14 效果门会另行冻结完整日志，并从来源字节重算观察、冲突、假设和未执行提案。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="read-sre-log",
                    title="读取双十一 Elasticsearch 日志",
                    objective="核对一条可回开的 QPS 观测",
                    input_file_refs=[source["file_ref"]],
                    tool="file.read",
                )
            ],
        )


class SREDiagnosisAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        source = files[0]
        return HarnessTaskResult(
            summary="已读取一条 QPS 观测；完整事故复盘由服务端固定 TC-14 效果门从批准日志独立重算。",
            findings=[
                HarnessFinding(
                    plan_unit_id=plan.units[0].unit_id,
                    title="查询 QPS 相对日志基线升高",
                    detail="这条记录只作为可回开的模型分析证据；来源冲突、假设和提案由确定性效果门重算。",
                    file_refs=[source["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=source["file_ref"],
                            role="observed",
                            label="查询 QPS 峰值与基线",
                            quote="node.indices.search.query_qps: 峰值 4800/s（正常基线 600/s，激增 8 倍）",
                        )
                    ],
                )
            ],
            follow_ups=[],
            review_required=True,
        )


class FinanceReconciliationPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        source = next(item for item in files if item["display_label"] == "2026往来明细.xlsx")
        return HarnessPlanCandidate(
            summary="读取 2026 往来明细并形成可定位的财务核对上下文",
            selection_reason="固定 TC-05 效果门会另行冻结三个期间工作簿，并从来源字节重新计算明细和跨期候选。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="read-finance-ledger",
                    title="读取 2026 往来明细",
                    objective="核对一条可回开的期末余额记录",
                    input_file_refs=[source["file_ref"]],
                    tool="table.inspect",
                )
            ],
        )


class FinanceReconciliationAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        source = files[0]
        return HarnessTaskResult(
            summary="已读取一条 2026 往来记录；三份成果由服务端固定 TC-05 效果门独立重算。",
            findings=[
                HarnessFinding(
                    plan_unit_id=plan.units[0].unit_id,
                    title="2026 年存在正数借方期末余额",
                    detail="这条记录只作为可回开的模型分析证据；财务明细和候选由确定性效果门重算。",
                    file_refs=[source["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=source["file_ref"],
                            role="observed",
                            label="一条正数借方期末余额",
                            quote=(
                                "其他应收款\\其他应收往来 | 【绵阳长城发展融资担保有限公司】 | "
                                "借 | 1500000 | 200000 |  | 200000 |  | 借 | 1700000"
                            ),
                        )
                    ],
                )
            ],
            follow_ups=[],
            review_required=True,
        )


class OutboundFlowPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        source = next(item for item in files if item["display_label"] == "专业性说明.md")
        return HarnessPlanCandidate(
            summary="读取批准的专业性说明并形成可定位的流程规则上下文",
            selection_reason="固定 TC-10 效果门会另行冻结批准 Markdown，并从来源行重新推导规则账本和状态图。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="read-outbound-guidance",
                    title="读取专业性说明",
                    objective="核对身份确认与欠款披露的来源顺序",
                    input_file_refs=[source["file_ref"]],
                    tool="file.read",
                )
            ],
        )


class OutboundFlowAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        source = files[0]
        return HarnessTaskResult(
            summary="已读取一条身份确认规则；完整规则账本、状态图和 DOCX 由服务端固定 TC-10 效果门独立重算。",
            findings=[
                HarnessFinding(
                    plan_unit_id=plan.units[0].unit_id,
                    title="身份确认必须早于欠款披露",
                    detail="这条模型分析只作可回开的上下文；规则覆盖与图可达性由确定性效果门验证。",
                    file_refs=[source["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=source["file_ref"],
                            role="expected",
                            label="身份确认顺序",
                            quote=(
                                "接通后第一步，询问是否本人。确认是本人才进入催收话术；"
                                "非本人只请转告；无法确认则结束通话。"
                            ),
                        )
                    ],
                )
            ],
            follow_ups=[],
            review_required=True,
        )


class NoisyOnboardingPlanner:
    model = "deepseek-v4-pro"

    async def plan(self, *, scenario, files):
        schedule = next(
            item for item in files if item["display_label"] == ONBOARDING_LABEL
        )
        rules = next(
            item
            for item in files
            if item["display_label"] == "入职物资权限软件分配.pdf"
        )
        return HarnessPlanCandidate(
            summary="读取名单、规则并生成入职资产匹配表",
            selection_reason="名单与分配规则共同决定日期范围内的匹配结果。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="read-schedule",
                    title="读取入职时间表",
                    objective="筛选日期范围内的员工",
                    input_file_refs=[schedule["file_ref"]],
                    tool="table.inspect",
                ),
                HarnessPlanCandidateUnit(
                    unit_id="read-rules",
                    title="读取入职物资权限软件分配规则",
                    objective="核对岗位分类、优先级与备注覆盖规则",
                    input_file_refs=[rules["file_ref"]],
                    tool="file.read",
                ),
                HarnessPlanCandidateUnit(
                    unit_id="generate-assets",
                    title="生成入职资产匹配表",
                    objective="按时间表与规则形成可下载成果",
                    input_file_refs=[schedule["file_ref"], rules["file_ref"]],
                    depends_on=["read-schedule", "read-rules"],
                    tool="evidence.verify",
                ),
            ],
        )


class NoisyOnboardingAnalyst:
    model = "deepseek-v4-pro"

    def __init__(self) -> None:
        self.calls = 0

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        self.calls += 1
        schedule = next(item for item in files if item["display_label"] == ONBOARDING_LABEL)
        rules = next(
            item
            for item in files
            if item["display_label"] == "入职物资权限软件分配.pdf"
        )
        unit_ids = {unit.title: unit.unit_id for unit in plan.units}
        review = AgentControlLoopFindingReview(
            requires_human_decision=True,
            question="是否需要人工指定技术研发岗位的分类？",
            why_human="模型把已经明确的关键词优先级误判为需要用户选择。",
            options=[
                AgentControlLoopFindingDecisionOption(
                    option_id="A",
                    label="按规则归类",
                    meaning="使用文档中已经给出的关键词优先级。",
                    agent_next_step="保留当前匹配结果。",
                    next_instruction="按明确规则复核当前匹配结果。",
                ),
                AgentControlLoopFindingDecisionOption(
                    option_id="B",
                    label="另行指定",
                    meaning="由用户手工指定其他岗位分类。",
                    agent_next_step="形成另一份只读匹配建议。",
                    next_instruction="按用户指定分类形成另一份只读匹配建议。",
                ),
            ],
            recommended_option_id="A",
            recommendation_reason="规则已经明确给出分类优先级。",
            after_confirmation="只更新分析说明，不修改原文件。",
        )
        priority_quote = (
            '优先级说明：若岗位同时包含多个分类关键词（如"产品运营"、"市场研发"），'
            "以排列靠前的分类为准——技术研发 > 产品/视觉设计 > 运营/市场/职能。"
        )
        return HarnessTaskResult(
            summary="日期范围内的入职资产已匹配，另有范围外候选和多余人工门需要服务端处理。",
            findings=[
                HarnessFinding(
                    plan_unit_id=unit_ids["读取入职时间表"],
                    title="日期范围内共有九名待入职员工",
                    detail="3 月 20 日至 4 月 20 日的边界员工已保留。",
                    file_refs=[schedule["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=schedule["file_ref"],
                            role="observed",
                            label="日期上界记录",
                            quote=(
                                "林舒志 | 4月20日 (周一) | 技术研发 | "
                                "林某某 138xxxx0015 | 共享工位"
                            ),
                        )
                    ],
                ),
                HarnessFinding(
                    plan_unit_id=unit_ids["读取入职物资权限软件分配规则"],
                    title="技术研发按明确优先级归类",
                    detail="规则已经给出关键词和优先级，不需要用户再次决定。",
                    file_refs=[schedule["file_ref"], rules["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=schedule["file_ref"],
                            role="observed",
                            label="技术研发员工",
                            quote=(
                                "林舒志 | 4月20日 (周一) | 技术研发 | "
                                "林某某 138xxxx0015 | 共享工位"
                            ),
                        ),
                        HarnessEvidenceQuote(
                            file_ref=rules["file_ref"],
                            role="expected",
                            label="岗位分类优先级",
                            quote=priority_quote,
                        ),
                    ],
                    review=review,
                ),
                HarnessFinding(
                    plan_unit_id=unit_ids["生成入职资产匹配表"],
                    title="两条特殊备注均已生效",
                    detail="设计软件权限和共享工位分别覆盖默认值。",
                    file_refs=[schedule["file_ref"], rules["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=schedule["file_ref"],
                            role="observed",
                            label="多条备注员工",
                            quote=(
                                "冯子健 | 4月13日 (周一) | 设计 | "
                                "冯某某 138xxxx0018 | 不开通设计软件权限、共享工位"
                            ),
                        ),
                        HarnessEvidenceQuote(
                            file_ref=rules["file_ref"],
                            role="expected",
                            label="多条备注规则",
                            quote=(
                                '多条备注处理：若同一员工有多条备注（以顿号"、"分隔），'
                                "每条备注均须生效。"
                            ),
                        ),
                    ],
                ),
                HarnessFinding(
                    plan_unit_id=unit_ids["读取入职时间表"],
                    title="范围外岗位包含组合关键词",
                    detail="4 月 21 日和 4 月 23 日不属于当前任务范围。",
                    file_refs=[schedule["file_ref"], rules["file_ref"]],
                    evidence_quotes=[
                        HarnessEvidenceQuote(
                            file_ref=schedule["file_ref"],
                            role="observed",
                            label="范围外产品运营员工",
                            quote=(
                                "姜映雪 | 4月21日 (周二) | 产品运营 | "
                                "姜某某 138xxxx0012"
                            ),
                        ),
                        HarnessEvidenceQuote(
                            file_ref=schedule["file_ref"],
                            role="observed",
                            label="范围外市场运营员工",
                            quote=(
                                "孟雨桐 | 4月23日 (周四) | 市场运营 | "
                                "孟某某 138xxxx0029"
                            ),
                        ),
                        HarnessEvidenceQuote(
                            file_ref=rules["file_ref"],
                            role="expected",
                            label="岗位分类优先级",
                            quote=priority_quote,
                        ),
                    ],
                ),
            ],
            follow_ups=[],
            review_required=True,
        )


class RejectedOnboardingAnalyst:
    model = "deepseek-v4-pro"

    async def analyze(self, **kwargs):
        raise HarnessModelError("invalid structured response", called=True, elapsed_ms=9)


class MainThreadCatalog:
    """Fails if a live catalog method leaks into the effect worker thread."""

    def __init__(self, catalog: BenchmarkWorkspaceCatalog) -> None:
        self.catalog = catalog
        self.owner_thread_id = threading.get_ident()

    def _assert_main_thread(self) -> None:
        assert threading.get_ident() == self.owner_thread_id

    def internal_workspace(self):
        self._assert_main_thread()
        return self.catalog.internal_workspace()

    def public_workspace(self):
        self._assert_main_thread()
        return self.catalog.public_workspace()

    def public_file(self, file_ref: str):
        self._assert_main_thread()
        return self.catalog.public_file(file_ref)

    def checked_input_bytes(self, file_ref: str):
        self._assert_main_thread()
        return self.catalog.checked_input_bytes(file_ref)

    def checked_input_bytes_many(self, file_refs):
        self._assert_main_thread()
        return self.catalog.checked_input_bytes_many(file_refs)


class BlockingScenarioEffectEngine(ScenarioEffectEngine):
    def __init__(self, owner_thread_id: int) -> None:
        self.owner_thread_id = owner_thread_id
        self.started = threading.Event()
        self.release = threading.Event()
        self.execute_calls = 0
        self.worker_thread_id: int | None = None

    def execute(self, instruction, catalog):
        self.execute_calls += 1
        self.worker_thread_id = threading.get_ident()
        assert self.worker_thread_id != self.owner_thread_id
        self.started.set()
        if not self.release.wait(timeout=5):
            raise ScenarioEffectError("controlled blocking probe timed out")
        spec = self.match(instruction)
        assert spec is not None and spec.scenario_id == "TC-04"
        source_refs = tuple(catalog.input_bytes)
        check = AgentControlLoopArtifactCheck(
            check_id="check-tc04-responsive-probe",
            label="受控 TC-04 工作线程只生成一次成果",
            passed=True,
            detail="该探针只验证调度、响应性与去重，不替代真实 117 项效果门。",
        )
        artifact = GeneratedOfficeArtifact(
            title="TC-04 受控响应探针",
            file_name="tc04-responsive-probe.md",
            media_type="text/markdown",
            content=b"tc04 responsive probe\n",
            source_file_refs=source_refs,
            validator_id="validator-tc04-responsive-probe-v1",
            checks=(check,),
            summary="受控阻塞释放后只写入一次测试成果。",
        )
        return ScenarioEffectExecution(
            scenario_id=spec.scenario_id,
            capability_id=spec.capability_id,
            status="passed",
            state="frozen_tc04_probe",
            action="run_in_worker_thread",
            observation="health、Run GET 与 SSE 在阻塞期间仍可响应",
            cost="一次受控工作线程",
            result="只生成一次探针成果",
            source_file_refs=source_refs,
            artifacts=(artifact,),
            prohibited_side_effects=spec.prohibited_side_effects,
        )


class FailingScenarioEffectEngine(ScenarioEffectEngine):
    def execute(self, instruction, catalog):
        raise ScenarioEffectError("controlled effect failure")


def _forte_digests() -> dict[str, str]:
    return {
        item.relative_to(FORTE_ROOT).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in FORTE_ROOT.rglob("*")
        if item.is_file()
    }


async def _wait_for_effect(
    runtime: HarnessRuntime,
    owner: str,
    run_id: str,
    *,
    timeout_seconds: float = 10.0,
    poll_interval_seconds: float = 0.01,
):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    while True:
        snapshot = await runtime.get(owner, run_id)
        if snapshot.effect_receipts:
            return snapshot
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise AssertionError(
                "scenario effect was not recorded before the monotonic deadline; "
                f"timeout={timeout_seconds:.2f}s status={snapshot.status} "
                f"version={snapshot.version} receipts={len(snapshot.effect_receipts)} "
                f"artifacts={len(snapshot.workspace_artifacts)}"
            )
        await asyncio.sleep(min(poll_interval_seconds, remaining))


async def _wait_for_settled(
    runtime: HarnessRuntime,
    owner: str,
    run_id: str,
    *,
    timeout_seconds: float = 10.0,
    poll_interval_seconds: float = 0.01,
):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    while True:
        snapshot = await runtime.get(owner, run_id)
        if snapshot.status in {"waiting_input", "completed", "stopped", "failed"}:
            return snapshot
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise AssertionError(
                "run did not settle before the monotonic deadline; "
                f"timeout={timeout_seconds:.2f}s status={snapshot.status} "
                f"version={snapshot.version} receipts={len(snapshot.effect_receipts)}"
            )
        await asyncio.sleep(min(poll_interval_seconds, remaining))


@pytest.mark.asyncio
async def test_runtime_writes_downloadable_verified_artifact_without_touching_forte(
    tmp_path: Path,
) -> None:
    before = _forte_digests()
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        OnboardingPlanner(),
        OnboardingAnalyst(),
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
        started = await runtime.start(
            "alice",
            HarnessRunStart(
                idempotency_key="scenario-effect-runtime-onboarding-0001",
                instruction=ONBOARDING_INSTRUCTION,
            ),
        )
        snapshot = await _wait_for_effect(runtime, "alice", started.run.run_id)

        assert snapshot.effect_receipts[0].status == "passed"
        assert snapshot.effect_receipts[0].scenario_id == "TC-01"
        assert len(snapshot.workspace_artifacts) == 1
        record = snapshot.workspace_artifacts[0]
        assert record.file_name == "入职资产匹配表.csv"
        assert record.verifier_status == "passed"
        assert all(check.passed for check in record.checks)
        assert record.original_inputs_modified is False
        assert record.external_action == "none"
        assert _forte_digests() == before

        public = runtime.public_snapshot(snapshot)
        serialized = public.model_dump_json()
        assert "content_sha256" not in serialized
        assert record.content_sha256 not in serialized
        assert public.workspace_artifacts[0].download_path.endswith(record.artifact_id)

        metadata, content = await runtime.get_workspace_artifact(
            "alice", snapshot.run_id, record.artifact_id
        )
        assert metadata.file_name == "入职资产匹配表.csv"
        assert content.startswith(b"\xef\xbb\xbf")
        assert "紧急联系人" not in content.decode("utf-8-sig")
        with pytest.raises(Exception):
            await runtime.get_workspace_artifact(
                "bob", snapshot.run_id, record.artifact_id
            )

        event_names = [item.event_name for item in snapshot.events]
        assert "deterministic_office_tool_started" in event_names
        assert "run_workspace_artifact_written" in event_names
        assert "deterministic_verification_completed" in event_names

        app = create_app()
        app.state.harness_runtime = runtime
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get(
                record.download_path,
                headers={"X-User-Id": "alice"},
            )
            denied = await client.get(
                record.download_path,
                headers={"X-User-Id": "bob"},
            )
        assert response.status_code == 200
        assert response.content == content
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert denied.status_code == 404
        json.dumps(public.model_dump(mode="json"), ensure_ascii=False)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_tc11_runtime_persists_verified_files_and_failed_business_gates(
    tmp_path: Path,
) -> None:
    before = _forte_digests()
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        ReleaseReadinessPlanner(),
        ReleaseReadinessAnalyst(),
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
        started = await runtime.start(
            "release-owner",
            HarnessRunStart(
                idempotency_key="tc11-derived-release-runtime-0001",
                instruction=TC11_INSTRUCTION,
            ),
        )
        snapshot = None
        for _ in range(1_000):
            candidate = await runtime.get(
                "release-owner", started.run.run_id
            )
            if candidate.status in {"waiting_input", "completed", "stopped", "failed"}:
                snapshot = candidate
                break
            await asyncio.sleep(0.01)
        assert snapshot is not None

        assert snapshot.status == "completed"
        assert len(snapshot.workspace_artifacts) == 2
        assert snapshot.effect_receipts[0].status == "passed"
        outcome = snapshot.effect_receipts[0].business_gate_outcome
        assert outcome is not None
        assert outcome.status == "failed"
        assert outcome.decision == "不得上线"
        assert outcome.failed_gate_count == outcome.total_gate_count == 4
        assert [gate.actual for gate in outcome.gates] == [71.4, 80.0, 40.0, 4.0]
        assert len(outcome.records) == 18
        assert sum(item.final_risk_level == "severe" for item in outcome.records) == 4
        assert sum(item.final_risk_level == "major" for item in outcome.records) == 2
        assert sum(item.final_risk_level == "minor" for item in outcome.records) == 2
        assert all(
            item.business_gate_outcome == outcome
            for item in snapshot.workspace_artifacts
        )
        assert all(
            item.verifier_status == "passed"
            for item in snapshot.workspace_artifacts
        )
        assert all(
            check.passed
            for item in snapshot.workspace_artifacts
            for check in item.checks
        )

        by_name = {item.file_name: item for item in snapshot.workspace_artifacts}
        _, report = await runtime.get_workspace_artifact(
            "release-owner",
            snapshot.run_id,
            by_name["上线合规与风险报告.docx"].artifact_id,
        )
        with zipfile.ZipFile(io.BytesIO(report)) as package:
            document = package.read("word/document.xml").decode("utf-8")
        assert document.count("<w:tbl>") >= 6
        assert "上线结论：不得上线" in document

        _, ledger = await runtime.get_workspace_artifact(
            "release-owner",
            snapshot.run_id,
            by_name["上线功能风险逐项台账.csv"].artifact_id,
        )
        ledger_rows = list(csv.DictReader(io.StringIO(ledger.decode("utf-8-sig"))))
        assert len(ledger_rows) == 18
        assert sum(item["最终等级"] == "严重" for item in ledger_rows) == 4
        assert _forte_digests() == before

        public = runtime.public_snapshot(snapshot).model_dump(mode="json")
        public_outcome = public["effect_receipts"][0]["business_gate_outcome"]
        assert public_outcome["decision"] == "不得上线"
        assert len(public_outcome["records"]) == 18
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_tc06_runtime_keeps_source_verification_advice_and_hr_decision_separate(
    tmp_path: Path,
) -> None:
    before = _forte_digests()
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        CandidateReviewPlanner(),
        CandidateReviewAnalyst(),
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
        started = await runtime.start(
            "candidate-owner",
            HarnessRunStart(
                idempotency_key="tc06-derived-candidate-runtime-0001",
                instruction=TC06_INSTRUCTION,
            ),
        )
        snapshot = None
        for _ in range(1_000):
            candidate = await runtime.get("candidate-owner", started.run.run_id)
            if candidate.status in {"waiting_input", "completed", "stopped", "failed"}:
                snapshot = candidate
                break
            await asyncio.sleep(0.01)
        assert snapshot is not None
        assert snapshot.status == "completed"
        assert len(snapshot.workspace_artifacts) == 3
        assert len(snapshot.effect_receipts) == 1

        receipt = snapshot.effect_receipts[0]
        assert receipt.status == "passed"
        assert receipt.scenario_id == "TC-06"
        assert receipt.candidate_review_outcome is not None
        outcome = receipt.candidate_review_outcome
        assert outcome.status == "review_required"
        assert outcome.decision == "这是人工复核建议，不是录用或淘汰决定。"
        assert outcome.role_count == 2
        assert outcome.candidate_count == 5
        assert outcome.review_count == 10
        assert outcome.assessment_count == 110
        assert (
            outcome.met_count,
            outcome.not_met_count,
            outcome.unverifiable_count,
            outcome.human_exception_count,
        ) == (32, 6, 71, 1)
        assert outcome.human_review_required is True
        assert outcome.fairness_evaluated is False

        for artifact in snapshot.workspace_artifacts:
            assert artifact.verifier_status == "passed"
            assert artifact.candidate_review_outcome == outcome
            assert all(check.passed for check in artifact.checks)
            assert artifact.review_required is True
            assert artifact.external_action == "none"

        by_name = {item.file_name: item for item in snapshot.workspace_artifacts}
        assert len(by_name["外卖商户BD岗位辅助筛选报告.docx"].source_file_refs) == 6
        assert len(by_name["文本评测岗位辅助筛选报告.docx"].source_file_refs) == 6
        assert len(by_name["候选人岗位条件逐项台账.csv"].source_file_refs) == 7
        _, report = await runtime.get_workspace_artifact(
            "candidate-owner",
            snapshot.run_id,
            by_name["外卖商户BD岗位辅助筛选报告.docx"].artifact_id,
        )
        with zipfile.ZipFile(io.BytesIO(report)) as package:
            report_xml = package.read("word/document.xml").decode("utf-8")
        assert report_xml.count("<w:tbl>") >= 8
        assert "不是录用或淘汰决定" in report_xml

        _, ledger = await runtime.get_workspace_artifact(
            "candidate-owner",
            snapshot.run_id,
            by_name["候选人岗位条件逐项台账.csv"].artifact_id,
        )
        rows = list(csv.DictReader(io.StringIO(ledger.decode("utf-8-sig"))))
        assert len(rows) == 110
        assert len({(row["岗位ID"], row["候选人ID"], row["条件ID"]) for row in rows}) == 110
        assert sum(row["状态"] == "需人工例外判断" for row in rows) == 1
        assert "手机号" not in ledger.decode("utf-8-sig")
        assert _forte_digests() == before

        public = runtime.public_snapshot(snapshot).model_dump(mode="json")
        public_outcome = public["effect_receipts"][0]["candidate_review_outcome"]
        assert public_outcome["assessment_count"] == 110
        assert public_outcome["fairness_evaluated"] is False
        assert "content_sha256" not in json.dumps(public, ensure_ascii=False)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_tc13_runtime_keeps_cleaning_strategy_review_and_customer_actions_separate(
    tmp_path: Path,
) -> None:
    before = _forte_digests()
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        CustomerSegmentationPlanner(),
        CustomerSegmentationAnalyst(),
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
        started = await runtime.start(
            "customer-segmentation-owner",
            HarnessRunStart(
                idempotency_key="tc13-source-derived-customer-runtime-0001",
                instruction=TC13_INSTRUCTION,
            ),
        )
        snapshot = None
        for _ in range(1_000):
            candidate = await runtime.get(
                "customer-segmentation-owner", started.run.run_id
            )
            if candidate.status in {"waiting_input", "completed", "stopped", "failed"}:
                snapshot = candidate
                break
            await asyncio.sleep(0.01)
        assert snapshot is not None
        assert snapshot.status == "completed"
        assert len(snapshot.workspace_artifacts) == 2
        assert len(snapshot.effect_receipts) == 1

        receipt = snapshot.effect_receipts[0]
        assert receipt.status == "passed"
        assert receipt.scenario_id == "TC-13"
        assert receipt.customer_segmentation_outcome is not None
        outcome = receipt.customer_segmentation_outcome
        assert outcome.status == "sales_review_required"
        assert (
            outcome.source_row_count,
            outcome.unique_payload_count,
            outcome.duplicate_count,
            outcome.classified_count,
            outcome.unclassified_count,
            outcome.excluded_count,
        ) == (11, 10, 1, 8, 2, 3)
        assert outcome.profile_counts == {"技术型": 3, "安全型": 3, "敏捷型": 2}
        assert outcome.priority_witness_count == 0
        assert outcome.strategy_evidence_status == "no_approved_strategy_source"
        assert outcome.policy_assumption_review_required is True
        assert outcome.human_review_required is True
        assert outcome.original_inputs_modified is False
        assert outcome.external_action == "none"

        for artifact in snapshot.workspace_artifacts:
            assert artifact.verifier_status == "passed"
            assert artifact.customer_segmentation_outcome == outcome
            assert len({check.check_id for check in artifact.checks}) == 8
            assert all(check.passed for check in artifact.checks)
            assert artifact.review_required is True
            assert artifact.external_action == "none"
            assert len(artifact.source_file_refs) == 2

        by_name = {item.file_name: item for item in snapshot.workspace_artifacts}
        _, report = await runtime.get_workspace_artifact(
            "customer-segmentation-owner",
            snapshot.run_id,
            by_name["客户画像及销售策略.md"].artifact_id,
        )
        report_text = report.decode("utf-8")
        assert "多标签优先级 witness：0" in report_text
        assert "no_approved_strategy_source" in report_text
        assert "待批准模板" in report_text
        assert "没有联系客户、写 CRM、创建商机或触发营销动作" in report_text

        _, ledger = await runtime.get_workspace_artifact(
            "customer-segmentation-owner",
            snapshot.run_id,
            by_name["客户画像逐样本台账.csv"].artifact_id,
        )
        rows = list(csv.DictReader(io.StringIO(ledger.decode("utf-8-sig"))))
        assert len(rows) == 11
        assert len({row["样本ID"] for row in rows}) == 11
        duplicate = next(row for row in rows if row["样本ID"] == "111")
        assert duplicate["duplicate_of"] == "101"
        assert duplicate["排除原因"] == "exact_duplicate"
        assert _forte_digests() == before

        public = runtime.public_snapshot(snapshot).model_dump(mode="json")
        public_outcome = public["effect_receipts"][0]["customer_segmentation_outcome"]
        assert public_outcome["source_row_count"] == 11
        assert public_outcome["priority_witness_count"] == 0
        assert public_outcome["external_action"] == "none"
        assert "content_sha256" not in json.dumps(public, ensure_ascii=False)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_tc14_runtime_keeps_observations_hypotheses_and_actions_separate(
    tmp_path: Path,
) -> None:
    before = _forte_digests()
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        SREDiagnosisPlanner(),
        SREDiagnosisAnalyst(),
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
        started = await runtime.start(
            "sre-diagnosis-owner",
            HarnessRunStart(
                idempotency_key="tc14-source-derived-sre-runtime-0001",
                instruction=TC14_INSTRUCTION,
            ),
        )
        snapshot = None
        for _ in range(1_000):
            candidate = await runtime.get("sre-diagnosis-owner", started.run.run_id)
            if candidate.status in {"waiting_input", "completed", "stopped", "failed"}:
                snapshot = candidate
                break
            await asyncio.sleep(0.01)
        assert snapshot is not None
        assert snapshot.status == "completed"
        assert len(snapshot.workspace_artifacts) == 2
        assert len(snapshot.effect_receipts) == 1

        receipt = snapshot.effect_receipts[0]
        assert receipt.status == "passed"
        assert receipt.scenario_id == "TC-14"
        assert receipt.sre_diagnosis_outcome is not None
        outcome = receipt.sre_diagnosis_outcome
        assert outcome.status == "incident_review_required"
        assert outcome.source_line_count == 232
        assert outcome.conflict_count == 3
        assert outcome.hypothesis_count == 2
        assert outcome.proposal_count == 8
        assert outcome.business_mitigation_count == 3
        assert outcome.node_facts["listed_count"] == 11
        assert outcome.node_facts["listed_master_count"] == 3
        assert outcome.node_facts["listed_data_count"] == 8
        assert outcome.resolved_target_count == 0
        assert outcome.human_review_required is True
        assert outcome.original_inputs_modified is False
        assert outcome.external_action == "none"
        assert all(item.executed is False for item in outcome.action_proposals)
        assert all(item.approval_required is True for item in outcome.action_proposals)
        assert all(item.target_status == "unresolved" for item in outcome.action_proposals)

        for artifact in snapshot.workspace_artifacts:
            assert artifact.verifier_status == "passed"
            assert artifact.sre_diagnosis_outcome == outcome
            assert len({check.check_id for check in artifact.checks}) == 12
            assert all(check.passed for check in artifact.checks)
            assert artifact.review_required is True
            assert artifact.external_action == "none"
            assert artifact.source_file_refs == ["forte-df5ae9b9a1273380"]

        by_name = {item.file_name: item for item in snapshot.workspace_artifacts}
        _, report = await runtime.get_workspace_artifact(
            "sre-diagnosis-owner",
            snapshot.run_id,
            by_name["ES故障诊断与止损建议.md"].artifact_id,
        )
        report_text = report.decode("utf-8")
        assert "不是在线监控、根因定论或命令执行回执" in report_text
        assert "dedicated master" in report_text
        assert "external_action=none" in report_text

        _, ledger = await runtime.get_workspace_artifact(
            "sre-diagnosis-owner",
            snapshot.run_id,
            by_name["SRE事故观察与动作台账.csv"].artifact_id,
        )
        rows = list(csv.DictReader(io.StringIO(ledger.decode("utf-8-sig"))))
        assert len(rows) == (
            outcome.observation_count
            + outcome.conflict_count
            + outcome.hypothesis_count
            + outcome.proposal_count
            + outcome.business_mitigation_count
        )
        assert sum(row["记录类型"] == "conflict" for row in rows) == 3
        assert sum(row["记录类型"] == "proposal" for row in rows) == 11
        assert all(row["已执行"] != "true" for row in rows)
        assert _forte_digests() == before

        public = runtime.public_snapshot(snapshot).model_dump(mode="json")
        public_outcome = public["effect_receipts"][0]["sre_diagnosis_outcome"]
        assert public_outcome["conflict_count"] == 3
        assert public_outcome["resolved_target_count"] == 0
        assert public_outcome["external_action"] == "none"
        assert "content_sha256" not in json.dumps(public, ensure_ascii=False)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_tc05_runtime_keeps_calculation_candidates_and_finance_decision_separate(
    tmp_path: Path,
) -> None:
    before = _forte_digests()
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        FinanceReconciliationPlanner(),
        FinanceReconciliationAnalyst(),
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
        started = await runtime.start(
            "finance-owner",
            HarnessRunStart(
                idempotency_key="tc05-derived-finance-runtime-0001",
                instruction=TC05_INSTRUCTION,
            ),
        )
        snapshot = None
        for _ in range(1_000):
            candidate = await runtime.get("finance-owner", started.run.run_id)
            if candidate.status in {"waiting_input", "completed", "stopped", "failed"}:
                snapshot = candidate
                break
            await asyncio.sleep(0.01)
        assert snapshot is not None
        assert snapshot.status == "completed"
        assert len(snapshot.workspace_artifacts) == 3
        assert len(snapshot.effect_receipts) == 1

        receipt = snapshot.effect_receipts[0]
        assert receipt.status == "passed"
        assert receipt.scenario_id == "TC-05"
        assert receipt.finance_review_outcome is not None
        outcome = receipt.finance_review_outcome
        assert outcome.status == "review_required"
        assert outcome.period_ids == ["2025_h1", "2025_h2", "2026"]
        assert (outcome.unpaid_count, outcome.unreceived_count, outcome.candidate_count) == (
            31,
            2,
            0,
        )
        assert outcome.unpaid_total == "3984606.46"
        assert outcome.unreceived_total == "4992891.47"
        assert outcome.human_review_required is True
        assert outcome.original_inputs_modified is False
        assert outcome.external_action == "none"

        for artifact in snapshot.workspace_artifacts:
            assert artifact.verifier_status == "passed"
            assert artifact.finance_review_outcome == outcome
            assert len(artifact.checks) == 5
            assert all(check.passed for check in artifact.checks)
            assert artifact.review_required is True
            assert artifact.external_action == "none"

        by_name = {item.file_name: item for item in snapshot.workspace_artifacts}
        assert len(by_name["未付统计.csv"].source_file_refs) == 1
        assert len(by_name["未收统计.csv"].source_file_refs) == 1
        assert len(by_name["跨期核对说明.md"].source_file_refs) == 3
        assert by_name["未付统计.csv"].source_file_refs == by_name["未收统计.csv"].source_file_refs

        _, unpaid = await runtime.get_workspace_artifact(
            "finance-owner", snapshot.run_id, by_name["未付统计.csv"].artifact_id
        )
        unpaid_rows = list(csv.DictReader(io.StringIO(unpaid.decode("utf-8-sig"))))
        assert len(unpaid_rows) == 31
        assert sum(float(row["期末余额"]) for row in unpaid_rows) == pytest.approx(3984606.46)
        assert all(row["来源文件"] == "2026往来明细.xlsx" for row in unpaid_rows)
        assert all(row["来源位置"].startswith("Sheet1!A") for row in unpaid_rows)

        _, unreceived = await runtime.get_workspace_artifact(
            "finance-owner", snapshot.run_id, by_name["未收统计.csv"].artifact_id
        )
        unreceived_rows = list(
            csv.DictReader(io.StringIO(unreceived.decode("utf-8-sig")))
        )
        assert len(unreceived_rows) == 2
        assert sum(float(row["期末余额"]) for row in unreceived_rows) == pytest.approx(
            4992891.47
        )

        _, explanation = await runtime.get_workspace_artifact(
            "finance-owner", snapshot.run_id, by_name["跨期核对说明.md"].artifact_id
        )
        explanation_text = explanation.decode("utf-8")
        assert "跨期僵尸账款候选：0 条" in explanation_text
        assert "当前启发式未发现候选，仍需财务复核" in explanation_text
        assert "不是付款、核销、记账或坏账确认" in explanation_text
        assert _forte_digests() == before

        public = runtime.public_snapshot(snapshot).model_dump(mode="json")
        public_outcome = public["effect_receipts"][0]["finance_review_outcome"]
        assert public_outcome["unpaid_count"] == 31
        assert public_outcome["candidate_count"] == 0
        assert public_outcome["original_inputs_modified"] is False
        assert "content_sha256" not in json.dumps(public, ensure_ascii=False)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_tc10_runtime_keeps_flow_verification_approval_and_actions_separate(
    tmp_path: Path,
) -> None:
    before = _forte_digests()
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        OutboundFlowPlanner(),
        OutboundFlowAnalyst(),
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
        started = await runtime.start(
            "outbound-owner",
            HarnessRunStart(
                idempotency_key="tc10-source-derived-outbound-runtime-0001",
                instruction=TC10_INSTRUCTION,
            ),
        )
        snapshot = None
        for _ in range(1_000):
            candidate = await runtime.get("outbound-owner", started.run.run_id)
            if candidate.status in {"waiting_input", "completed", "stopped", "failed"}:
                snapshot = candidate
                break
            await asyncio.sleep(0.01)
        assert snapshot is not None
        assert snapshot.status == "completed"
        assert len(snapshot.workspace_artifacts) == 1
        assert len(snapshot.effect_receipts) == 1

        artifact = snapshot.workspace_artifacts[0]
        receipt = snapshot.effect_receipts[0]
        assert artifact.verifier_status == receipt.status == "passed"
        assert artifact.outbound_flow_outcome is not None
        assert receipt.outbound_flow_outcome == artifact.outbound_flow_outcome
        outcome = artifact.outbound_flow_outcome
        assert outcome.status == "approval_required"
        assert outcome.atomic_requirement_count == len(outcome.rules)
        assert outcome.covered_count == outcome.atomic_requirement_count
        assert outcome.unsupported_count == outcome.conflict_count == 0
        assert outcome.reachable_terminal_count == outcome.terminal_count
        assert outcome.human_approval_required is True
        assert outcome.legal_opinion is False
        assert outcome.original_inputs_modified is False
        assert outcome.external_action == "none"
        assert all(check.passed for check in artifact.checks)
        assert artifact.source_file_refs == ["forte-ba23e986a9c7e8d8"]

        _, content = await runtime.get_workspace_artifact(
            "outbound-owner", snapshot.run_id, artifact.artifact_id
        )
        with zipfile.ZipFile(io.BytesIO(content)) as package:
            document = package.read("word/document.xml").decode("utf-8")
        assert document.count("<w:tbl>") >= 6
        assert "来源规则账本" in document
        assert "最终合规审批未发生" in document
        assert "这是流程设计，不是拨号、CRM/短信执行，也不是法律意见" in document
        assert _forte_digests() == before

        public = runtime.public_snapshot(snapshot).model_dump(mode="json")
        public_outcome = public["effect_receipts"][0]["outbound_flow_outcome"]
        assert public_outcome["atomic_requirement_count"] == outcome.atomic_requirement_count
        assert public_outcome["external_action"] == "none"
        assert "content_sha256" not in json.dumps(public, ensure_ascii=False)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_tc07_runtime_keeps_file_verification_legal_gate_and_human_review_separate(
    tmp_path: Path,
) -> None:
    before = _forte_digests()
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        LegalDelegationPlanner(),
        LegalDelegationAnalyst(),
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
        started = await runtime.start(
            "legal-owner",
            HarnessRunStart(
                idempotency_key="tc07-derived-legal-runtime-0001",
                instruction=TC07_INSTRUCTION,
            ),
        )
        snapshot = None
        for _ in range(1_000):
            candidate = await runtime.get("legal-owner", started.run.run_id)
            if candidate.status in {"waiting_input", "completed", "stopped", "failed"}:
                snapshot = candidate
                break
            await asyncio.sleep(0.01)
        assert snapshot is not None
        assert snapshot.status == "completed"
        assert len(snapshot.workspace_artifacts) == 2
        assert len(snapshot.effect_receipts) == 1

        receipt = snapshot.effect_receipts[0]
        assert receipt.status == "passed"
        assert receipt.business_gate_outcome is not None
        assert receipt.business_gate_outcome.outcome_kind == "legal_delegation_review"
        assert receipt.business_gate_outcome.failed_gate_count == 3
        assert receipt.legal_review_outcome is not None
        assert receipt.legal_review_outcome.status == "review_required"
        assert receipt.legal_review_outcome.document_count == 6
        assert receipt.legal_review_outcome.assessment_count == 126
        assert receipt.legal_review_outcome.high_risk_document_count == 6
        assert receipt.legal_review_outcome.signing_evidence_count == 0
        assert receipt.legal_review_outcome.human_review_required is True

        for artifact in snapshot.workspace_artifacts:
            assert artifact.verifier_status == "passed"
            assert artifact.business_gate_outcome == receipt.business_gate_outcome
            assert artifact.legal_review_outcome == receipt.legal_review_outcome
            assert all(check.passed for check in artifact.checks)

        by_name = {item.file_name: item for item in snapshot.workspace_artifacts}
        _, report = await runtime.get_workspace_artifact(
            "legal-owner",
            snapshot.run_id,
            by_name["授权委托书风控报告.docx"].artifact_id,
        )
        with zipfile.ZipFile(io.BytesIO(report)) as package:
            report_xml = package.read("word/document.xml").decode("utf-8")
        assert report_xml.count("<w:tbl>") >= 8
        assert "不是正式法律意见" in report_xml
        assert "R05" in report_xml

        _, ledger = await runtime.get_workspace_artifact(
            "legal-owner",
            snapshot.run_id,
            by_name["授权委托书逐项核查台账.csv"].artifact_id,
        )
        rows = list(csv.DictReader(io.StringIO(ledger.decode("utf-8-sig"))))
        assert len(rows) == 126
        assert len({(row["文档ID"], row["规则ID"]) for row in rows}) == 126
        assert sum(row["规则ID"] == "R05" and row["状态"] == "triggered" for row in rows) == 6
        assert _forte_digests() == before

        public = runtime.public_snapshot(snapshot).model_dump(mode="json")
        public_legal = public["effect_receipts"][0]["legal_review_outcome"]
        assert public_legal["decision"] == "不得据此签署，必须法务复核"
        assert len(public_legal["documents"]) == 6
        assert len(public_legal["documents"][0]["assessments"]) == 21
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_runtime_close_cancels_and_awaits_pending_run_task() -> None:
    planner = WaitingPlanner()
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        planner,
        OnboardingAnalyst(),
    )
    closed = False
    try:
        started = await runtime.start(
            "alice",
            HarnessRunStart(
                idempotency_key="runtime-close-pending-task-0001",
                instruction=ONBOARDING_INSTRUCTION,
            ),
        )
        await asyncio.wait_for(planner.started.wait(), timeout=1)
        run_task = runtime._tasks[started.run.run_id]
        assert run_task.get_coro().__qualname__ == "HarnessRuntime._run"
        assert not run_task.done()

        await runtime.close()
        closed = True
        await asyncio.sleep(0)

        assert run_task.done()
        assert run_task.cancelled()
        assert started.run.run_id not in runtime._tasks
    finally:
        planner.release.set()
        if not closed:
            await runtime.close()


@pytest.mark.asyncio
async def test_blocking_effect_keeps_health_run_get_and_sse_responsive(
    tmp_path: Path,
) -> None:
    catalog = MainThreadCatalog(BenchmarkWorkspaceCatalog(FORTE_ROOT))
    engine = BlockingScenarioEffectEngine(catalog.owner_thread_id)
    runtime = HarnessRuntime(
        catalog,
        OnboardingPlanner(),
        OnboardingAnalyst(),
        effect_engine=engine,
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    app = create_app()
    app.state.harness_runtime = runtime
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/harness/runs",
                headers={"X-User-Id": "alice"},
                json={
                    "idempotency_key": "scenario-effect-responsive-0001",
                    "instruction": TC04_INSTRUCTION,
                },
            )
            assert response.status_code == 202
            run_id = response.json()["run"]["run_id"]

            for _ in range(200):
                if engine.started.is_set():
                    break
                await asyncio.sleep(0.01)
            assert engine.started.is_set()

            health = await asyncio.wait_for(client.get("/v1/health"), timeout=1)
            current = await asyncio.wait_for(
                client.get(
                    f"/v1/harness/runs/{run_id}",
                    headers={"X-User-Id": "alice"},
                ),
                timeout=1,
            )
            assert health.status_code == 200
            assert current.status_code == 200
            snapshot = await runtime.get("alice", run_id)
            start_events = [
                event
                for event in snapshot.events
                if event.event_name == "deterministic_office_tool_started"
            ]
            assert len(start_events) == 1
            assert start_events[0].details["scenario_id"] == "TC-04"
            assert start_events[0].details["frozen_source_file_count"] == 46
            assert start_events[0].details["progress_percent"] is None
            assert not snapshot.workspace_artifacts

            stream = await stream_harness_events(
                run_id=run_id,
                owner_id="alice",
                runtime=runtime,
                after=start_events[0].sequence - 1,
            )
            chunk = await asyncio.wait_for(anext(stream.body_iterator), timeout=1)
            if isinstance(chunk, bytes):
                chunk = chunk.decode("utf-8")
            assert "event: deterministic_office_tool_started" in chunk
            await stream.body_iterator.aclose()

            await asyncio.wait_for(
                runtime._apply_scenario_effect("alice", run_id, round_number=1),
                timeout=1,
            )
            assert engine.execute_calls == 1

            engine.release.set()
            settled = await _wait_for_settled(runtime, "alice", run_id)
            assert settled.effect_receipts[0].status == "passed"
            assert settled.effect_receipts[0].scenario_id == "TC-04"
            assert len(settled.workspace_artifacts) == 1
            assert len(
                [
                    event
                    for event in settled.events
                    if event.event_name == "deterministic_office_tool_started"
                ]
            ) == 1
            assert engine.execute_calls == 1
    finally:
        engine.release.set()
        await runtime.close()


@pytest.mark.asyncio
async def test_effect_failure_emits_ordered_failure_fact_without_artifact(
    tmp_path: Path,
) -> None:
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        OnboardingPlanner(),
        OnboardingAnalyst(),
        effect_engine=FailingScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
        started = await runtime.start(
            "alice",
            HarnessRunStart(
                idempotency_key="scenario-effect-failure-event-0001",
                instruction=ONBOARDING_INSTRUCTION,
            ),
        )
        settled = await _wait_for_settled(runtime, "alice", started.run.run_id)

        assert settled.status == "failed"
        assert not settled.workspace_artifacts
        assert not settled.effect_receipts
        names = [event.event_name for event in settled.events]
        assert names.index("deterministic_office_tool_started") < names.index(
            "scenario_effect_failed"
        )
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_tc01_verified_artifact_is_not_blocked_by_pdf_layout_or_scope_noise(
    tmp_path: Path,
) -> None:
    analyst = NoisyOnboardingAnalyst()
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        NoisyOnboardingPlanner(),
        analyst,
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
        started = await runtime.start(
            "alice",
            HarnessRunStart(
                idempotency_key="tc01-layout-scope-regression-0001",
                instruction=ONBOARDING_INSTRUCTION,
            ),
        )
        snapshot = await _wait_for_settled(runtime, "alice", started.run.run_id)

        assert snapshot.status == "completed"
        assert analyst.calls == 1
        assert len(snapshot.workspace_artifacts) == 1
        assert snapshot.workspace_artifacts[0].verifier_status == "passed"
        assert len(snapshot.workspace_artifacts[0].checks) == 5
        assert all(check.passed for check in snapshot.workspace_artifacts[0].checks)
        assert snapshot.effect_receipts[0].status == "passed"
        assert all(branch.status == "completed" for branch in snapshot.branches)
        assert all(not round_item.evidence_gaps for round_item in snapshot.rounds)
        assert not snapshot.decision_requests
        assert snapshot.result is not None
        assert len(snapshot.result.findings) == 3
        assert all(
            "范围外" not in finding.title for finding in snapshot.result.findings
        )
        assert all(finding.review is None for finding in snapshot.result.findings)
        event_names = [event.event_name for event in snapshot.events]
        assert "analysis_scope_filtered" in event_names
        assert "decision_gate_suppressed" in event_names
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_verified_artifact_survives_rejected_analyst_output(tmp_path: Path) -> None:
    runtime = HarnessRuntime(
        BenchmarkWorkspaceCatalog(FORTE_ROOT),
        OnboardingPlanner(),
        RejectedOnboardingAnalyst(),
        effect_engine=ScenarioEffectEngine(),
        artifact_store=RunWorkspaceArtifactStore(tmp_path / "run-workspaces"),
    )
    try:
        started = await runtime.start(
            "alice",
            HarnessRunStart(
                idempotency_key="scenario-effect-runtime-rejected-analysis-0001",
                instruction=ONBOARDING_INSTRUCTION,
            ),
        )
        snapshot = await _wait_for_settled(runtime, "alice", started.run.run_id)

        assert snapshot.analysis_receipt is not None
        assert snapshot.analysis_receipt.called is True
        assert snapshot.analysis_receipt.output_used is False
        assert snapshot.effect_receipts[0].status == "passed"
        assert snapshot.workspace_artifacts[0].verifier_status == "passed"
        assert snapshot.workspace_artifacts[0].original_inputs_modified is False
        assert [item.event_name for item in snapshot.events].index(
            "deterministic_verification_completed"
        ) < [item.event_name for item in snapshot.events].index(
            "analysis_structure_rejected"
        )
    finally:
        await runtime.close()


def test_scope_validator_rebinds_only_a_uniquely_implied_plan_unit() -> None:
    workspace = BenchmarkWorkspaceCatalog(FORTE_ROOT).public_workspace()
    files = [item for folder in workspace["folders"] for item in folder["files"]]
    schedule_ref = next(
        item["file_ref"] for item in files if item["display_label"] == ONBOARDING_LABEL
    )
    rules_ref = next(
        item["file_ref"]
        for item in files
        if item["display_label"] == "入职物资权限软件分配.pdf"
    )
    plan = HarnessRuntime._compile_plan(
        HarnessPlanCandidate(
            summary="核对入职资料",
            selection_reason="两份资料共同决定匹配结果。",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id="read-schedule",
                    title="读取名单",
                    objective="读取名单",
                    input_file_refs=[schedule_ref],
                    tool="table.inspect",
                ),
                HarnessPlanCandidateUnit(
                    unit_id="read-rules",
                    title="读取规则",
                    objective="读取规则",
                    input_file_refs=[rules_ref],
                    tool="file.read",
                ),
                HarnessPlanCandidateUnit(
                    unit_id="compare",
                    title="交叉匹配",
                    objective="交叉匹配",
                    input_file_refs=[schedule_ref, rules_ref],
                    tool="evidence.verify",
                ),
            ],
        )
    )
    finding = HarnessFinding(
        plan_unit_id="read-schedule",
        title="需要联合核对",
        detail="结论同时使用名单和规则。",
        file_refs=[schedule_ref, rules_ref],
        evidence_quotes=[
            HarnessEvidenceQuote(
                file_ref=schedule_ref,
                role="observed",
                label="名单",
                quote="王子涵 | 3月23日 (周一) | 设计",
            )
        ],
    )
    result = HarnessTaskResult(
        summary="联合核对",
        findings=[finding],
        follow_ups=[],
        review_required=True,
    )

    normalized = HarnessRuntime._validate_candidate_result_scope(
        result,
        [{"file_ref": schedule_ref}, {"file_ref": rules_ref}],
        plan,
    )
    assert normalized.findings[0].plan_unit_id == "compare"

    ambiguous = result.model_copy(
        update={
            "findings": [
                finding.model_copy(
                    update={"plan_unit_id": None, "file_refs": [schedule_ref]}
                )
            ]
        }
    )
    with pytest.raises(HarnessPlanError, match="共享资料"):
        HarnessRuntime._validate_candidate_result_scope(
            ambiguous,
            [{"file_ref": schedule_ref}, {"file_ref": rules_ref}],
            plan,
        )
