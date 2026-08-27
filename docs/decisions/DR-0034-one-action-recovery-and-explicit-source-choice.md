# DR-0034：单一恢复动作与明确原文选择

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`；确定性浏览器回归和截图已完成，目标用户效果仍待研究 |
| 日期 | 2026-08-27 |
| 触发来源 | [`USER-FEEDBACK-20260827-ONE-ACTION-RECOVERY`](../sources/USER-FEEDBACK-20260827-one-action-recovery.md) |
| 上游协议 | [`DR-0031`](DR-0031-active-budget-and-agent-owned-gap-recovery.md)、[`DR-0032`](DR-0032-persistent-decision-and-local-recovery.md)、[`DR-0033`](DR-0033-closable-review-and-branch-lanes.md) |
| 场景 | [`SCENARIO-020`](../scenarios/SCENARIO-020-retry-or-select-one-source.md) |
| Evidence | [`DR-0034-ONE-ACTION-RECOVERY-EVIDENCE-20260827`](../evidence/DR-0034-ONE-ACTION-RECOVERY-EVIDENCE-20260827.md) |

## 问题定位

现有 Runtime 已经区分 Branch、EvidenceResolution 和 DecisionRequest，但前台仍把两类完全不同的
人机任务压在一个“待处理”语义里：普通定位/结构缺口只需用户授权 Agent 重试，ambiguous 引用
则必须由用户从多个真实位置中选择。统一的长解释、默认展开的文件预览和可选输入框让用户误以为
自己必须先理解技术原因、修改文件或补写答案，服务端正确的局部恢复能力没有转化成清晰操作。

## 决策

1. 待处理分支总览动态显示“共有 N 个待处理，每次处理 1 个”，并按服务端事实区分两类动作：
   非 ambiguous Branch 标为“无需核对文件，建议重试”；ambiguous Branch 标为“需要从 N 个原文
   位置中选 1 个”。
2. 对可恢复的 `source_location/analysis_output` 和普通可继续 Gap，审查首屏只保留一个推荐主路径：
   “继续任务，只重试此分支”。同时明确“不需要修改文件，也不需要填写内容”，且点击前不启动
   调用、不消耗下一轮预算。
3. 可选输入默认折叠在“我有额外线索”下；原因、调用/采用回执和安全 Preview 折叠在“为什么停下 /
   查看相关文件”下。审计事实仍然可达，但不压过主动作。
4. ambiguous 首屏只回答“为什么需要我、我选什么、选完发生什么”。候选不默认选择；用户选择
   以前主按钮禁用，选择以后才能提交 versioned/idempotent Decision。
5. terminal Run 不能伪装原地恢复。其唯一主路径改为“用此分支新建任务继续”，明确旧 Run 已结束；
   旧 Snapshot、ArtifactVersion 和调用回执保持不变。
6. 本轮不改服务端协议、EvidenceResolution、expected version、幂等、Branch 局部恢复或预算计费。

## 前后台统一

| 前台状态 | 服务端事实 | 用户动作 | 隐藏/禁止推断 |
| --- | --- | --- | --- |
| 无需核对文件，建议重试 | waiting Branch + 非 ambiguous Gap/Resolution + recovery mode | 空反馈直接 resume 一条 Branch；可选 steer 后 resume | 用户必须修文件、填写答案、其他 Branch 已启动 |
| 需要从 N 个位置中选 1 个 | `EvidenceResolution(status=ambiguous).candidates[]` + open DecisionRequest | 先选 candidate，再 accept | 默认候选、随机定位、Finding 已被证明 |
| 为什么停下 / 查看相关文件 | Branch refs、Gap、模型 `called/output_used`、Preview GET | 按需展开审计 | 技术细节是继续的前置条件 |
| 继续任务，只重试此分支 | control `resume(branch_id)`，可选先 `steer` | 显式授权后才进入下一轮 | 点击前已调用模型或已花预算 |
| 用此分支新建任务 | terminal Snapshot + Branch objective + 新 Run POST | 创建独立 Run | terminal resume、覆盖旧成果 |

## 验收门

- retry 首屏可见且只有一个推荐继续动作；可选输入和文件审计默认折叠。
- ambiguous 明确要求“选 1 个”，无默认候选，未选择前主按钮禁用。
- Branch 总览在同一组中同时区分 retry 与 ambiguous。
- 390 px 视口中标题、关闭按钮和主次动作可见，页面与审查页无横向溢出。
- 既有 decision、Branch resume、terminal 新 Run、PostgreSQL 顺序恢复和全量门不回归。

## 边界

本决策只改变服务端事实的前台编排，没有新增模型能力、Worker、Tool、文件写入或外部动作。自动化
证明控件、状态和请求映射成立，不证明目标用户能在 3 秒内理解；该效果结论继续标 `Draft`。
