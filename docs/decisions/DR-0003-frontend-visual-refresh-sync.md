# DR-0003：同步 V0.1 前端视觉与工作区交互，并兼容 Demo 1 Runtime

| 字段 | 内容 |
| --- | --- |
| Decision ID | `DR-0003` |
| Owner | Office Agent 项目组 |
| Date | 2026-08-10 |
| Status | `Verified` |
| Scope | 基础工作区视觉、任务看板、月历/日视图、CRM 阶段条，以及 Demo 1 Task Runtime/Artifact Workspace 的兼容样式 |

## 1. 用户场景与问题

目标用户在同一页面中切换邮件、文档、报价、手工待办、日历、CRM 和 Demo 1 长期任务。触发条件是把 `D:\Projects\lenovo\Agent_V0.1` 中 2026-07-16 的前端工作区改动同步到当前分支。直接覆盖会删除当前分支后来增加的 TaskSnapshot、ArtifactVersion、Conflict、Control、Commit 和恢复交互；只同步颜色又会丢失看板、月历日视图和 CRM 阶段条。

完成条件：来源工作区视觉与交互可用；长期任务与手工待办双 Tab 保留；Task Artifact、右侧 Runtime、Action Gate 和移动端恢复语义不退化；新增页面字号与刷新后的基础页面接近；桌面和 390px 移动视口无页面级横向溢出。异常路径至少覆盖移动端 Runtime 挤压对话区和请求中断后的幂等恢复。

## 2. 来源与依据

| Source ID | 类型 | 精确引用 | 日期或版本 | 支持判断 | 局限 |
| --- | --- | --- | --- | --- | --- |
| `USER-REQUEST-20260810-FRONTEND-SYNC` | 用户要求 | 当前任务中“结合 `D:\Projects\lenovo` git 记录中对于前端的新改动，把这个改动同步过来” | 2026-08-10 | 明确同步和兼容目标 | 不指定逐像素实现 |
| `REPO-LENOVO-V01-WORKTREE-20260716` | 源码工作树 | `D:\Projects\lenovo\Agent_V0.1` 相对 `0f8c6d6` 的 `apps/web/app/page.tsx`、`styles.css` 与两份交互文档 diff | 文件修改时间 2026-07-16；读取于 2026-08-10 | 支持工作区身份色、固定标题、任务看板、全宽月历/日视图、CRM 阶段条和确认卡视觉 | 来源改动未提交，不能作为稳定 commit 引用；不包含 Demo 1 Runtime |
| `REPO-TARGET-C61960A` | 源码事实 | 当前仓库 `c61960a` 的 `page.tsx`、`task-artifact-workspace.tsx`、`task-types.ts`、E2E 与 DR-0002 | 2026-08-10 | 约束必须保留的 TaskSnapshot、工件、冲突、控制、Commit 和恢复能力 | 只证明当前工程基线，不证明视觉刷新兼容 |

## 3. 决策与取舍

采用共同基线 `0f8c6d6` 做三方合并：来源工作树提供视觉和基础工作区交互，当前分支提供 Demo 1 功能。`page.tsx` 只人工解决 Active Task Bar 与连接状态样式的一处重叠；`styles.css` 以来源视觉体系为主，并增加作用于 Task Runtime/Artifact 的兼容层。

未采用整文件覆盖，因为会删除当前分支新功能。未保留原 6-9px Task 字号，而是提升为约 10-13px；移动端 Runtime 仍保持 220px 上限并内部滚动，避免较大字体挤压对话区。手工待办看板允许内部横向滚动，但页面和工作区本身不得横向溢出。

## 4. 后端事实映射

本决策不改变 API、Pydantic、TaskSnapshot、WorkspaceArtifact、SSE、Risk、Policy、Approval、Permit 或 Gateway。长期任务 UI 仍从 `TaskSnapshot` 的 `branches`、`artifact_versions`、`verification_reports`、`conflicts`、`controls` 和 `last_commit` 渲染；手工待办仍来自 `WorkspaceArtifact(kind=tasks)`，切换状态只重排浏览器中的看板，点击保存后才通过 Workspace API 更新服务端 Artifact。

月历与日视图只改变同一 `WorkspaceArtifact(kind=calendar)` 的前端投影；新建或编辑日程仍沿用既有保存路径，外部邀请仍走 RunService 和 Action Gate。视觉颜色、阶段条和动画不产生新的服务端完成、风险、审批或执行事实。

## 5. 前台输出与恢复

- 工作区页头使用固定“XX 工作台”标题和工作区身份色，业务标题仍在编辑卡内部。
- Tasks 保留“长期任务工件 / 工作台待办”双 Tab；前者完整展示工件、来源、验证、冲突、lineage 和 Commit，后者按状态分栏并可编辑保存。
- 日历一级页为全宽月历，日期格显示日程摘要；点击日期进入当日安排，可前后翻日、返回月历和新建日程。
- CRM 展示当前、目标和中间阶段，但目标阶段仍由用户选择并保存；阶段条不表示 CRM 已真实写入。
- Action Gate 打开时继续保留 Active Task Bar，Runtime 保持挂载但隐藏且不可交互；结果待确认、断线、版本冲突和幂等恢复语义不变。

## 6. 验证与边界

验证结果见 [`DR-0003-FRONTEND-VISUAL-SYNC-EVIDENCE.md`](../evidence/DR-0003-FRONTEND-VISUAL-SYNC-EVIDENCE.md)。本次范围内的实现和兼容性标记为 `Verified`。该结论不证明真实 Connector、PostgreSQL 重启、多实例 SSE、用户价值或可用性收益；来源视觉工作树本身仍是未提交状态。
