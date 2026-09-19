# DR-0053 单步事项运行证据

设计日期：2026-09-18；验证跨至 2026-09-19。实现为 `1276bc0` 后的本地未提交修改，没有 PR。范围为单进程测试记录、固定策略、未调用模型、没有外部业务动作。

## 验证记录

新增 `tests/unit/test_office_actions.py` 初次运行 21 项通过，覆盖五种操作、准确撤销、来源摘录、缺信息、内容版本、强确认、受限规则、并发幂等、store 恢复、通用控制绕过、持久化失败、Owner 和输入字段检查。

| 检查 | 结果 | 范围 |
| --- | --- | --- |
| `uv run pytest -q` 首次全库 | 387 通过，13 跳过 | 当时含新增 21 项；跳过项要求真实 PostgreSQL |
| `uv run pytest -q` 补测后全库 | 389 通过，13 跳过 | 含 23 项事项测试；随后新增的研究幂等兼容测试由下面 72 项定向复查覆盖 |
| `uv run pytest tests/unit/test_office_actions.py tests/unit/test_harness_runtime.py -q` 最后定向复查 | 72 通过 | 含当前 24 项事项测试及 48 项既有 Runtime 测试；补测空来源不采用说明文字、store 重载幂等、旧研究请求摘要兼容 |
| `uv run ruff check .` | 通过 | 全库 |
| `pnpm --dir apps/web lint` | 通过 | TypeScript |
| `pnpm --dir apps/web build` | 通过 | Next.js 生产构建 |
| `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts e2e/office-actions.spec.ts` | 65 通过 | 62 项既有界面回归、3 项真实 API 事项测试；Edge，单 Worker |
| `pnpm --dir apps/web exec playwright test e2e/office-actions.spec.ts` 最后补测 | 4 通过 | 包含前三项；新增真实 allowlist 文件摘录、原始来源核对和打开安全预览，确认补充说明不冒充原文 |
| 本地 Markdown 链接检查 | 191 个链接可解析 | 本次修改的主要文档及提交版/开发版 |
| `git diff --check` | 通过 | 已跟踪修改，无空白错误 |

真实 API 浏览器流程覆盖五种事项、内容修改清空核对、暂缓后刷新、移动端完整联系人、取消和提交响应丢失后的原请求重放。浏览器截图为 [1440 px 桌面](screenshots/DR0053-desktop-review.png) 与 [390 px 手机](screenshots/DR0053-mobile-review.png)，已打开检查状态、信息层次及文字布局。手机 DOM 检查无横向溢出。桌面工作区为独立滚动区，确认按钮需向下滚动；截图并非整个滚动区域的拼接。

## 环境与负例

初始环境缺少 Python pypdf、uv 与前端依赖，已安装项目声明依赖。首次浏览器检查在创建页面之前失败，原因是缺少 Playwright ffmpeg-1011，不是业务断言；安装匹配版本后重新运行。保留此记录，不将环境失败改写成首轮通过。

首次联合浏览器回归为 56 通过、9 失败。9 个失败均在查找旧标签“发现与建议”时超时；基线 `1276bc0` 的页面已使用“成果与建议”。将旧测试的 10 处定位同步为现有标签，未删减业务断言，再运行全套。新事项的 3 个真实 API 流程在此轮全部通过。

## 证明范围

测试任务和发件回执保存在服务端 Snapshot；下载的是当前回执的文本。它们不是通过 Artifact Verifier 的文件，不是邮件、项目系统写入或审批受理。无数据库时重启丢失记录；InMemory store 在两个 Runtime 间复用的测试不等于真实 PostgreSQL 进程重启验证。

界面和截图用于核对状态与布局，不能证明用户理解、降低风险或提高效率。设计自查不等于设计方正式评审。
