# DR-0036：成果优先、版面容错定位与任务范围收敛

## 决策元数据

| 字段 | 内容 |
| --- | --- |
| 状态 | `Limited Verified`；确定性 Runtime/E2E 与一次真实 Provider 纵切已覆盖，重复稳定性与目标用户效果仍待验证 |
| 日期 | 2026-08-28 |
| 触发来源 | [`USER-FEEDBACK-20260828-TC01-OUTCOME-CITATION-CONFUSION`](../sources/USER-FEEDBACK-20260828-tc01-outcome-and-citation-confusion.md)、[`RUNTIME-OBSERVATION-20260828-TC01-PDF-LAYOUT-ANCHOR`](../sources/RUNTIME-OBSERVATION-20260828-tc01-pdf-layout-anchor.md) |
| 上游协议 | [`DR-0029`](DR-0029-server-verified-evidence-anchors.md)、[`DR-0034`](DR-0034-one-action-recovery-and-explicit-source-choice.md)、[`DR-0035`](DR-0035-scenario-effect-gate-and-run-workspace-artifacts.md) |
| 场景 | [`SCENARIO-022`](../scenarios/SCENARIO-022-verified-outcome-and-audit-location.md) |
| Evidence | [`DR-0036-TC01-OUTCOME-EVIDENCE-LOCALIZATION-EVIDENCE-20260828`](../evidence/DR-0036-TC01-OUTCOME-EVIDENCE-LOCALIZATION-EVIDENCE-20260828.md) |

## 问题定位

TC-01 的确定性工具已经生成并验证成果，但 PDF 版面换行让 Analyst 的逐字 quote 无法按旧算法
匹配。服务端随后把同一来源缺口投影到两个 Branch，并允许范围外 Finding 和无矛盾证据的人工
Gate 进入流程。后端仍然保留了真实成果，前台却先展示“缺引用”和“重试分支”，用户自然会把
审计定位失败理解为日期错误或任务未完成。

## 决策

### 1. 严格匹配失败后，允许版面归一化的唯一定位

文本定位仍先执行原有逐字/空白归一化匹配。只有没有候选且 quote 归一化后至少 12 个字符时，
服务端才执行第二层版面归一化：忽略空白和标点，但保留字符到安全 Preview 行号的映射。只有一个
匹配位置才能成为 `exact`；两个以上位置继续成为 `ambiguous`，绝不替用户猜选。

这不是模糊搜索或语义相似度。它只修复 PDF/DOCX 提取产生的断行和标点差异，不改写 quote，
也不把唯一位置解释为结论正确。

### 2. 用用户指令中的明确日期窗口收敛 Finding

Runtime 从原始 `instruction` 读取“X 月 X 日至/到 X 月 X 日”的闭区间。Finding 完成服务端
Anchor 定位后，若其所有 `observed` 日期都在窗口外，则不采用该 Finding，也不让其 Resolution
阻塞本轮，并记录 named event `analysis_scope_filtered`。

当前只实现明确中文月日闭区间，不声称已经有通用对象、部门、版本或任意谓词编译器。没有可定位
日期的 Finding 不会被猜测过滤，越权 `file_ref` 和 Catalog 完整性错误仍 fail closed。

### 3. 人工 Gate 必须有服务端定位的矛盾证据

若模型输出 `requires_human_decision=true`，但该 Finding 没有任何 `role=contradiction` 的 exact
Anchor，服务端移除 review，保留普通 Finding，并记录 `decision_gate_suppressed`。关键词、优先级
或覆盖关系已经明确时，不再让用户重复决定。

### 4. TC-01 Verifier 必须核对 PDF 规则合同

`check-onboarding-mapping` 不再只检查输出行长度和“是/否”。它还从批准的 PDF 安全 Preview 中
确定性核对三类岗位关键词、分类优先级和多条备注同时生效规则。找不到这些固定规则片段时，TC-01
效果门失败，不能仅凭 CSV 已生成显示 5/5。

### 5. 前台先交代成果，再交代审计

当 `workspace_artifacts[]` 全部通过、EffectReceipt 为 `passed`，但 Loop 仍因来源定位处于
`waiting_input` 时：

1. 真实成果区移到本轮内部 Branch 和 Gap 之前，先显示文件名、5/5、下载和原件只读事实。
2. 状态改为“成果可用，审计待补充”，明确缺的是 Agent 说明中的原文位置，不是源文件或日期结果。
3. 仅在这个状态下，把相同 `candidate_file_refs` 且失败说明相同的多个 Gap 合并成一个审计项，
   显示“同一来源影响 N 个内部步骤”；同文件中的不同失败说明仍分开，Snapshot 的 Branch、Gap
   和恢复协议不变。
4. 动作改为“补齐来源定位”，并写明不会重新生成或覆盖当前成果。没有已验证成果的普通恢复仍沿用
   `DR-0034` 的“继续此分支”语义。

## 前后台事实映射

| 前台状态 | 服务端事实 | 用户动作 | 禁止推断 |
| --- | --- | --- | --- |
| 成果可用，审计待补充 | passed EffectReceipt + 全部 Artifact checks passed + `waiting_input` | 下载/复核成果；可选补齐定位 | Run completed、所有 Finding 正确 |
| 5/5 项检查通过 | TC-01 Artifact `checks[]`，含 PDF 规则合同 | 展开逐项检查 | 引用位置等于规则执行正确 |
| 1 处来源定位待补充 | 多个 Gap 共享同一组 `candidate_file_refs` 和失败说明的客户端合并投影 | 打开一个审计项 | 后端 Branch 被合并或删除 |
| 已过滤范围外候选 | `analysis_scope_filtered` | 无需用户处理 | 任意范围表达式都已支持 |
| 已取消无证据人工阻塞 | `decision_gate_suppressed` | 普通复核，不创建 DecisionRequest | 模型 review 永远错误 |

## 验收门与边界

- 唯一断行引用定位为 exact；相同断行片段出现两次仍返回两个候选。
- TC-01 噪声回归同时覆盖 5/5 Artifact、4 月 21/23 日范围外候选、无矛盾 review、三 Branch 和
  PDF 断行，最终 Run 完成且没有开放 DecisionRequest。
- 确定性浏览器 Snapshot 覆盖成果优先、两个 Gap 合并为一个审计项、桌面/390 px 无横向溢出。
- 用户原始 TC-01 指令的一次真实 `deepseek-v4-pro` 运行在第 1 轮 `completed`：真实 CSV 5/5、
  三个 Branch 全部完成、0 Gap、0 开放 DecisionRequest；本机使用 memory store，不是重启恢复证据。
- 历史 Snapshot 不重写；已存在的 waiting Run 只得到更清楚的客户端投影，新 Run 才使用新的定位、
  范围和 Gate 准入逻辑。
- 自动化、一次真实运行与截图不证明目标用户理解提升；真实 Provider 仍可能在重复运行中产生其他
  不可定位或不正确的内容。
