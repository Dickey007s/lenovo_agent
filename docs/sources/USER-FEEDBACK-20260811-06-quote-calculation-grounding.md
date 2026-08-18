# USER-FEEDBACK-20260811-06：报价核算与数据来源回答错误

## 1. 来源

本记录来自 2026-08-11（Asia/Shanghai）当前 Codex 协作任务中的 Stakeholder 试用反馈。用户在报价工作台看到三行报价后，先要求 Agent 重算，再追问数据来源，并明确反馈：

> “还有就是报价工作台这里是不是出问题了，为什么回答给我的数据是错误的数据，让它再算还是错”

两张原始截图已稳定留存：

| 截图 | 尺寸 | 文件大小 | SHA-256 | 记录的现象 |
| --- | --- | ---: | --- | --- |
| [`user-feedback-20260811-quote-wrong-calculation.png`](../evidence/assets/user-feedback-20260811-quote-wrong-calculation.png) | `1820 x 780` | 207234 bytes | `FACD5442C27D6175A7B3BC14600DFEF78E88F0CCD66380DDDFD21D9B4A2DF071` | 工作台显示折后总计为 253400 元，但 Agent 回答使用 2000000 元与 1770000 元并给出 88.5% |
| [`user-feedback-20260811-quote-wrong-source-followup.png`](../evidence/assets/user-feedback-20260811-quote-wrong-source-followup.png) | `601 x 366` | 56367 bytes | `C5773369F568936295D1706890599146BF323CE407E7D52A4AB80052BD1B3E76` | 追问“你的数据是哪里来的”后，Agent 又把 253400 元同时当作原价和折后价，并声称无法计算 |

来源类型登记为 **Stakeholder feedback**。这是项目决策者对当前可运行原型的直接反馈，不是目标用户访谈、可用性实验或统计性用户研究。

## 2. 用户场景与问题

- **目标角色**：需要核对客户报价的销售、客户经理或报价审批人。
- **触发条件**：用户正在报价工作台编辑数量或折后比例，并用自然语言询问“总折扣多少”“再算一次”或“数据从哪里来”。
- **当前痛点**：界面与 Agent 使用了不同的数值事实；Agent 会从历史对话或模型生成内容中补造总价，用户无法判断当前屏幕、保存版本和回答哪个可信。
- **目标**：界面与 Agent 对同一组当前行项目给出一致、可复算的标准总价、折后总价、优惠金额、综合折后比例、优惠率和最低折后比例检查，并明确数据来自演示工作区而非真实 CRM。
- **完成条件**：基线三行必须重算为标准总价 272000 元、折后总价 253400 元、优惠金额 18600 元、综合折后比例 93.16%（约 9.32 折）、优惠率 6.84%；修改数量或折后比例后，界面和 Agent 同步更新；旧 `subtotal/total` 不得覆盖行级重算。
- **关键异常**：字段为空、非数字、越界、行数与服务端版本不一致或金额超出安全范围时，应停止显示总计并明确要求修正，不能回退到历史金额或让模型猜测。

## 3. 支持的判断

- 报价数值属于可验证业务事实，不应由 LLM 自由生成；前端显示与 Agent 回答必须采用同一套明确公式与舍入规则。
- 未保存的 `qty`、`discount`、`name` 和 `valid_until` 可以参与当前核算，但报价编号、客户、币种、最低折后比例、标准价和来源必须保持服务端所有权。
- 用户追问来源时，回答需要同时说明使用的是当前屏幕行项目、计算公式和演示数据边界；不能暗示访问了真实 CRM。
- 保存已修改报价后必须显示需要重新复核，不能沿用演示基线的审批结论。

## 4. 局限

该反馈足以证明原回答与界面数值冲突，并约束确定性核算与来源说明，但不能证明修复后的交互已被目标用户理解，也不能证明真实企业报价、税费、多币种、阶梯价或审批政策已经接入。当前基线仍是固定演示数据。

实现中增加的 Artifact/revision 冲突保护、服务端 Action/source 绑定和结果重放，是为避免“当前屏幕、保存版本、回答与执行对象不一致”而采取的工程防护，不应反写成用户已经明确提出或验证了这些具体机制。其有效范围以 `DR-0006` 和 Evidence 的自动化结果为准。

## 5. 关联项

- Source ID：`USER-FEEDBACK-20260811-QUOTE-CALCULATION-04`
- Decision：[`DR-0006`](../decisions/DR-0006-deterministic-quote-calculation.md)
- Evidence：[`QUOTE-WORKSPACE-DETERMINISTIC-CALCULATION-EVIDENCE-20260811`](../evidence/QUOTE-WORKSPACE-DETERMINISTIC-CALCULATION-EVIDENCE-20260811.md)
- UI 事实矩阵：[`UI_SERVER_FACT_MATRIX.md`](../contracts/UI_SERVER_FACT_MATRIX.md)
- Implementation commits：`2f9866f + fe865bd + e2c4b56`
- Evidence status：`Verified`（固定演示报价与被测协议/UI 范围；不改变本记录仍是单一 Stakeholder feedback 的性质）
