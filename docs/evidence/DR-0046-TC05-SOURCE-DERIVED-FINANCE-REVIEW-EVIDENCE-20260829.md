# DR-0046 TC-05 来源推导财务候选 Evidence

## 当前结论

`Limited Verified`。严格三份来源合同、XLSX 原始字节解析、2026 明细、跨期候选启发式、独立输出 Verifier、来源变异、负向合同、三状态前台、真实 `deepseek-v4-pro` Run、三份下载独立解析与 PostgreSQL 进程重启复读均已通过。实现提交 [`6b5e778`](https://github.com/Dickey007s/lenovo_agent/commit/6b5e778d61677cffe32d8a1577870d1eff34bc92) 已进入 [PR #62](https://github.com/Dickey007s/lenovo_agent/pull/62)，远端 PostgreSQL 门已通过。

## 历史基线为何不足

历史 `_finance_reconciliation` 从固定安全预览生成列表，再用同一批列表检查输出；`check-finance-zombie` 把“候选为空”当成成功答案。它会在合法来源真的产生相同跨期余额时把业务发现误判成失败，也不能证明生成的 CSV/Markdown 字节与批准 XLSX 一致。这一历史 false green/false red 事实保留，不改写旧 Evidence 数值或截图。

## 来源推导与当前固定事实

- 来源合同只允许 `Finance-018` 三份 XLSX，绑定 `2025_h1 / 2025_h2 / 2026`、文件名、展示路径、allowlist、声明大小、file ref 和互异冻结字节。
- 原始 XLSX 解析固定单工作表和十列位置，保留期初/期末方向、业务金额、工作表、Excel 行和 `A:J` locator。同期间重复“科目+客商”不覆盖、不合并，直接失败。
- 当前动态结果：2026 未付 31 条、合计 `3,984,606.46`；未收 2 条、合计 `4,992,891.47`；三期启发式候选 0 条。
- 两个 CSV 只绑定 2026 来源；跨期说明绑定三个期间。三份 Artifact 各有 5 项检查，共 15 项不同检查。
- `finance_review_outcome` 明确 `review_required`、`original_inputs_modified=false`、`external_action=none`，并随 Artifact、EffectReceipt 和 Snapshot 持久化。

## 可证伪门

- 把测试副本中 2026 的绵阳长城余额由 170 万改为 150 万，候选动态变为 1 条，三份 Artifact 与 EffectReceipt 仍通过；候选三个位置为上半年 `Sheet1!A5:J5`、下半年 `Sheet1!A3:J3`、2026 `Sheet1!A3:J3`。
- 再改变任一期间解除候选后回到 0；只修改旧期间且未形成候选时两个 2026 CSV 字节保持不变。
- 新增、删除、改额和借转贷测试只改变来源影响范围；重复键、空表、未知方向、非法/非有限金额、公式、错误单元格、缺/多/错路径来源、同内容冒充和损坏 XLSX 均失败。
- 篡改 CSV 金额、方向、locator、删除或重复行，篡改 Markdown 候选数、候选文案或旧固定“无候选”，均使独立 Verifier 转红。

## 前台与截图

- 首屏说明“这是跨期风险候选，不是付款、核销、记账或坏账确认”，然后分开显示确定性检查、2026 明细/三期候选和最终处置。
- 0 候选显示“当前启发式未发现候选，仍需财务复核”；1 条候选显示琥珀色“需财务复核”，可展开三期金额、来源文件和 locator。
- [`tc05-ui-screenshots-20260829.json`](manifests/tc05-ui-screenshots-20260829.json) 记录 1440×1100 普通三栏和 390 px 单栏截图及 SHA。E2E fixture 由服务端 Scenario Effect 导出的 [`tc05-public-finance-review-outcome-20260829.json`](manifests/tc05-public-finance-review-outcome-20260829.json) 驱动，不在 React 测试中另写 31/2/0。
- 截图与自动化只证明被测投影、字号和几何，不证明财务用户理解、效率、信任或会计政策正确。

## 已通过工程门

- 来源/Verifier 单元：`21 passed`。
- 合同与 Runtime 定向：`2 passed`。
- 真实 PostgreSQL TC-05 顺序恢复：`1 passed`。
- TC-05 前台 canonical、positive candidate、Verifier failure：`3 passed`。
- 全量 Python（含真实 PostgreSQL）：`231 passed in 307.23s`。
- 全量 Playwright：首次发现两个历史文件预览断言仍引用退休的合成客商名；改为当前 FORTE 预览事实后 `48 passed`。
- Ruff、TypeScript lint 与 Next.js production build 通过。
- 远端 [`durable-agent-control-loop`](https://github.com/Dickey007s/lenovo_agent/actions/runs/33203777256/job/98959521498) 通过。

## 真实 Provider、下载与重启

- Run：`harness:55a7fdb7174d45e9a1dc11c6d390c1e7`；Owner header：`X-User-Id: tc05-live-20260829`；状态 `completed`，Snapshot `version=13`，1 轮。
- Planner：`called=true`、`output_used=true`、`elapsed_ms=11538`；Analyst：`called=true`、`output_used=true`、`elapsed_ms=23711`。模型回执与 15/15 确定性效果检查分开记录。
- 下载解析：`未付统计.csv` 31 行、合计 `3984606.46`；`未收统计.csv` 2 行、合计 `4992891.47`；`跨期核对说明.md` 的机器摘要为候选 0 条，且包含人工复核动作、退出条件与无会计动作边界。
- [`tc05-live-source-derived-finance-review-20260829.json`](manifests/tc05-live-source-derived-finance-review-20260829.json) 记录精确请求 header、模型回执、三份成果哈希、批准 XLSX 与 pinned manifest 一致、下载解析、API 进程重启前后哈希一致及 `deepseek-v4-pro + PostgreSQL` health。
- PostgreSQL 证明的是同一主机顺序 Runtime 的 Snapshot/Artifact/EffectReceipt/outcome 恢复；不证明多实例 CAS、在途工具跨进程续跑或生产高可用。

## 不能支持的结论

当前适配器不构成通用总账、应收应付、账龄或坏账系统，不证明候选就是僵尸账款，不执行付款、核销、记账或坏账确认，不处理主体、科目编码、币种、子项、期间内活动、Connector、多 Worker 或生产高可用；也没有财务用户研究。
