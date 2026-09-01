# Agent 能力工作台 UI 走查 Evidence（2026-09-01）

- 状态：`Limited Verified`
- 被测提交：`bc52a73ddcee77ed0b146411f09777461fc31c83`
- 说明报告：[`AGENT-CAPABILITY-UI-TEST-WALKTHROUGH-20260901`](../reports/AGENT-CAPABILITY-UI-TEST-WALKTHROUGH-20260901.md)
- 截图目录：[`ui-test-walkthrough-20260901`](screenshots/ui-test-walkthrough-20260901/)

## 1. 真实本地运行

- health：`model=deepseek-v4-pro`、`checkpoint=memory`、`task_store=memory`；
- 输入：`根据入职时间表和分配规则，生成 3 月 20 日至 4 月 20 日的入职资产匹配表。`；
- Run：`harness:05c77975d7d149f5a8990a1cfdb7d5ed`；
- 结果：`completed`、1 轮、3 次模型调用、2 份来源、3/3 Branch 已核对、2 条 Finding、
  1 份 `入职资产匹配表.csv`；
- 确定性效果门：5/5 通过，原始输入未修改，外部动作未发生；
- 时序：成果文件于 `2026-09-01T13:18:57Z` 写入；分析第一次返回结构不合格并受控
  重试；结果与 Evidence Gate 于 `13:20:18Z` 完成。

该运行证明当前 TC-01 固定适配器、隔离成果文件、模型分析和 Evidence Gate 能串联运行；
不证明业务匹配结果已由目标用户确认，也不证明其他办公任务拥有同等确定性 Verifier。

## 2. 确定性浏览器门

在独立 worktree 运行：

```powershell
$env:CAPTURE_CAPABILITY_SCREENSHOTS='1'
pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts --grep "Agent capabilities route (keeps the two dimensions peer-level and navigable|shows fixed route boundary without fake workers|exposes a real review entry without making history actionable)"
```

结果：`3 passed (16.1s)`。

另单独复跑证据审查入口，结果 `1 passed (11.9s)`；临时扩展截图步骤后复跑 Adaptive
确认、第一波和第二波，最终结果 `1 passed (13.3s)`。扩展截图代码在运行后移除，测试文件
内容 hash 与分支 HEAD 一致，未提交临时代码。

首次扩展截图时，临时断言误写为界面必须包含字面量 `5/5 已完成`，实际界面用“5 个工作包
已完成、5 个已汇合、2 个成果版本”分别表达，因此该临时断言失败；修正为现有结构化状态
后通过。这是截图脚本的错误，不记作产品回归。

## 3. 截图清单

| 文件 | 类型 | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `tc01-live-input.png` | 真实本地 | 62530 | `C8D2AE36D9A34AF0BF7971B5C4B19B94B0A817A06A948660181697D0AC4401B7` |
| `tc01-live-running-viewport.png` | 真实本地 | 63252 | `1FDC9FC1F7402B90AB57C232A151F734141DD9EFE0A04DA7CC34A902F5304331` |
| `tc01-live-running-expanded.png` | 真实本地 | 101036 | `907F17DBC7E9011ED2223D31D6AE92DB5FF1F9C436780FD692F2A9DA2C8A7F4E` |
| `tc01-live-final-summary.png` | 真实本地 | 100136 | `D59291DBD49BD723E4C9CB43185A313187CC94857904914CBDB25C0740D8226F` |
| `tc01-live-final-artifact-and-evidence.png` | 真实本地 | 105509 | `D8E3A367508DA80B21BA371BAC4D606B975969D0866722FD2E91ED0F031525CA` |
| `tc01-live-final-branches-and-findings.png` | 真实本地 | 137677 | `E4CD9FC0174157ED7CD0BD01597E52B539AAF2E9DD7406C4CBF8AC19E1078AC2` |
| `case2-fixed-progress.png` | Fixture | 59759 | `BB56D2F46947BC9415CD97FD2298C2D8C07F1B3D2BC929E0400C8CF87120AF07` |
| `case2-fixed-collaboration.png` | Fixture | 83882 | `ED2712BE5982BD76B45E36E33C0205DED0372E195BF6872DAACC061B4FC58F03` |
| `case3-adaptive-before-confirm.png` | Fixture | 88418 | `FA6482411EA64416130458BA446A9E48B4FD03280028A4707338968BA0D37B3E` |
| `case3-adaptive-wave1.png` | Fixture | 87049 | `407D1316430A5332F99D9C9DBC1D602D26485639FD3AED880F8C1F5D4276D881` |
| `case3-adaptive-wave2.png` | Fixture | 86408 | `EFD987D2FB9E6ACF8AB48E0FC2F294CAD768868F5DC0FE8F5B448369F76DC7D2` |
| `case4-evidence-review.png` | Fixture | 112871 | `90053788D703FB74B113E23050CB9F8735DB67441D5E45A9C08448524FC9C424` |

## 4. 本轮发现

1. Adaptive 第二波已完成时仍显示“继续下一批”，会制造不存在的后续动作；
2. TC-01 成果先写入、分析仍在运行时，摘要显示“状态待确认 / 当前没有待处理事项”，没有
   准确表达“后台核对中、暂无需用户动作”；
3. Adaptive 用户确认前 Worker 调用为 0，但阶段文案写“正在处理”，没有严格区分计划拆解
   与真实执行；
4. 固定流程未伪造 Worker/Contribution，成果文件、模型说明和证据门的分层保持成立；
5. 证据审查页能把事实、影响、用户动作、保留内容、安全 Preview 和来源回开同时表达。

前三项已发送给开发任务 `019fe97b-43a7-7760-a481-3498c2aeb678`，要求由独立开发提交
修正并补浏览器门。

## 5. 边界

- memory 状态库不支持本轮进程重启恢复验证；
- Fixture 不冒充真实 Provider、多 Worker 或用户研究；
- 自动化通过不能证明界面降低认知负担、提高信任或提高效率；
- 本轮未修改 FORTE Manifest、96 份公开输入、历史 Evidence 数值或既有截图。
