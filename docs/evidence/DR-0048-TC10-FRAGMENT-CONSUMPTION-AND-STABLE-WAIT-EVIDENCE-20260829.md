# DR-0048 TC-10 规范片段消费与稳定 Effect 等待 Evidence

## 当前结论

`Limited Verified`。片段级来源消费、动态转人工规则、同行冲突门、单调时钟 Effect 等待、公共前台 fixture、本地全量工程门、真实 PostgreSQL TC-10 顺序门与 [PR #64](https://github.com/Dickey007s/lenovo_agent/pull/64) 远端 durable 门已通过。实现提交 [`a77fd1b`](https://github.com/Dickey007s/lenovo_agent/commit/a77fd1b)；最终合并 SHA 与最新 master 重启由交付回执记录。

## 可复现负例

- 旧实现以 `recognized_numbers` 跳过已识别整行。在 TIME 行末追加“高龄客户必须立即转人工”后，结果仍为 34 条，没有独立 rule、guard 或 edge。
- 在同一位置追加未知规范、冲突顺序或第二套频次参数，也不会进入剩余片段检查。
- 用户给出的 86 项定向集合曾出现 1 条偶发失败；失败测试单独重跑通过，定位为固定 500 次 `sleep(0)` 先耗尽，而非 Effect 本身失败。

## 实现事实

- 解析器把规范行拆成保留同一服务端 locator 的可审计片段，并逐片段记录已消费语义。
- 同行高龄/重病转人工片段生成独立 `DISPUTE` rule，进入现有 graph compiler 和 DOCX/Verifier。
- 同行未知规范、身份/录音顺序冲突、禁呼时段冲突和频次冲突 fail closed。
- 公共动态 manifest 由服务端 builder 生成，浏览器 fixture 不另写规则数字或 mapped IDs。
- `_wait_for_effect` 与 `_wait_for_settled` 使用单调 deadline；超时回执包含可诊断的 Snapshot 事实。

## 已完成的定向门

- `uv run pytest -q tests/unit/test_outbound_flow_effect.py`：36 passed。
- 用户指定四文件集合：90 passed in 211.03s。
- 原 flaky 测试独立重复 10 次：10/10 passed，每次约 1.53 至 1.81 秒。
- TC-10 动态前台门：新增同行规则、guard、edge 可展开；最终工程数字将在合并前补录。

## 动态公开事实

- canonical Operations-008 没有改动，继续是 DR-0047 已记录的 15 组/34 条、31 节点/36 边/7 守卫/7 终态。
- 公共动态变体同时修改时段、频次并在既有 TIME 行追加高龄转人工要求，得到 15 组/35 条、31 节点/37 边/8 守卫/7 终态，35/35 条覆盖。
- 新增规则保留 locator `专业性说明.md:L22`，excerpt 为“高龄客户必须立即转人工。”，并映射 `out-guard-extra-human-1` 与 `out-edge-response-extra-human-1`。

## 本地工程门

- 配置真实 PostgreSQL 的 `uv run pytest -q`：270 passed in 312.16s。
- `uv run pytest -q tests/integration/test_postgres_agent_control_loop.py -k tc10`：1 passed, 8 deselected。
- `uv run ruff check .`、`pnpm --dir apps/web lint`、`pnpm --dir apps/web build` 与公共 fixture `--check`：全部通过。
- `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts`：50 passed；TC-10 canonical/dynamic/failure 为 3/3。
- canonical UI 数字和布局没有变化，因此不改写 DR-0047 的历史 1440/390 截图；本轮完整 Playwright 继续执行同一桌面/移动几何与无溢出断言。

## 远端门

- PR #64 的 `durable-agent-control-loop` 在实现提交上通过，job [`98986856245`](https://github.com/Dickey007s/lenovo_agent/actions/runs/33211909915/job/98986856245)，耗时 49 秒。
- 文档收口提交会再次触发同一远端门；合并后从最新 master 以 PostgreSQL 重启，并保留 DR-0047 canonical live Run 作为历史复读，不额外消费 Provider。

## 不证明什么

本 Evidence 不证明最新监管、合规法律意见、生产审批、真实外呼、CRM/短信写入、Connector、多 Worker、多实例并发或用户理解提升。canonical 来源与 `DR-0047` 历史 Evidence 保持不变。
