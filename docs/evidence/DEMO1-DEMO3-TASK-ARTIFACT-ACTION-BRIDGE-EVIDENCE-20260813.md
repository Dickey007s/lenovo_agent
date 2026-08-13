# Demo 1 → Demo 3 已验证工件动作桥接证据

| 字段 | 内容 |
| --- | --- |
| Evidence ID | `TASK-ARTIFACT-ACTION-BRIDGE-20260813` |
| Date | 2026-08-13 |
| Status | `Verified`（限定于固定客户 A、最终客户回复草稿、当前 L4 策略、Email Simulator 与被测前台路径） |
| Decision | [`DR-0007`](../decisions/DR-0007-task-artifact-action-bridge.md) |
| Source | [`USER-FEEDBACK-20260813-DEMO-BRIDGE-05`](../sources/USER-FEEDBACK-20260813-07-task-artifact-action-bridge.md)、`MEETING-DECK-0716-V2-01`、`SCRIPT-V5-202607` |
| Implementation | `d827f29`；文档基线 `d1cc746` |

## 1. 验证问题与成功标准

| 验证问题 | 成功标准 | 证据入口 |
| --- | --- | --- |
| 历史或未验证工件能否准备动作 | 必须返回冲突，不创建 Run | `tests/integration/test_task_runtime.py` |
| 动作是否绑定最终事实 | Task/Commit/Artifact/Verification 的 ID、版本和 digest 全部进入 `TaskArtifactBinding` | `tests/integration/test_task_action_bridge.py` |
| 模型能否替换目标或正文 | 专用路由从绑定 reply draft 和固定演示目标重建 ActionCandidate，不调用 LLM parser | 路由集成测试；`UnusedParser` fail-fast |
| 创建重试是否重复 Run | 同 Owner+key+同事实返回同 Run；同 key 不同事实 409 | RunService 与真实 HTTP 路由集成测试 |
| 绑定变化后能否继续审批/执行 | 重新验证失败后 Action 失效，状态 failed，旧审批/Permit 不可用 | Task action bridge 集成测试 |
| 用户是否知道“准备”不是“发送” | 完成态和 Gate 都明确尚未发送；Gate 显示绑定版本、目标、L4 原因和确认后果 | system Edge E2E 与 Gate 截图 |
| 批准路径是否经过完整治理链 | `WAITING_APPROVAL → READY_TO_AUTHORIZE → Permit → ToolGateway → EXECUTED`；Audit 含 `PERMIT_ISSUED/TOOL_EXECUTED` | Python 集成、浏览器 E2E、Run/Audit GET |
| 拒绝是否破坏已完成成果 | Run 进入 DENIED，不执行工具；Task 仍 committed 且三个最终工件不变 | 独立浏览器拒绝用例 |
| 结果是否诚实表达 Simulator | 完成说明包含 Email Simulator、未连接真实邮箱、未向真实客户发送 | 浏览器 E2E 与结果截图 |

## 2. 最终运行记录

| 检查 | 命令 | 最终结果 |
| --- | --- | --- |
| Python 全量 | `uv run pytest -q` | `112 passed, 1 skipped in 4.11s` |
| Python 静态检查 | `uv run ruff check .` | `Passed` |
| 前端 lint | `pnpm --dir apps/web lint` | `Passed` |
| Next.js 构建 | `pnpm --dir apps/web build` | `Passed` |
| 治理门槛 | `uv run pytest -q tests/unit/test_reporting_governance.py` | `4 passed in 0.03s` |
| Demo 1 浏览器 | `pnpm --dir apps/web test:e2e -- apps/web/e2e/demo1-runtime.spec.ts` | `13 passed (1.0m)` |
| 完整浏览器 | `pnpm --dir apps/web test:e2e` | `29 passed (1.4m)` |
| Diff whitespace | `git diff --check` | `Passed`（只有 Windows LF/CRLF 提示） |

浏览器用例启动真实本地 FastAPI `8011`、Next.js `3011` 与 system Edge，使用内存 Store。它通过真实 HTTP、Run 状态、Audit、Conversation continuation 与 DOM 验证固定纵切；不代表 PostgreSQL 恢复或真实 Connector。

## 3. 视觉证据

| 截图 | 尺寸与文件大小 | SHA-256 | 支持的判断 |
| --- | --- | --- | --- |
| [`task-artifact-action-gate-1440.png`](screenshots/task-artifact-action-gate-1440.png) | `1440 x 900`，172203 bytes | `59082B2157C8C2020D6163C0CF62589326DA5F34D443631C4423862FFB6FF5A9` | 同屏显示完成的三项成果、绑定回复版本、L4 原因、外部目标与确认边界；Gate 完整停靠在右侧而非窄列溢出 |
| [`task-artifact-action-result-1440.png`](screenshots/task-artifact-action-result-1440.png) | `1440 x 900`，168713 bytes | `B563F6C5FDF39457C26E0F287D2854E91365312C7272B5B13938C50668631A28` | Task 保持完成，Agent 说明治理链和 Email Simulator 结果，并明确没有真实发送 |

截图是自动化运行证据，不是可用性研究。它不证明普通用户已理解 L4、版本绑定或两段确认，也不证明移动端动作 Gate 已完成专门设计。

## 4. 后端事实链

```text
TaskSnapshot committed
  → TaskCommit 包含 reply ArtifactVersion
  → VerificationReport passed
  → TaskArtifactBinding
  → ProposedActionSpec(payload digest + creation idempotency)
  → RiskAssessment L4 / Evidence / Approval
  → one-time Permit
  → ToolGateway
  → Email Simulator
  → deterministic Conversation result
```

Run 的批准、拒绝或执行不会回写 Task 状态。Task Commit 是成果事实，Run 是派生业务动作事实；绑定只允许后者引用前者的一个不可变版本。

## 5. 当前边界

- 只支持固定客户 A 的最终 `reply_draft → email.send`，不是通用 Artifact Action registry。
- 收件人 `customer@example.com` 是固定演示地址；没有读取真实 CRM 联系人或真实邮箱目录。
- 工具执行仅为 `email_simulator`，没有真实发送。
- 当前 E2E 使用内存 Store；未验证 Task 派生 Run 与创建幂等在 PostgreSQL/API 重启、多实例或网络响应丢失时的恢复。
- 前端只验证 1440 桌面 Gate；移动端、键盘完整路径和无障碍读屏专项仍待独立验证。
- 自动化证明预设协议与投影一致，不证明真实用户理解、确认质量、效率提升或业务价值。
- Demo 2 Adaptive Swarm 仍是目标架构；本轮只建立其未来输出工件可复用的治理接口形状。

## 6. 提交与 PR

- Implementation commit：`d827f29`
- Documentation commit：`d1cc746`
- PR：[#12](https://github.com/Dickey007s/lenovo_agent/pull/12)，base 为 PR #11 分支
