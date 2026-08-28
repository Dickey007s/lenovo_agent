"""Build the fixed TC-02 refactor from the real FORTE project copy."""

from __future__ import annotations

import difflib
import json
import re
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class ReactRefactorBuild:
    archive_files: dict[str, bytes | str]
    report: bytes
    checks: tuple[tuple[str, str, bool, str], ...]
    test_count: int
    compile_ms: int
    test_ms: int
    execution_ok: bool
    changed_files: tuple[str, ...]
    unchanged_files: tuple[str, ...]


CONFIG_EXTENSION = """

    # ReAct loop boundary. Kept on the existing config contract so callers can
    # tune the loop without learning a second configuration object.
    max_iterations = 6

    def __init__(self, max_iterations=None):
        if max_iterations is not None:
            self.max_iterations = max_iterations
        if type(self.max_iterations) is not int or not 1 <= self.max_iterations <= 20:
            raise ValueError("max_iterations must be an integer between 1 and 20")
"""


REACT_AGENT = textwrap.dedent(
    r'''
    """Bounded ReAct controller over the original search-agent contracts.

    The public trace contains only selected actions and tool observations. It
    deliberately excludes private model reasoning and provider responses.
    """

    import json
    from dataclasses import dataclass, field

    from config import WorkflowConfig
    from llm import LLMClient
    from tools import ArxivSearchTool, KnowledgeBaseTool, ToolRegistry, WebSearchTool
    from workflow import (
        QueryAnalysisNode,
        ResultRankingNode,
        SearchExecutionNode,
        SearchPlanNode,
        SummaryGenerationNode,
        WorkflowState,
    )


    @dataclass
    class ReActRunResult:
        state: WorkflowState
        trace: list[dict] = field(default_factory=list)
        stopped_reason: str = "finish"


    class DefaultReActPolicy:
        """Choose each planned tool once, then finish.

        A production policy can replace this class without changing the loop,
        tool registry, state, or business-rule nodes.
        """

        def next_action(self, state, trace):
            attempted = {
                item["action"]["tool"]
                for item in trace
                if item["action"]["type"] == "search"
            }
            for tool_name in state.selected_tools:
                if tool_name not in attempted:
                    return {
                        "action": "search",
                        "tool": tool_name,
                        "query": state.rewritten_query,
                    }
            return {"action": "finish"}


    class ReActSearchAgent:
        """Run a bounded action/observation loop over the original project."""

        def __init__(
            self,
            config=None,
            llm_client=None,
            tool_registry=None,
            action_policy=None,
        ):
            self.config = config or WorkflowConfig()
            self.llm_client = llm_client or LLMClient(
                model=self.config.llm_model,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens,
                api_base=self.config.llm_api_base,
            )
            self.tool_registry = tool_registry or self._default_registry()
            self.action_policy = action_policy or DefaultReActPolicy()

        def _default_registry(self):
            registry = ToolRegistry()
            registry.register(
                "web_search",
                WebSearchTool(
                    engine=self.config.web_search_engine,
                    top_k=self.config.web_search_top_k,
                ),
            )
            registry.register(
                "knowledge_base",
                KnowledgeBaseTool(top_k=self.config.knowledge_base_top_k),
            )
            registry.register(
                "arxiv_search",
                ArxivSearchTool(top_k=self.config.arxiv_search_top_k),
            )
            return registry

        @staticmethod
        def _parse_action(payload):
            if isinstance(payload, str):
                payload = json.loads(payload)
            if not isinstance(payload, dict):
                raise ValueError("action payload must be an object")
            allowed_keys = {"action", "tool", "query"}
            if set(payload) - allowed_keys:
                raise ValueError("action payload contains unsupported fields")
            action = payload.get("action")
            if action not in {"search", "finish"}:
                raise ValueError(f"unsupported action: {action}")
            if action == "search" and not isinstance(payload.get("tool"), str):
                raise ValueError("search action requires a tool")
            return payload

        def _filter_and_rank(self, accumulated_results):
            execution = SearchExecutionNode(self.config, self.tool_registry)
            threshold = self.config.result_quality_threshold
            filtered = execution._filter_by_quality(accumulated_results, threshold)
            if len(filtered) < self.config.min_results_after_filter and threshold > 0:
                filtered = execution._filter_by_quality(
                    accumulated_results, threshold / 2
                )
            state = WorkflowState(filtered_results=filtered)
            return ResultRankingNode(self.config).execute(state).ranked_results

        def run(self, query):
            state = WorkflowState(original_query=query)
            state = QueryAnalysisNode(self.config, self.llm_client).execute(state)
            state = SearchPlanNode(self.config, self.tool_registry).execute(state)
            trace = []
            accumulated_results = []

            for iteration in range(1, self.config.max_iterations + 1):
                action = self._parse_action(
                    self.action_policy.next_action(state, list(trace))
                )
                if action["action"] == "finish":
                    trace.append(
                        {
                            "iteration": iteration,
                            "action": {"type": "finish"},
                            "observation": {"result_count": len(state.ranked_results)},
                        }
                    )
                    state = SummaryGenerationNode(
                        self.config, self.llm_client
                    ).execute(state)
                    return ReActRunResult(state, trace, "finish")

                tool_name = action["tool"]
                tool = self.tool_registry.get_tool(tool_name)
                query_text = str(action.get("query") or state.rewritten_query)
                results = tool.search(query_text)
                accumulated_results.extend(results)
                state.raw_results = list(accumulated_results)
                state.filtered_results = self._filter_and_rank(accumulated_results)
                state.ranked_results = list(state.filtered_results)
                trace.append(
                    {
                        "iteration": iteration,
                        "action": {
                            "type": "search",
                            "tool": tool_name,
                            "query": query_text,
                        },
                        "observation": {
                            "returned": len(results),
                            "accepted": len(state.ranked_results),
                        },
                    }
                )

            state = SummaryGenerationNode(self.config, self.llm_client).execute(state)
            return ReActRunResult(state, trace, "max_iterations")
    '''
).strip() + "\n"


