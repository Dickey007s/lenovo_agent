# SCENARIO-041：五个工作包的可恢复执行与局部成果收敛

- 状态：`Limited Verified`；固定 Fixture、Memory/API、浏览器与隔离 PostgreSQL 17.11
  单主机顺序门通过
- 决策：`DR-0055`
- Source：`USER-FEEDBACK-20260831-DEMO1-DEMO2-FIXED-SCENARIO-HARDENING`、
  `MULTI-AGENT-ORCHESTRATION-OFFICIAL-20260830`、
  `AGENT-INTEROP-AND-ELICITATION-OFFICIAL-20260830`、
  `HAI-MIXED-INITIATIVE-RESEARCH-20260830`

## 用户、触发与完成条件

- 用户：需要核对产品、法务、运营、质量和发布材料，但不愿管理多个 Agent 会话的业务
  负责人。
- 触发：validated plan 形成五条 Branch，其中三项能独立读取，两项依赖前置结论；
  `TopologyAdmission` 判断为 `adaptive_readonly_workers`。
- 用户目标：知道为什么值得并行、每个工作包实际做到哪一步、哪个返回已进入统一成果、
  某一项失败会影响谁。
- 完成条件：五个 WorkUnit 与 Branch 一对一；采用候选形成 append-only ArtifactVersion；
  失败或歧义只阻塞依赖它的工作包，旧成果和兄弟成果不被覆盖。

## 正向主路径

1. 前台显示路线建议：跨多个来源且存在三个独立 root，最多启动三个只读 Worker；同时
   显示预算、只读和无外部动作边界。
2. 用户确认后，服务端先持久化第一波 `u1/u2/u3` 的 reservation 和预算，再启动 Worker。
   `u4 <- u1`、`u5 <- u2` 保持 pending，不提前调用。
3. 每个 Worker 返回时追加独立 Contribution。前台先显示“已返回”，只有通过来源、Anchor、
   Branch Evidence Gate 和适用对账后才改成“已采用”。
4. 第一波 adopted 后形成 Artifact v1；依赖已满足的 `u4/u5` 进入 ready。用户无需重开
   已完成工作包，也无需把多个对话手工复制到一起。
5. 第二波完成后形成 Artifact v2 和新的 TaskCommit；v1、第一波 Contribution 和每个
   attempt 继续可审计。

## 用户动作

| 时点 | 用户看到 | 用户可做 | 不会发生 |
| --- | --- | --- | --- |
| 路线等待确认 | 为什么建议 Worker、预计上限、预算和只读边界 | 确认或降级单 Controller | 自动扩容、隐藏调用 |
| Worker 运行 | 工作包、依赖、实际状态和已批准来源 | 展开来源和 Trace | 管理 Worker 私聊、改 Prompt |
| Contribution 返回 | 返回/采用分离、Gate 结果和原因 | 回开 Anchor、处理单个异常 | “返回即真相”或最后回复覆盖 |
| 部分成果 | ArtifactVersion、已采用项、待处理项和阻塞影响 | 下载已有成果、只处理目标异常 | 清空兄弟成果、改写源文件 |
| 全部收敛 | v1/v2 历史、当前 Commit 和只读边界 | 审查或恢复历史成果 | 外部发送、审批或生产变更 |

## 异常 A：两项采用，一项引用歧义

- 触发：`u1/u2` 的 Evidence Anchor 唯一，`u3` 的逐字 quote 在批准文件中出现多个位置。
- Agent 路径：`u1/u2` Contribution adopted 并形成可用 v1；`u3` 记录为 waiting，依赖
  `u3` 的下游 blocked，依赖其他 root 的工作包仍可继续。
- 前台输出：“已有 2 项进入成果，1 项需核对原文位置”；显示具体受影响工作包，而不是
  把整个 Run 涂成失败。
- 用户动作：回开真实候选位置并处理该异常；首版尚无 Worker 专属局部恢复 API，不能
  声称一次选择后只重放远端 Worker。
- 后端事实：WorkUnit state、不可变 Contribution、Branch Evidence Gate、
  ArtifactVersion/TaskCommit 和 ordered named SSE。
