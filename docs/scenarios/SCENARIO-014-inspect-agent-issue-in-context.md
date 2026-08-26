# SCENARIO-014：在原始资料中核对 Agent 发现的问题

## 用户、触发与痛点

一名办公用户打开统一 FORTE 资料库，先按文件夹浏览财务、法务和研发资料，再要求 Agent
核对跨文件事实。Agent 在第一轮发现一条证据缺口：某个分析分支仍缺少授权材料引用。
用户不愿仅凭一张“有 1 个缺口”的卡片继续花下一轮预算；他要先知道问题发生在哪一轮、
哪条分支、Agent 具体说了什么，以及候选文件里是否真的有相关内容。

同一任务完成后，用户还要审查 Finding 和下一步建议。Finding 有逐条引用，建议当前只有
本轮上下文，没有逐项引用。产品必须把这两种证据强度明确区分。

## 主路径

1. 用户在左侧目录树展开顶层目录和嵌套子目录，或搜索文件/目录名称；点击文件后读取
   只读安全预览。该浏览动作不创建 Run，也不限制 Agent 的整库范围。
2. 用户提交任务。Agent Control Loop 形成 Branch、Finding 和 Evidence Gap。
3. 某 Branch 进入 `waiting_input`。分支卡和 Gap 列表同时出现“查看问题”入口；用户点击，
   打开全页式问题审查页，而不是离开或覆盖当前 Run。
4. 左侧提交记录式轨迹显示“Agent 提出 -> 服务端记录 -> 等待你核对”；上方明确标出
   第几轮和业务分支。右侧显示问题原文、候选文件列表和首份文件的安全预览。
5. 用户切换关联文件，对照表格或文档内容。用户可关闭审查页返回分支现场，也可点击
   “回到资料库中打开”进入常规文件预览。
6. 用户确认仍需补证后，返回分支现场点击“继续此分支”。只有服务端 resume 回执返回后，
   下一轮才开始；查看问题本身没有状态副作用。
7. 终态 Finding 的“打开审查页”使用该 Finding 自己的 `file_refs`。用户核对后可继续打开
   单份来源文件。
8. 下一步建议的“查看形成依据”明确显示“尚未逐项验证”。其关联文件只是本轮 Findings
   的上下文并集；只有点击“确认并启动”才创建新 Run。

## 完成条件

- 15 个顶层目录由服务端 workspace 投影驱动；嵌套 `display_path` 可形成任意深度子目录。
- 搜索和类型筛选保留匹配祖先并自动展开；清除筛选后恢复用户自己的展开状态。
- Gap、waiting Branch、Finding 和 proposal 均有可访问的审查入口。
- 审查页可见轮次/业务分支、问题描述、服务端事实、边界说明、关联文件和实际 Preview。
- 打开/关闭审查页不改变 Run version；只有原有 resume/start 控制才改变服务端状态。
- 普通 DOM 不暴露 raw file_ref、Branch ID、内部路径/hash、Prompt、CoT 或 raw response。

## 异常路径

| 异常 | 前后台行为 | 用户恢复 |
| --- | --- | --- |
| 目录搜索无结果 | 客户端显示空结果，不填充静态文件 | 清除搜索或类型筛选 |
| 关联 file_ref 不在 workspace 投影 | 不渲染伪文件；显示当前没有可打开关联文件 | 返回任务现场，刷新权威 Snapshot |
| Preview 完整性/解析失败 | Preview API fail closed，审查页显示文件预览不可用 | 切换其他关联文件或稍后重试 |
| Gap 没有候选 refs | 仍显示问题和服务端 Gate 事实，不伪造证据 | 返回后调整方向、停止或等待补充资料 |
| 建议无逐项 citation | 明示只显示结果上下文 | 用户可不启动，或先回看 Findings |
| 旧 Snapshot/网络断开 | 审查内容以当前已接收 Snapshot 为准；Run 控制仍需 version 对账 | 关闭审查页，GET/SSE 恢复后再决定 |

## 来源与证据边界

- Stakeholder 来源：[`USER-FEEDBACK-20260826-22`](../sources/USER-FEEDBACK-20260826-22-hierarchical-workspace-and-evidence-review.md)。
- 工程依据：workspace `display_path`、Finding `file_refs`、Evidence Gap candidate refs、
  Branch `missing_file_refs`、Snapshot/version 与既有安全 Preview API。
- 数据依据：FORTE 固定公开输入，不是真实企业网盘或未公开 benchmark 样本。
- Git 风格只用于审查记录的信息结构；当前没有源文件提交 Diff、页内精确定位或语义判定。
- 本场景的自动化和截图不能证明目标用户理解、核对效率、信任或业务正确性。
