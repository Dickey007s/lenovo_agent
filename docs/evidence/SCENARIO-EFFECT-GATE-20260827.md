# 场景效果验证闭环 Evidence

## 1. 结论

`Limited Verified`。在固定 FORTE 公开输入和本机顺序 Runtime 内，TC-01、TC-02、TC-04、TC-05、TC-06、TC-07、TC-10、TC-11、TC-12、TC-13、TC-14、TC-15 已生成真实运行工作区文件并通过各自确定性 Verifier；TC-03、TC-08、TC-09 因外部 SQL/Web/Scheduler 未授权保持 `blocked_external_boundary`。这不是任意办公能力、生产沙箱、多 Worker 或真实外部动作证据。

## 2. 负例没有被删除

第一次真实 `deepseek-v4-pro` 六场景运行是 `0/6`：Planner/Analyst 已发生 18 次调用，但 Artifact/EffectReceipt 均为 0。根因是确定性工具只在 Analyst Finding 被采用后运行；结构或证据定位失败把办公成果一起挡住。证据：[`scenario-effect-gate-deepseek-live-baseline-red-20260827.json`](manifests/scenario-effect-gate-deepseek-live-baseline-red-20260827.json)。

修复把确定性工具移到“计划已校验、Analyst 解释之前”，并把模型质量、确定性效果、Run 终态拆成三条事实。中间 iteration 已能 `6/6` 生成成果，但仅 1 条模型输出采用，证据：[`scenario-effect-gate-deepseek-live-effect-only-iteration-20260827.json`](manifests/scenario-effect-gate-deepseek-live-effect-only-iteration-20260827.json)。随后简化 Analyst schema 并增加唯一安全 Unit 重绑，保留两个探针：[`prompt probe`](manifests/scenario-effect-gate-deepseek-live-prompt-probe-20260827.json)、[`scope rebind probe`](manifests/scenario-effect-gate-deepseek-live-scope-rebind-probe-20260827.json)。

## 3. 六个优先 live 场景

最终整组六场景证据：[`scenario-effect-gate-deepseek-live-20260827.json`](manifests/scenario-effect-gate-deepseek-live-20260827.json)。该轮 `6/6` 效果通过、6/6 Planner 与 Analyst 实际调用 `deepseek-v4-pro`、4/6 模型输出采用、1/6 Run 直接 completed；其余状态如实保留。两个后续探针使 TC-10 与 TC-15 的模型输出也在独立真实 Run 中被采用。跨所有保留尝试，六个场景均至少有一次“模型真实调用并采用 + Artifact 效果通过”的证据，但这不表示每次运行必然完成。

| 场景 | 最佳保留 Run | 模型采用 | Artifact / 检查 | Run 状态 | 说明 |
| --- | --- | --- | --- | --- | --- |
| TC-01 入职资产 | `harness:571d189b3e9e4bfd93dce86fd6ce0a29` | 是 | 1 / 5 | completed | CSV 可下载，隐私列、日期、排序、映射、分隔符通过 |
| TC-05 财务跨期 | `harness:7ef0fcf28e3e48b8a07845764a13b330` | 是 | 3 / 10 | completed | 两个 CSV 和说明，金额/跨期规则由代码复算 |
| TC-10 合规外呼 | `harness:725be696eecc47c4aae18d5b408b28da` | 是 | 1 / 13 | completed | DOCX 规则门通过，拨号/CRM/短信均未发生 |
| TC-13 客户画像 | `harness:066dd81ec5df48789ec4172139cb22d0` | 是 | 1 / 6 | completed | Markdown 分群守恒、规则映射通过，未联系客户 |
| TC-14 SRE 日志 | `harness:107b01c24de042eda5bfd445a43253f6` | 是 | 1 / 9 | waiting_input | 成果已通过；模型额外计划分支仍等待，命令未执行 |
| TC-15 交互排序 | `harness:4fdd0db5083d4cfca3b0f4d8f653083a` | 是 | 1 / 6 | waiting_input | CSV 效果通过；模型额外分支仍等待，未自动发布 |

`waiting_input` 不抹掉已验证 Artifact，也不冒充整个 Agent 解释已经完成。这正是本轮把效果和 Control Loop 状态分开的边界。

## 4. TC-01 至 TC-15 机器门

- 修复前固定 baseline：6 passed / 6 unsupported local / 3 blocked external，见 [`scenario-effect-gate-baseline-20260827.json`](manifests/scenario-effect-gate-baseline-20260827.json)。
- 修复后固定门：12 passed / 3 blocked external，见 [`scenario-effect-gate-post-fix-20260827.json`](manifests/scenario-effect-gate-post-fix-20260827.json)。
- 两次门均核对 FORTE input tree 前后 digest 相同；公开输入没有被修改。
- 每条记录独立指令、输入事实、预期 Artifact、Validator、前台效果、Snapshot/event/receipt、禁止副作用和实际结果。

