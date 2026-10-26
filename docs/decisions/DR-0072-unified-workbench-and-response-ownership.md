# DR-0072：统一工作台入口与响应归属

- 日期：2026-10-07；状态：Limited Verified，仅统一入口、已测迟到响应隔离和兼容共存；最终组合浏览器门 149 项通过。
- Source：USER-FEEDBACK-20261007-UNIFIED-WORKBENCH。
- Scenario：[SCENARIO-059](../scenarios/SCENARIO-059-switch-workbench-without-stale-responses.md)。
- Evidence：[本轮记录](../evidence/DR-0072-INTEGRATION-20261007.md)。

## 场景与来源

用户要求继续项目，检查队友 xyzhu1225 的远程 Demo3，并研究 nanoMuse 的设计启发；随后授权按统一工作台方向整合。[来源](../sources/USER-FEEDBACK-20261007-unified-workbench.md)区分用户要求、源码观察和设计推论。
远程基线为 `fa974ae`，本地保留 DR-0064 至 DR-0069 优化。两个分支的历史工程测试不是当前组合版本的验证。

## 决策

1. 保留 `/` 办公资料库和 `/agent-capabilities` 的同任务能力视图，继续使用同一 HarnessWorkbench、Task/Run/Snapshot。Demo1/2/3 是展示视角，不新增产品或运行时选择器。
2. 六类固定单步事项与资料研究共享工作台入口和选中任务上下文，但不合并其业务权限。`office_action` 与分析 Run 仍采用各自既有服务端控制合同；事项不自动成为 Worker 候选决定。
3. 界面切换、新建草稿、历史重开或卸载后，旧请求完成不得覆盖新的上下文。响应只有仍属于发起时的前台上下文才可应用；取消等待不宣称取消服务端动作。
4. 仅查看入口、历史、详情不调用模型、不提交决定、不修改旧任务。未知提交仍需同请求/同幂等键查询或重试，不因前台切换生成第二个提交。
5. 不复制 nanoMuse 源码、品牌或跨设备权限，不新增真实发件、任务委派、通用 Risk Gate 或生产身份。

## 前台交互影响

先看到当前任务与下一步，Loop 记录、Swarm 协作与事项详情按需展开；已存在的原入口可继续使用。查看不等于执行，记录人工材料判断不等于业务审批。旧响应被忽略后当前任务、草稿和选择保持不变；当前请求失败则显示错误，不能伪造成功回执。
根页和能力页的空白任务显示“分析资料 / 办理事项”，选中事项时隐藏不适用的 Loop/成果入口。当前截图和桌面/窄屏核看状态按 Evidence 逐项报告。任何新状态必须来自下述权威字段，不从标题、动画或时间推断执行。

## 后端事实映射

沿用服务端 `run_id/task_id/run.version/event.sequence`、`office_action.status/revision/receipt/history`、Branch、WorkUnit、Contribution、ArtifactVersion 及顶层 DecisionRequest。客户端仅拥有当前视图/请求代次，不成为业务权威。
事项控制继续通过 `/action-controls`，Loop 决定继续通过 `/controls`，Worker 派发通过 `/workers`；Owner、预期版本和幂等检查不变。入口共用不新增 API，不将本地勾选解释为已批准。迟到响应隔离不得破坏合法的新 Run 切换和同 Run 单调更新。

## 验证与边界

当前组合后端最终单次 573 passed、26 个真实 PG 条件跳过，全库 Ruff 通过；最后代码修复后 `pnpm lint`（tsc --noEmit）及 `next build --webpack` 复跑通过。浏览器第一轮 144 passed/3 failed、修复后 147 passed；随后新增的初始化恢复与局部新事项竞态先 2 failed，修复 restoreLatestRun 的代次检查及 newItem 的 readRef 后单独 2 passed。最终完整单次组合门为 149 passed（约 7.1 分钟），不是历史数字加总。
已有延迟成功、错误、冲突刷新与导航测试支持限定响应归属，不等于所有网络竞态穷举。各回执和截图状态见 Evidence；失败记录保留，不借旧版本数量掩盖新缺陷。
本轮不承诺 Worker 人工恢复闭环、真实 Provider 成功率、PostgreSQL 新保证、生产权限或用户理解收益。截图、Fixture、真实 API 与模型运行分别标明。

## 下一纵切：Worker 人工恢复（Draft，未纳入本轮）

首版限定同 Run 非终态、只读、一个根 Worker 引用歧义及一个依赖工作包，保留其他兄弟成果。
需要保存结构化未采用候选和 Resolution，发布绑定 Branch/Worker/attempt 的原 DecisionRequest；使用原版本化 decision 合同和来源版本，不借用 compare_materials 或 Controller 循环恢复。
接受后仅授权目标 Worker 新 attempt，仍过来源、数字、依赖及贡献采用检查。仅依赖全部 adopted 且未执行的依赖阻塞 WorkUnit 可转 READY；不能只将 Branch 染绿。后续仍显式派发，旧贡献/成果不覆盖，刷新重启不自动调用。
验收必须走通等待、选择、目标重试、贡献采用、原 blocked 下游执行，并覆盖暂缓/取消、过期/篡改、预算、幂等及零调用查看。跨 Run 终态、来源变更、业务争议和外部动作另期处理。
