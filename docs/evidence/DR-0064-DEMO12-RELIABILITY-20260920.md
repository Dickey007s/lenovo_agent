# DR-0064 Evidence：Demo1/2 可靠性

日期：2026-09-20。Limited Verified，仅覆盖下列本地工程门与真实 Provider 状态。

## 证据索引

- [决策](../decisions/DR-0064-demo12-reliability-and-bounded-narratives.md)
- [用户来源](../sources/USER-FEEDBACK-20260920-demo12-reliability.md)
- [场景](../scenarios/SCENARIO-051-demo12-reliable-office-results.md)
- [完整报告、复跑输入与开放问题](../reports/demo12-reliability-20260920/README.md)
- [后端 JUnit](../reports/demo12-reliability-20260920/backend-junit.xml)：452 passed / 23 skipped
- [PostgreSQL JUnit](../reports/demo12-reliability-20260920/postgres-junit.xml)：10 passed
- [浏览器 JUnit](../reports/demo12-reliability-20260920/browser-junit.xml)：104 passed
- [13 份下载文件独立复核](../reports/demo12-reliability-20260920/download-audit.json)
- [5 个实际 Run 重启保留](../reports/demo12-reliability-20260920/checkpoint-comparison.json)

## 修复与测试绑定

| 行为 | 源码 | 回归 |
| --- | --- | --- |
| 三类指标上下文、拒绝错误数字、匹配仍为草稿 | office_narrative_facts.py、narrative_reconciliation.py | test_office_narrative_facts.py，含历史负例、500 字后冲突、变更事实、96 条上限 |
| 实际模型输入及表格截断事实 | benchmark_workspace_catalog.py、model_input_coverage.py、harness_runtime.py | 文本/空 rows/60 行/metadata 用例，Playwright 范围与窄屏检查 |
| 等待时钟、派发预算、停止与调用事实 | harness_runtime.py、readonly_workers.py、workunit_ledger.py | test_demo12_worker_reliability.py，等待 1000 秒、过期不派发、越界调用回执、7 条发现 |
| 编号下游及初始 ready | HarnessRuntime Planner/Plan validator/admission | 5 个编号要求、3 根/2 依赖、确认前无 WorkUnit/Worker |
| 局部恢复与历史 | 既有 Task/Branch/Artifact Store | 全量 + 固定 Demo acceptance + 10 项 PostgreSQL + 真实 continuation checks |
| 前台分清文件与说明，计划不等于执行 | HarnessWorkbench / capabilities.css | Playwright、新增计划前投影、真实 1920/390 截图 |

完整工程回归不调用付费 Provider。真实 `live/` 使用 deepseek-v4-pro，公共回执不含 raw response、
密钥、Prompt、隐藏任务或内部路径；所有下载文件均来自现有 Artifact endpoint。
生产构建及 TypeScript 检查通过，改动 Python 文件 Ruff 通过；文档治理与合同补验 14 passed。

## 必须保留的失败

1. 首次新表格/PDF 覆盖代码把 PDF 的空 rows 当表格，旧 onboarding-173827 回执没有改写；修后 onboarding-180115 重新记录 1180 字符。
2. swarm-174813 暴露等待时间计费，旧 397.99 秒不作为性能数据；修后虚拟时钟跨两次 1000 秒等待只累计 4 秒工作。
3. single-175942 的 Planner 两次因根节点限定被拒。后续放行合法编号依赖，保留该 failed Run。
4. swarm-180730 的旧核对误判规范 100% 为实测；新增精确文本回归，不篡改旧 rejected 回执。
5. 部分请求被准入 fixed_workflow 而不是 Workers，均按实际路线记账，不计作蜂群成功。
6. 最终 swarm_readonly 只有 1/3 贡献采用，2 个待核对阻塞下游。两波完整真实汇总尚未通过。
7. single_readonly 虽按用户确认切回单主控，但仍生成固定上线文件，与只展示不生成文件的指令不符。
   这是固定 Adapter 输出意图门的开放问题，导致两路线不是等工作量对照；不报告速度/质量优势。
8. 首次针对 PostgreSQL 子集运行遇到 Windows Proactor/psycopg 事件循环不兼容；增加 integration
   session selector policy 后 10 项通过，不依赖其他测试文件的导入副作用。
9. 浏览器文案断言曾失败，旧 JUnit 单独保留；改用新文案并增加不证明解释正确的断言。
10. 首次计划投影用例的 Fixture 没有对应 Branch 的 Plan，导致新增断言失败。补齐已验证计划与分支的对应关系后，全量 104 项通过；旧子集回执保留于 browser-plan-mobile-junit.xml。

## 未证明

通用全文分析、语义蕴含、规则完整性、外部办公执行、通用 Worker、前序贡献完整消费、
多实例协调、蜂群优于基线、真实用户理解、Demo3 接入或整项多场景闭环均没有由本记录证明。
