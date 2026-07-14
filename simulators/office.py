from datetime import UTC, datetime
from uuid import uuid4


class OfficeActionSimulator:
    """Deterministic side-effect simulator for non-email office capabilities."""

    name = "office_action_simulator"

    async def execute(self, capability: str, arguments: dict) -> dict:
        parameters = arguments.get("parameters", {})
        base = {
            "operation_id": f"sim_office_{uuid4().hex}",
            "capability": capability,
            "simulated": True,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if capability == "task.create":
            return base | {
                "task_id": f"TASK-{uuid4().hex[:6].upper()}",
                "assignee": parameters.get("assignee", "待指定"),
                "title": parameters.get("title", "Agent 生成任务"),
                "due_at": parameters.get("due_at"),
            }
        if capability == "calendar.invite":
            return base | {
                "event_id": f"CAL-{uuid4().hex[:6].upper()}",
                "title": parameters.get("title", "会议邀请"),
                "attendees": arguments.get("recipients", []),
                "start_at": parameters.get("start_at"),
            }
        if capability == "crm.opportunity.update":
            return base | {
                "opportunity_id": parameters.get("opportunity_id", "OPP-DEMO-001"),
                "before": parameters.get("before", "方案沟通"),
                "after": parameters.get("after", "合同谈判"),
            }
        if capability == "expense.request_evidence":
            return base | {
                "case_id": parameters.get("case_id", "BX-0412"),
                "requested_from": parameters.get("owner", "报销申请人"),
                "missing_items": parameters.get("missing_items", ["发票原件"]),
            }
        return base | {"parameters": parameters}
