# 整库自主研究与人工确认下一轮 Evidence

> 状态：`Limited Verified`。结论只适用于固定 FORTE 公开资料库、单 API 进程
> memory、只读 Agent Control Loop 和本文件列出的自动化/截图路径。

## 1. 主张范围

本 Evidence 只验证固定 FORTE 公开资料库、单 API 进程 memory 和只读边界内：用户无需预选文件即可启动 Agent Control Loop；Planner 面向完整安全索引自主选择每轮证据；服务端限制每轮文件预算；前台展示选择理由和可回开的引用；终态建议只有经用户确认才创建新的独立 Run。

不证明检索/分析语义正确、用户理解、生产持久化、多 Worker、真实 Tool Gateway、Connector 或外部动作。

## 2. 实现位置

| 事实 | 实现 |
| --- | --- |
| 完整资料库合同 | `packages/contracts/harness_models.py`、`services/api/app/application/harness_runtime.py` |
| Planner 全索引与每轮选证据 | `services/api/app/application/harness_runtime.py` |
| 文件管理器与结果建议 | `apps/web/app/harness-workbench.tsx`、`apps/web/app/styles.css` |
| 浏览器主路径 | `apps/web/e2e/harness-workbench.spec.ts` |
| 预算编译与合同回归 | `tests/unit/test_harness_runtime.py` |

## 3. 已观测 live 路径

最终截图绑定的一次真实 `deepseek-v4-pro` 浏览器运行在完整 96 文件索引上完成：

- Run：`harness:eca17a4d88d646c991b50d7a566543b3`
- 状态：`completed`
- 轮次：1
- 合同冻结：96 个稳定 `file_ref`
- 本轮 Agent 自主选择并核对：3 份文件
- 模型调用：2 次
- Planner：`deepseek-v4-pro`，12,078 ms，`output_used=true`
- Analyst：`deepseek-v4-pro`，21,568 ms，`output_used=true`
- Snapshot 观测时长：33,650 ms
- 结果：5 条发现、4 条下一步建议，`review_required=true`
- 终态：v11 / seq 10 `loop_committed`，`external_action=false`

这是一条运行时交互记录与截图证据，不是持久化可重放实验。它证明模型调用、整库合同、逐轮限权和建议确认 UI 在该次运行中发生，不证明文件选择、发现或建议在业务语义上正确。

## 4. 自动化

- Python 全量：`57 passed in 13.36s`
- Harness Runtime 聚焦：`20 passed in 0.80s`
- Ruff：`uv run ruff check .` 通过
- 前端 lint：TypeScript `tsc --noEmit` 通过
- 前端 build：Next.js 生产构建通过；compile 3.4s、TypeScript 3.4s、静态生成 584ms
- Harness 浏览器：`10 passed in 40.5s`
- Governance：`4 passed in 0.03s`
- 页面宽度：1440px 与 390px 均满足 `scrollWidth <= clientWidth`
- `git diff --check` 与本地 Markdown 链接检查通过

## 5. 截图

| 文件 | 状态 | 说明 |
| --- | --- | --- |
| `dr-0023-whole-workspace-file-manager-desktop.png` | 1440×900；`B562F0287B224D3A1B43FBF87FC9A74F44E3C6E9AD63E58C70DBFA84D3375374` | 桌面文件管理器、统一资料库与任务输入 |
| `dr-0023-whole-workspace-file-manager-mobile.png` | 374×575；`ED6A18FDF8DB3D101C5BD893045C325EA11C0FF63B2B3C551CD32CA976CB6CDD` | 390px CSS 视口中的移动文件管理器裁图 |
| `dr-0024-autonomous-next-task-proposals-desktop.png` | 599×452；`5E3E2B88BB32D6BDE8748D781C05FFC88F6C8748B2FF73094D65854BF9B861F5` | 真实模型结果中的四条建议与人工确认入口 |

## 6. 前台事实与边界

- 文件类型筛选和预览是浏览器交互，不改变 Run 合同。
- `Agent 本轮自主选择` 只显示服务端 `round.input_file_refs/selection_reason`。
- `确认并启动` 会创建新 Run；建议本身没有被写成服务端已接受状态，也没有逐项引用绑定。
- 模型超选时服务端裁剪到每轮预算，这只是安全/成本边界，不证明裁剪后的证据最优。
- 所有结果仍需人工复核，原文件不修改，外部动作不发生。

## 7. 绑定

- 实现提交：[`2b8e58c161df02d4f2c09bc2692db76d075f2ae2`](https://github.com/Dickey007s/lenovo_agent/commit/2b8e58c161df02d4f2c09bc2692db76d075f2ae2)
- Pull Request：[#29](https://github.com/Dickey007s/lenovo_agent/pull/29)，开放、未合并
- 首份文档提交：[`379b92d`](https://github.com/Dickey007s/lenovo_agent/commit/379b92d)