MAIN = textwrap.dedent(
    r'''
    """CLI entry for the bounded ReAct search agent."""

    import logging

    from config import WorkflowConfig
    from react_agent import ReActSearchAgent


    def setup_logging(config):
        logging.basicConfig(
            level=getattr(logging, config.log_level),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[logging.StreamHandler()],
        )


    def main():
        config = WorkflowConfig()
        setup_logging(config)
        agent = ReActSearchAgent(config=config)
        queries = [
            "What is the difference between React and Vue.js?",
            "Latest news about artificial intelligence",
            "How to implement a binary search tree in Python",
        ]
        for query in queries:
            result = agent.run(query)
            print("\n" + "=" * 60)
            print(f"Query: {query}")
            print(f"Answer: {result.state.final_answer}")
            print(f"Stopped: {result.stopped_reason}")
            print(f"Public trace: {result.trace}")


    if __name__ == "__main__":
        main()
    '''
).strip() + "\n"


TESTS = textwrap.dedent(
    r'''
    import json
    import os
    import sys
    import unittest
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(PROJECT_ROOT))

    from config import WorkflowConfig
    from react_agent import DefaultReActPolicy, ReActSearchAgent
    from tools import SearchResult, ToolRegistry
    from workflow import QueryAnalysisNode, SearchWorkflow, SummaryGenerationNode, WorkflowState


    class StubLLM:
        def __init__(self, rewrite="Python GIL details", summary="Complete answer."):
            self.rewrite = rewrite
            self.summary = summary

        def generate_with_prompt(self, system_prompt, user_input, **kwargs):
            lowered = system_prompt.lower()
            if "classifier" in lowered:
                return "factual"
            if "rewrite" in lowered:
                return self.rewrite
            if "decompose" in lowered:
                return user_input
            return self.summary


    class ScriptedPolicy:
        def __init__(self, actions):
            self.actions = list(actions)

        def next_action(self, state, trace):
            return self.actions.pop(0)


    class CountingTool:
        def __init__(self, results=None):
            self.calls = []
            self.results = results or [
                SearchResult("One", "local://one", "snippet", "local", 0.9)
            ]

        def search(self, query):
            self.calls.append(query)
            return list(self.results)


    def result(index, source="web", score=0.9):
        return SearchResult(
            str(index), f"local://{source}/{index}", "snippet", source, score
        )


    def build_agent(actions, *, config=None, tool=None, llm=None):
        registry = ToolRegistry()
        registry.register("search", tool or CountingTool())
        agent = ReActSearchAgent(
            config=config or WorkflowConfig(),
            llm_client=llm or StubLLM(),
            tool_registry=registry,
            action_policy=ScriptedPolicy(actions),
        )
        agent.config.query_rewrite_enabled = False
        return agent


    class ReActProjectTests(unittest.TestCase):
        def test_config_accepts_minimum_iteration_bound(self):
            self.assertEqual(WorkflowConfig(max_iterations=1).max_iterations, 1)

        def test_config_accepts_maximum_iteration_bound(self):
            self.assertEqual(WorkflowConfig(max_iterations=20).max_iterations, 20)

        def test_config_rejects_zero_iterations(self):
            with self.assertRaises(ValueError):
                WorkflowConfig(max_iterations=0)

        def test_config_rejects_more_than_twenty_iterations(self):
            with self.assertRaises(ValueError):
                WorkflowConfig(max_iterations=21)

        def test_normal_finish_stops_before_iteration_cap(self):
            outcome = build_agent([{"action": "finish"}]).run("q")
            self.assertEqual(outcome.stopped_reason, "finish")
            self.assertEqual(outcome.trace[-1]["action"], {"type": "finish"})

        def test_iteration_cap_stops_repeated_search(self):
            action = {"action": "search", "tool": "search", "query": "q"}
            outcome = build_agent(
                [action, action, action], config=WorkflowConfig(max_iterations=2)
            ).run("q")
            self.assertEqual(outcome.stopped_reason, "max_iterations")
            self.assertEqual(len(outcome.trace), 2)

        def test_non_object_action_is_rejected(self):
            with self.assertRaises(ValueError):
                build_agent([json.dumps(["search"])]).run("q")

        def test_private_reasoning_field_is_rejected(self):
            with self.assertRaisesRegex(ValueError, "unsupported fields"):
                build_agent([{"action": "finish", "thought": "private"}]).run("q")

        def test_unknown_action_is_rejected(self):
            with self.assertRaisesRegex(ValueError, "unsupported action"):
                build_agent([{"action": "delete"}]).run("q")

        def test_unknown_tool_is_rejected(self):
            with self.assertRaisesRegex(ValueError, "not found"):
                build_agent([{"action": "search", "tool": "missing"}]).run("q")

        def test_original_tool_registry_is_actually_called(self):
            tool = CountingTool()
            outcome = build_agent(
                [
                    {"action": "search", "tool": "search", "query": "changed"},
                    {"action": "finish"},
                ],
                tool=tool,
            ).run("q")
            self.assertEqual(tool.calls, ["changed"])
            self.assertEqual(outcome.trace[0]["observation"]["returned"], 1)

        def test_public_trace_contains_only_action_and_observation(self):
            outcome = build_agent(
                [
                    {"action": "search", "tool": "search", "query": "q"},
                    {"action": "finish"},
                ]
            ).run("q")
            serialized = json.dumps(outcome.trace).lower()
            self.assertEqual(
                set(outcome.trace[0]), {"iteration", "action", "observation"}
            )
            self.assertNotIn("thought", serialized)
            self.assertNotIn("reasoning", serialized)

        def test_original_query_drift_falls_back(self):
            config = WorkflowConfig()
            state = QueryAnalysisNode(config, StubLLM(rewrite="Java threads")).execute(
                WorkflowState(original_query="Python GIL")
            )
            self.assertFalse(state.rewrite_accepted)
            self.assertEqual(state.rewritten_query, "Python GIL")

        def test_original_quality_filter_relaxes_threshold(self):
            tool = CountingTool([result(1, score=0.3), result(2, score=0.2)])
            agent = build_agent([{"action": "finish"}], tool=tool)
            ranked = agent._filter_and_rank(tool.results)
            self.assertEqual([item.title for item in ranked], ["1"])

        def test_original_source_quota_is_preserved(self):
            tool = CountingTool(
                [result(i, "web") for i in range(5)]
                + [result(9, "knowledge_base")]
            )
            config = WorkflowConfig()
            config.source_quota_per_type = 2
            agent = build_agent([{"action": "finish"}], config=config, tool=tool)
            ranked = agent._filter_and_rank(tool.results)
            self.assertEqual(len([item for item in ranked if item.source == "web"]), 2)
            self.assertEqual(len(ranked), 3)

        def test_original_summary_truncates_at_sentence_boundary(self):
            config = WorkflowConfig()
            config.max_summary_length = 30
            node = SummaryGenerationNode(
                config,
                StubLLM(summary="First sentence. Second sentence is too long."),
            )
            state = node.execute(WorkflowState(original_query="q"))
            self.assertTrue(state.answer_truncated)
            self.assertEqual(state.final_answer, "First sentence....")

        def test_default_policy_is_deterministic_and_replaceable(self):
            state = WorkflowState(
                rewritten_query="q", selected_tools=["web_search", "knowledge_base"]
            )
            policy = DefaultReActPolicy()
            first = policy.next_action(state, [])
            second = policy.next_action(
                state,
                [{"action": {"type": "search", "tool": first["tool"]}}],
            )
            final = policy.next_action(
                state,
                [
                    {"action": {"type": "search", "tool": first["tool"]}},
                    {"action": {"type": "search", "tool": second["tool"]}},
                ],
            )
            self.assertEqual([first["tool"], second["tool"]], ["web_search", "knowledge_base"])
            self.assertEqual(final, {"action": "finish"})

        def test_legacy_workflow_remains_importable_for_review(self):
            self.assertTrue(callable(SearchWorkflow))

        def test_main_entry_uses_react_not_legacy_workflow(self):
            source = (PROJECT_ROOT / "main.py").read_text(encoding="utf-8")
            self.assertIn("ReActSearchAgent", source)
            self.assertNotIn("SearchWorkflow", source)

        def test_fixed_environment_contains_no_credentials_or_proxies(self):
            absent = ("OPENAI_API_KEY", "DATABASE_DSN")
            disabled = ("HTTP_PROXY", "HTTPS_PROXY")
            self.assertTrue(all(name not in os.environ for name in absent))
            self.assertTrue(all(not os.environ.get(name) for name in disabled))


    if __name__ == "__main__":
        unittest.main()
    '''
).strip() + "\n"


