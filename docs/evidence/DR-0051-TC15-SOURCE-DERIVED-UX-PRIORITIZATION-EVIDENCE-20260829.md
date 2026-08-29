# DR-0051 TC-15 全量来源推导交互优先级 Evidence

## 当前结论

`Limited Verified`。固定 uiux-021 纵切已经完成严格来源合同、完整 212 行解析、来源推导规则、逐组 content-addressed rule refs、两份 CSV 独立复核、真实 `deepseek-v4-pro`、本地 PostgreSQL 进程重启、完整本地工程门、前台截图和 PR #67 远端 PostgreSQL 门。实现提交为 `22aa685`；远端门见 [durable-agent-control-loop](https://github.com/Dickey007s/lenovo_agent/actions/runs/33226861708/job/99032179492)。

## 历史基线为何不足

旧 `_ux_prioritization` 只读取 120 行 bounded Preview，却把严重度、频次矩阵、页面元素映射、规范顺序和具体建议写在生产代码中，再检查同一份内存结果。旧成果有 66 个组合、6 项检查全绿；完整 212 行实际形成 87 个组合，后 92 行新增 21 组，且 66 个重叠组合中有 22 个因完整分母或次数变化而改变频次档位。旧结果因此是被安全 Preview 截断掩盖的 false green，保留为历史负例，不被本次实现反向改写。

## 来源推导与当前固定事实

- 来源合同只允许 `用户体验/用户交互行为日志.xlsx`、`用户体验/交互行为痛点及优化规则.md`、`用户体验/页面级交互规范.docx`，绑定逻辑 ID、文件名、display path、allowlist、声明大小、file ref 与冻结字节。
- 服务端直接读取 XLSX 原始字节：1 个可见 Sheet、212 个数据行、9 个唯一表头。212/212 行都进入逐行台账；161 行有痛点、51 行无痛点仍进入全量分母，55 行是成功但有痛点。
- 当前有 192 个唯一完整载荷、16 个重复组、20 条额外重复事件。固定适配器不擅自去重，重复口径保持为数据 Owner 待决事实。
- 当前动态形成 87 个 page×operation×pain 组合，P0/P1/P2/P3/P4 为 25/40/14/6/2；这些只是当前来源观测，不是生产成功常量。
- 规则 Markdown 动态提供 9 类严重度、全量操作分母、3%/5% 频次档位、3×3 P0-P4 矩阵和处置说明。第 26 行的 3% 开闭区间冲突被显式保留；canonical 没有恰好 3% 的组合。
- 每个组合保留实际采用的严重度、频率、优先级规则 ID 与 locator。规则 ID 绑定语义槽位、来源摘录和参数的短 hash；来源阈值或矩阵变化时 ref 与结果一起变化。边界组保留两侧 frequency refs，不应用 priority ref。
- DOCX 动态解析 5 个页面、28 个规范元素和顺序。24 项操作映射明确标记 `controlled_adapter_assumption/review_required`，4 个规范元素当前未覆盖。
- 三份来源没有批准具体技术优化方案。成果统一保留 `suggestion_status=no_approved_solution_source`，只给来源处置、规范要求和待 UX 负责人补充/批准的模板。
- `ux_prioritization_outcome.status=prioritization_review_required`；原件不修改，`external_action=none`。`completed` 不表示方案获批、体验改善、生产 UI 修改、发布或实验发生。

## 已通过的可证伪门

- 合法追加 XLSX 行会动态改变全量分母、逐行计数和受影响聚合；第 120 行之后独有组合进入成果。
- XLSX 与规则源同步新增合法痛点后进入动态规则账本和组合，不被静默丢弃；只改 XLSX 的未知痛点进入显式 manual review。
- 高频阈值、严重度、优先级矩阵与 DOCX 元素顺序变异会改变相应投影；content-addressed rule refs 同步变化。
- 来源消除 3% 冲突后 Verifier 仍通过；恰好 3% 且冲突存在时保留两条频率规则引用并停止优先级裁决。
- 多/隐藏 Sheet、宏、外链、截断 OOXML、额外/缺失 DOCX 规范表、重复表头、非法数值、CSV 注入、来源缺/多/错路径与同内容冒充均 fail closed。
- 成果篡改覆盖分母、计数、规范要求、`suggestion_status`、优先级、locator，以及重复/删除行；独立 Verifier 必须转红。
- 公共前台 canonical 与阈值变体由同一来源模块导出，不在浏览器另写答案；逐组详情显示“为何这样分级”的 rule refs 和 locator。

## 真实 Run、下载与重启

