# LLM API Smoke Evidence 2026-08-11

| 字段 | 内容 |
| --- | --- |
| Evidence ID | `LLM-API-SMOKE-20260811` |
| Date | 2026-08-11，Asia/Shanghai |
| Model | `deepseek-v4-pro` |
| Adapter | `AutoDLActionParser`，OpenAI-compatible `/chat/completions` |
| Status | `Verified connectivity`，仅限通用问答文本路径 |

用户在 Git 忽略的根目录 `.env` 中配置了 LLM endpoint、key 和模型名。检查只确认字段已配置和模型为 `deepseek-v4-pro`，没有读取、输出或提交 endpoint 与 key。

实际验证两层路径：

1. 直接调用 `AutoDLActionParser.answer_general()`，要求只返回标记；结果为 `{"ok": true, "model": "deepseek-v4-pro", "response": "API_OK"}`。
2. 通过真实 FastAPI 创建 Thread，再调用 `/v1/threads/{id}/messages/stream`；收到 `message.created → assistant.status → message.started → message.delta → message.completed`，最终内容包含 `LLM_API_E2E_OK`，没有 `event:error` 或 `action.proposed`。

该 smoke 证明当前 OpenAI-compatible 文本请求和 Conversation SSE 可以连通，不证明结构化规划、JSON mode 回退、修复重试、ActionCandidate、长期 Task、风险治理、工具调用、真实 Connector、质量、稳定性或供应商 SLA。固定 Demo 1 Task start 本身不调用 LLM。
