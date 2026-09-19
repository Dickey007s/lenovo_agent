# SCENARIO-045：从任务进展逐层查看执行、协作与原文依据

- 状态：`Limited Verified`；固定 Fixture 纵切通过，用户效果仍为 `Draft`
- 日期：2026-09-01
- 决策：`DR-0058`
- 用户来源：`USER-FEEDBACK-20260901-PROGRESSIVE-AGENT-CAPABILITY-PAGE`

## 1. 目标用户、触发与完成条件

产品负责人已经启动一条跨产品、算法和用户体验的只读核对任务。任务产生了部分成果，
同时有一个证据位置需要确认。用户进入 Agent 能力页，不想先阅读完整 Runtime Trace，只想
知道进度、自己的待办和现有成果；需要时再追溯 Loop 或 Adaptive Swarm。

完成条件：

1. 默认首屏在不展开技术记录时说明当前进展、主要待办和成果；
2. Loop 与 Swarm 使用同一 selected Run，但不同时全部展开；
3. 用户可按需查看当前 Round/Branch 和 WorkUnit/Contribution；
4. 人工核对页只显示真实候选和安全原文，选择后只恢复受影响部分；
5. 历史 Run 只读，Fixed/Single Controller 不生成假 Swarm；
6. 页面不暗示智能工作驾驶舱或分布式 Worker 已实现。

## 2. 可直接使用的输入

> 请分别核对产品上线、搜索 Agent 运行和用户交互三条工作线中最需要人工处理的风险与
> 证据，形成一份跨职能风险与待办简报。按工作包列出已核对来源、关键发现、缺口、受
> 影响下游和下一步；先独立核对，再统一收敛。不要修改源文件，不要执行代码，不调用
> 外部系统。

固定 Demo 2 纵切可使用产品 4、算法 3、交互 3 份 FORTE 公开输入。该数量只适用于固定
场景，普通 Run 必须显示实际批准来源和实际 WorkUnit。

## 3. 用户过程与前台输出

1. 用户从 Workspace 打开“Agent 能力”。默认进入“执行进展”。
2. 首屏显示当前 Run 身份、阶段、一个待确认项、三条 Branch 摘要和当前逻辑成果。
3. 用户点击“查看完整执行记录”，只展开当前 Round 与等待 Branch；其他 Branch 显示成果
   已保留，服务端事件和模型回执仍收起。
4. 用户返回并切换“协作方式”。页面显示服务端实际 route。Adaptive 时在左侧看准入到
   成果的阶段轨，在中央看三根两依赖或当前真实 WorkUnit DAG；父子方向线说明先后关系，
   `ready_branch_ids` 对应节点显示“下一波待确认 / 可执行”。右侧把下一波说明与唯一主要
   确认动作放在一起，并显示其他等待/阻塞对下游的当前影响；底部显示返回、采用、待确认
   和 Artifact 版本。非 Adaptive 时只显示准入原因，不画假 DAG。
5. 用户点击待确认项，进入专注核对页。页面解释同一 quote 有多个候选、影响哪个工作包、
   哪些成果不变，并并列显示安全原文。
6. 用户选择候选并确认。服务端校验版本、来源 revision 与 candidate membership，只恢复
   受影响 Branch/WorkUnit，并追加新 ArtifactVersion；浏览器返回任务进展。

## 4. 后端事实

- 页面身份：Owner-scoped Task current pointer 与 selected Run；
- 进度：Snapshot status、rounds、branches、next_step 与 decision_requests；
- 成果：append-only ArtifactVersion 和 TaskCommit；
- 协作：TopologyAdmission、WorkUnit、Contribution 与 Worker receipt；
- 原文：EvidenceResolution candidates、公开 source revision 和安全 preview；
- 更新：expected version、幂等键、named SSE 后 final GET。

## 5. 停顿与失败

### 没有 Run

显示空态并返回 Workspace 启动任务，不渲染示例进度或工作包。

### 多个 open DecisionRequest

默认首屏显示稳定排序后的首个主要待办和总数，其余进入待办列表；不得静默截断或把多个
问题合并成一个候选选择。

### stale 或 candidate tamper

服务端拒绝操作，前台刷新 Snapshot 并说明资料或候选已经变化；不自动接受旧位置。

### 历史 Run

四层全部只读，不连接历史 SSE，不允许控制、Worker confirmation 或 Evidence accept。

### Fixed Workflow / Single Controller

“协作方式”显示实际 route 和原因，Worker/Contribution 为空；不硬编码五个 WorkUnit。

### API、Catalog 或 preview 失败

按现有 fail-closed 边界显示对应错误和重试入口，不用概念图或缓存假数据填充。

## 6. 当前边界

- 当前 Worker 是单 API 进程内、每波最多三个的只读 Analyst；
- 当前成果是逻辑 ArtifactVersion，不证明 DOCX/XLSX 写回；
- source location 不证明结论语义、穷举或数值正确；
- 概念图与自动化不替代目标用户研究；
- 未来智能工作驾驶舱仍未实现。

## 7. 验证回填

场景的默认进展、完整执行记录、协作方式、真实审查入口、历史只读、Fixed 反例、键盘
tab、动态 DAG、局部阻塞影响与 390 px 已由 DR-0058 Evidence 记录。Fixture 没有把一个
真实复杂办公任务从输入到业务正确输出跑一遍，也没有目标用户走查，因此场景完成度只
限于前台纵切。
