# DR-0037 TC-05 成果语义与审查可读性 Evidence

- 日期：2026-08-28
- 状态：`Limited Verified`（本地确定性门）；等待最终提交与 PR 门绑定
- Decision：[`DR-0037`](../decisions/DR-0037-tc05-artifact-semantics-and-review-readability.md)
- Scenario：[`SCENARIO-023`](../scenarios/SCENARIO-023-understand-finance-artifacts-and-review-evidence.md)
- 反馈来源：[`USER-FEEDBACK-20260828-TC05-ARTIFACT-MEANING-AND-REVIEW-READABILITY`](../sources/USER-FEEDBACK-20260828-tc05-artifact-meaning-and-review-readability.md)

## 负例

- [`user-feedback-20260828-tc05-artifact-meaning.png`](screenshots/user-feedback-20260828-tc05-artifact-meaning.png)：旧成果卡只给文件名、记录数、来源数和检查数，用户无法判断期间与相互关系。
- [`user-feedback-20260828-review-text-too-small.png`](screenshots/user-feedback-20260828-review-text-too-small.png)：问题审查页正文、事实卡、证据与表格过小。

## 实现事实

1. `GeneratedOfficeArtifact`、公开 Workspace Artifact 合同与 Runtime 持久记录新增
   `covered_period/statistic_basis/purpose/record_count`。
2. TC-05 两个 CSV 的 `source_file_refs` 缩小为 2026 工作簿，检查缩小为本期来源、逐行复算
   和排序；三期说明保留三期来源完整与僵尸账款复算。
3. 浏览器以 `title` 作为显示标题，保留旧下载文件名，并显示三个语义字段、记录数与“内容来源”。
4. 问题审查页事实卡、影响说明、证据摘录、文件元数据、正文与安全表格预览提高字号和行高。

## 本地验证

- `uv run pytest -q`：`116 passed, 3 skipped in 38.49s`。三个 skip 是需要显式
  `TEST_DATABASE_DSN` 的 PostgreSQL 集成门；本轮字段保持 Snapshot JSONB 兼容，仍等待
  PR 的真实 PostgreSQL workflow 结论。
- `uv run ruff check .`：通过。
- `pnpm --dir apps/web lint`：通过。
- `pnpm --dir apps/web build`：通过。
- `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts`：
  `30 passed in 58.5s`。
- TC-05 后端事实测试断言：未付/未收为 31/2 条真实数据行；两个 CSV 都只绑定 2026
  `file_ref` 与各自三项检查；三期说明绑定三个期间与两项跨期检查。
- 浏览器回归断言：三张成果卡的期间、口径、用途、内容来源和记录数；问题审查页 fact
  `14px`、impact `14px`、excerpt/callout `13px`、metadata `11px`、安全表格 `15px`；
  桌面和 390 px 页面级无横向溢出。

## 修复后截图

- [`dr-0037-tc05-artifact-semantics-desktop.png`](screenshots/dr-0037-tc05-artifact-semantics-desktop.png)，`441 x 1272`，52538 bytes，SHA-256 `3711947B6834929145035ECCACBA19E550A351BB5910A58C97177C0E1B9E1A8D`。
- [`dr-0037-tc05-artifact-semantics-mobile.png`](screenshots/dr-0037-tc05-artifact-semantics-mobile.png)，`334 x 1747` 的 390 px 视口成果区，92885 bytes，SHA-256 `AC82537DD16AE8059B5E07A8837576FE1FB3E87C04929F56A769E0556278B012`。
- [`dr-0037-review-readability-desktop.png`](screenshots/dr-0037-review-readability-desktop.png)，`1380 x 972`，142220 bytes，SHA-256 `16A128846C02685AFE5C6CEA12D6D5D1460ADC7428A8C44CF2D240D5421FEF79`。
- [`dr-0037-review-readability-mobile.png`](screenshots/dr-0037-review-readability-mobile.png)，`390 x 844`，46142 bytes，SHA-256 `669FC66706B380FCD3FD79D1F67565145259048DC03D7B77254CA355B6C5057A`。

## 待绑定

- 最终代码 SHA、PR、远端 PostgreSQL/check 状态和最新 master 本地服务状态。

## 证明边界

这些证据最多证明固定 FORTE `Finance-018` 路径的字段、数值、来源/检查归属与被测布局。
它们不证明生产财务政策、通用财务 Verifier、用户理解提升、任意文件语义正确或真实外部动作。
