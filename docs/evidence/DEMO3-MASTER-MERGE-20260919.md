# Demo3 与最新主分支合并记录

日期：2026-09-19。状态：Limited Verified，限下列工程检查与单进程事项路径。来源：[用户合并要求](../sources/USER-FEEDBACK-20260919-merge-demo3-master.md)。

## 基线与范围

Demo3 提交 `f01a903` 与主分支 `9a4bbbf` 以普通 merge 整合，共同基线 `1276bc0`。不 rebase、不强制推送；主分支新增的 128 个提交全部保留。未创建 PR。

主分支新增内容中，与本次合并相关的部分是：

- Task Ledger/current Run 指针、双版本 continuation 和任务会话；
- 每批最多三个进程内只读 Worker、WorkUnit/Contribution 台账、依赖波次与局部恢复；
- 独立能力页的进展、执行记录、协作方式、专注证据核对及共驾边界解释；
- 显式编号要求记账、分析输出受限恢复、Windows memory 模式和独立 Playwright 构建目录。

这些能力按主分支的原合同保留；本次没有改动 Worker 调度算法、模型输入上限或真实业务权限。

## 冲突处理与前后台对应

1. Run 与公共 Snapshot 同时保留 `office_action` 和主分支 Task/Topology/Worker 字段。六类单步事项通过原子 start 事务形成独立 Task 和首个 Run；不会进入 Planner、Worker 或 continuation。
2. 无 action 的 start 摘要保留主分支完整 continuation/Workspace 上下文，并省略新增的空 action 字段，避免破坏主分支已有研究请求幂等键。旧 Demo3 分支的 start 摘要不承诺跨协议迁移；未以改写历史回执的方式伪造兼容。
3. 重启恢复保留事项状态，不对事项执行 Loop checkpoint 回退；主分支 Worker checkpoint 与贡献恢复逻辑完整保留。该事项路径本轮仅验证 InMemory store 重载，不冒称 PostgreSQL 实跑。
4. 主分支任务会话重新打开单步事项时进入事项面；能力页打开同一个事项时复用统一工作台，不把零轮次事项渲染为运行中的研究任务。新建任务仍只清除前台投影，旧事项保持。
5. Task GET 尚未确认当前指针或失败时，事项修改与确认不可用；重新核对成功后恢复。迟到的旧 Task GET 错误不能改变新任务的可操作状态。事项 SSE 在确认 current Run 后连接。
6. 公开 API 合计 12 个 path、13 个 operation；新增 action-controls 不替代主分支 continue/workers/controls。

### 记录编号

主分支已使用 DR-0053/0054 与 SCENARIO-038/039。Demo3 决策改为 [DR-0064](../decisions/DR-0064-single-action-boundary-workbench.md)、[DR-0065](../decisions/DR-0065-demo3-editable-drafts-and-human-judgment.md)，场景改为 [SCENARIO-051](../scenarios/SCENARIO-051-single-action-boundary-workbench.md)、[SCENARIO-052](../scenarios/SCENARIO-052-demo3-human-judgment-and-return.md)。

历史 Evidence、Source ID 和截图文件名保留原名，避免改写历史测试标识；决策/场景链接指向新编号。仓库外的指导手册、评审稿、需求原件继续作为本地资料，不纳入此次上传。

## 检查与失败修正

| 检查 | 结果 | 范围 |
| --- | --- | --- |
| 合并主要实现后 `uv run pytest -q` | 468 passed，23 skipped，370.76 秒 | 全库；真实 PostgreSQL 环境门跳过 |
| 新增兼容检查后 office_actions/task_ledger/demo2_runtime | 91 passed，2.78 秒 | 含六类事项 Task GET/Owner/恢复、拒绝 Worker/续办、判断状态更新、不新增 lineage |
| 边界解释纯函数 | 13 passed | 保留主分支 capability-boundaries 投影 |
| Ruff | 通过 | 全库 |
| 主工作台与事项组合浏览器门 | 111 passed，1 failed，约 4.9 分钟 | 原有 101 项全部通过；新增事项测试的状态定位器匹配两个元素而失败 |
| 定位修正后事项浏览器复查 | 11 passed，58.3 秒 | 含历史/能力页往返零 POST、Task 指针失败只读及其恢复；没有重跑或冒称组合门单次 112 全绿 |
| TypeScript、生产构建 | 通过 | Next.js 16.2.10，保留根页面与 /agent-capabilities |
| reporting governance | 4 passed，0.05 秒 | 合并后定向复查 |
| 文档本地链接 | 17 份文档、583 条链接，缺失 0 | 其中 4 条在仓库外，仅本地可用，不冒称 GitHub 可访问 |
| 差异检查 | `git diff --cached --check origin/master` 通过 | 仅检查相对主分支的合并增量；主分支已有 Markdown 行尾双空格原样保留 |

首次定向单测的旧摘要断言失败：它仍按共同基线的裸 request 计算，现改为主分支带 continuation/Workspace 上下文的格式，不删除兼容性断言。新增 API 负例一度使用不符合 Branch ID 格式的假值而在 schema 层得到 422；改成合法格式的不存在 ID 后，确认在 Runtime 层 409 且没有状态变化。

首次事项浏览器检查为 7 通过、2 超时：测试在自动恢复历史期间填新表单。入口改为显式“新建任务”后原九条路径通过。新增历史/能力页检查初次使用错误的暂缓文案和会话按钮定位，按实际服务端文案与会话结构修正；未通过放宽等待或跳过断言消除失败。

最终截图单列为 [材料对照](screenshots/DEMO3-MERGE-human-judgment.png)、[操作区](screenshots/DEMO3-MERGE-human-controls.png)、[草稿编辑](screenshots/DEMO3-MERGE-draft-edit.png)与[手机界面](screenshots/DEMO3-MERGE-mobile-judgment.png)。桌面截图已打开核对；手机路径有 390 px 无横向溢出断言。不覆盖 DR0053/DR0054 的历史图片。

## 结论边界

没有读取 API Key、调用真实模型、发件或执行企业动作。本轮不复跑真实数据库、不证明多实例调度、全文语义覆盖、通用风险识别、生产授权或用户收益。设计人员正式评审仍未举行。
