# DR-0026：可选择任务分支与不可变成果历史

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`，限固定 FORTE、最多三轮、顺序单 Controller、只读结果路径 |
| 日期 | 2026-08-26 |
| 触发来源 | [`USER-FEEDBACK-20260826-20`](../sources/USER-FEEDBACK-20260826-20-demo1-branch-artifact-completion.md) |
| 场景 | [`SCENARIO-012`](../scenarios/SCENARIO-012-selective-branch-and-artifact-restore.md) |
| Evidence | [`DEMO1-BRANCH-ARTIFACT-CONTROL-EVIDENCE-20260826`](../evidence/DEMO1-BRANCH-ARTIFACT-CONTROL-EVIDENCE-20260826.md) |
| 延续/替代 | 延续 `DR-0025`；替代其“只能整组补证”和“版本仅内嵌 Snapshot、最终修改为 committed”的当前实现结论 |

## 问题定位

`DR-0025` 解决了轮次间暂停，但 `candidate_file_refs` 仍是一组文件。用户只能确认“全部继续”，
不能判断是哪条任务分支卡住，也不能只推进一条分支。每轮成果虽然可见，却仍内嵌在
Run Snapshot；最终提交会修改最新版本的状态，无法证明版本本身不可变，也没有恢复旧版的操作面。

## 决策

1. 服务端把每个 validated plan unit 编译为 `AgentControlLoopBranch`。Branch 拥有稳定 ID、轮次、父分支、依赖、输入、已核对/缺失引用和状态；模型不能提供或修改 Branch ID/状态。
2. 每轮验证后，Branch 根据服务端已批准引用更新为 `completed` 或 `waiting_input`。Evidence Gate 返回 `candidate_branch_ids`；前台按 Branch 展示，而不是重新解释原始计划。
3. `resume` 可携带 `branch_id`。下一轮范围严格等于该 Branch 的 `missing_file_refs`；其他等待分支继续留在 Snapshot。兼容旧客户端时，服务端只选择第一个等待分支，不再整组静默推进。
4. ArtifactVersion 与 TaskCommit 成为 StateStore 的独立 append-only 记录。PostgreSQL 使用独立表和 payload digest；相同键出现不同内容时拒绝写入。
5. Snapshot 保留 Artifact/Commit 的前台投影和当前指针，但不再通过修改 ArtifactVersion 状态表达提交。版本保持 `draft/verified`；TaskCommit 单独表达“当前选择”。
6. `rollback` 是 versioned/idempotent 控制命令。它只允许终态已提交 Run，必须指定现有版本，并先核对独立记录；成功后新增 `operation=rollback` TaskCommit、更新 `last_commit` 和前台简报，不删除任何历史。
7. Branch 仍由一个顺序 Controller 和 Analyst 调用处理。当前不声称分支并行、独立 Worker、跨实例 lease、真实工具执行或源文件写入。

## 技术差异及其交互后果

| 技术差异 | 之前 | 当前用户流程 | 前台输出 |
| --- | --- | --- | --- |
| 服务端 Branch 状态 | UI 只能展示 plan units | 用户看到哪条完成、哪条缺证，并选择一条继续 | 分支现场、依赖、资料/缺口数量、继续此分支 |
| 分支级补证范围 | resume 继续整组 candidates | 每次决定只消耗一条分支的一轮预算 | 未选分支保持等待，选中分支标为本轮来源 |
| append-only ArtifactVersion | 版本只在 Snapshot 内，最终状态被改写 | 用户可确信旧版仍存在 | 阶段草稿/已核对、当前版本指针 |
| TaskCommit 历史 | 只有 `last_commit` | 每次提交或恢复都留下新记录 | 当前 vN、提交记录数量、恢复轨迹 |
| 受控版本恢复 | 没有恢复动作 | 用户选择任一非当前版本，服务端核验后恢复 | 恢复按钮、已恢复状态、原文件未修改 |
| 真实 PostgreSQL 重启门 | 仅共享 memory Store 模拟 | CI 用真实 PostgreSQL 顺序启动多个 Runtime | 报告可区分本地 memory 与真实数据库证据 |

## 前后台统一事实

| UI 状态 | 服务端事实 | 用户能做什么 | 隐藏细节 |
| --- | --- | --- | --- |
| 任务分支现场 | `snapshot.branches[]`、`round.branch_ids` | 查看状态和依赖 | Branch hash 生成、validator internals |
| 等你决定 | Branch `status=waiting_input` + Gate candidates | 选择一条“继续此分支”或停止 | Prompt、CoT、文件排名 |
| 正在继续某分支 | resume ControlEvent `branch_id` + `active_branch_id` | 查看下一轮轨迹 | 内部稳定 ID 不作为主要文案 |
| 当前成果 vN | `last_commit.artifact_version` | 查看成果和引用 | 完整 digest、数据库行 |
| 历史版本 | 独立 ArtifactVersion 的安全投影 | 选择非当前版本恢复 | append-only payload、内部 JSON |
| 已恢复 | `artifact_version_restored` + rollback TaskCommit | 继续审阅或恢复其他版本 | 不存在的源文件回滚/工具动作 |

## 验证与边界

- 后端测试覆盖两个等待分支按用户选择分别推进，未选分支不被消耗；ControlEvent 记录所选 Branch。
- append-only Store 测试覆盖两版 Artifact、初始 Commit、恢复 v1、幂等重放、再恢复 v2，并核对版本数量不减少。
- Playwright 覆盖分支现场、指定分支继续、成果当前指针和恢复交互；390px 路径仍需满足最小触控尺寸和无横向溢出。
- PostgreSQL integration test 用真实服务覆盖中断恢复、完成、独立记录和恢复指针；其最终结论以对应 CI run 为准。
- `completed` 仍只证明 schema/ref/read-only/branch-record checks 通过且需要人工复核，不证明语义、穷举或算术正确。
- Branch 是单任务内部工作单元，不是 Demo 2 的多任务 Adaptive Swarm；Artifact 是逻辑只读简报，不是源办公文件或 Connector 写入。
- 自动化不是用户研究；交互理解、信任、效率和价值仍为 `Draft`。
