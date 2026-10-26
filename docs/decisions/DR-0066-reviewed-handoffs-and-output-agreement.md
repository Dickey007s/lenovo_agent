# DR-0066：有界修复、交接核对与输出约定

| 字段 | 内容 |
| --- | --- |
| 状态 | Limited Verified，限定自动化与单主机 PostgreSQL；无本轮真实 Provider/用户效果证据 |
| 日期 | 2026-09-22 |
| 来源 | USER-FEEDBACK-20260922-RESEARCH-DEMO12-ROUTES；RESEARCH-20260922-HUMAN-AGENT-TOP-VENUES；RUNTIME-20260922-REVIEWED-HANDOFFS |
| 前置 | DR-0031 / DR-0034 / DR-0035 / DR-0053 / DR-0055 / DR-0059 / DR-0065 |
| 场景 | [SCENARIO-053](../scenarios/SCENARIO-053-review-handoffs-and-local-repairs.md) |
| 证据 | [Evidence](../evidence/DR-0066-REVIEWED-HANDOFFS-20260922.md) |

## 场景与来源

[用户要求](../sources/USER-FEEDBACK-20260922-research-and-demo12-routes.md) 支持原位实现四条路线。
[八篇正式论文](../research/HUMAN-AGENT-TOP-VENUE-TO-DEMO12-20260922.md) 支持反馈、交接验证、
有限澄清与产物中心交互的设计取舍，不能证明本项目语义正确、优于单 Agent 或真实用户收益。
源码基线 `9a4bbbffe9d3477610718fbba8dae47749ac9aee`，本轮在含历史未提交变更的工作树上增量修改；无新提交/PR。

## 前台交互影响

1. 原两处任务输入增加原生 radio 输出约定。提交前可改；服务端拒绝冲突时保留输入和当前视图。
   已开始的任务只显示冻结合同，不以切换选项修改旧 Run 权限。新任务仍须明确提交才创建。
2. 原进展页先保留已生成文件事实和当前待办，再展示工作项的已保存发现、来源数量和证据入口。
   默认前三项，其余可展开；绑定缺失不按标题猜测。没有新增完成百分比、假产物或新导航入口。
3. 原协作页展示实际被调用 Worker 的职责、修复尝试和逐项前序核对回执。冲突意见及可定位引用
   可直接查看；未调用或历史无字段时不补造。图中待复核不标成可执行，ready 但未准入波次只显示等待派发。
4. 交接分歧不再提示“无需核对文件”。先看核对意见；既有局部续办仍保留，但重试不是业务批准。
   历史只读、版本控制、来源选择无默认项、关闭审查页与未生成文件边界不变。

## 后端事实映射

- `POST /runs` 可选 `output_preference=auto|analysis_only|workspace_files_allowed`。`auto` 默认省略
  序列化以兼容旧幂等摘要；服务端编译 `contract.output_policy`。显式允许与受支持禁文件短语冲突
  返回 422，尚未创建 Run 或调用模型。restrictive 父合同继续继承，允许不等于保证生成某种文件。
- 新 Run 冻结 `collaboration_protocol=reviewed_handoffs_v1`；旧 Snapshot 未带字段时为 `legacy`。
  只升级公共显式只读 Worker 路径，不强制改写旧运行，不扩大固定办公 adapter 或外部权限。
- 职责由实际直接前序数量决定并进入 Analyst 反馈上下文：0 来源分析、1 交叉核对、多份核对与综合。
  不是另建常驻 Agent，也不是证明独立模型之间意见不相关。
- 模型必须返回每份前序的核对项。服务端精确检查 Contribution 身份/唯一性、Finding 序号/定位，
  supported/conflict 必须有前序批准来源的 Anchor。任意冲突或不足暂不采用目标综合贡献。
  模型判断不构成事实蕴含验证或业务裁决；合法结构也可能给出错误观点。
- JSON/结构/截断、未定位引用、核对结构缺项允许当前 Worker 最多 1 次额外调用。
  `worker_repair_requested` 保存失败类别和目标 Branch；再次调用前检查模型预算、active deadline、
  control 状态和目标 WorkUnit。原波次预算仍先预留，额外调用单独计数；不能自动重做其它工作包。
- 来源越权/完整性失败、Provider 非结构错误、ambiguous 引用和非 supported 核对结论不自动修复。
  停止请求阻止下一次调用，但不宣称取消在途 HTTP。
- `worker_runs[].work_role/repair_count/dependency_assessments` 保存实际回执；核对项含前序 ID、
  verdict、解释、Finding IDs 和已定位 Anchor。它们随 Snapshot 持久化，不冒充独立 DecisionRecord。
  旧空字段序列化省略，不改变原 WorkUnit/Contribution 不可变校验；已有版本/贡献不覆盖。
- 原 `expected_version`、Owner、Task/Run 绑定和幂等键不变。幂等回放不能再调用；窗口控制依据
  既有状态机。公共界面不暴露私有路径、Prompt、raw response 或内部哈希。

## 验证与边界

测试、截图、恢复门及失败修正见 [Evidence](../evidence/DR-0066-REVIEWED-HANDOFFS-20260922.md)。
真实 Provider 对新增核对字段的遵循、语义正确性、多人误批率、任务效率未验证。
正式人类裁决记录及其后续语义再验证不是本轮闭环；现有 resume/continue 不冒充新增裁决协议。
本轮也不是 Reflexion/AgentAsk/CollabLLM 算法复现、通用澄清策略或 Demo3 全部完成。
