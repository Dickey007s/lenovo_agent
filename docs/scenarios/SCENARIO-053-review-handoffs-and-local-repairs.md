# SCENARIO-053：核对交接中的分歧并局部修复

| 字段 | 内容 |
| --- | --- |
| Target user | 需要核对产品、搜索运行与用户体验的项目负责人，对最终业务判断负责 |
| Trigger | 多来源分析要合成简报，其中一包结构损坏、引用多位置或前后口径冲突 |
| Current pain | 下游拿到摘要就合并；用户分不清已经交付什么、重试了谁、冲突是否解决 |
| Goal | 只修能自动修的局部结构，保留有效成果，向人呈现仍需判断的引用与分歧 |
| Completion condition | 服务端记录每次调用/采用及前序核对；冲突不进入当前综合成果；旧成果不变；输出约定在文件写入前生效 |
| Source | USER-FEEDBACK-20260922-RESEARCH-DEMO12-ROUTES；RESEARCH-20260922-HUMAN-AGENT-TOP-VENUES |
| Decision | [DR-0066](../decisions/DR-0066-reviewed-handoffs-and-output-agreement.md) |
| Evidence status | Limited Verified，确定性 Runtime、浏览器 Fixture、PostgreSQL 单主机门；未做本轮真实模型及目标用户试用 |

## Happy path

1. 在原办公资料库或能力页创建任务，写“核对产品上线、搜索运行和用户体验，汇总风险与待办”，
   选择仅页面分析。提交后冻结合同；没有新增报告文件，也不修改原件。
2. 服务端验证计划并等待显式只读协作确认。每波最多 3 个 ready 工作包；先分析根来源。
3. 一个 Worker 结构错误时仅它进行最多一次有预算修复，其它采用成果不重做。修复仍失败则保留待办。
4. 后续显式波次拿到真实直接前序摘要与版本，逐项核对并引用批准原文。
5. 无分歧且通过其它门的贡献进入新版本。原任务页展示交付清单、证据入口与当前成果，协作页
   展示真实角色与输入核对回执。查看记录不调用模型。

## Exception path

- 输出选项与明确禁文件文字冲突：422，未创建 Run；文字保留，改选后用新请求键提交。
- 多处原文、来源越权、超时：不借自动结构修复掩盖风险；旧有效成果保留，具体处置仍走既有入口。
- 下游漏核对一个前序、引用错贡献或无关联原文：最多一次结构修复，仍不合格则不得采用。
- `conflict/insufficient`：显示模型意见与其引用，综合候选未采用；不是业务结论已被人拒绝。
- 没有额外预算或发生 stop：不再发新修复调用。暂停/停止不承诺取消已经开始的模型 HTTP。
- 刷新/重启：已落库核对意见恢复，旧 Artifact 不改写，不自动重放 Worker；memory 模式不保证重启恢复。
- 人选择后续核查方向：现有单分支恢复可用，但不是“按下确认便解决事实冲突”的新协议。

## 前台交互影响

原路径 `/` 与 `/agent-capabilities` 不变。输出选择、交付清单与协作回执都在原工作面；
当前待办不被长清单压到末尾。默认前三项、完整信息可展开。未知绑定明确显示未知，历史只读。
内部 Contribution 身份、原始模型响应与路径不作为业务文案。

## 后端事实映射

`HarnessRunStart.output_preference -> contract.output_policy`；
`contract.collaboration_protocol -> Worker 职责/结构核对`；
`worker_runs[].repair_count/dependency_assessments -> 重试/分歧显示`；
`ArtifactVersion.findings[].affected_branch_ids -> 工作项交付绑定`。
沿用 Owner、expected version、start/control/Worker 幂等、Task lineage 和 append-only Artifact。
服务端事实缺失不补造，不以模型结论替代来源/位置验证，不以源码结构测试替代语义和用户效果。

验证入口：[可操作验收](../reports/demo12-research-20260922/README.md)、[Evidence](../evidence/DR-0066-REVIEWED-HANDOFFS-20260922.md)。
