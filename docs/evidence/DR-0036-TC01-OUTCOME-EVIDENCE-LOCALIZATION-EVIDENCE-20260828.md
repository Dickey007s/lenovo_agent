# DR-0036-TC01-OUTCOME-EVIDENCE-LOCALIZATION-EVIDENCE-20260828

## 状态

`Limited Verified`。当前证据证明固定 TC-01 输入上的版面换行定位、日期范围收敛、人工 Gate 准入、
PDF 规则检查和前台成果/审计分层，并包含一次真实 `deepseek-v4-pro` 成功运行；不证明任意 PDF、
任意日期表达式、真实 Provider 的重复稳定质量或目标用户理解提升。

## 负例与根因证据

| Evidence | 事实 | 边界 |
| --- | --- | --- |
| [`user-feedback-20260828-tc01-artifact-and-citation-confusion.png`](screenshots/user-feedback-20260828-tc01-artifact-and-citation-confusion.png) | 同页已有真实成果，却显示两个“缺引用/重试”分支 | Stakeholder 单次试用，不证明发生率 |
| [`user-feedback-20260828-tc01-generated-output.png`](screenshots/user-feedback-20260828-tc01-generated-output.png) | 下载 CSV 的日期列均落在用户指定区间 | 人工观察不替代全部规则 Verifier |
| [`RUNTIME-OBSERVATION-20260828-TC01-PDF-LAYOUT-ANCHOR`](../sources/RUNTIME-OBSERVATION-20260828-tc01-pdf-layout-anchor.md) | quote 的“技术研发”被 PDF Preview 拆为“技术”换行“研发”，同一 PDF 缺口投影到两个 Branch；还存在范围外 Finding 与无矛盾 review | 只绑定被审计 Run 和当前源码，不证明所有 Provider 输出 |

## 自动化账本

| 门 | 结果 | 能证明 | 不能证明 |
| --- | --- | --- | --- |
| Python 定向 Runtime/Effect | `78 passed in 24.50s` | 唯一断行 exact、重复断行仍 ambiguous、日期范围过滤、无矛盾 Gate 降级、TC-01 5/5 与完整三 Branch 终态 | 真实 Provider、浏览器理解 |
| TC-01 噪声纵切 | `test_tc01_verified_artifact_is_not_blocked_by_pdf_layout_or_scope_noise` 通过 | 同一次 Run 中 5/5 Artifact、范围外候选、错误 review 和 PDF 断行共同出现时最终 `completed`、无 Gap/DecisionRequest | 任意模型响应或任意任务 |
| Web TypeScript | `pnpm --dir apps/web lint` 通过 | 新状态投影和 E2E fixture 类型成立 | 浏览器布局和交互 |
| Playwright 定向 | `2 passed` | 成果区先于审计区、5/5、同源同问题 Gap 合并、同文件不同问题保持分开、旧误导文案消失、390 px 无页面溢出 | 目标用户一定理解或真实 API 状态 |
| 全量 Python | `116 passed, 3 skipped in 40.94s` | 当前整库 Python 回归通过 | 3 个 PostgreSQL 门因本机无 Docker/`TEST_DATABASE_DSN` 跳过 |
| 全量 Ruff | `uv run ruff check .` 通过 | 当前 Python 静态检查通过 | 运行时行为 |
| Web build | lint 通过；Next.js production build 通过 | TypeScript 与生产构建成立 | 浏览器中的业务理解 |
| 全量 Harness Playwright | `29 passed in 53.8s` | 当前桌面/窄屏与 Harness 交互回归通过；同文件但失败说明不同的 Gap 不会被错误合并 | 目标用户研究 |
| Markdown 相对链接 | 检查 18 个变更 Markdown，全部相对链接可解析 | 本次新增/更新文档没有失效相对链接 | 外部网页长期可用性 |
| PostgreSQL | 未执行真实门；本机没有 Docker、5432 服务或 `TEST_DATABASE_DSN` | 明确记录未覆盖项 | 不得据此声称本次验证了重启恢复或多实例 |

## 真实 Provider 纵切

