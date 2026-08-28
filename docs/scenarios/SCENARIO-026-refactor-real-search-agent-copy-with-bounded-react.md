# SCENARIO-026：在真实搜索 Agent 副本上完成有界 ReAct 控制结构重构

## 用户与触发

- 用户：需要审阅、复测和合并 Agent 代码改造的软件工程师。
- 触发：在整个办公资料库输入“把搜索 Agent 从固定 Workflow 重构为带迭代上限和轨迹的 ReAct 结构。”
- 痛点：一个另造的迷你 Demo 即使测试全绿，也不能回答真实项目改了哪里、原业务逻辑是否保留、下载后能否独立复测。

## 主路径

1. Planner 从冻结整库索引选择 algorithm-013 的真实项目文件，服务端将七个输入复制到隔离 Run Workspace，FORTE 原树保持只读。
2. 固定 TC-02 适配器在副本内给 `WorkflowConfig` 增加迭代上限，改写主入口，新增有界 ReAct Controller；原 Workflow/LLM/ToolRegistry 文件仍保留供比较与复用。
3. 默认策略按 Planner 已规划的工具依次执行；`action_policy` 接口可替换。本场景不把外层 `deepseek-v4-pro` 回执写成副本内部策略，也不宣称模型已根据 Observation 自主决定下一动作。
4. 固定 runner 不安装依赖，不注入凭据与代理，执行 `compileall` 和项目内 unittest；Verifier 核对实际测试 ID、完整副本、diff、主入口、动作白名单、策略边界、轨迹和四类原业务规则。
5. 成果区先说明真实发生了什么，再分别显示“完整可运行项目副本”和“测试与改动说明”。用户可以展开自测卡、下载 ZIP、独立复测并人工合并。
5. Agent 分析/Evidence Gate 与固定 Artifact 效果独立；即使 Run 后续等待引用定位，已经通过的 ZIP 和测试回执继续保留。

## 异常路径

- 编译或任一测试失败：Artifact 红灯，显示失败项和“不要合并”；保留失败包供排查，不写回原仓库。
- 测试声明与执行 ID 不一致：效果门失败，不能只按“Ran N tests”给绿灯。
- ZIP 缺真实源文件、保留文件 digest 变化或主入口仍只调用旧 Workflow：效果门失败。
- 用户要求任意仓库、依赖安装、联网搜索或自动 PR：当前固定适配器之外保持能力边界，不伪造执行。

## 完成条件

- 下载 ZIP 含 15 个文件，七个真实输入齐全，五个声明保留的契约文件逐字一致。
- 独立解压后 `compileall` 退出码 0；当前 20 个声明测试 ID 与实际执行集合一致且全部通过。
- 前台能直接看到副本边界、文件变更、两个自测命令、失败信号和人工合并责任。
- Planner/Analyst 均真实调用 `deepseek-v4-pro`，并分别记录是否采用；`external_action=none`。

## 来源与边界

- 数据来源：FORTE 固定 revision `345c1ec1487139db9dd319787fa9405ba85d1869` 的 `algorithm-013/input/search_agent_workflow`。
- 用户来源：`USER-FEEDBACK-20260828-TC02-REAL-PROJECT-REFACTOR`。
- 这是固定 algorithm-013 纵切，不是任意代码沙箱；本次固定测试未调用网络或生产搜索，但没有 OS 级 socket 隔离。
