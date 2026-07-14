import json

import httpx
from pydantic import ValidationError

from packages.contracts import ActionCandidate
from services.api.app.application.conversation_models import ConversationPlan


class ModelConfigurationError(RuntimeError):
    pass


class ModelOutputError(RuntimeError):
    pass


class AutoDLActionParser:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60,
        thinking_mode: str = "disabled",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.thinking_mode = thinking_mode

    async def parse(self, message: str) -> ActionCandidate:
        if not self.base_url or not self.api_key:
            raise ModelConfigurationError("LLM_BASE_URL 和 LLM_API_KEY 尚未配置")

        schema = json.dumps(ActionCandidate.model_json_schema(), ensure_ascii=False)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是办公动作解析器。只提取业务事实，不判断风险、权限或审批。"
                        "所有枚举值必须原样使用 JSON Schema 中的英文值，禁止翻译。"
                        "输出必须是符合以下 JSON Schema 的单个 JSON 对象：" + schema
                    ),
                },
                {"role": "user", "content": message},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": 1200,
            "thinking": {"type": self.thinking_mode},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            if response.status_code == 400 and "response_format" in response.text:
                # Some AutoDL OpenAI-compatible gateways reject JSON mode even though
                # the underlying model can emit JSON. Keep the schema prompt and strict
                # Pydantic validation, but retry without that optional protocol field.
                payload.pop("response_format", None)
                response = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
            response.raise_for_status()
        try:
            content = response.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.removeprefix("```json").removeprefix("```")
                content = content.removesuffix("```").strip()
            return ActionCandidate.model_validate(json.loads(content))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            raise ModelOutputError("模型未返回合法的 ActionCandidate JSON") from exc

    async def plan(
        self,
        message: str,
        history: list[dict[str, str]],
        trusted_context: dict | None = None,
    ) -> ConversationPlan:
        """Generate a grounded conversational response and an optional typed office action."""
        if not self.base_url or not self.api_key:
            raise ModelConfigurationError("LLM_BASE_URL 和 LLM_API_KEY 尚未配置")

        schema = json.dumps(ConversationPlan.model_json_schema(), ensure_ascii=False)
        system = (
            "你是企业办公 Agent，需要用中文与用户进行自然、简洁、专业的多轮对话。"
            "必须把最新一条用户消息作为当前唯一任务；除非用户明确延续上一动作，禁止重复上一轮的动作或回复。"
            "你可以准备邮件、文档、报价表、任务、日历、报销核查和 CRM 内容。"
            "active_workspace 是用户当前正在编辑的内容，可能尚未保存；必须优先理解并保留其中未要求修改的字段。"
            "当用户要求编辑工作区时，artifact 必须返回修改后的字段，assistant_response 只写一句很短的状态，不要复述生成物正文。"
            "只提取业务事实，不得自行判断权限、风险、审批结果或声称已执行真实工具。"
            "对普通问答 action 和 artifact 可为 null。如用户要求准备可视化办公内容，必须返回 artifact。"
            "如用户要求实际发送、创建任务、创建邀请、更新 CRM 或发起报销补件，"
            "必须返回对应 ActionCandidate，但 assistant_response 只能说已准备并等待确认。"
            "动作对应关系："
            "发送邮件=send_email/email.send/external_effect；"
            "邮件草稿=draft_email/email.draft/draft_only；"
            "会议纪要或周报=draft_document/document.draft/draft_only；"
            "报价草稿=quote_draft/quote.draft/draft_only；"
            "创建内部任务=create_internal_task/task.create/internal_system_write；"
            "创建会议=create_calendar_invite/calendar.invite/internal_system_write或external_effect；"
            "报销核查=expense_inspect/expense.read/read_only；"
            "通知补材料=expense_request_evidence/expense.request_evidence/internal_system_write；"
            "CRM更新=update_crm_stage/crm.opportunity.update/internal_system_write。"
            "artifact.content 建议字段："
            "mail 使用 to/cc/subject/body/attachments；"
            "document 使用 document_type/sections；"
            "quote 使用 quote_id/customer/currency/valid_until/items/total；"
            "tasks 使用 tasks；calendar 使用 month/selected_date/events，events 中每项使用 id/title/date/start/end/attendees/location/agenda；"
            "expense 使用 case_id/owner/amount/invoices/anomalies；crm 使用 customer/opportunity_id/before/suggested_stage/next_step。"
            "内部事实、金额、发票号、报价和权限只能使用 trusted_context 中给出的内容。"
            "如果 trusted_context 没有某个事实，必须表述为待查询或待确认，禁止编造记录。"
            "sources 只可引用 trusted_context 列出的来源。"
            "所有英文枚举必须严格使用 JSON Schema 中的值。"
            "返回符合以下 JSON Schema 的单个 JSON 对象：" + schema
        )
        context_message = json.dumps(trusted_context or {}, ensure_ascii=False)
        messages = [
            {"role": "system", "content": system},
            {"role": "system", "content": "trusted_context（只读模拟企业数据）：" + context_message},
            *history[-12:],
        ]
        if not messages or messages[-1].get("content") != message:
            messages.append({"role": "user", "content": message})
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 3200,
            "thinking": {"type": self.thinking_mode},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            if response.status_code == 400 and "response_format" in response.text:
                payload.pop("response_format", None)
                response = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
            response.raise_for_status()
        try:
            content = response.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.removeprefix("```json").removeprefix("```")
                content = content.removesuffix("```").strip()
            return ConversationPlan.model_validate(json.loads(content))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as first:
            # OpenAI-compatible gateways do not always enforce JSON schema. Give
            # the model one deterministic repair turn, then validate again.
            payload["temperature"] = 0
            payload["messages"] = [
                *messages,
                {"role": "assistant", "content": content if "content" in locals() else "{}"},
                {
                    "role": "user",
                    "content": (
                        "上一个 JSON 未通过严格 Schema 校验。"
                        "请仅返回修正后的完整 JSON，不要解释。校验摘要："
                        + str(first)[:1200]
                    ),
                },
            ]
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                repaired = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
                repaired.raise_for_status()
            try:
                content = repaired.json()["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = content.removeprefix("```json").removeprefix("```")
                    content = content.removesuffix("```").strip()
                return ConversationPlan.model_validate(json.loads(content))
            except (
                KeyError,
                IndexError,
                TypeError,
                json.JSONDecodeError,
                ValidationError,
            ) as exc:
                raise ModelOutputError("模型未返回合法的办公对话计划") from exc

    async def respond_after_action(
        self,
        original_request: str,
        history: list[dict[str, str]],
        execution_result: dict,
    ) -> str:
        """Let the Agent observe a terminal action result and close the loop itself."""
        if not self.base_url or not self.api_key:
            raise ModelConfigurationError("LLM_BASE_URL 和 LLM_API_KEY 尚未配置")
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是企业办公 Agent。用户刚刚对一个受控动作作出决定，"
                        "系统已返回真实的 Simulator 执行或拒绝结果。请根据结果用中文简洁回应用户，"
                        "只需明确成功、失败或被拒绝。风险等级和判断规则已在确认前展示，"
                        "最终回复中禁止再次复述风险等级或判断规则。"
                        "不得声称结果中不存在的事实，也不要输出 JSON。"
                    ),
                },
                *history[-10:],
                {
                    "role": "user",
                    "content": (
                        "原始请求："
                        + original_request
                        + "\n受控动作结果："
                        + json.dumps(execution_result, ensure_ascii=False)
                    ),
                },
            ],
            "temperature": 0.2,
            "max_tokens": 700,
            "thinking": {"type": self.thinking_mode},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
        try:
            return response.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelOutputError("模型未返回合法的执行结果回应") from exc

    async def answer_general(
        self,
        message: str,
        history: list[dict[str, str]],
        current_datetime: str,
    ) -> str:
        """Answer public knowledge directly without forcing an office ActionSpec."""
        if not self.base_url or not self.api_key:
            raise ModelConfigurationError("LLM_BASE_URL 和 LLM_API_KEY 尚未配置")
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是企业办公平台中的通用助手。直接回答用户最新的非敏感通识问题，"
                        "用中文、简洁且有帮助。不要重复或延续历史中的办公动作，不要虚构企业内部数据。"
                        f"当前本地日期时间为 {current_datetime}。"
                    ),
                },
                *history[-6:],
            ],
            "temperature": 0.3,
            "max_tokens": 900,
            "thinking": {"type": self.thinking_mode},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
        try:
            return response.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelOutputError("模型未返回合法的通识问答回应") from exc