def _unified_diff(original: str, revised: str, file_name: str) -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            revised.splitlines(keepends=True),
            fromfile=f"a/{file_name}",
            tofile=f"b/{file_name}",
        )
    )


def build_real_react_refactor(
    sources: dict[str, bytes],
    run_command: Callable[..., tuple[int, str, int]],
) -> ReactRefactorBuild:
    """Copy the pinned source project, modify it, and execute its real tests."""

    required = (
        "config.py",
        "llm.py",
        "main.py",
        "requirements.txt",
        "search_agent.log",
        "tools.py",
        "workflow.py",
    )
    missing = [name for name in required if name not in sources]
    if missing:
        raise ValueError(f"missing TC-02 source files: {missing}")

    source_text = {
        name: sources[name].decode("utf-8", errors="strict") for name in required
    }
    config_text = source_text["config.py"].rstrip() + CONFIG_EXTENSION
    changed_files = (
        "config.py",
        "main.py",
        "react_agent.py",
        "tests/test_react_agent.py",
        "CHANGESET.patch",
        "changes.json",
        "改动说明.md",
        "TC-02自测卡.md",
        "TEST_RECEIPT.txt",
        "test_receipt.json",
    )
    unchanged_files = (
        "workflow.py",
        "llm.py",
        "tools.py",
        "requirements.txt",
        "search_agent.log",
    )
    project_files: dict[str, bytes | str] = {
        "config.py": config_text,
        "llm.py": sources["llm.py"],
        "main.py": MAIN,
        "requirements.txt": sources["requirements.txt"],
        "search_agent.log": sources["search_agent.log"],
        "tools.py": sources["tools.py"],
        "workflow.py": sources["workflow.py"],
        "react_agent.py": REACT_AGENT,
        "tests/test_react_agent.py": TESTS,
    }
    patch = "".join(
        (
            _unified_diff(source_text["config.py"], config_text, "config.py"),
            _unified_diff(source_text["main.py"], MAIN, "main.py"),
            _unified_diff("", REACT_AGENT, "react_agent.py"),
            _unified_diff("", TESTS, "tests/test_react_agent.py"),
        )
    )
    changes = {
        "schema_version": "tc02-react-refactor.v2",
        "source_project": "algorithm-013/input/search_agent_workflow",
        "changed_files": list(changed_files[:4]),
        "added_evidence_files": list(changed_files[4:]),
        "unchanged_contract_files": list(unchanged_files),
        "source_tree_modified": False,
        "network_access": False,
        "production_search_called": False,
        "internal_action_policy": "deterministic_default_with_injected_policy_interface",
        "model_driven_internal_react_verified": False,
    }
    project_files["CHANGESET.patch"] = patch
    project_files["changes.json"] = json.dumps(
        changes, ensure_ascii=False, indent=2
    ) + "\n"
    project_files["改动说明.md"] = textwrap.dedent(
        """
        # algorithm-013 搜索 Agent 有界 ReAct 控制结构说明

        这是 FORTE `search_agent_workflow` 的隔离副本，不会覆盖原数据集。

        - `config.py`：在原 `WorkflowConfig` 上加入 1 到 20 的 `max_iterations`。
        - `main.py`：主入口改走 `ReActSearchAgent`，固定五节点不再是唯一入口。
        - `react_agent.py`：复用原 LLM、ToolRegistry、WorkflowState 与五个业务节点，
          增加受限的 action/observation 循环；轨迹不记录私有思维过程。
        - 当前 `DefaultReActPolicy` 按规划工具依次执行；`action_policy` 可替换，
          但本包没有证明模型依据 Observation 自主选择下一动作。
        - `workflow.py`、`llm.py`、`tools.py`、`requirements.txt` 和日志原样保留，
          便于评审者逐文件比较和人工合并。

        当前只验证固定 algorithm-013 副本；没有联网、安装依赖、调用生产搜索，
        也不是可以执行任意仓库代码的通用沙箱。
        """
    ).strip() + "\n"
    project_files["TC-02自测卡.md"] = textwrap.dedent(
        """
        # TC-02 自测卡

        **输入**：把搜索 Agent 从固定 Workflow 重构为带迭代上限和轨迹的 ReAct 结构。

        **预期文件**：完整 `search_agent_workflow/`、`CHANGESET.patch`、
        `changes.json`、中文说明、测试、文本和 JSON 测试回执。

        **下载后命令**：

        ```bash
        python -m compileall -q search_agent_workflow
        python -m unittest discover -s search_agent_workflow/tests -v
        ```

        测试项、实际数量与失败信号以同目录的 `test_receipt.json` 为准。
        """
    ).strip() + "\n"

    import tempfile

    with tempfile.TemporaryDirectory(prefix="office-agent-tc02-") as directory:
        root = Path(directory)
        project_root = root / "search_agent_workflow"
        for name, value in project_files.items():
            target = project_root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(value, bytes):
                target.write_bytes(value)
            else:
                target.write_text(value, encoding="utf-8")
        compile_rc, compile_output, compile_ms = run_command(
            [sys.executable, "-m", "compileall", "-q", "search_agent_workflow"], cwd=root
        )
        test_rc, test_output, test_ms = run_command(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "search_agent_workflow/tests",
                "-v",
            ],
            cwd=root,
        )

    declared_test_ids = tuple(
        re.findall(r"^\s+def (test_[a-z0-9_]+)\(self\):", TESTS, flags=re.MULTILINE)
    )
    executed_test_ids = tuple(
        re.findall(r"^(test_[a-z0-9_]+) \(", test_output, flags=re.MULTILINE)
    )
    match = re.search(r"Ran (\d+) tests?", test_output)
    test_count = int(match.group(1)) if match else 0
    manifest_consistent = (
        test_count == len(declared_test_ids)
        and set(executed_test_ids) == set(declared_test_ids)
    )
    execution_ok = compile_rc == 0 and test_rc == 0 and manifest_consistent
    receipt_lines = [
        "# TC-02 真实项目测试回执",
        "",
        "- 执行对象：隔离 Run Workspace 中的完整 algorithm-013 项目副本。",
        f"- 编译：`python -m compileall -q search_agent_workflow`，退出码 {compile_rc}，{compile_ms} ms。",
        f"- 测试：`python -m unittest discover -s search_agent_workflow/tests -v`，退出码 {test_rc}，{test_ms} ms。",
        f"- 测试数量：{test_count}；结论：{'通过' if execution_ok else '失败，不得合并'}。",
        "- 本次固定测试未调用网络或生产搜索；未注入凭据和代理；依赖安装未执行。",
        "- 边界：runner 没有 OS 级 socket 隔离，不等于通用安全沙箱。",
        "- FORTE 原始源码：未修改。",
        "",
        "```text",
        test_output or compile_output or "命令没有返回输出。",
        "```",
    ]
    receipt = "\n".join(receipt_lines) + "\n"
    receipt_json = {
        "schema_version": "tc02-test-receipt.v2",
        "compile": {"exit_code": compile_rc, "elapsed_ms": compile_ms},
        "tests": {
            "exit_code": test_rc,
            "elapsed_ms": test_ms,
            "count": test_count,
            "declared_ids": list(declared_test_ids),
            "executed_ids": list(executed_test_ids),
            "manifest_consistent": manifest_consistent,
        },
        "network_access": False,
        "dependency_install": False,
        "production_search_called": False,
        "status": "passed" if execution_ok else "failed",
    }
    project_files["TEST_RECEIPT.txt"] = receipt
    project_files["test_receipt.json"] = json.dumps(
        receipt_json, ensure_ascii=False, indent=2
    ) + "\n"
    project_files["TC-02自测卡.md"] = textwrap.dedent(
        f"""
        # TC-02 自测卡

        **输入**：把搜索 Agent 从固定 Workflow 重构为带迭代上限和轨迹的 ReAct 结构。

        **预期文件**：完整 `search_agent_workflow/`、`CHANGESET.patch`、
        `changes.json`、中文说明、测试、文本和 JSON 测试回执。

        **下载后命令**：

        ```bash
        python -m compileall -q search_agent_workflow
        python -m unittest discover -s search_agent_workflow/tests -v
        ```

        **应看到**：当前清单声明的 {len(declared_test_ids)} 项测试全部通过，且
        `test_receipt.json` 中 `declared_ids` 与 `executed_ids` 一致。测试覆盖迭代边界、
        正常结束、到上限停止、非法动作、真实 ToolRegistry、公开轨迹，以及原有
        漂移/质量/配额/截断行为。测试可随风险扩展，不把当前数量当业务上限。

        **策略边界**：默认策略按已规划工具依次执行；测试证明策略接口可替换，
        不证明模型在副本内部根据 Observation 自主规划下一步。

        **失败信号**：退出码非 0、声明与执行测试 ID 不一致、缺少原项目文件、
        主入口仍只调用 `SearchWorkflow`，或测试开始要求网络/生产凭据。失败时不要合并。
        """
    ).strip() + "\n"

    report = textwrap.dedent(
        f"""
        # TC-02 测试与改动说明

        ## 交付结论

        {f'真实副本编译及当前 {test_count} 项测试全部通过。' if execution_ok else '测试未通过，代码包不得进入人工合并。'}
        FORTE 原始源码：未修改。
        Agent 修改的是隔离 Run Workspace 副本，FORTE 原文件没有被覆盖。

        ## 从什么变成什么

        原主入口只运行固定五节点 `SearchWorkflow`。新主入口运行有 1 到 20 次上限的
        `ReActSearchAgent` 控制结构：每轮由注入的 `action_policy` 选择下一动作，
        Controller 记录可审查的 action/observation，完成或达到上限即停止。
        轨迹不是模型思维过程。

        当前 `DefaultReActPolicy` 确定性地依次选择已规划工具；控制器提供可插拔
        `action_policy` 接口，但本次没有证明模型在副本内根据 Observation 自主选动作。
        外层 Run 的 `deepseek-v4-pro` Planner/Analyst 回执不属于这个内部策略。

        ## 文件与检查

        修改/新增：{', '.join(changed_files[:4])}。
        原样保留：{', '.join(unchanged_files)}。
        编译退出码 {compile_rc}；测试退出码 {test_rc}；共 {test_count} 项测试；
        总耗时 {compile_ms + test_ms} ms。

        ## 如何继续

        下载 ZIP 后先阅读 `CHANGESET.patch` 和 `改动说明.md`，再运行自测卡中的两条命令。
        通过后由代码评审者挑选提交或人工合并；系统没有写回原仓库，也没有发起 PR。

        ## 边界

        这是固定 algorithm-013 适配器，不是通用代码沙箱。本次固定测试没有调用网络、
        安装依赖或生产搜索，也没有注入凭据和代理；runner 仍不具备 OS 级 socket 隔离。
        测试通过证明这个固定副本满足已列契约，不证明可推广到任意项目。
        """
    ).strip().encode("utf-8")

    exact_unchanged = all(project_files[name] == sources[name] for name in unchanged_files)
    tests_expected = all(
        token in TESTS
        for token in (
            "test_config_accepts_minimum_iteration_bound",
            "test_config_accepts_maximum_iteration_bound",
            "test_iteration_cap_stops_repeated_search",
            "test_unknown_action_is_rejected",
            "test_unknown_tool_is_rejected",
            "test_original_tool_registry_is_actually_called",
            "test_public_trace_contains_only_action_and_observation",
            "test_original_query_drift_falls_back",
            "test_original_quality_filter_relaxes_threshold",
            "test_original_source_quota_is_preserved",
            "test_original_summary_truncates_at_sentence_boundary",
            "test_default_policy_is_deterministic_and_replaceable",
        )
    )
    checks = (
        ("check-react-full-copy", "完整复制真实项目", set(required) <= set(project_files), "七个 FORTE 输入文件全部进入隔离副本。"),
        ("check-react-contract-copy", "原契约文件逐字保留", exact_unchanged, "workflow、llm、tools、requirements 和日志与冻结输入逐字一致。"),
        ("check-react-main-entry", "主入口改走有界 ReAct", "ReActSearchAgent" in MAIN and "SearchWorkflow" not in MAIN, "固定五节点文件保留，但不再是唯一主入口。"),
        ("check-react-diff", "可机器审查改动", bool(patch) and '"changed_files"' in project_files["changes.json"], "ZIP 同时包含 unified diff 与 JSON 变更清单。"),
        ("check-react-compile", "完整副本编译", compile_rc == 0, compile_output or "compileall 无错误输出。"),
        ("check-react-tests", "测试清单与执行一致", test_rc == 0 and manifest_consistent and "OK" in test_output, f"声明并实际运行 {test_count} 项 unittest；测试 ID 集合一致。"),
        ("check-react-contract-tests", "风险契约测试齐全", tests_expected, "迭代、动作、工具、轨迹和四类原业务行为均有测试。"),
        ("check-react-cap", "迭代上限 1 到 20", "1 <= self.max_iterations <= 20" in config_text and "range(1, self.config.max_iterations + 1)" in REACT_AGENT, "配置与循环共同限制迭代次数。"),
        ("check-react-actions", "非法动作与工具拒绝", "unsupported action" in REACT_AGENT and "get_tool(tool_name)" in REACT_AGENT, "动作白名单和原 ToolRegistry 双重校验。"),
        ("check-react-trace", "只记录动作与观察", '"observation"' in REACT_AGENT and "private model reasoning" in REACT_AGENT, "公开轨迹不含私有 CoT。"),
        ("check-react-policy-boundary", "默认策略边界明确", "class DefaultReActPolicy" in REACT_AGENT and "action_policy or DefaultReActPolicy" in REACT_AGENT, "默认策略确定性执行已规划工具；接口可替换，不冒充内部模型自主 ReAct。"),
        ("check-react-no-network", "固定测试无网络调用", execution_ok, "本次代码路径仅编译和 unittest，未调用网络或生产搜索，未注入凭据和代理；不代表 OS 级隔离。"),
    )
    return ReactRefactorBuild(
        archive_files={f"search_agent_workflow/{name}": value for name, value in project_files.items()},
        report=report,
        checks=checks,
        test_count=test_count,
        compile_ms=compile_ms,
        test_ms=test_ms,
        execution_ok=execution_ok,
        changed_files=changed_files,
        unchanged_files=unchanged_files,
    )
