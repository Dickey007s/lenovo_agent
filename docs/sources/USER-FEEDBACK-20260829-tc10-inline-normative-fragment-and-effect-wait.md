# USER-FEEDBACK-20260829-TC10-INLINE-NORMATIVE-FRAGMENT-AND-EFFECT-WAIT

## 来源

- 类型：Stakeholder 独立验收、来源变异审计与工程门稳定性反馈
- 日期：2026-08-29，Asia/Shanghai
- 场景：固定 `Operations-008` 来源推导外呼流程，以及 Scenario Effect 异步测试等待
- 状态：已记录；实现与验证结论由 `DR-0048` 及其 Evidence 单独给出

## 发现的负例

1. 在已经被 TIME 解析器识别的同一行末尾追加“高龄客户必须立即转人工”，旧实现会因为该行号已进入 `recognized_numbers` 而跳过整行剩余内容。结果仍显示批准待审、34 条规则，新增要求既没有独立 rule，也没有 guard/edge。
2. 同样把未知规范、冲突的身份/录音顺序或第二套频次参数追加到已识别行，也可能绕过未知规则与冲突门。
3. `_wait_for_effect` 只执行 500 次 `await asyncio.sleep(0)`。在单测较多、线程 Effect 较慢的机器上，循环次数先耗尽会产生偶发 false red；单独重跑又能通过。

## Stakeholder 要求

- 规范解析必须按可审计语句或片段消费。识别一行中的已知要求不能代表该行的所有内容都已覆盖。
- 同行新增高龄或重病转人工要求必须成为独立规则，并动态增加 guard 与 edge；不能只让关键词被动出现在既有 excerpt 中。
- 同行未知规范、冲突顺序和冲突数值必须 fail closed。
- 异步 Effect 测试使用单调时钟 deadline 与短实时间隔，并在超时时输出 Run 状态、版本、Artifact 和 receipt 数量。

## 局限

这是一条固定来源解析与工程门负例，不是外呼合规用户研究、法律意见或生产稳定性 SLA。修复只证明批准 Markdown 的规范片段不会因共享行号被静默忽略；它不执行拨号、CRM、短信、禁呼写入或转人工。
