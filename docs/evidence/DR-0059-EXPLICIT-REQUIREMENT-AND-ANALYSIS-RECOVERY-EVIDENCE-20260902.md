# DR-0059 显式要求与分析恢复 Evidence（2026-09-02）

## 结论

状态：`Limited Verified`。明确编号的复杂任务现在由服务端逐项记账；本轮执行、已知来源延后
和当前索引缺源不会再静默混在一起。Analyst 严格输出失败会留下分类事件并最多受控修复一次，
合法子集可保留；没有 ready Branch 时，前台不会再派发空 Worker 波次。

这只证明列出的源码、自动化、截图与两条真实 Provider 运行，不证明业务结论、通用需求解析、
目标用户理解、生产可靠性或分布式执行。

## 1. 实现范围

- `HarnessPlanCandidate.requirement_coverage[]` 对最多 12 个明确编号要求使用
  `planned/deferred/uncovered` 私有记账；服务端校验连续编号、唯一根单元与来源边界。
- 文件预算裁掉根单元时转为 `deferred`，并生成可恢复 waiting Branch；公共 Plan 只公开
  `units[]/deferred_requirements[]/uncovered_requirements[]`。
- Catalog 为 Planner 增加内部 `planner_search_hint`，公共 Workspace 仍不含该字段。
- Analyst 使用 180 秒独立超时、12,000 token 上限、严格 JSON/Schema 分类和一次受控修复。
- Worker 汇合保留延后 Branch 的候选；UI 分开本轮工作与后续项，并禁止空 Worker 波次按钮。
- Windows 启动器另以显式 `STATE_STORE_MODE=memory` 修正空环境变量未可靠传给后台进程的问题；
  该运行修复属于 `DR-0027` 的 2026-09-02 更正。

## 2. 真实 Provider 运行

服务健康事实：`status=ok`、模型 `deepseek-v4-pro`、`checkpoint=memory`、
`task_store=memory`。`.env` 密钥与连接串未记录。

### 页面可见 Run

- Run：`harness:e9e1f62564ae461bb525eca643fd5163`；Task：`task-976c08de42ab`；
- 输入：SCENARIO-046 的六项完整指令；
- 首轮结果：6 条 Branch，4 条本轮执行、2 条延后、0 条缺源；
- 路由：`fixed_workflow`，原因是独立分支超过每波最多 3 个只读 Worker 的准入上限；
- Analyst：首次候选因没有绑定到单一业务分支被拒绝，第二次采用；共 3 次模型调用；
- 当前：`waiting_input`，2 条完成、4 条可选择继续；原文件与外部动作均未发生。

### 三轮恢复 Run

- Run：`harness:aaa335744fbc4d2b820da3bfacfed5ed`；Task：`task-523f8c98a9ec`；
- 首轮同样形成 6 条 Branch，并把搜索可靠性、用户体验两项保留为延后 Branch；
- 第二轮真实继续搜索可靠性：第一次来源定位失败触发重试，第二次只采用 2 条可定位 Finding；
- 第三轮真实继续用户体验：同样发生一次重试并保留 2 条可定位 Finding；
- 最终：3 轮、8 次模型调用、14 份累计已核对来源、3 个逻辑 ArtifactVersion；
- 两份隔离 Run Workspace 文件通过确定性检查：`上线合规与风险报告.docx`、
  `上线功能风险逐项台账.csv`；FORTE 原件未修改；
- Run 以 `轮次预算已耗尽` 正常停止，未完成 Branch 保留；这不是六项业务工作全部完成。

机器可读的无密钥摘要见
[`complex-task-requirement-accounting-20260902.json`](manifests/complex-task-requirement-accounting-20260902.json)。

## 3. 浏览器验证

- 固定 Fixture：六项要求显示为 5 条本轮分支 + 1 项资料缺口，不虚构第六个可执行 Branch；
- 延后 Fixture：5 条本轮分支 + 1 项后续处理，“继续此项”绑定真实 Branch；
- 协作页没有 ready 波次时，“继续下一批/确认并开始协作”均不存在，并显示返回工作进展提示；
- 桌面与 390 px 的页面级横向溢出均为 0；
- 真实页面可见 Run：完整执行记录实测为 4 条本轮分支 + 2 项后续处理 + 0 项缺源。

截图：

- [`dr-0059-complex-task-progress-desktop.png`](screenshots/dr-0059-complex-task-progress-desktop.png)
- [`dr-0059-complex-task-record-mobile.png`](screenshots/dr-0059-complex-task-record-mobile.png)
- [`dr-0059-deferred-no-empty-wave-desktop.png`](screenshots/dr-0059-deferred-no-empty-wave-desktop.png)
- [`dr-0059-deferred-no-empty-wave-mobile.png`](screenshots/dr-0059-deferred-no-empty-wave-mobile.png)

## 4. 自动化

- 定向 Python：`93 passed in 14.69s`；
- 定向 Playwright：`2 passed in 13.9s`；
- 全量 Python：`429 passed, 23 skipped in 312.74s`；23 项仍是环境条件跳过，
  本轮没有把它们写成通过；
- 全量浏览器：直接使用当前在线 `http://localhost:3000` 的 live 配置，
  `82 passed (3.3m)`；默认配置第一次在开始测试前因同一项目已有 `next dev`
  实例而拒绝再启动，不是用例失败，也没有为跑门而关闭用户当前页面；
- Web lint：`tsc --noEmit` 通过；生产 build 成功生成 `/`、`/_not-found`、
  `/agent-capabilities`；
- 变更 Python Ruff 与 `git diff --check` 通过。

## 5. 限制

- 显式要求识别依赖受限编号语法，不是任意自然语言编译器；
- Provider 两次运行不是统计评测，不能比较模型质量、速度或成本；
- 位置核对不证明结论语义、穷举或计算正确；
- memory 状态库不会跨 API 重启恢复；
- 没有运行 PostgreSQL、多实例、远端 Worker、外部动作或目标用户研究；
- 本次没有修改 PPT。
