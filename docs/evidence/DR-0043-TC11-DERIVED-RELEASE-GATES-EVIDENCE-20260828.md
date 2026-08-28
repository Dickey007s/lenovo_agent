# DR-0043 TC-11 来源推导上线 Gate Evidence

## 当前结论

`Limited Verified`。严格来源合同、逐功能风险推导、来源行变异、正式 Gate 与辅助指标分离、DOCX/CSV 下载解析、失败不伪绿前台、真实 `deepseek-v4-pro` Run 和 PostgreSQL 顺序恢复均已验证。PR 编号与远端门在创建 PR 后补入本 Evidence。

## 历史基线为何不足

历史 `_release_readiness` 在固定 `pm-014` 样本上得出严重 4、主要 2、次要 2，但三个等级由功能名称集合硬编码，`check-release-risk` 又只验证同一批固定名称。因此样本答案碰巧正确，规则是否真的随 PRD 优先级、原因类型和异常环境变化并未被证明。历史 DOCX 也只有摘要段落，不能逐项复算。

## 来源推导与可证伪性

- PRD 解析 18 项功能、模块、优先级、负责人和正式上线规则；配置、功能测试、兼容测试各解析 13 项。
- 兼容测试两行表头折叠为八个唯一“浏览器+OS”环境；重复语义、未知状态和数值越界均失败。
- F17 异常环境从 4 改为 2 后由严重降为次要；F05 原因从功能缺陷改为界面缺陷后由主要降为次要；删除 F02 的问题记录后该功能移出风险。
- 这些变异直接修改来源行再运行同一 builder，不直接修改期望集合。

## 业务 Gate 与成果

- P0 提测：`5/7=71.4% < 100%`。
- P0 已提测功能可接受结论：`4/5=80.0% < 100%`。
- P1 已提测功能通过：`2/5=40.0% < 80%`。
- 严重问题：`4 > 0`，未清零。
- 四条正式 Gate 全部失败，结论为“不得上线”。`93.4%/86.4%/85.7%` 分级用例通过率和 `113/126=89.7%` 综合通过率只作辅助指标。
- `上线合规与风险报告.docx` 独立解析到 6 个表；`上线功能风险逐项台账.csv` 独立解析为 18 行、20 列，风险为严重 4、主要 2、次要 2、无风险 10。

## 真实 Provider 与 PostgreSQL

- Run：`harness:d1a3d9fca21d4e2299ac308bbaf73e1e`；健康状态为 `model=deepseek-v4-pro`、`checkpoint=postgres`、`task_store=postgres`。
- Planner `called=true/output_used=true/13321 ms`；Analyst `called=true/output_used=true/27304 ms`。
- Runtime 使用 1 轮、4 份已核对文件、2 次模型调用、43255 ms active elapsed。
- 确定性效果生成两份 passed Artifact，共享 9 个唯一检查；业务 Gate 独立为 failed。整个 Run 因额外模型分支保持 `waiting_input`，不能把 Artifact 通过冒充 Run `completed`。
- API 进程重启后，同一 Run、两份 Artifact、EffectReceipt、18 项业务台账和下载 SHA-256 保持一致。该门只证明 PostgreSQL 顺序 Runtime 已提交状态恢复，不证明多实例 CAS 或在途工具续跑。
- 机器 Evidence：[`tc11-live-derived-release-gates-20260828.json`](manifests/tc11-live-derived-release-gates-20260828.json)。

## 前台与负向门

- 首屏先显示“业务 Gate 4/4 未通过，不得上线”与四条公式原因；辅助指标和 18 项台账默认渐进披露。
- 两份成果仍显示“确定性检查通过”，并明确这只代表公式、来源和文件结构已复核。
- 强制 DOCX 结构检查失败时，两份 Artifact 与 EffectReceipt 变红，不出现 `9/9` 或可靠报告结论。
- 1440x1100 无 CSS 注入桌面截图和 390px 全页面截图分别为 [`tc11-release-gate-desktop.png`](screenshots/tc11-release-gate-desktop.png) 与 [`tc11-release-gate-mobile.png`](screenshots/tc11-release-gate-mobile.png)；尺寸与 SHA-256 见 [`tc11-ui-screenshots-20260828.json`](manifests/tc11-ui-screenshots-20260828.json)。
- Playwright 与截图是工程代理，只证明被测 DOM、字号、折叠、颜色状态和无页面级横向溢出，不证明真实用户理解改善。

## 本地完整门

- `$env:TEST_DATABASE_DSN='postgresql://postgres@127.0.0.1:55432/office_agent'; uv run pytest -q`：`153 passed in 262.60s`，真实 PostgreSQL 用例未跳过。
- `uv run ruff check .`：通过。
- `pnpm --dir apps/web lint`：通过。
- `pnpm --dir apps/web build`：通过，Next.js 生产构建完成。
- `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts`：`39 passed`，其中 TC-11 正向双状态和强制 Verifier 失败负向均通过。
- `git diff --check`：通过；仅有工作树行尾转换提示，无空白错误。

## 不能支持的结论

当前证据不证明任意发布资料都可自动审计、真实上线或配置写入已经发生、模型稳定质量、用户理解提升、多 Worker、通用 Tool Gateway、生产 Connector、多实例并发安全或外部动作。
