# 处理路径与真实等待 Evidence · 2026-08-20

- 状态：`Verified`（仅限本地固定报价、Demo 2 路由写入与一次当前模型连通样本）
- 用户反馈：[`USER-FEEDBACK-20260820-04`](../sources/USER-FEEDBACK-20260820-04-processing-path-realism.md)
- 关联决策：[`DR-0006`](../decisions/DR-0006-deterministic-quote-calculation.md)、[`DR-0008`](../decisions/DR-0008-demo2-explainable-admission.md)、[`DR-0011`](../decisions/DR-0011-demo2-route-impact.md)

## 1. 问题复现

旧 API access log 只能看到 Demo 2 route POST 和 Conversation SSE 均为 200，无法判断是否调用模型。运行 Snapshot 显示 Demo 2 选择后仍为 `execution_status=not_started`；报价 Thread 的用户消息和确定性回答创建时间相差约 3.6 ms。两条路径都没有调用模型，但旧前台都像普通 Agent 操作，造成“秒执行”的错误理解。

## 2. 实现事实

- `ChatMessage.processing` 记录 `path/label/elapsed_ms/model`；前台在完成消息下持续显示处理来源与实际耗时。
- 确定性报价显示“服务端公式核算，未调用大模型”。
- 通用问答与业务规划在真实请求等待期间显示“正在调用 deepseek-v4-pro”，完成后保留模型名和真实模型调用耗时。
- Demo 2 主动作改为“记录本轮方式”，同时显示“规则路由，不调用大模型”；POST 后仍为 `not_started`。
- API runtime log 记录处理路径、是否调用模型、模型名、耗时、Thread 与活动视图，不记录消息正文、Key、Prompt 或思维链。
- Conversation 不再按每两个字固定 sleep 模拟流式输出；只保留 `sleep(0)` 调度点，不制造可见等待。

## 3. 本地运行证据

同一重启后的 API 进程、当前配置模型 `deepseek-v4-pro`：

```text
assistant_processing path=deterministic_formula model_called=False model=none elapsed_ms=0 active_view=quote
assistant_processing path=language_model model_called=True model=deepseek-v4-pro elapsed_ms=4237 active_view=document
demo2_route_selection path=policy_engine model_called=false elapsed_ms=2 replay=false
```

请求端计时：固定报价核算约 17 ms 完成，消息元数据为 `<1 ms` 公式处理；真实模型通用问答约 4242 ms 完成，消息元数据为 4237 ms；Demo 2 路由写入约 7 ms，返回 `execution_status=not_started`。这些是最终重启后的一次本机样本，不是延迟 SLA。

## 4. 自动化

- Python 聚焦：`39 passed (1.74s)`，覆盖确定性报价 `processing` 与模型回答 `processing` 持久化，以及 Demo 2 相关协议/服务回归。
- 完整 Python：`151 passed, 1 skipped (3.59s)`。
- system Edge 聚焦：报价工作台 + Demo 2 `13 passed (46.6s)`；覆盖可见“未调用大模型”和“记录本轮方式”。
- `uv run ruff check ...`、`pnpm --dir apps/web lint`、`pnpm --dir apps/web build`、治理测试 `4 passed` 与 `git diff --check` 通过。

## 5. 边界

本证据不证明模型质量、Token 消耗、供应商稳定性或延迟 SLA；没有增加人为等待。Demo 2 仍没有真实 Worker、Adaptive Swarm Runtime 或 Connector。确定性报价瞬时完成是预期行为，只有处理来源不可见才是本轮修复的问题。
