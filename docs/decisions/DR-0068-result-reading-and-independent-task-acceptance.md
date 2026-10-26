# DR-0068：成果分层阅读与独立任务验收

| 字段 | 内容 |
| --- | --- |
| 状态 | Limited Verified，117 项原系统浏览器、49 项受控 Runtime 与构建通过；真实跨领域任务未通过结论验收 |
| 日期 | 2026-09-22 |
| 来源 | USER-FEEDBACK-20260922-RESULT-ACCEPTANCE；RUNTIME-20260922-RESULT-ACCEPTANCE |
| 前置 | DR-0037 / DR-0046 / DR-0052 / DR-0053 / DR-0055 / DR-0066 / DR-0067 |
| 场景 | [SCENARIO-055](../scenarios/SCENARIO-055-read-results-and-check-office-delivery.md) |
| Evidence | [验收记录](../evidence/DR-0068-RESULT-ACCEPTANCE-20260922.md) |

## 场景与来源

[本轮用户批准](../sources/USER-FEEDBACK-20260922-result-acceptance.md) 延续原系统成果页的减法设计，
同时验证单项办公、跨领域协作和局部恢复。前一轮已改导航，本轮不另建产品或增加 Demo 选择器。
工作树基线 HEAD 为 `9a4bbbffe9d3477610718fbba8dae47749ac9aee`；包含此前未提交工作，未提交或创建 PR。

真实运行暴露出重要反例：只读 Worker 的来源能唯一定位，但已采用文字中仍有错误数字。
因此本决策的有限结论是改善阅读层级、独立验收固定成果，不是补齐通用语义验证。

## 前台交互影响

1. 分析记录使用中性文件标识与“已保存 / 草稿已保留”，不再用绿色提交标识暗示结论正确。
   `review_required` 继续显示“结论待复核”。已生成文件仍独立展示其真实检查与业务边界。
2. 普通发现默认显示前三项，每项先看事实与影响，“查看依据 · N 份资料”按需展开。
   N 对真实 file refs 去重；失联资料显示不可用，不能伪造文件名或来源位置。
3. 所有仍待决定的发现保留在默认层，即使在第四项之后；需要人处理的按钮不藏在依据内。
   顶层已接受、过期等终结状态优先于嵌入的旧 open 状态；历史 Run 只给只读记录入口。
4. 财务校验通过的文件卡保留文件、条数、期间、用途、下载和非付款边界。长计算口径、关键
   输出及复核说明按需展开；失败文件不折叠处置说明。总额、候选和最终财务处置仍分开。
5. 后续建议明确“尚未执行”，打开依据不创建任务，不发送控制，不消耗模型预算。
   原审查、返回、Escape、版本历史、Loop/Swarm 入口不变。

## 后端事实映射

- 无 Runtime、持久化、工具权限或公开 API 修改。Snapshot 仍是权威，SSE/版本单调规则不变。
- 分析版本与保存状态来自 ArtifactVersion / TaskCommit；它们证明保存，不证明业务正确。
- 发现、来源及复核标记来自现有 Result/Artifact；待决由既有 `findingReviewRequest` 解析顶层
  DecisionRequest。只有没有权威 request 的旧记录才使用旧 Finding/DecisionRecord 回退。
- 默认展开数量只是客户端投影，不截断实际 findings；接受/拒绝仍走原 Owner、expected version、
  幂等键和 source revision。收起详情不等于已接受，不触发任何写入。
- 财务各文件用途与期间来自 Artifact 字段。金额与候选来自 `finance_review_outcome`；前台没有
  重新计算或静默改写内容。`verifier_status=failed` 的错误提示与处置保持可见。

## 验证与边界

见 [本轮报告](../reports/demo12-outcomes-20260922/README.md)。两次真实 Provider 任务总计 8 次调用，
每任务上限 3 轮、12 次调用、600 秒 active time，临时 memory 状态库，外部动作均未发生。

- 财务：三份下载文件用独立 `openpyxl + Decimal` 从原表逐行重算；96 份原输入 hash 未变。
  临时副本修改金额、位置、删除行且同步改下载回执，三个负例仍被独立核对拒绝。
- 跨领域：5 个工作包、4 个 Worker 回执、2 个贡献采用；搜索歧义、下游修复未通过、最终仍等待。
  已采用产品分析的 P0 数量与提测数量错误，不能汇报为协作任务完成或已验证的业务结论。
- 恢复：新增实际 Runtime + ASGI `/continue` 受控测试，不手工植入 Artifact/Commit；失败分支
  续办为同 Task 新 Run，兄弟调用数与父 Snapshot 不变，重放不新增调用。
- UI：覆盖 1920/390、键盘展开、返回、全部发现和第五项待决。具体最终工程门见 Evidence。

真实 Provider 只运行两个固定例；无统计显著性、真人可用性、生产部署、跨实例恢复或新 PG
重启证据。独立验收不回写模型 Snapshot；失败原文与回执原样保留。下一优先级是只读分析的
完整表格读取、数字核验与下游真实交接，而不是继续增加可视化统计卡。