## 5. PostgreSQL、前端和完整门

- 真实 PostgreSQL 顺序重启测试：`test_postgres_restart_preserves_verified_run_workspace_artifact`。它验证 Snapshot 中 Artifact/EffectReceipt、稳定运行工作区文件字节、Owner 下载和公开投影隐藏 digest 在 Runtime 重启后保持一致。本机直接门为 `3 passed`，完整 Python 门为 `115 passed`。API 进程重启后再次读取 TC-05 的 completed Snapshot，三份 Artifact 下载均为 `200` 且大小一致，见 [`scenario-effect-gate-api-postgres-restart-20260827.json`](manifests/scenario-effect-gate-api-postgres-restart-20260827.json)。这仍只证明同机顺序恢复。
- 浏览器 E2E 为 `27 passed`，覆盖真实成果卡、逐项检查、效果回执、下载、外部边界和 390 px 无页面级横向溢出。四张桌面/移动截图的尺寸、字节数和 SHA-256 登记在 [`scenario-effect-gate-screenshots-20260827.json`](manifests/scenario-effect-gate-screenshots-20260827.json)，截图不是用户研究。
- Ruff、Web lint 和 Next.js production build 均已通过。固定代码验证子进程只接收 OS 启动所需的环境变量 allowlist，明确不继承 API Key、Token、数据库 DSN、`PYTHONPATH` 或用户 shell hook；TC-02、TC-04、TC-12 的本地测试在该边界下重新通过。
- 远端审查载体为 [PR #44](https://github.com/Dickey007s/lenovo_agent/pull/44)。初始实现 head `a4fa2028b3072b0b50a9ccb34ae61363e1bfd63a` 的实际 `durable-agent-control-loop` check 已通过；本节更新后的最终 head 仍须等待同一远端检查通过才允许合并。合并 SHA 以 PR 和最终交付为准，在完成前不把分支状态写成已合并。

## 6. 能证明与不能证明

| Evidence | 能证明 | 不能证明 |
| --- | --- | --- |
| live Provider manifest | 固定配置下模型确实调用、是否采用、耗时、Run/Artifact/Receipt 状态 | 模型质量稳定性、SLA、用户价值 |
| deterministic verifier | 当前固定输入和检查代码下字段/数值/排序/规则/测试成立 | 任意任务正确、语义完整性 |
| Artifact 下载 | 运行工作区文件真实存在且 Owner 约束有效 | 原始 Office 文件被修改、外部系统已同步 |
| PostgreSQL restart | 顺序 Runtime 可恢复 Snapshot 元数据和稳定 Artifact 文件 | 独立 Artifact ledger、CAS、多实例、高可用 |
| E2E/截图 | 被测 DOM、下载和响应式布局成立 | 用户理解、效率、信任或业务成效 |

代码场景只运行固定、最小环境变量的本地测试命令。该阶段 TC-02 的 8 条 unittest 对应后来确认不足的 9 文件迷你包，历史记录保留但已由 DR-0040 取代；当前 TC-02 复制完整 algorithm-013 项目，声明/执行测试 ID 一致并在下载后独立复测。下载项目的默认策略按已规划工具确定性执行，虽然 `action_policy` 可替换，但尚未证明模型依据 Observation 在包内自主选动作；外层 Planner/Analyst 回执不得冒充包内策略。TC-04 的 105 条替身测试假绿已由 DR-0041 取代。TC-12 的历史 9/9 只证明修复后固定命令运行，DR-0042 改为复制 qa-003 全部 11 个输入，用同一 71 项 Vitest 经过三阶段红灯和最终绿灯，核对三个变更业务模块的逐文件 V8 coverage，并独立复跑下载 ZIP。测试环境不注入凭据或代理，本次固定路径未观察到网络调用；没有 OS 级 socket 隔离，也不是生产多租户沙箱或完整集成测试证明。

## 7. 2026-08-28 TC-01 后续加固

本文件保留 2026-08-27 的原始运行数值，不回写历史 Run。后续 Stakeholder 试用发现 TC-01 的
Artifact 已通过，但 PDF 版面断行造成 Analyst 引用 unavailable，并在前台重复成两个重试分支。
`DR-0036` 将 TC-01 的 `check-onboarding-mapping` 加固为同时核对 PDF 岗位关键词、优先级和多备注
规则，并新增唯一版面定位、日期范围收敛、人工 Gate 准入和成果优先浏览器回归。新增证据见
[`DR-0036-TC01-OUTCOME-EVIDENCE-LOCALIZATION-EVIDENCE-20260828`](DR-0036-TC01-OUTCOME-EVIDENCE-LOCALIZATION-EVIDENCE-20260828.md)。
