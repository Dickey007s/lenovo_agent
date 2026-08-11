# DR-0002：先实现受控单任务持久 Loop，再进入 Adaptive Swarm

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0002` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-10 |
| Status | `Ready` |
| Scope | Demo 1 固定 Fixture 的 Task Contract、可持久状态模型、单任务受控纵切、Verifier、Control 和前台闭环 |
| Depends on | `DR-0001`、现有 RunService/Risk/Policy/Permit/Gateway 不变量 |
| Supersedes | 不替代 V0.1 动作治理；只替代“继续扩写静态 Demo 即可证明进展”的工作方式 |

## 1. 场景

本决策采用 [`SCENARIO-001`](../scenarios/SCENARIO-001-customer-a-durable-report.md)：项目负责人围绕同一 Task ID 生成客户 A 的经营分析、风险页和回复草稿。Verifier 发现正式收入 2,400 万与预测收入 2,680 万冲突时，只暂停受影响分支；用户通过服务端控制事件 Steer、Pause branch 或 Take over；最终只有通过验证的工件进入 Commit。

## 2. Claim Ledger

| Claim ID | 类别 | 判断 | Source ID 与精确落点 | 支持范围 | 局限与状态 |
| --- | --- | --- | --- | --- | --- |
| `C-001` | Stakeholder requirement | 后续技术推进必须同时说明场景来源、前台影响和后端事实 | `USER-FEEDBACK-20260810-01`、`USER-FEEDBACK-20260810-02` | 证明这是明确的项目要求 | 不证明某个设计有效；已确认要求 |
| `C-002` | 源码事实 | 基线 commit `84aabc9` 没有长期 Task、Branch、ArtifactVersion、ControlEvent 和任务级 UI | `REPO-BASELINE-84AABC9` | 支持本轮缺口和依赖顺序 | 只适用于该基线；已被后续 PR 部分改变 |
| `C-003` | 内部设计输入 | 客户 A、三个交付物、分支收入冲突和控制事件构成 Demo 1 参考路径 | `MEETING-DECK-0716-V2-01`、`SCRIPT-V5-202607` | 支持固定 Fixture 和演示连续性 | 内部材料，不是独立用户或运行证据 |
| `C-004` | 研究/工程依据 | 推理、动作与观察应交错组织；长任务恢复需要 checkpoint、确定性和幂等 | `REACT-ICLR-2023`、`LANGGRAPH-DURABLE-20260810` | 支持 Loop、checkpoint 和幂等设计原则 | 不规定本项目协议或 UI；需由本地测试证明实现 |
| `C-005` | 治理依据 | 人类监督、责任记录和持续风险管理应是运行过程职责 | `NIST-AI-RMF-1.0` | 支持控制事件、Trace 和人工接管方向 | 通用框架，不规定具体风险算法或组件布局 |
| `C-006` | 源码事实 | PR 2 实现 TaskService/TaskStore、创建/读取/列表/SSE、Owner scope、创建幂等和最薄 Task Bar | PR 2 merge commit `2923d19` 及当时源码 | 支持 PR 3 的输入基线 | 只描述 PR 2；不能代表当前 PR 3 能力 |
| `C-007` | 源码、测试与截图事实 | PR 3 工作区已出现固定 Fixture 的 start/control、Artifact/Verify/Conflict/Commit 和最薄 Branch/Conflict/Control UI | [`RUNTIME-EVIDENCE-DEMO1-PR3-20260810`](../evidence/DEMO1-PR3-RUNTIME-EVIDENCE.md) | 支持固定 Fixture 的可观察工程纵切、内存引用/hash/幂等行为和前后端事实映射 | 不证明 PostgreSQL 重启、真实 Connector、通用后台 Loop 或用户价值 |
| `C-008` | 浏览器运行证据 | PR 4 用同一服务端 Snapshot 驱动只读交付物工作区，并通过固定主路径与发送前失败恢复 E2E | [`FRONTEND-E2E-DEMO1-PR4-20260810`](../evidence/DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md) | 支持 head/version/verification/conflict/content/source/lineage/Commit 的前台映射、Tasks 双 tab、reload 同 key 恢复及被测移动布局 | 仅内存 Store 与固定 Fixture；不证明服务端已提交但响应丢失、SSE 回放、PostgreSQL、用户价值或 Artifact/Action 绑定 |
| `C-009` | 源码、PostgreSQL 自动化与浏览器运行证据 | PR 5 在 PostgreSQL 16.14、同一数据库和三个顺序 API 进程上恢复 v2/v3，重放历史 start/resolve 结果且 Event/Artifact/Commit 零新增；同页前台能显示断线、禁用和重新对账 | `POSTGRES-WINDOWS-16.14-20260811`、[`POSTGRES-BACKED-API-RESTART-DEMO1-PR5-20260811`](../evidence/DEMO1-PR5-POSTGRES-BACKED-API-RESTART-EVIDENCE.md)、tested implementation `4634d8a`、merge compatibility `9814183` | 支持固定 Fixture 的 TaskStore 跨 API 进程恢复、幂等原响应、显式轮次 key 重放和前台传输状态映射 | 不证明 Conversation、数据库重启/崩溃、多实例、事件缺口回放、响应丢失、真实 Connector 或用户价值 |
| `C-010` | LLM 运行证据 | 当前配置的 `deepseek-v4-pro` 可通过 OpenAI-compatible 通用问答和 Conversation SSE 返回文本 | [`LLM-API-SMOKE-20260811`](../evidence/LLM-API-SMOKE-EVIDENCE-20260811.md) | 只支持当前文本连通性 | 不证明固定 Demo 1 Task 使用 LLM，也不证明结构化规划、Action、工具执行、质量或 SLA |
| `H-001` | 待验证假设 | Task Bar 与分支列表能降低用户恢复上下文的成本 | 尚无目标用户研究 | 指导前台原型和指标 | `Draft hypothesis`，不得汇报为已提升体验 |
| `H-002` | 待验证假设 | 冲突只暂停受影响分支能减少等待且不扩散错误 | 固定 Fixture 已有工程行为；无真实任务收益数据 | 指导分支隔离测试 | 功能正确不等于真实业务收益，仍是 `Draft hypothesis` |
| `H-003` | 待验证假设 | 客户 A 场景代表联想目标办公用户的高价值流程 | 尚无访谈/任务频率证据 | 仅作为 Demo Fixture | 需要情境访谈与真实任务样本验证 |
| `H-004` | 待验证假设 | `Steer / Pause / Take over` 符合用户对长期任务的控制心智 | 尚无可用性研究 | 指导控制界面 | 完成按钮功能后仍不能宣称易用 |

## 3. 决策与取舍

采用下面的顺序：

1. 先固定 Task/Branch/Artifact/Verification/Conflict/Control/Event/Commit 协议和 UI 事实矩阵。
2. 再实现持久 Task Store、Snapshot API、按 sequence 恢复的 SSE 和最薄 Task Bar。
3. 再实现单任务 `Observe → Plan → Act → Verify → Commit`、分支冲突隔离、任务控制和幂等恢复，同时交付最薄真实控制 UI。
4. 最后完成 Task Artifact Workspace、断线/过期/失败/部分完成/恢复和浏览器端到端验证。
5. Adaptive Swarm 必须等单任务 Loop 和 Admission 对照成立后另立决策，不进入本决策。

未采用的方案：

- **先做动态 Swarm**：基础 Task 真值、版本、Verifier 和恢复还不存在，Worker 数量只会扩大不可控面。
- **只改静态 HTML**：无法证明状态来自服务端、不能测试重启和幂等，也违反 DR-0001。
- **把长期 Task 塞进 RunSnapshot**：Run 表达一次受控动作，Task 表达跨步骤、分支和工件的聚合生命周期，语义和恢复粒度不同。
- **先接真实邮箱/CRM**：当前身份、Connector 和多实例一致性仍是 Demo 边界，会扩大风险和验证成本。
- **前端先模拟进度**：会让 UI 拥有虚假完成真值，明确禁止。

## 4. 后端事实

协议见 [`TASK_RUNTIME_PROTOCOL.md`](../contracts/TASK_RUNTIME_PROTOCOL.md)。关键不变量：

- Task、Branch、ArtifactVersion、TaskEvent、ControlEvent、VerificationReport、ConflictRecord 和 TaskCommit 都有服务端身份；需要并发或演进语义的对象另以 version、sequence 或 task_version 关联服务端状态。
- Snapshot 是当前投影，TaskEvent 是追加式 Trace；事件在每个 Task 内严格单调。
- 所有 mutation 校验 Owner、允许状态转换、`expected_task_version` 和 `idempotency_key`。
- ArtifactVersion 只追加；candidate 不能进入 Commit；解决冲突必须创建新版本并重新验证。
- Snapshot、Artifact/Control 和对应 TaskEvent 原子提交后才能通过 SSE 广播。
- 任务涉及副作用时继续调用现有 RunService 和 Gateway，Task Runtime 不签发 Permit，也不建立旁路。

PR 3 至 PR 5 当前可观察落点为：

- `TaskService` 仍从服务端 Task ID、Owner、契约、三个初始 Branch 和 `TASK_CREATED(sequence=1)` 开始；`POST /v1/tasks/{task_id}/start` 在一次 mutation 中物化固定客户 A 的 Observe/Plan/Act/Verify Trace、ArtifactVersion、VerificationReport 和局部 Conflict。
- `POST /v1/tasks/{task_id}/controls` 接受 Steer、Pause、Resume、Take over、Return control 和 Resolve evidence。分支控制经服务端应用后改变 Snapshot；Steer 当前只持久记录为 `accepted`，不宣称已重新规划。
- `TaskStore` 已有内存和 PostgreSQL 的 Snapshot、Event 和 ArtifactVersion commit 路径。PR 5 的 opt-in system test 在随机 PostgreSQL 16.14 数据库上，以 API A/B/C 顺序恢复 v2/v3，并验证旧 start/resolve key 返回首次结果且原 Task 维持 `45 events / 7 artifacts / 1 TASK_COMMITTED`；合并兼容回归另验证同一显式轮次 key 跨进程返回同 Task、不同 key 产生第二个 Task。
- `POST /v1/demo1/tasks` 接受可选 `Idempotency-Key` 作为演示轮次：同一 Owner+key 重放返回原 Task，不同 key 创建独立 Task；未传 key 时保留 Owner 绑定的兼容默认键。`POST /v1/tasks` 同样接受可选 key，同一 key 改用于不同契约返回 409。
- `GET /v1/tasks`、`GET /v1/tasks/{task_id}` 和 Task SSE 均按当前 Owner 过滤，跨 Owner 按不存在处理。
- Task SSE 按 `after` 轮询 Store 并发送 heartbeat。当前没有 `LISTEN/NOTIFY`、消息代理或跨实例广播，多实例通知未实现或验证。

该 start 路径不调用 LLM，也不读取真实邮箱、CRM、预测表或项目系统；所有阶段在一次服务端事务提交后才对浏览器可见。因此当前结论是“固定 Fixture 的确定性受控纵切”，不是“通用长任务已在后台持续运行”。内存回归已覆盖 Artifact lineage/head、Commit state hash、剩余 open Conflict 不提交和 mutation 原响应幂等；PostgreSQL 16.14 已补齐顺序 API 进程恢复证据。数据库进程重启/崩溃、已有库迁移、Conversation、多实例通知和通用后台 Loop 仍无证据。

## 5. 前台输出

完整映射见 [`UI_SERVER_FACT_MATRIX.md`](../contracts/UI_SERVER_FACT_MATRIX.md)。前台必须提供：

- Active Task Bar：Task ID、目标、阶段、预算、同步状态和最近 Commit。
- Branch Status List：running、waiting evidence、paused、taken over、failed、committed。
- Conflict Card：冲突主题、来源、影响分支和解决动作。
- Task Artifact Workspace：版本、来源、验证结果和 Artifact head。
- Task Control：Steer、Pause、Resume、Take over、Return control，并在服务端确认后才改变状态。
- 断线、过期版本、预算耗尽、权限不足、部分失败和恢复的明确反馈。

默认隐藏 Prompt、思维链、Worker 对话、完整 Trace JSON、JWT/Permit、幂等键、权限哈希、DSN、工具秘密和堆栈。现有业务动作确认 tray 保持独立，不能与任务级控制合并。

PR 4 在上述 Task Bar 与控制 UI 之外增加只读交付物工作区。Task 面板从 `branches[].artifact_heads` 直达版本；工作区从同一 Snapshot 显示版本/状态、验证、冲突、结构化内容、折叠来源与检查、lineage 以及 Commit/state hash，并以两个 tab 保留原“工作台待办”。PR 5 让 Conflict Card 与 Artifact Workspace 共用 fail-closed source-ref 投影，只放行契约中的四个已知 Fixture；顶部连接文案改由独立传输状态驱动，pending mutation/Snapshot 对账继续由 Task 同步状态表达，避免相互误报。这仍只是前端第二道投影，服务端通用字段可见性 Schema/display projection 尚未实现。

system Edge E2E 通过真实本地 Next.js `3011` 与 FastAPI `8011` 覆盖创建、start、冲突、Steer accepted、resolve、Commit、客户回复 v3/2,400 万元/仅草稿未发送，以及 start 请求发送前 abort 后的 `sessionStorage` reload、同 key 重试和无重复工件。五张截图、DOM 断言与完整边界见 [`FRONTEND-E2E-DEMO1-PR4-20260810`](../evidence/DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md)。该用例没有把 start 请求交给服务端，不能扩展为“服务端已提交但响应丢失”的恢复证明；Task SSE 断线回放也未测试。

PR 5 的同页 system Edge 运行通过实际停止 API A/B、启动 API B/C，验证 v2/v3 的同一 Task ID、Snapshot 全等、断线时保留最后事实并禁用控制、重新 GET 后恢复已同步；五张截图见 [`POSTGRES-BACKED-API-RESTART-DEMO1-PR5-20260811`](../evidence/DEMO1-PR5-POSTGRES-BACKED-API-RESTART-EVIDENCE.md)。停机期间没有写入新事件，因此该路径不是 `after` 事件缺口回放证据，也不是提交后响应丢失证据。

Action Gate 打开时保留 Active Task Bar，Gate 占用独立网格行；TaskRuntimePanel 保持挂载以保留 Steer 草稿，但视觉隐藏，Task Control 与 Task Bar 操作均不可用；Gate 收起后行高缩至 58px。Task Control 与副作用 Action 仍是两条服务端事实链；Task Artifact 尚未绑定 ActionCandidate/Run 的参数版本，Artifact 改动也尚未触发旧 Action 失效。人工接管编辑并创建新 ArtifactVersion、预算耗尽、单分支失败、事件缺口和响应丢失恢复仍未完成。

## 6. 验证计划与完成边界

| 验证问题 | 成功标准 | 证据 |
| --- | --- | --- |
| 协议能否拒绝越权字段和非法引用 | 未知字段、重复 Deliverable、未知引用、非法控制形状均被 Pydantic 拒绝 | PR 1 unit tests |
| 持久状态能否恢复 | PostgreSQL 下顺序 API 进程恢复 v2/v3，Task ID、version、heads、artifacts、sequence 和 Commit 全等 | PR 5 opt-in system test 与浏览器证据；数据库故障/迁移/多实例不在结论内 |
| SSE 能否无漏地续订 | 服务层证明 `after=N`；PR 5 浏览器证明无停机期新事件时的断线、重连和 GET 对账；事件缺口与多实例待验 | integration tests + PR 5 browser evidence |
| 冲突能否局部隔离 | 固定收入冲突只令目标 Branch waiting，另两 Branch 形成已验证工件 | PR 3 tests + Snapshot；只证明 Fixture 工程行为 |
| 控制与恢复是否幂等 | 相同 mutation 不产生重复 Event/ArtifactVersion/Commit，并返回协议规定结果 | PR 3 内存 tests；PR 5 PostgreSQL 跨进程重放保持 `45/7/1`，返回原 v2/v3 |
| 前后端是否一致 | UI 只根据服务端 Snapshot/Event 显示业务状态；连接文案只表达客户端传输状态 | PR 4 固定主路径 + PR 5 API 重启 system Edge；其他异常/事件缺口待补 |
| pending mutation 能否浏览器恢复 | reload 后保留原 key/intent，同 key确认且不重复工件 | PR 4 已覆盖发送前 abort；服务端已提交但响应丢失待补 |
| 用户是否更易理解和控制 | 尚未设为功能完成条件 | 后续独立用户研究；未完成前保持假设 |

截至 PR 5，“固定 Fixture 的功能实现、前后端映射、PostgreSQL 顺序 API 进程恢复和本次列出的浏览器路径”已有 `C-007/C-008/C-009` 工程证据，可以在各自边界内标记 `Verified`。本决策整体仍保持 `Ready`：数据库故障/迁移、多实例、事件缺口、服务端已提交但响应丢失、真实 Connector 和 Artifact/Action 绑定尚未验收，用户价值、代表性与易用性假设仍需独立证据。

PR 1 实际验证（2026-08-10）：`uv run pytest -q` 为 37 passed，`uv run ruff check .`、`pnpm --dir apps/web lint`、`pnpm --dir apps/web build` 和 `git diff --check` 均通过。该结果只证明协议、类型、文档留痕和防回退检查已落地，不证明 Task Store、SSE、Loop 或界面已经实现。

PR 2 实际验证（2026-08-10）：针对性 Task 测试为 7 passed；全量 `uv run pytest -q` 为 44 passed，`uv run ruff check .`、`pnpm --dir apps/web lint`、`pnpm --dir apps/web build` 和 `git diff --check` 均通过。它证明内存 Store 下的初始创建、Owner scope、创建幂等、事件游标、路由以及前端类型和生产构建；不证明 PostgreSQL 进程重启、多实例通知、浏览器 E2E 或任何 Loop/控制/工件提交行为。本机没有可用的 Docker/PostgreSQL 进程，因此没有把 PostgreSQL 实现表述为已完成运行验收。

PR 3 Runtime 验证（2026-08-10）：针对性 Task 测试 `15 passed`，全量 Python 回归 `56 passed`，Ruff、前端 lint 和生产构建通过。测试覆盖固定 Fixture 主路径、局部冲突、解决最后冲突时联动重生成回复、仍有其他 open Conflict 时只持久化本次 resolution 且不生成 reply v3/Commit、Artifact lineage/head、state hash、预算/截止时间、Owner/版本与原响应幂等。完整记录与三张截图哈希见 [`RUNTIME-EVIDENCE-DEMO1-PR3-20260810`](../evidence/DEMO1-PR3-RUNTIME-EVIDENCE.md)。它不证明 PostgreSQL 重启、多实例通知、真实 Connector、后台持续调度、完整浏览器恢复或 `H-001` 至 `H-004`。

PR 4 前端验证（2026-08-10）：`pnpm --dir apps/web test:e2e` 在本地 FastAPI `8011`、Next.js `3011` 与 system Edge 上为 `2 passed (18.4s)`。主路径覆盖 create/start/conflict/Steer/resolve/commit、客户回复 v3、正式收入 2,400 万元、仅草稿未发送和 state hash；恢复路径覆盖发送前 abort、`sessionStorage` reload、同 key 重试及无重复工件；移动 DOM 断言覆盖被测区域无横向 overflow 和可见操作目标至少 44px。该结果不覆盖服务端已提交但响应丢失、SSE 断线、PostgreSQL、真实 Connector 或 `H-001` 至 `H-004`。

PR 5 PostgreSQL 与前台恢复验证（2026-08-11）：基线证据以五张 1440 x 900 截图和 DOM 断言验证连接文案、控制禁用、同 Task ID 与 v2/v3 Snapshot 全等。与 `origin/master@1a413f3` 合并后，commit `9814183` 的兼容封口为：opt-in PostgreSQL 16.14 system test `1 passed (9.78s)`，同一显式轮次 key 跨 API A/B/C 返回同 Task，不同 key 产生第二个 Task，原 Task 保持 `45 events / 7 artifacts / 1 TASK_COMMITTED`；system Edge suite `3 passed (17.0s)`，还断言“再次演示”首次创建请求中断时旧 Task 仍显示已连接、重试复用同 key 且只新增一个 Task。完整 Python 为 `58 passed, 1 skipped (2.00s)`，治理文档 `4 passed`，Ruff、前端 lint、生产构建和 `git diff --check` 均通过；skip 是普通测试没有显式配置 opt-in 维护库 DSN。该结果不覆盖 Conversation、数据库进程故障、事件缺口、响应丢失、多实例或 `H-001` 至 `H-004`。

## 7. 关联项

- 场景：[`SCENARIO-001`](../scenarios/SCENARIO-001-customer-a-durable-report.md)
- 来源：[`SOURCE_REGISTER.md`](SOURCE_REGISTER.md)
- Pydantic：`packages/contracts/task_models.py`
- TypeScript：`apps/web/app/task-types.ts`
- 当前静态原型边界：[`docs/prototypes/README.md`](../prototypes/README.md)
- PR 3 运行证据：[`DEMO1-PR3-RUNTIME-EVIDENCE.md`](../evidence/DEMO1-PR3-RUNTIME-EVIDENCE.md)
- PR 4 前端 E2E 证据：[`DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md`](../evidence/DEMO1-PR4-FRONTEND-E2E-EVIDENCE.md)
- PR 5 PostgreSQL-backed API 重启证据：[`DEMO1-PR5-POSTGRES-BACKED-API-RESTART-EVIDENCE.md`](../evidence/DEMO1-PR5-POSTGRES-BACKED-API-RESTART-EVIDENCE.md)
- LLM 连通性证据：[`LLM-API-SMOKE-EVIDENCE-20260811.md`](../evidence/LLM-API-SMOKE-EVIDENCE-20260811.md)
- 后续证据：数据库故障/迁移、SSE 事件缺口、响应丢失、多实例、Task/Action 绑定、真实 Connector 和用户研究，产生后继续回填。
