# DR-0067：任务优先的减法设计

| 字段 | 内容 |
| --- | --- |
| 状态 | Limited Verified，111 项浏览器回归与构建通过；目标用户效果未验证 |
| 日期 | 2026-09-22 |
| 来源 | USER-FEEDBACK-20260922-SIMPLE-USER-WALKTHROUGH；UX-WALKTHROUGH-20260922 |
| 前置 | DR-0058 / DR-0061 / DR-0063 / DR-0066 |
| 场景 | [SCENARIO-054](../scenarios/SCENARIO-054-inspect-task-without-information-overload.md) |
| 证据 | [Evidence](../evidence/DR-0067-SIMPLE-USER-WALKTHROUGH-20260922.md) |

## 场景与来源

[用户反馈](../sources/USER-FEEDBACK-20260922-simple-user-walkthrough.md) 要求自行扮演普通办公用户，
实际操作并简化信息层级。当前前端走查发现交付清单、分支进展、当前成果重复；协作的长回执
挤走分工图；成果点击后追加在长页底部，缺少明确的进入和返回。

本轮读取本地 Product Design audit skill 的任务入口、信息层级、错误恢复和键盘检查框架。
这是审查方法，不是本项目用户研究或可用性评分的依据。工作树基线 HEAD 为
`9a4bbbffe9d3477610718fbba8dae47749ac9aee`，保留此前未提交实现；未提交或创建 PR。

## 前台交互影响

1. 原资料库保留文件树、任务输入和预览。任务示例默认收起，展开后点击只填入草稿，不启动任务。
2. 原进展页保留简化阶段、一个主要待办和当前成果。删除重复分支区和重复成果区，合并为工作项
   清单；默认三个紧凑条目，按项展开摘要与证据，其余工作项有明确入口，不修改服务端数量。
3. 长来源列表改为显示真实数量，按需展开。执行范围说明默认折叠；截断输入范围的提示仍在其
   摘要中可见。业务 Gate 失败/无效、文件失败和不完整待决仍在默认层，不以折叠隐藏。
4. 成果与版本历史直接进入专注内容区，不再追加到进展下面。打开时聚焦内容，返回或 Escape 后
   恢复入口焦点和已展开的工作项；成果内打开核对页时，Escape 仅关闭核对页。
5. 协作页先显示实际调用/采用计数、真实依赖图和当前影响。交接、逐项核对与原始回执集中在既有
   执行回执内。默认收起；有分歧的“查看交叉核对”可直接打开并聚焦回执。不能为了少信息而
   隐藏分歧提醒、波次批准范围和剩余预算。
6. 缺少完整待决证据时，不再提供“无需核对文件”的普通重试建议；业务 Gate 未通过时，不再
   展示绿色“无待办”。文件通过与业务拒绝同时存在时，默认结果提示保留失败色和真实业务结论。

## 后端事实映射

- 入口仍是 `/` 与 `/agent-capabilities`，同一 Task/Run/Snapshot；无新增 API、模型调用或权限。
- 工作项由 `branches[]` 生成；实际 ready IDs 与 deferred_requirements 仍分别表达就绪和延后。
  Findings 仅按 `affected_branch_ids` 绑定，不用文案猜测来源或完成状态。
- 当前成果取当前 TaskCommit 指向的 Artifact，否则取已保留草稿；检查与业务 Gate 分开。
  新 UI 不改写 Artifact、Branch、Contribution、Snapshot、当前 Run 指针或历史版本。
- 每个控制、证据候选和续办仍走原 Owner / expected version / idempotency / source revision 合同。
  打开成果、展开工作项或查看回执均为客户端状态，不会授权 Worker 或发起新 Run。
- 分歧提示来自等待 Branch 与最新被调用 Worker 的非 supported 核对意见，不代表独立真值。
  不完整待决由顶层待决数量和真实可用证据包形成，不用普通重试冒充人类决定。
- 实际文件校验失败、业务失败/无效、来源过期、历史只读和未知回执继续 fail closed。

## 验证与边界

[Evidence](../evidence/DR-0067-SIMPLE-USER-WALKTHROUGH-20260922.md) 分开记载修改前截图、开发者
用户流程走查、自动化、构建和未验证范围。截图使用原前端加受控 API fixture，不是模型重画。
没有新真实 Provider、PostgreSQL 重启或目标用户试用；不据此声称用户更快、误批更少或业务正确。
原系统服务的实际可用性也单列，不能把本地源码和临时测试服务当成常驻系统已更新。
