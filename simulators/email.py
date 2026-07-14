from datetime import UTC, datetime
from uuid import uuid4


class EmailSimulator:
    name = "email_simulator"

    async def send(self, arguments: dict) -> dict:
        parameters = arguments.get("parameters", {})
        return {
            "message_id": f"sim_email_{uuid4().hex}",
            "accepted_recipients": list(arguments.get("recipients", [])),
            "resources": list(arguments.get("resources", [])),
            "subject": parameters.get("subject", ""),
            "body_digest_bound": bool(parameters.get("body")),
            "simulated": True,
            "timestamp": datetime.now(UTC).isoformat(),
        }
