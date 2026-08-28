# DR-0040：TC-02 真实项目副本有界 ReAct 控制结构

- 状态：Implemented，真实 Provider、下载后独立复测与 PR #51 远端门已通过；合并待本分支收尾
- 日期：2026-08-28
- Source：`USER-FEEDBACK-20260828-TC02-REAL-PROJECT-REFACTOR`
- Scenario：`SCENARIO-026`

## 决策

1. TC-02 仍由 Workspace-first 通用入口触发，不增加 Scenario 选择器；服务端固定适配器只匹配原始用户指令和 algorithm-013 的七个 allowlisted 输入。
2. 适配器必须把七个真实输入复制到隔离 Run Workspace。`workflow.py`、`llm.py`、`tools.py`、`requirements.txt`、`search_agent.log` 逐字保留；`config.py` 和 `main.py` 在副本内修改，新增 `react_agent.py`、测试与审计文件。
3. 新主入口运行有界 `ReActSearchAgent` 控制结构，复用原 `WorkflowConfig`、`LLMClient`、`ToolRegistry`、`WorkflowState` 与原五节点业务逻辑。公开轨迹只有 `iteration/action/observation`，不输出私有 CoT。
4. 当前 `DefaultReActPolicy` 确定性地依次选择 Planner 已规划的工具；`action_policy` 是可替换接口。本轮没有实现或证明模型根据 Observation 在副本内自主选择下一动作。外层真实 `deepseek-v4-pro` Planner/Analyst 回执也不属于工件内部策略，前台和 Evidence 必须分开陈述。
5. ZIP 必须含完整副本、`CHANGESET.patch`、`changes.json`、中文改动说明、自测卡、测试源码及文本/JSON 回执。Verifier 比较声明和实际执行测试 ID，不把当前数量写成永久上限。
6. Artifact 增加可选服务端事实 `key_outputs_label` 与 `self_test`。前台据此区分“代码包”和“测试与改动说明”，显示文件变更、策略边界、自测命令、通过项、失败信号和人工合并边界。
7. 只要编译、测试、文件完整性或清单一致性有一项失败，Artifact 与 EffectReceipt 均为失败；失败包可下载排查，但前台必须明确不要合并并建议重新创建 TC-02 任务。
8. 两份 Artifact 使用同一组 12 个服务端 `check_id`。单卡保留各自的 12/12 投影，Run 汇总、任务结语、SSE 与 EffectReceipt 必须按 ID 去重，写成“2 份成果共享 12 项确定性检查，12/12 通过”，不得写成 24 个独立检查。

## 前后端事实

| 前台 | 服务端事实 | 不允许推断 |
| --- | --- | --- |
| 完整项目副本 | Artifact 文件、`check-react-full-copy`、下载 ZIP 内容门 | 已改写 FORTE 原树 |
| 哪些文件修改/保留 | `key_outputs[]/key_outputs_label`、`changes.json`、diff | 任意项目都能自动重构 |
| 有界 ReAct 控制结构 | `main.py`、`react_agent.py`、迭代与动作测试 | 包内模型已自主 ReAct，或私有推理已公开 |
| 默认策略与模型回执 | `changes.json.internal_action_policy/model_driven_internal_react_verified`、Artifact `key_outputs[]/execution_summary`、外层调用回执 | 外层 Planner/Analyst 就是副本内部 action policy |
| 自己如何验证 | Artifact `self_test` 与包内 `TC-02自测卡.md` | 用户已经实际执行命令 |
| 检查通过数 | Artifact `checks[].check_id/passed`；事件 `check_count/passed_check_count`；EffectReceipt observation | 相同清单投影到两个文件就产生 24 个独立检查 |
| 可以人工合并 | `verifier_status=passed`、逐项检查和 `review_guidance` | 系统已写回仓库或创建 PR |
| 本次未调用网络 | 固定测试代码路径、回执、无凭据/代理环境 | OS 级网络隔离或通用沙箱 |

## 备选方案

- 延续 9 文件迷你包：拒绝。它只证明另一个 Demo 可运行，不能证明真实项目被改造。
- 只把原文件装进 ZIP、测试仍跑迷你模块：拒绝。文件存在不证明主入口或原业务规则参与执行。
- 直接运行任意仓库测试：拒绝。当前没有生产安全沙箱、依赖安装治理或任意命令授权。

## 验证门

- 真实 Provider Run 必须记录 Planner/Analyst 的 `called/output_used/elapsed_ms`。
- 下载 ZIP 后在第二个临时目录独立解压、编译、执行测试，并核对原样保留文件的 SHA-256。
- `test_receipt.json` 的声明/执行测试 ID 集合必须一致；主入口不得仍只调用 `SearchWorkflow`。
- E2E 必须看到隔离副本、文件变更、自测卡、人工合并边界和真实网络边界；390 px 无页面级横向溢出。
- Unit/E2E 必须断言 24 个卡片级投影只形成 12 个唯一 `check_id`，回执和顶层 UI 不出现 `24/24`。