2026-08-28 11:52（Asia/Shanghai）在本分支启动本地 API/Web，使用用户原始指令：

> 根据入职时间表和分配规则，生成 3 月 20 日至 4 月 20 日的入职资产匹配表。

公开 Snapshot 的审计摘要如下。这里只记录公共协议字段，不保存 Prompt、CoT、raw provider response
或密钥：

| 字段 | 结果 |
| --- | --- |
| Run | `harness:3ce6eb4ff129494d8e6e5edac3546a6a` |
| 终态 | `completed`，第 1/12 轮，2/30 次模型调用 |
| 来源 | CSV + PDF，共 2 份文件进入本轮 |
| 真实成果 | `入职资产匹配表.csv`，`verifier_status=passed`，5/5 检查通过，原始输入未修改 |
| 下载后复核 | 9 行；最早 3 月 23 日、最晚 4 月 20 日；范围外 0 行；`紧急联系人` 列已删除 |
| 效果回执 | `scenario_id=TC-01`，`status=passed` |
| Branch | 3/3 `completed`，0 Evidence Gap |
| 分析结果 | 3 条范围内 Finding，11 个服务端 Evidence Anchor，0 人工 review，0 开放 DecisionRequest |
| Named event | `decision_gate_suppressed`；模型本次未生成范围外 Finding，因此没有 `analysis_scope_filtered` |
| Durable State | `memory`；本机没有 PostgreSQL，本次 Run 不作为重启恢复证据 |

该纵切直接证明用户给出的 TC-01 在一次真实模型运行中不再出现“缺一份引用/建议重试/等待人工输入”，
但一次成功不能证明 Provider 重复运行稳定性，也不能把 5/5 扩展为任意办公任务正确率。

## 截图清单

| 文件 | 尺寸 / 字节 | SHA-256 | 能证明 |
| --- | --- | --- | --- |
| `dr-0036-tc01-outcome-first-desktop.png` | `791 x 1686` / `86788` | `134B6F9220A40BF83EB85FDF39448BDDA67840E7DDE3ED480F816982816EBDC9` | 桌面主区先显示真实成果、5/5、下载，再解释审计待补充 |
| `dr-0036-tc01-grouped-audit-desktop.png` | `761 x 254` / `27993` | `D1C69420D05F3B34DF2D638319EDA2D2CCB223F05370E08462F84878859E863B` | 两个同源内部步骤合并成一个“不影响成果”的审计项 |
| `dr-0036-tc01-outcome-first-mobile.png` | `350 x 2695` / `142355` | `7413DE2CA9FD81723294E317C88306CBD1D649557EED62D7A85A46E60D984FE8` | 390 px CSS 视口下成果、状态、分支和合并审计动作保持可见 |
| `dr-0036-tc01-live-run-completed.png` | `1440 x 1000` / `178218` | `EC3DF4A81CF84DB24B5658051EF631D7925272D5FBF024950680D7301A1AB63E` | 真实 Provider Run 已完成，三条范围内 Finding 可回开来源，旧误导文案与等待状态均不存在 |
| `dr-0036-tc01-live-run-artifact.png` | `601 x 325` / `22704` | `610F0604128B95C4387D4A8664406E6E443BE2F7B50203AD71ADC5AB932F71CC` | 同一真实 Run 的 `入职资产匹配表.csv`、5/5、下载和原始输入只读事实 |

## 当前事实边界

- 版面容错只在严格匹配没有候选时启用，至少 12 个归一化字符，并继续要求唯一位置；没有使用
  embedding、编辑距离或模型猜测。
- 日期过滤只处理用户指令中的明确中文月日闭区间，并以服务端已定位的 `observed` Anchor 为准。
- `decision_gate_suppressed` 只说明缺少 contradiction Anchor，不能证明 Finding 无需业务复核。
- 前台 Gap 合并只针对相同候选来源和失败说明，不同问题仍分开；它不改写 Snapshot、Branch、DecisionRequest 或恢复控制。
- TC-01 的 5/5 是固定适配器和固定公开输入的确定性效果证据，不是通用 Office Agent 正确率。
