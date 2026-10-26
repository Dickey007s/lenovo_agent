# DR-0069：只读数字核对与可回看资料范围

- 日期：2026-09-22；状态：Limited Verified，限定范围见 Evidence。
- 来源：USER-FEEDBACK-20260922-SOURCE-CHECKS、RUNTIME-20260922-SOURCE-CHECKS。
- 场景：[SCENARIO-056](../scenarios/SCENARIO-056-check-readonly-counts-before-handoff.md)。
- 证据：[本轮执行记录](../evidence/DR-0069-SOURCE-CHECKS-20260922.md)。

## 场景与来源

用户要求在原系统继续下一步，不增加新 Demo 或信息层。[用户来源](../sources/USER-FEEDBACK-20260922-source-checks.md)
和 DR-0068 的真实失败记录支持修复：已采用产品贡献把 7 项 P0 写成 6 项，把 13 条提测记录写成 14 条。
引用均可定位，但内容错误；交互日志输入只有 60/212 行。文献不是这些源表数值的依据。

## 决策

1. 从现有 TC-11 builder 提取无渲染的 `analyze_release_readiness`，复用原四文件严格合同及规则。
   固定 18 项 PRD / 13 条源表的合同未改为通用引擎；P0、已配置、已提测数量从解析记录推导。
   表头行不是业务记录；有条件通过是否计入 P0 可接受结论，继续由 PRD 规则决定。
2. 仅对当前批准且实际供应的完整产品四文件建立 `readonly_context`。缺少文件时不冒充完整核对；
   四文件齐全但截断、重复、结构不合法时明确拒绝。不得读取 Branch 范围外文件补全上下文。
3. 同一 Analyst 调用路径在 Loop 和 Worker 中检查受支持的明确当前计数。数字冲突不进入结果或
   下游，不自动用额外模型调用改答案。只保留调用/错误和既有局部恢复；通过此门仍是 model-only、
   review-required，不新造 passed Artifact/Effect 或确定性权威。原生成文件对账路径不被取代。
4. 比较仅涵盖有限中文表达的 PRD/P0/配置/已提测计数。未知措辞、未匹配数值及业务语义不算通过。
   原文 quotes 不作为模型断言；阈值、假设及“PRD 有 N 项 P0 功能”等子集不能冒充全部功能数。
5. Workspace 的 XLSX 首个可见工作表预览和模型行数上限统一为 240；模型文本上限与安全预览
   对齐为 30000 字符。120000 字节总正文上限、allowlist/size/hash/格式边界不变。超限仍明确失败。
   CSV 仍沿用其现有 120 行预览上限；这不是分页续读、多 sheet 覆盖或任意长文件完整读取。
6. 实际输入继续记入 `model_input_coverage`。此次 UX 可供 212/212 行，workflow/log 可供完整安全文本；
   能供给不等于理解。超过窗口的资料仍必须标 bounded，不能从“整库索引”推断读过整库正文。
7. 下游输出允许为各前序提供各自发现，不再一律挤进一条。引用必须来自 text/rows.values，而非
   total_rows 等元数据或前序摘要。角色首次反馈不再误称“上次定位失败”。真实重复位置仍等待人工，
   不自动选择、不以更少证据规避歧义，前序意见和旧 ArtifactVersion 不覆盖。

## 前台交互影响

保留原资料库与能力页、Loop/Swarm 和渐进披露。用户能在同一预览中回看新增范围，数字拒绝在原
执行记录中用中文提示，调用与采用继续分开。非终态目标 Worker 为 ambiguous、没有完整待决项且
没有可派发波次时，首屏不再说“无需核对文件”，而显示“引用位置尚未确定”，原主操作改为
“查看核对详情”，打开原协作回执。没有可提交的确认项就明确说没有，不生成假的候选选择器。
浏览回执在只读投影中仍可用，实际恢复和派发命令仍按原权限限制。
真实 DecisionRequest 仍优先；终态仍保留新 Run 继续的合同。无新仪表盘、权限或业务审批。
数字错误不是让用户改原件；后续沿用目标分支继续。模型内部计算上下文不能充当来源摘录。

## 后端事实映射

- `BenchmarkFilePreview.rows` 合同最大 240；保留真实 row_number、total_rows 和 truncated。
- `rounds[].model_input_coverage` 来自本次实际 payload，不从浏览器表格或文件名猜测。
- `analysis_numeric_rejected` / `failure_kind=source_numeric_conflict|source_numeric_contract` 与
  现有 called/output_used、Worker error、Branch/WorkUnit/Contribution 记录说明拒绝。
- 待办歧义提示只读目标 Branch 最新 `worker_runs[].outcome=ambiguous`，不从错误句子猜测；
  打开核对详情不发 POST，不增加模型调用，也不表示 Worker 人工确认流程已经闭合。
- `contract.output_policy=analysis_only` 仍在 Effect freeze/write 前阻止文件生成；只读数值辅助不
  调用 renderer、不生成 EffectReceipt。已有 Owner、版本、幂等、局部恢复及历史不可变合同不变。

## 验证与边界

复放两条真实错误、来源变异、完整资料供应、真实两波受控交接、单 Controller 拒绝与既有生成文件
回归分别验证。两次真实跨领域任务仍 waiting_input，不能宣称完整任务通过或蜂群收益得到证明。
没有新增 PostgreSQL 重启门、真实用户研究、任意公式/语义验证、全长检索或外部办公动作。
代码位于既有未提交工作树；未创建提交或 PR。具体门及失败均保留于 Evidence。
