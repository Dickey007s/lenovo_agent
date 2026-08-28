# DR-0048：TC-10 规范片段消费与稳定 Effect 等待

- 状态：Implemented / Locally Verified；等待远端门与合并后转为 Accepted
- 日期：2026-08-29
- Source：`USER-FEEDBACK-20260829-TC10-INLINE-NORMATIVE-FRAGMENT-AND-EFFECT-WAIT`
- 继承：`DR-0047`

## 问题

`DR-0047` 已禁止未知规范静默通过，但首版解析器用行号表示“已识别”。一行包含既有 TIME 规则和新增规范时，只要 TIME 规则消费了该行，剩余规范也会被错误视为已覆盖。这会让来源账本、状态图、DOCX 和前台同时出现 false green。

测试侧另有独立 false red：Effect 等待以固定让出事件循环次数为界。在慢机上它可能在真实 Effect 写入前提前失败，无法表达“最多等待多少真实时间”。

## 决策

1. 对所有已选择规范行按句号、问号、叹号和分号拆成可定位片段；片段继续保留服务端来源行 locator。
2. 每个既有解析规则声明它实际消费的语义 token 组合。只有唯一匹配且尚未消费的片段可计为已覆盖；缺少必需片段、重复匹配或剩余片段不得由行号掩盖。
3. 剩余片段先经过冲突门。新的禁呼时间、每日/小时频次或身份/录音顺序与已解析参数不一致时 fail closed。
4. 支持的高龄、重病或显式转人工触发片段生成独立 `DISPUTE` rule，并由现有图编译器产生独立 guard 与 edge。其他规范性剩余片段进入 `outbound_unsupported_rule`，不生成绿色成果。
5. canonical Operations-008 原件和历史 Evidence 不修改；canonical 仍是当前来源观测的 34 条。只有合法变体动态增加规则、守卫和边。
6. 前台继续只投影公开 `outbound_flow_outcome.rules[]` 与 mapped IDs。浏览器不重新解析 Markdown，也不靠关键词猜测覆盖。
7. Runtime 测试等待使用事件循环的单调时钟 deadline 和短实时间隔；超时诊断包含 status、version、receipt 和 Artifact 数量。等待策略不改变生产预算、模型 deadline 或 Runtime 状态机。

## 可证伪门

- 同行追加高龄客户转人工：规则数、guard 数和 edge 数各增加 1，DOCX 独立 Verifier 仍通过，前台展开能看到独立 rule/guard/edge。
- 同行追加未知冻结账户规范：`outbound_unsupported_rule`。
- 同行追加“接通后第一步先告知录音”：`outbound_identity_order_conflict`。
- 同行追加第二套每日频次：`outbound_frequency_conflict`。
- 原 TC-10 canonical、dynamic、Verifier failure E2E 均继续通过；动态 fixture 必须来自服务端公共 manifest。
- 原 flaky Effect 测试重复运行，并与定向、全量 Python 门共同通过，不得靠隐藏 stderr 或无限增加等待次数。

## 边界

片段级消费是固定 Operations-008 适配器的来源完整性增强，不是通用自然语言规范编译器。它不证明来源是最新监管、不构成法律意见或生产审批，也没有执行任何外部动作。
