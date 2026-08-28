# DR-0043：TC-11 来源推导风险、正式业务 Gate 与双状态前台

- 状态：Accepted；本地来源变异、Artifact 解析、前台与 PostgreSQL 顺序恢复已验证，真实 Provider 与远端 PR 事实见 Evidence
- 日期：2026-08-28
- Source：`USER-FEEDBACK-20260828-TC11-DERIVED-RELEASE-GATES`
- Scenario：`SCENARIO-029`

## 决策

1. TC-11 继续从 Workspace-first 通用入口触发，不增加 Scenario 选择器。固定适配器只匹配普通办公指令与 `pm-014` 四份 allowlisted 输入。
2. 服务端严格解析 PRD 18 项功能和配置、功能测试、兼容测试各 13 项记录，校验表头、必填列、编号、名称、优先级、状态、数字范围、交叉表一致性和八个唯一兼容环境。重复行不能被字典覆盖。
3. 每项风险从 PRD 规则、功能优先级、测试原因类型和异常环境数量推导，并只保留最高等级。固定样本的严重 4、主要 2、次要 2 是期望结果，不是实现常量。
4. 正式上线 Gate 只包含 P0 提测率、P0 已提测功能可接受结论率、P1 已提测功能通过率和严重问题清零。每项保留分子、分母、运算符、阈值、结果和来源规则；零分母明确失败。
5. P0/P1/P2 用例通过率和综合用例通过率单列为辅助质量指标，不参与上线 Gate 聚合。
6. 输出真实 `上线合规与风险报告.docx` 和 `上线功能风险逐项台账.csv`。DOCX 必须含结构化 Gate、18 项矩阵、风险、未提测和整改计划表；CSV 一行一个 PRD 功能并可独立复算。
7. 前台使用通用 `business_gate_outcome` 投影业务结论。Artifact `verifier_status=passed` 与 EffectReceipt `status=passed` 只证明确定性文件效果；`business_gate_outcome.status=failed` 单独以非绿色状态显示“不得上线”。
8. 任一来源合同或 Verifier 失败时，Artifact/EffectReceipt 必须失败，保留错误和恢复动作，不显示可靠报告或全绿回执。
9. 四份原件在构建前后由服务端再次读取并逐字节比较；运行只写隔离 Run Workspace，不执行上线、不修改配置、不发送通知。

## 前后端事实

| 前台 | 服务端事实 | 不允许推断 |
| --- | --- | --- |
| 不得上线 | `business_gate_outcome.status=failed`、`decision`、4 个 `gates[]` | Artifact 生成失败；真实上线已被系统阻止 |
| 4/4 条业务 Gate 未通过 | 每项 `numerator/denominator/operator/threshold/actual/passed` | 用例通过率就是正式 Gate |
| 确定性检查通过 | Artifact `checks[]`、`verifier_status=passed`、EffectReceipt `status=passed` | 业务条件通过；整个 Run completed |
| 18 项逐功能台账 | `business_gate_outcome.records[]` 与下载 CSV | 浏览器自行推导风险或补全缺失行 |
| 辅助质量指标 | `auxiliary_metrics[]` | 指标替代 PRD 上线条件 |
| 没有外部动作 | `original_inputs_modified=false`、`external_action=none` | 已执行上线、改配置或发通知 |

## 拒绝的替代方案

- 按功能名称写死风险集合：拒绝。固定样本相同也不能证明规则实现。
- 检查固定百分比或“不得上线”字符串：拒绝。结论必须由来源数据和 Gate 布尔聚合产生。
- 用 `max(1, denominator)` 避免除零：拒绝。空分母是数据合同错误。
- 用绿色文件检查覆盖业务失败：拒绝。用户必须先看到业务结论和四条原因。
- 只输出摘要段落：拒绝。用户需要结构化 DOCX、18 行 CSV 和来源行台账。

## 验证门

- 来源变异：F17 的异常环境从 4 改为 2 后由严重降为次要；F05 原因改为界面缺陷后由主要降为次要；移除 F02 问题后其风险消失。
- 负向来源合同覆盖重复/未知编号、名称与优先级冲突、未知状态、非法数字、通过数越界、环境重复语义和零分母。
- 下载后独立解析 DOCX/CSV：6 个表、18 行、严重 4/主要 2/次要 2、5 项未提测、四条 Gate 与无外部动作声明。
- 强制 Verifier 失败时两份 Artifact/EffectReceipt 保持失败，前台不出现可靠报告或 9/9 绿灯。
- 真实 PostgreSQL 重启后两份 Artifact、EffectReceipt、18 项业务台账与下载 bytes 一致；只证明顺序 Runtime 已提交状态恢复。
