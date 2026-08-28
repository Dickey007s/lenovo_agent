# 运行观察：TC-01 的 PDF 版面换行造成假性 unavailable 引用

## 来源

- Source ID：`RUNTIME-OBSERVATION-20260828-TC01-PDF-LAYOUT-ANCHOR`
- 类型：当前产品 Snapshot、安全 Preview、下载成果与源码联合审计
- 日期：2026-08-28，Asia/Shanghai
- 观察 Run：`harness:8fa03852b0474c6db199587988c5a616`
- 固定数据：FORTE commit `345c1ec1487139db9dd319787fa9405ba85d1869`

## 已确认事实

1. Run 在第 1 轮进入 `waiting_input`，但 `入职资产匹配表.csv` 已生成，EffectReceipt 为
   `passed`，5/5 检查通过，原始输入没有修改。
2. Analyst 引用的优先级原文包含连续文本“技术研发”；PDF 安全 Preview 因版面提取把它拆成
   “技术”换行“研发”。旧定位器只把空白统一成一个空格，于是 Preview 变成“技术 研发”，无法
   匹配无空格的 quote，Resolution 被标为 `unavailable`。
3. 同一 PDF `file_ref` 同时属于“读取分配规则”和“生成匹配表”两个 Branch。一个定位失败被投影
   为两个 waiting Branch，因此前台出现两个近似重试入口；这不表示 PDF 文件有两处损坏。
4. Analyst 还把 4 月 21 日的“产品运营”和 4 月 23 日的“市场运营”写成 Finding，而用户任务的
   日期上界是 4 月 20 日；这些范围外候选不应阻塞当前成果。
5. Analyst 对文档已经明确给出的关键词优先级创建了人工 review，但引用中没有可验证的
   `contradiction`；这不是必须由用户决定的业务冲突。

## 根因边界

根因是服务端 Evidence Anchor 的版面归一化、任务范围校验和人工 Gate 准入不足，不是用户输入
错误，也不是已经下载的 CSV 日期列错误。定位只证明原文位置和成员关系；即使位置修复成功，仍
不能由此推断映射语义、计算或完整性正确。

## 对应实现位置

- Evidence Anchor 与任务范围：`services/api/app/application/harness_runtime.py`
- TC-01 确定性规则检查：`services/api/app/application/scenario_effects.py`
- 成果/审计前台投影：`apps/web/app/harness-workbench.tsx`