- 当前边界：Anchor 证明位置与 membership，不证明语义、穷举或业务结论正确。

## 异常 B：Worker 已返回但候选被拒绝

- 触发：Contribution 使用越 Branch 文件、缺 Anchor、来源 revision 已变化、候选被篡改，
  或 narrative/deterministic reconciliation 冲突。
- Agent 路径：保留调用回执和 rejected Contribution，不进入 Artifact；已 adopted 兄弟项
  不回滚。
- 前台输出：“已返回，未进入成果”，并用中文说明来源越界、定位不足或对账冲突；不把
  `output_used=false` 说成未调用。
- 用户动作：审查来源和影响，结束或在后续受控任务中重试。
- 后端事实：`model_called/output_used`、Contribution gate status/reason、WorkUnit version、
  `contribution_rejected` 和最终 GET。
- 当前边界：普通候选问题局部化；Catalog/Preview 完整性失败仍必须 fail closed。

## 异常 C：服务在模型调用中断

- 触发：WorkUnit 已 reserved/running，但 API 进程在 Provider 返回前停止。
- Agent 路径：重启读取 durable WorkUnit，将在途 attempt 标成需处理的失败状态；绝不
  自动重放模型调用，也不伪造 Contribution。
- 前台输出：“上次调用未确认返回，未自动重试；已有成果保留”。
- 用户动作：审查后使用新的幂等键和当前 version 显式重试该工作包；原幂等键只回放旧
  reservation。不能从旧页面假定 Provider 没有收费或副作用。
- 后端事实：持久 WorkUnit、attempt/version、checkpoint recovery 和无新增 Contribution。
- 当前边界：首版没有 durable queue/lease、跨实例 Worker ownership 或在途 HTTP 续跑。

## 反例：三期同结构财务核对

- 触发：三份同结构期末明细需要生成未付、未收和跨期说明；Prompt 即使写“多 Agent”也
  不能成为准入事实。
- Agent 路径：Admission 选择 `fixed_workflow`，使用既有确定性适配器顺序处理，不创建
  Worker WorkUnit/Contribution 事件。
- 前台输出：解释未付统计、未收统计和跨期说明各代表什么，并说明没有启用多 Worker 的
  原因是结构一致、依赖强、固定核对更可控。
- 当前边界：这只证明路线规则和固定 Fixture，不证明对真实财务数据的通用正确性。

## 设计来源怎样改变前台

- OpenAI Agents SDK 与 Anthropic 的实践说明并行只适用于真实独立工作面，因此路线卡
  必须先解释为什么并行，而不是先展示多个 Agent。
- A2A 对 Task、状态、Artifact 和按序事件的区分支持把“执行状态”和“可交付成果”分开；
  本项目据此把 Contribution 返回与 Artifact 采用分开，但不宣称协议兼容。
- Microsoft HAI 指南支持及时显示状态、后果和纠错入口，因此前台突出失败影响、当前
  可用成果和唯一下一步，而把内部 reservation/digest 隐藏。

## 验证与局限

当前自动化已经验证五单元 DAG 的三 root/两 dependent 两波推进、局部 waiting、兄弟
成果保留、fixed workflow 反例、Snapshot/SSE 对账和 1440/390 布局。隔离 PostgreSQL
17.11 门又验证已完成候选与 v1/v2 重启后保留、在途 WorkUnit 不自动重放，以及新幂等键
只重试 checkpoint-recovered 目标 Branch；与 Task Ledger 一起最终为
`10 passed in 10.84s`。整库结果为 `417 passed, 23 skipped`，Playwright 为 `68 passed`。

这些固定 Fixture 与自动化只证明被测状态可复现，不能证明目标用户理解更快、信任更高、
多 Worker 更省成本或真实 Provider 更可靠。形成性用户研究仍需让参与者回答：哪项已
返回、哪项已采用、失败影响谁、点击下一步会不会触发外部动作。完整工程记录见
[`DR-0055 Evidence`](../evidence/DR-0055-WORKUNIT-CONTRIBUTION-LEDGER-V1-EVIDENCE-20260831.md)。
