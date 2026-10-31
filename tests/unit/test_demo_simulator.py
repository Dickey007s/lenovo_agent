"""Demo mode runs the real Run pipeline with offline planner/analyst: no model is ever called."""

import asyncio

import pytest

from services.api.app.application import demo_simulator
from services.api.app.application.benchmark_workspace_catalog import BenchmarkWorkspaceCatalog
from services.api.app.application.harness_runtime import HarnessRunStart, HarnessRuntime

FORK = (
    "请分别核对以下要求：\n"
    "1. 阅读《外卖商户BD岗位JD.docx》，摘出学历和沟通要求，附原文。\n"
    "2. 准备吴嘉木的软件权限清单，并评估一个尚未批准的变更请求：希望给他开通 GitHub Enterprise。"
    "先核对《3月20日-4月20日入职时间表.csv》的个人备注与《入职物资权限软件分配.pdf》的覆盖规则；"
    "变更请求若与明确的不开通备注冲突，说明为什么需要负责人决定，不要自行裁决。\n"
    "3. 核对绵阳长城发展融资担保有限公司那笔其他应收往来的银行到账回单，判断是否已实际收到款。"
    "如果资料库没有到账回单，明确记为缺少来源。\n只在页面分析，不修改文件。"
)
SWARM = (
    "本周办公盘点。请分别核对以下要求：\n"
    "1. 阅读《3月20日-4月20日入职时间表.csv》，摘出吴嘉木的入职日期，附原文。\n"
    "2. 阅读《入职物资权限软件分配.pdf》，摘出通用软件配置，附原文。\n"
    "3. 阅读《外卖商户BD岗位JD.docx》，摘出学历要求，附原文。\n"
    "4. 在以上三项都完成后，汇总成一份本周办公要点，逐项注明出处。\n只在页面整理，不修改原文件。"
)


class NeverCalled:
    model = "never"

    async def plan(self, **_):
        raise AssertionError("real planner was called")

    async def analyze(self, **_):
        raise AssertionError("real analyst was called")


async def _run(instruction: str, key: str, **extra):
    runtime = HarnessRuntime(BenchmarkWorkspaceCatalog(), NeverCalled(), NeverCalled())
    try:
        start = await runtime.start(
            "demo-user",
            HarnessRunStart(
                instruction=instruction, idempotency_key=key, simulated=True,
                loop={"max_rounds": 3, "max_files_per_round": 8, "max_model_calls": 8, "deadline_seconds": 120},
                **extra,
            ),
        )
        for _ in range(400):
            run = await runtime.get("demo-user", start.run.run_id)
            if run.status in {"completed", "failed", "stopped"} or (run.status == "waiting_input" and not extra):
                break
            await asyncio.sleep(0.05)
        return run, runtime.public_snapshot(run)
    finally:
        await runtime.close()


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(demo_simulator, "PLAN_DELAY_SECONDS", 0)
    monkeypatch.setattr(demo_simulator, "ANALYSIS_DELAY_SECONDS", 0)


@pytest.mark.asyncio
async def test_fork_has_one_unit_waiting_on_owner_and_one_missing_source():
    run, public = await _run(FORK, "sim-fork-0001", execution_policy="automatic_readonly", output_preference="analysis_only")
    assert run.simulated and not run.validation_errors and run.status == "completed"
    nodes = {node.node_id: node for node in public.workflow.nodes}
    assert nodes["u1"].status == "done"
    assert {node.ref_kind for node in nodes.values() if node.kind == "human_gate"} == {"judgment", "missing"}
    assert nodes["deliver"].status == "pending"
    assert public.model_receipt.called is False


@pytest.mark.asyncio
async def test_independent_items_run_as_one_wave_then_the_summary_follows():
    run, public = await _run(SWARM, "sim-swarm-0001", execution_policy="automatic_readonly", output_preference="analysis_only")
    assert run.status == "completed" and not run.validation_errors
    assert [wave.label for wave in public.workflow.waves] == ["第 1 波 · 3 个子 Agent 并行", "第 2 波 · 1 个子 Agent 并行"]
    assert all(node.status == "done" for node in public.workflow.nodes)