- Run：`harness:731c429f82a941438b838fa8982699fd`；Owner header：`X-User-Id: tc15-live-owner-20260829`；start idempotency key：`scenario-effect-live-tc-15-bc9f95e9d5534b63b570b998c128ac38`。
- 服务：`deepseek-v4-pro`、`checkpoint=postgres`、`task_store=postgres`。Planner `called=true/output_used=true/12277 ms`；Analyst `called=true/output_used=true/29746 ms`。
- Run 为 `completed`，EffectReceipt 为 `passed`。两份 Artifact 共享 13 项检查，`13/13` 通过；确定性 outcome、模型回执和 Run 终态仍是不同事实。
- `交互规范优化方案.csv`：114020 bytes，SHA-256 `4ffde115be2447633799e8b2a7339dbf55b1f9ce945268afe229cd4176ea2f3e`。
- `交互行为逐行归因台账.csv`：74518 bytes，SHA-256 `c9c863777cc70a3cb92abef72643c041971444c2d0fce6920576387710c527fd`。
- 下载后重新读取三份批准来源并独立解析两份 CSV：212 行、87 组、25/40/14/6/2、16 个重复组、20 条额外重复事件和 1 组来源冲突均一致，13 项检查再次通过。FORTE input tree SHA-256 前后均为 `2c19e31a8e437f8ccb0ab811ba20a940f022a5bea69bcc750574d753f10a250d`。
- 停止并重新启动 API 后，以同一 Owner GET 同一 Run；Snapshot version 13、Run 状态、EffectReceipt、`ux_prioritization_outcome`、两份 Artifact 大小和 SHA 全部一致。这里只证明顺序 Runtime 恢复，不证明在途调用续跑、多实例 CAS 或 durable tool execution。
- 证据清单：[`tc15-live-source-derived-ux-prioritization-20260829.json`](manifests/tc15-live-source-derived-ux-prioritization-20260829.json)、[`tc15-live-source-derived-ux-prioritization-after-restart-20260829.json`](manifests/tc15-live-source-derived-ux-prioritization-after-restart-20260829.json)。

## 当前工程门

- TC-15 独立来源模块：`39 passed`。
- TC-15 来源/Scenario/Runtime/Contract 定向集合：`98 passed`。
- 真实本地 PostgreSQL TC-15 顺序恢复门：`1 passed, 11 deselected`。
- 不带数据库环境的全量 Python：`358 passed, 12 skipped in 263.05s`；跳过项均为显式要求 `TEST_DATABASE_DSN` 的 PostgreSQL 集成门。
- `$env:TEST_DATABASE_DSN=...; uv run pytest -q`：`370 passed in 357.59s`，12 项真实 PostgreSQL 集成门全部执行且没有跳过。
- `uv run ruff check .`、公共 manifest `--check`、`pnpm --dir apps/web lint` 与 `pnpm --dir apps/web build` 均通过。
- 全量浏览器：`60 passed`；其中 TC-15 canonical、动态阈值和 Verifier failure 为 `3 passed`。
- [PR #67](https://github.com/Dickey007s/lenovo_agent/pull/67) 的实现提交与最终文档提交两轮远端 `durable-agent-control-loop` 均通过，分别用时 `53s` 与 [`52s`](https://github.com/Dickey007s/lenovo_agent/actions/runs/33226953865/job/99032436192)。

## 前台证据

- 1440×1100 完整三栏截图：[`tc15-ux-prioritization-desktop.png`](screenshots/tc15-ux-prioritization-desktop.png)。中央首屏分开确定性验证、完整数据覆盖、P0-P4/规则来源和待审批方案；文件目录与右侧 Control Loop 均保留真实比例。
- 390×844 单栏截图：[`tc15-ux-prioritization-mobile.png`](screenshots/tc15-ux-prioritization-mobile.png)。长 locator、规则摘要和状态无页面级横向溢出。
- 尺寸、bytes、SHA 与捕获方式：[`tc15-ui-screenshots-20260829.json`](manifests/tc15-ui-screenshots-20260829.json)。截图是受控 E2E 投影，不是 UX 用户研究。

## 研究依据与用途边界

- [Microsoft Guidelines for Human-AI Interaction](https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/) 支持先说明系统能力/边界、显示上下文并允许纠正的交互取向。
- [Google HEART](https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/) 支持把行为信号映射到产品目标与指标，也反向说明单份离线日志频次不能证明体验改善。
- [W3C Status Messages](https://www.w3.org/WAI/WCAG21/Understanding/status-messages) 与 [W3C Target Size](https://www.w3.org/WAI/WCAG21/Understanding/target-size) 仅作为动态状态和移动端可操作性参考。
- 这些研究/官方来源不批准 uiux-021 的当前排序、映射或具体方案，也不能替代正式无障碍审计和真实用户研究。

## 不能支持的结论

当前只覆盖固定 uiux-021 的公开离线日志排序适配器。它不是线上遥测、用户研究、通用产品分析、设计效果验证、自动修改 UI、A/B 实验或生产发布系统；不证明当前 P0-P4 排序具有外部效度，也不含多 Worker、多实例协调、Connector 或外部动作。
