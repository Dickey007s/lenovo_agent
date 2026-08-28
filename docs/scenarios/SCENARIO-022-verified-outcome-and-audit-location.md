# SCENARIO-022：成果已验证时，把来源定位作为独立审计项

## 用户与触发

行政办公用户输入 TC-01 指令，希望直接得到 3 月 20 日至 4 月 20 日的入职资产匹配表。系统已
生成并通过确定性检查的 CSV，但 Analyst 说明引用的 PDF 原文可能因版面断行、范围外记录或错误
人工 Gate 产生噪声。

## 正常路径

1. 用户只输入任务，不选择 Scenario 或文件。
2. Planner 从整库选择入职时间表与分配规则，服务端校验计划。
3. 固定 TC-01 工具只读两份输入，在隔离 Run Workspace 生成 `入职资产匹配表.csv`。
4. Verifier 核对日期闭区间、排序、隐私列、完整表头、PDF 分类/优先级/多备注规则和分隔符，5/5
   才显示成果通过。
5. Analyst 的 PDF quote 即使在“技术/研发”之间发生版面换行，也由服务端唯一定位；4 月 21 日和
   4 月 23 日的候选被任务日期窗口过滤；没有 contradiction Anchor 的 review 不创建人工阻塞。
6. 三条任务 Branch 均完成，Run 可提交；用户看到成果、下载、引用回开与人工复核边界。

## 历史或残余定位缺口路径

1. 若旧 Snapshot 或其他合法 quote 仍留下 `waiting_input`，前台先显示已验证成果和检查数。
2. 页面写明“成果可用，审计待补充”，不再说源文件或日期有错。
3. 同一 PDF 影响的多个内部 Gap 合并为一个审计项；用户可点“补齐来源定位”，也可先下载成果。
4. 合并只发生在客户端展示。继续控制仍带一个真实 `branch_id`、expected version 和幂等键；已有
   Artifact、其他 Branch 和原始文件不覆盖。

## 异常路径

| 异常 | 前台反馈 | 后端事实与恢复 |
| --- | --- | --- |
| PDF 断行但唯一 | 不要求用户处理 | 版面归一化后 exact，并保留安全 Preview 行范围 |
| 断行片段出现多次 | 要求选择原文位置 | ambiguous candidates，不默认选择 |
| Finding 日期全在 4 月 20 日之后 | 轨迹显示已过滤范围外候选 | `analysis_scope_filtered`，不进入结果或 Gap |
| review 无矛盾 Anchor | 轨迹显示已取消无证据阻塞 | `decision_gate_suppressed`，不创建 DecisionRequest |
| PDF 固定规则缺失/漂移 | Artifact 检查失败 | TC-01 Verifier fail closed，不显示 5/5 |
| Catalog 完整性或 file_ref 越权 | 整轮安全停止 | 不用版面容错绕过 allowlist/integrity |

## 完成条件与边界

- 新 TC-01 回归最终 `completed`、Artifact 5/5、三 Branch 完成、无 Gap、无开放 DecisionRequest。
- 历史 waiting 投影中成果位于审计项之前，两个同源 Gap 只显示一个审计项，桌面与 390 px 无溢出。
- 本场景不证明模型 Finding 的语义正确、任意日期表达式、通用 PDF 坐标、任意 Office 写入或用户
  价值；Evidence Anchor 仍只证明安全 Preview 中的位置和来源成员关系。
