from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class WorkflowState(TypedDict, total=False):
    run_id: str
    status: str
    authorization_confirmed: bool


@dataclass(frozen=True)
class WorkflowCallbacks:
    evaluate: Callable[[str], Awaitable[str]]
    execute: Callable[[str], Awaitable[str]]
    panel: Callable[[str], dict]


class AgentWorkflow:
    def __init__(
        self,
        callbacks: WorkflowCallbacks,
        checkpointer: BaseCheckpointSaver,
    ) -> None:
        self.callbacks = callbacks
        self.graph = self._build().compile(checkpointer=checkpointer)

    def _build(self) -> StateGraph:
        async def evaluate(state: WorkflowState) -> WorkflowState:
            status = await self.callbacks.evaluate(state["run_id"])
            return {"status": status}

        def route_after_evaluate(state: WorkflowState) -> str:
            status = state["status"]
            if status in {"WAITING_EVIDENCE", "WAITING_APPROVAL"}:
                return "human_gate"
            if status == "READY_TO_AUTHORIZE":
                return "execute" if state.get("authorization_confirmed") else "authorization_gate"
            return "end"

        def human_gate(state: WorkflowState) -> WorkflowState:
            expected = {
                "WAITING_EVIDENCE": "evidence_submitted",
                "WAITING_APPROVAL": "approval_submitted",
            }[state["status"]]
            resume = interrupt(
                {
                    "kind": expected,
                    "status": state["status"],
                    "panel": self.callbacks.panel(state["run_id"]),
                }
            )
            if not isinstance(resume, dict) or resume.get("kind") != expected:
                raise ValueError(f"Expected resume kind: {expected}")
            return {"authorization_confirmed": False}

        def authorization_gate(state: WorkflowState) -> WorkflowState:
            resume = interrupt(
                {
                    "kind": "authorization_requested",
                    "status": state["status"],
                    "panel": self.callbacks.panel(state["run_id"]),
                }
            )
            if not isinstance(resume, dict) or resume.get("kind") != "authorization_requested":
                raise ValueError("Expected resume kind: authorization_requested")
            return {"authorization_confirmed": True}

        async def execute(state: WorkflowState) -> WorkflowState:
            status = await self.callbacks.execute(state["run_id"])
            return {"status": status}

        builder = StateGraph(WorkflowState)
        builder.add_node("evaluate", evaluate)
        builder.add_node("human_gate", human_gate)
        builder.add_node("authorization_gate", authorization_gate)
        builder.add_node("execute", execute)
        builder.add_edge(START, "evaluate")
        builder.add_conditional_edges(
            "evaluate",
            route_after_evaluate,
            {
                "human_gate": "human_gate",
                "authorization_gate": "authorization_gate",
                "execute": "execute",
                "end": END,
            },
        )
        builder.add_edge("human_gate", "evaluate")
        builder.add_edge("authorization_gate", "evaluate")
        builder.add_edge("execute", END)
        return builder

    async def start(self, run_id: str, thread_id: str) -> None:
        await self.graph.ainvoke(
            {"run_id": run_id, "authorization_confirmed": False},
            config={"configurable": {"thread_id": thread_id}},
        )

    async def resume(self, thread_id: str, kind: str) -> None:
        await self.graph.ainvoke(
            Command(resume={"kind": kind}),
            config={"configurable": {"thread_id": thread_id}},
        )

    async def state(self, thread_id: str) -> dict:
        snapshot = await self.graph.aget_state(
            config={"configurable": {"thread_id": thread_id}}
        )
        return {
            "values": dict(snapshot.values),
            "next": list(snapshot.next),
            "interrupts": [item.value for task in snapshot.tasks for item in task.interrupts],
        }
