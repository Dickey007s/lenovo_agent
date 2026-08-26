# DR-0028：分层文件目录与问题审查页

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`，限当前 FORTE 安全投影、确定性浏览器回归和有界只读预览 |
| 日期 | 2026-08-26 |
| 触发来源 | [`USER-FEEDBACK-20260826-22`](../sources/USER-FEEDBACK-20260826-22-hierarchical-workspace-and-evidence-review.md) |
| 场景 | [`SCENARIO-014`](../scenarios/SCENARIO-014-inspect-agent-issue-in-context.md) |
| Evidence | [`WORKSPACE-TREE-AND-EVIDENCE-REVIEW-20260826`](../evidence/WORKSPACE-TREE-AND-EVIDENCE-REVIEW-EVIDENCE-20260826.md) |
| 延续/替代 | 延续 `DR-0024/26` 的整库合同、Branch、Evidence Gate 和引用边界；替代左侧“平铺 96 文件”和“问题只能看摘要”的前台实现 |

## 问题定位

服务端已经返回 15 个顶层目录、每个文件的安全 `display_path`、Branch、Evidence Gap、
Finding 和 `follow_ups`，但旧前台把文件全部平铺。用户很难建立资料位置感；嵌套源码目录
也被压成文件标题旁的一段路径。运行过程中，缺口卡只说“有问题”，结果卡虽可回开引用，
却没有把“Agent 说了什么、服务端验证了什么、用户应该核对哪份原文”组织成一个审查动作。

## 决策

1. 浏览器只使用 `GET /v1/harness/workspace` 的 `folders[]` 与文件 `display_path` 构建
   层级目录树。目录展开、搜索和类型筛选是客户端展示状态，不改变整库 Run 范围。
2. 顶层目录和嵌套子目录均可展开/折叠；文件保持稳定 `file_ref`，点击后仍通过既有
   Preview API 打开安全预览。搜索命中时自动展开匹配祖先，不要求用户预选 Agent 输入。
3. Branch 缺口、逐条 Evidence Gap、逐条 Finding 和每条下一步建议新增审查入口。
   点击后打开覆盖当前工作台的全页式“问题审查页”，关闭后回到原任务现场。
4. 审查页采用提交记录式信息结构：Agent 提出 -> 服务端记录 -> 等待人工核对；同时展示
   轮次、业务分支、关联文件和实际安全预览。它不使用内部 Branch ID、hash、Prompt、
   思维链或 raw provider response 作为普通用户内容。
5. Finding 的关联文件来自该 finding 的 `file_refs`；Gap 来自
   `candidate_file_refs`/Branch `missing_file_refs`；两者可直接对照预览。
6. `follow_ups` 当前没有逐项引用契约。建议审查页只能显示本轮所有 Finding 引用的并集，
   并明确标注“上下文文件，不是该建议的直接证据”。确认建议仍创建新的独立 Run。
7. 不新增 API path，不在前端伪造业务事实。层级来自服务端路径；问题状态来自 Snapshot；
   文件内容来自现有安全 Preview API。

## 技术差异及其交互后果

| 技术差异 | 旧流程 | 当前用户流程 | 前台输出 |
| --- | --- | --- | --- |
| 服务端路径投影为目录树 | 在 96 项长列表中扫标题 | 按顶层目录、子目录逐级定位，也可全局搜索 | 文件夹、展开状态、文件数、嵌套层级 |
| 问题成为可打开对象 | 看到缺口摘要后自行猜相关文件 | 从 Branch/Gap/Finding 直接进入审查页 | “查看问题”“打开审查页” |
| 审查页复用安全 Preview | 在结果和文件列表之间来回找 | 同屏读取 Agent 描述和实际文件内容 | 关联文件列表、原文/表格预览、安全说明 |
| 服务端校验边界显式呈现 | 引用按钮容易被误解为正确性证明 | 先看校验事实，再看不能证明什么 | 引用成员关系、Evidence Gate 状态、黄色边界提示 |
| 建议上下文与直接证据分开 | 建议只有确认按钮 | 先查看形成上下文，再决定是否启动 | “尚未逐项验证”、上下文文件、确认并启动 |

## 前后台统一事实

| UI 状态/动作 | 服务端或客户端事实 | 用户能做什么 | 必须隐藏/不得声称 |
| --- | --- | --- | --- |
| 分层文件目录 | workspace `folders[]` + file `display_path`；展开为浏览器状态 | 展开、折叠、搜索、筛选、预览 | 绝对路径、完整 hash、职业入口、Agent 已读取 |
| Gap 审查页 | `round.evidence_gaps[]`、Branch `waiting_input`、候选/缺失 refs | 对照候选文件，返回后选择分支 | 缺口已解决、候选文件保证结论 |
| Finding 审查页 | `result.findings[].title/detail/file_refs` + Preview GET | 对照引用文件，回到资料库继续查看 | 语义正确、穷举完成、数值正确 |
| 建议审查页 | `result.follow_ups[]` + 当前结果 Finding refs 并集 | 查看形成上下文，确认后启动新 Run | 每条建议有直接 citation、工作已启动 |
| 审查时间线 | 上述 Snapshot 字段的前台组织 | 理解“提出/记录/待核对” | 伪造事件、行级 Git Diff、内部 ID |

## 验证与边界

- TypeScript、生产构建和 Playwright 覆盖目录层级、搜索后预览、Gap/Finding/建议审查、
  关闭返回、继续分支和 390px 触控/溢出路径。
- 截图来自确定性 API fixture，证明被测 DOM、入口与字段映射，不证明真实模型质量。
- 目录树不改变服务端整库合同，审查页不新增写入、Tool、Connector 或外部动作。
- 当前预览只能定位到文件，不能稳定定位到 PDF 页、DOCX 段落、CSV 单元格或代码行。
- 自动化不是用户研究；是否更清晰、减少核对时间或提升信任仍为 `Draft`。
