# DR-0035：用真实运行工作区成果和确定性验证关闭场景效果门

## 状态

`Limited Verified`。适用范围是固定 FORTE 公开输入、顺序单 Runtime、当前 12 个本地确定性办公能力和 3 个外部边界场景。它不等于生产 Tool Gateway、任意文件写入、多 Worker 或外部动作。

## 场景与来源

- 用户：需要判断 Office Agent 是否真正完成办公任务的方案负责人和演示者。
- 触发：固定三轮经常提前停止，而且过去的 `completed`、引用或模型文本不能证明任务效果。
- 来源：`USER-FEEDBACK-20260827-SCENARIO-EFFECT-GATE`、固定 FORTE commit `345c1ec1487139db9dd319787fa9405ba85d1869`、[`FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825.md`](../testing/FORTE-PUBLIC-OFFICE-TASK-TEST-CASES-20260825.md)。
- 完成条件：TC-01 至 TC-15 有机器可执行效果账本；本地场景生成真实文件并由代码复核；外部场景不伪造结果；六个优先场景有真实 `deepseek-v4-pro` Run。

## 决策

### 1. 预算不再绑定三轮假设

默认预算改为 `12 rounds / 16 files per round / 30 model calls / 7200 active seconds`；服务端上限改为 `24 / 24 / 60 / 14400`。四个边界仍彼此独立，人工等待、显式暂停和终态继续冻结 active elapsed，deadline 仍不硬取消在途 HTTP 请求。

### 2. 把“效果”建模为独立服务端事实

新增 `workspace_artifacts[]` 与 `effect_receipts[]`。每份运行工作区文件记录媒体类型、字节数、来源 refs、Validator、逐项检查、版本、轮次、下载路由、`original_inputs_modified=false`、`review_required=true` 和 `external_action=none`。`EffectReceipt` 固定记录 `state/action/observation/cost/result`，不能由前端从文案猜测。

新增事件：

- `deterministic_office_tool_started`
- `run_workspace_artifact_written`
- `deterministic_verification_completed`
- `scenario_effect_bounded`

新增 Owner-scoped 下载：`GET /v1/harness/runs/{run_id}/artifacts/{artifact_id}`。下载前重新核对 Store 元数据和内容完整性，返回 `private, no-store` 与 `nosniff`。

### 3. 模型质量、确定性效果和 Run 终态分开

Planner 仍真实调用并通过服务端计划校验。被允许的确定性办公工具在计划校验后执行，不额外消耗模型预算；其成果不依赖 Analyst 文案是否能通过 JSON/证据定位。Analyst 随后形成可解释 Finding。若 Analyst 未采用，Artifact 和 EffectReceipt 仍保留，界面必须同时显示“成果已验证”和“分析说明待处理”，不能把其中一项冒充另一项。

为减少模型结构截断，Analyst 默认最多返回 3 条 Finding、2 条 follow-up；只有真实业务冲突才输出 review。若模型把 Finding 绑错计划单元，服务端只在文件 refs 唯一指向一个 Unit 时重绑并记录 `analysis_scope_normalized`；多候选或越界仍 fail closed。

### 4. 本地能力与外部边界

当前确定性能力注册表覆盖 TC-01、02、04、05、06、07、10、11、12、13、14、15。注册表由用户原始指令匹配，不出现在产品 Scenario 选择器中，也不读取 `task.md`、rubric 或 solution。原始 FORTE 输入永远只读，成果只写 `.runtime/run-workspaces` 的隔离目录。

TC-03、08、09 需要远程 SQL、Web 或 Scheduler/cron。缺少明确授权和稳定依赖时返回 `blocked_external_boundary`，Artifact 数为 0，`external_action=none`。

## 前台交互影响

1. 用户仍从一个文件管理器和自由任务输入开始，不先选 Demo。
2. 成果区显示真实文件名、类型、大小、检查通过数和下载按钮。
3. “查看逐项检查”展开确定性规则；“查看效果回执”展开 state/action/observation/cost/result 和禁止副作用。
4. 外部边界显示“缺少已授权的外部连接”和“没有生成伪造结果”，不显示下载按钮。
5. 模型调用采用状态继续单独显示。Artifact 通过不把未采用模型响应改成已采用，Run waiting/failed 也不删除已经验证的 Artifact。
6. 普通界面隐藏绝对路径、完整 digest、原始 Provider 响应、Prompt/CoT、内部命令和源 `task.md`。

## 后端事实映射

| UI 事实 | 服务端权威 | 变化 |
| --- | --- | --- |
| 真实成果文件 | `workspace_artifacts[]` | `run_workspace_artifact_written` |
| 检查通过/失败 | `verifier_status`、`checks[]` | `deterministic_verification_completed` |
| 工具做了什么 | `effect_receipts[].state/action/observation/cost/result` | `deterministic_office_tool_started` |
| 没有外部动作 | Artifact/Receipt `external_action=none` | Snapshot 权威，SSE 仅投影 |
| 外部依赖阻断 | Receipt `status=blocked_external_boundary` | `scenario_effect_bounded` |
| 文件下载 | Artifact `download_path` + Owner/run/artifact Store 校验 | 无 Snapshot 变化 |

## 验证与边界

- 初始 live baseline：六个优先场景 `0/6` 通过，原因是确定性工具挂在 Analyst 采用之后；负例保留。
- 修复后：六个优先场景 `6/6` 生成真实成果并通过下载、逐项检查、模型调用和零副作用效果门。
- 本地固定效果门：12 个本地场景通过，3 个外部场景按边界阻断。
- PostgreSQL 顺序重启验证覆盖 Artifact 元数据、EffectReceipt 和文件内容恢复；这不是数据库内独立 Artifact ledger、CAS 或多实例安全。
- Python/前端/截图/PR 的最终数字见 [`SCENARIO-EFFECT-GATE-20260827.md`](../evidence/SCENARIO-EFFECT-GATE-20260827.md)。
- 自动化不能证明真实用户理解；代码场景使用固定本地受控命令，不是生产多租户安全沙箱；TC-04 的 105 条测试和标准库 trace coverage 不是完整数据库/HTTP 集成覆盖率。
