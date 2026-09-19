# Demo 3 动作影响账本证据

| 字段 | 内容 |
| --- | --- |
| Evidence ID | `DEMO3-ACTION-IMPACT-LEDGER-20260820` |
| Decision | [`DR-0012`](../decisions/DR-0012-demo3-action-impact-ledger.md) |
| Status | `Verified`（限定固定 Demo 3 工程范围） |
| Scope | 固定客户 A `reply_draft → email.send`、四类影响预演、治理回执与普通业务审计投影 |

## 1. 待验证问题

| 问题 | 成功标准 | 证据入口 |
| --- | --- | --- |
| 预演是否来自服务端事实 | `RunSnapshot.impact_preview` 含四类固定 `ImpactItem`，前端不补造 | 已验证：Python 与完整 E2E |
| 回执是否与预演分离 | 只有服务端治理/执行事实产生 `execution_receipt` | 已验证：成功回执 E2E 与后端回归 |
| 拒绝和失败是否保持成果 | Task Commit、ArtifactVersion、VerificationReport 不变 | 已验证：拒绝 E2E、失败后端回归 |
| 参数和版本是否绑定 | 绑定变化、篡改和 Permit 重放均不执行 | 已验证：后端回归；无独立篡改截图 |
| Simulator 边界是否诚实 | UI 明确模拟器结果，不说真实外部写入 | 已验证：成功回执截图与 E2E |
| 前台是否可理解 | 桌面/移动/键盘/读屏路径可完成，并隐藏内部标识 | 已验证布局/状态与触控断言；不证明用户理解 |
| 审计工作台是否隐藏内部事件 | 普通业务 UI 不渲染 raw `event_type/payload/trace`，技术值改为业务标签与服务端摘要；API/服务端审计仍保留原值 | 已验证：新增审计工作台 E2E 回归 |

## 2. 运行记录与提交

```text
Python tests: 151 passed, 1 skipped in 3.69s
Browser E2E: 37 passed (2.2m)
Ruff: passed
Governance: 4 passed in 0.02s
Frontend lint: passed
Next.js build: passed
Implementation commit: `9335470`
Documentation commit: `34aee71`
PR URL: https://github.com/Dickey007s/lenovo_agent/pull/18
```

## 3. 视觉证据与未覆盖路径

已保留以下工程证据图。截图只支持被测布局、状态文案、服务端事实投影、无横向溢出和触控尺寸断言，不证明目标用户理解、效率或交互新颖性：

| 文件 | 尺寸 | 大小 | SHA-256 | 支持的判断 |
| --- | --- | ---: | --- | --- |
| `screenshots/demo3-action-impact-preview-1440.png` | 1440×900 | 181478 bytes | `63839C2C5BD4706F37C7EE84EB6D1B4C97A9F092B4197C2DE27C8B48A440A8D3` | 提交前四类影响预演、确认前未执行 |
| `screenshots/demo3-action-impact-receipt-1440.png` | 1440×900 | 202859 bytes | `E0DEAC3F6E8C41825416D430975FC6C67C5E5E09399EA8C51E8DDB59167BB1D6` | Simulator 结果与执行回执、真实外部写入边界 |
| `screenshots/demo3-action-impact-denied-1440.png` | 1440×900 | 205343 bytes | `A8A9E77D2C2F04302AFF75F9F7CCCEE8C4534B70934F7EA473277AADFBBEC004` | 拒绝后未执行、成果保持不变 |
| `screenshots/demo3-action-impact-preview-mobile-390.png` | 390×3419 | 194868 bytes | `AA7E5FB4F982C70CFD7F35F96DEFCE53CBA783FBBC05A3879A737BD90A97A641` | 移动端预演、无横向溢出、触控尺寸 |

当前没有独立的参数篡改、Simulator 失败或未知结果前台截图；这些只由后端自动化证据覆盖。

## 4. 当前边界

本文件记录的是限定固定 Demo 3 工程纵切的运行结果，不是用户研究或生产能力证明。普通业务 UI 只显示业务标签与服务端摘要，不渲染 raw `event_type/payload/trace` 或 `email_simulator`、`email.send`、`PERMIT_ISSUED`、`Permit`；内部原值仅留在 API/服务端审计。真实邮箱、CRM、OA、日历、真实 Connector、生产身份、跨进程执行幂等/Permit replay、多实例/数据库恢复和用户理解仍未验证。实现提交、首次证据文档提交与 PR 已记录；不得把 DR-0007 的既有证据直接复用为 DR-0012 的完成证明。
