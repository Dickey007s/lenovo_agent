# DR-0094 Evidence：当前入口与办公示例

日期：2026-10-25。工作树未提交；来源、场景与决定见 DR-0094。

## 失败诊断与入口

3000 前端实际请求 8000。原 8000 进程于 10 月 22 日启动，尚不接受 execution_policy；以 automatic_readonly 提交返回 422 extra_forbidden，未创建任务。
原两条财务运行分别为 harness:ba912bd0d84d4b2dba824ddf617ab3b7 和 harness:ae940a81c91a43a5b6f717d4710ace72。
它们在 Planner 返回结构校验阶段失败，没有 Analyst 回执。无法从公开记录进一步断定是 Provider、响应格式还是 Schema 的哪一项错误。
确认无运行中模型工作后，使用已有 restart-demo12-live-api.ps1 更新 8000。两条公开 Snapshot 保存于 outputs/demo-ready-20261025/server/before-restart-231949.json；它们没有恢复进新内存服务。8010 等其他会话未停止。

## 真实运行

所有本轮新任务均由 3000 的实际 UI 提交至 8000，调用现有 deepseek-v4-pro Provider，未 mock。
共 17 个独立 Run、46 次调用；选定的 7 个 Run 使用 17 次调用。包括迭代中不推荐展示的结果，不隐去失败质量样本。

| 推荐案例 | Run ID | 调用 | 定位依据 | 结果 |
| --- | --- | ---: | ---: | --- |
| Word 招聘要求 | harness:f79d41c048294e3bbe2dde6a727b37f8 | 2 | 2 | 两组结果覆盖 2 个必备条件、3 个加分项 |
| 按明确例外整理权限 | harness:bf8dce8731314da18d9e9d82ef3078c8 | 2 | 4 | 通用软件保留，研发专属软件不开通，仅分析 |
| 缺到账凭证 | harness:6a147917dade4cbe8c8aae050ab3cfdd | 2 | 2 | 保留账面金额，银行凭证单列缺源 |
| 未批准的权限变更 | harness:5dadae4b4f974393b73e5d31c7469618 | 2 | 6 | 已有清单保留，冲突交负责人决定 |
| 三主题办公摘要 | harness:b1c47a0e2a91400b977d2875c2f399fc | 5 | 4 | 3 个 Worker、3 份采用回执、4 条分析 |
| 商务岗位要求 | harness:0134d951403f45168537d85f20197c9c | 2 | 2 | 学历、沟通两项，保留优秀者可放宽 |
| 单笔账面摘录 | harness:34890821a5a0430f86c4f9413c4f3ed6 | 2 | 1 | 1500000 / 200000 / 贷方空白 / 1700000，借方 |

三主题目标未指定 Agent 数量。实际准入为三项独立工作；一轮结果检查选择 unchanged。单任务的 2 次调用为 Planner 与 Analyst，不是 2 个 Worker。
缺材料和待选择案例的 Run 状态是 completed，但 UI 分别标记待补资料/待你判断，不能讲成整个业务已完成，也不能声称模拟了 paused 状态。

## 结果质量检查

- 首批宽泛简报有“3 人”后列出 4 人、将账面结平推断为已核销等表述，不推荐展示。
- 第一版 Word 有 2 条必备条件，但把加分条件放进后续建议；不是完整交付。改为明确分组后复跑，两组均进入已采用结果。
- 中间复杂简报复测把加分条件仅留在 Worker 摘要、未进入有定位依据的 Finding。不作为完整案例。最终复杂简报明确只含必备条件，加分项由 Word 案例单独完整展示。
- 这些现象未证明通用模型缺陷已经修复。固定样例筛选与指令澄清不等于自动语义验证。

## 工具验证

- node scripts/audit-ready-examples.cjs：通过。检查 7 例当前版本、样例要求中的关键字段、调用采用状态、5 份安全来源可读。具体源码说明它不是通用语义校验。
- node --test scripts/demo-service-preflight.test.cjs：3/3。
- node scripts/demo-service-preflight.cjs http://localhost:8000：支持 automatic_readonly。仅 OpenAPI 预检，不启动任务。
- pnpm --dir apps/web exec tsc --noEmit：通过。
- Playwright harness-workbench.spec.ts，grep responsibility presets|todo overview survives：3/3，覆盖折叠六示例不执行和桌面/手机批次往返。
- 实跑工具检查 1680/390 宽度，无页面错误、无横向溢出；任务/成果往返不重新提交。
- scripts/inspect-blurt-feedback.cjs：当前 3000 只读走查 4 个 Demo2 任务，强制等待依据按钮并打开安全原文。0 POST、0 页面错误；实际请求来源为 8000。
- 人工查看完整桌面待办、原文高亮、缺材料两栏截图。未做用户研究、未重跑全套后端或全套浏览器回归。
- [演示顺序与结果网页](../reports/demo-ready-20261025/index.html)在 1440/390 宽度均无横向溢出，2 张内嵌截图正常加载。仓库没有 eslint 命令；其 lint 脚本实际为 tsc --noEmit，不另报 ESLint 通过。

原始证据：outputs/demo-ready-20261025 下 batch、refined、repeat、final-batch、demo1、word-repeat、inspection。
汇总：validated-examples.json；原文：source-previews.json；截图不覆盖过去报告。
服务当前为内存状态，停止后台会失去当前运行列表；JSON/截图存档不是数据库恢复。所有示例仅页面只读分析，没有新办公文件或外部动作。
