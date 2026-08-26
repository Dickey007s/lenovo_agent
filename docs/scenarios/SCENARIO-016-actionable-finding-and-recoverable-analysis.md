# SCENARIO-016：从可定位问题到人工决断，并从分析失败继续

## 用户、触发与痛点

产品或发布负责人要求 Agent 核对 F07 功能测试、兼容环境测试、需求基线和上线清单是否基于
同一代码版本。资料彼此矛盾时，用户既要迅速看到每个判断来自哪个文件哪一行，也要决定下
一步是先核版本、形成修复建议，还是补齐依赖记录。若模型给出的原文片段无法唯一定位，用户
不能只得到一个没有后续的“安全停止”。

## 主路径：可处置 Finding

1. Analyst 为每条 Finding 分别返回短事实、影响、完整说明和结构化人工复核建议。
2. Runtime 在本轮批准的安全文件内容中解析逐字引用。服务端生成文件、文本行或表格行位置；
   模型自报位置不进入公共事实。
3. 用户打开“问题处置单”，先看编号的“发生了什么、不处理的影响、现在需要谁做什么”。
4. 用户点击任一证据。右侧立即打开对应真实文件，高亮服务端确认的实际位置，并同时保留
   文件路径、位置、逐字摘录和安全预览边界。
5. 如果 `requires_human_decision=true`，用户先比较 A/B/C 的业务含义、受影响 Branch、所需
   来源、预计轮次和外部动作，再主动展开 Agent 推荐；也可补充版本、时间或业务口径。
6. 用户接受、否决或暂缓后，浏览器用 expected version 与幂等键写入绑定 Finding/Branch 的
   DecisionRecord。关闭或按 Escape 记录 `defer`，不是静默丢弃。
7. 接受业务选项后，浏览器才以 `option.next_instruction + 用户决定 + 用户补充` 创建新的独立
   Run。旧 Run、DecisionRecord、证据和成果版本不被覆盖；原文件不被修改。

## 异常路径：定位或结构不可采用

1. Analyst 候选包含无法唯一定位的 Finding 时，Runtime 在预算内最多重试一次，并把拒绝、
   新调用和是否采用写入有序 Trace。
2. 同一候选中仍有可唯一定位 Finding 时，服务端只采用这些 Finding，并记录省略数量；不得
   因一条坏引用抹掉整轮有效结果。
3. 服务端把每条 quote 标成 `exact/ambiguous/unavailable`。`ambiguous` 返回多个真实候选位置；
   `unavailable` 明确没有候选。位置状态只说明定位，不说明结论成立。
4. 两次都没有可采用 Finding，或两次结构输出都无法解析时，Runtime 完成本轮记录但不生成
   伪结果，把受影响 Branch 保持为 `waiting_input`，并提供 `recovery_kind`、候选 Branch 和
   最小下一轮问题。
5. 前台展示“已保留、未采用、未发生”三类事实。多候选时用户先选择真实位置，系统记录
   DecisionRecord，再按 versioned `steer` 和 `resume` 只继续该 Branch；其他分支与成果不变。
6. 若轮次、调用或时间预算不足，Run 以 `stopped/bounded` 结束并保留缺口，不转成通用失败。
   前台不再显示不可用的“继续”暗示，而是明确说明旧 Run 已结束，列出未完成 Branch、已保留
   的 Plan/调用回执/ArtifactVersion 和无外部动作边界。用户可补充方向，并以其中一条 Branch
   作为目标创建新的独立 Run；新 Run 重新冻结整库索引和自主选证，不假装续跑旧调用。
7. 对升级前的历史 `failed` Snapshot，前台用原任务和已保留范围构造明确的缩小范围重试入口；
   这是新 Run，不是假装恢复旧模型调用。

## 完成条件

- 新 Finding 的事实、影响和人工动作可分开扫描。
- 每个已采用 Finding 至少有一个服务端 Evidence Anchor；证据卡与实际 Preview 高亮一致。
- 人工选项明确显示确认后 Agent 做什么，DecisionRecord 留下 accept/decline/defer 与反馈，
  接受业务选项后反馈进入新 Run 指令。
- 原文定位或结构失败不会静默重试，也不会留下没有动作入口的页面；重连后待决状态仍可恢复。
- `stopped/bounded` 页面提供每条候选 Branch 的“用此分支创建新任务”，并验证不会向 terminal
  Run 发送 `resume/steer`。
- 已验证 Finding、分支状态、文件范围、调用回执和 ArtifactVersion 不因局部失败丢失。
- 所有页面都明确“只读、新 Run、未修改文件、未发生外部动作”。

## 来源与边界

- Stakeholder 来源：[`USER-FEEDBACK-20260826-ACTIONABLE-RECOVERY`](../sources/USER-FEEDBACK-20260826-actionable-conflict-and-recovery.md)。
- 研究依据：[`ACTIONABLE-HITL-RECOVERY-RESEARCH-20260826`](../research/ACTIONABLE-HUMAN-DECISION-AND-FAILURE-RECOVERY-20260826.md)。
- 延续设计：[`DR-0029`](../decisions/DR-0029-server-verified-evidence-anchors.md) 与
  [`SCENARIO-015`](SCENARIO-015-pinpoint-and-compare-agent-evidence.md)。
- 自动化只证明协议映射和操作可达；真实 Provider Run 只证明本次候选经服务端规则进入
  等待、采用或有界停止，不证明 Finding 语义正确或人工推荐合理。
