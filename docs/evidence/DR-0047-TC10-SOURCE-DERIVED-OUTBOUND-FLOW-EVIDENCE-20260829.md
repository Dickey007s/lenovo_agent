# DR-0047 TC-10 来源推导外呼流程 Evidence

## 当前结论

`Limited Verified`。固定 Operations-008 纵切已完成来源推导、动态规则与状态图、DOCX 独立复核、真实 `deepseek-v4-pro`、PostgreSQL 顺序重启复读、canonical/dynamic/failure 前台和完整工程门。实现提交 [`ccc6177`](https://github.com/Dickey007s/lenovo_agent/commit/ccc61775e2cb9d8640f7da23b2fb93b529c27a3e) 已进入 [PR #63](https://github.com/Dickey007s/lenovo_agent/pull/63)，首轮远端 PostgreSQL 门通过；最终合并 SHA 由交付回执记录。

## 历史基线为何不足

历史 `_compliant_outbound_flow` 保存固定节点、边、终态和 13 项检查，再用同一批常量检查自己。固定样本可以是绿灯，但不能证明来源规则变化会进入流程；旧流程还使用“录音先于身份”的顺序，并包含来源不存在的第三方升级路径。该 false-green 基线保留在 `DR-0039` 历史 Evidence，不修改其 Run、检查数字或截图。

## 来源推导与当前固定事实

- 来源合同只允许 `运营管理/专业性说明.md`，绑定逻辑 ID、filename、display path、allowlist、声明大小、file ref 与冻结字节。
- 当前来源动态解析为 15 组、34 条原子要求；每条保留行号、原文、参数、期望动作、覆盖状态和映射 ID。
- 状态图动态生成 31 个节点、36 条边、7 个守卫与 7 个终态，7/7 从唯一 START 可达。
- 当前批准顺序是身份确认在先，录音告知与来意在后，欠款引导最后；第三方与身份不明路径不可到达欠款节点。
- DOCX 有来源规则、节点、边、守卫、终态与完整性六类结构化表格；Verifier 重读来源并独立解析 DOCX。
- `outbound_flow_outcome` 明确 `approval_required`、`legal_opinion=false`、`original_inputs_modified=false`、`external_action=none`。

## 可证伪门

- 时间 22-08 改为 21-09、频次 3/1 改为 5/2、保存 2 年改为 3 年、重拨 1 小时改为 2 小时，参数动态变化且图 ID 不漂移。
- 一致修改身份/录音顺序会改变边顺序；只改一处触发来源冲突。
- 新增“高龄或重病必须转人工”增加 1 条规则、1 个守卫和 1 条边；未知规范停止，新增无路径终态显示 invalid。
- 来源错配、空/二进制/截断、非法时间/频次/年限、重复终态均 fail closed。
- DOCX 的 edge ID、终态、locator、顺序或压缩包损坏后，独立 Verifier 至少一项转红。

## 前台与截图

- 首屏分开四层事实：来源/DOCX/图结构、规则覆盖/可达终态、最终审批、真实动作。
- 规则可按组展开，显示来源行、原文和 mapped node/edge/guard/terminal ID；技术细节不由浏览器自行推断。
- E2E fixture 来自服务端导出的公共 manifest，不在浏览器另写当前 counts。
- 完整桌面截图 [`tc10-source-derived-outbound-desktop-1440x1100.png`](screenshots/tc10-source-derived-outbound-desktop-1440x1100.png) 为 `1440 x 1100`、`169931` bytes、SHA-256 `15dbc4fb2160c3187c4b3d45502bee48cc160bb0cf05e1404f287228fca2ceaa`；无 CSS 注入，保留运营管理目录、中央流程结论和右侧 Control Loop。
- 完整移动截图 [`tc10-source-derived-outbound-mobile-390x844.png`](screenshots/tc10-source-derived-outbound-mobile-390x844.png) 为 `390 x 844`、`55537` bytes、SHA-256 `920dfd83430b56ec683cb2f915445fd1eaac2bce81ecc26bbe67329ccd2afb23`；保持单栏且无页面级横向溢出。
- 捕获方式、尺寸和哈希统一记录在 [`tc10-ui-screenshots-20260829.json`](manifests/tc10-ui-screenshots-20260829.json)。截图与自动化不证明用户理解、合规正确或业务价值。

## 真实 Run、下载与重启

- Run：`harness:072fb8485f634fefb057716cc6a5065a`；Owner header：`X-User-Id: tc10-live-20260829`；PostgreSQL checkpoint/task store；终态 `completed`，第 1 轮、2 次模型调用。
- Planner：`called=true`、`output_used=true`、`elapsed_ms=7849`；Analyst：`called=true`、`output_used=true`、`elapsed_ms=17086`。模型回执与确定性 Artifact Effect 分开记录。
- Effect：1 份只读来源、1 份 DOCX、12/12 唯一检查通过；来源推导 15 组、34 条要求，图为 31 节点、36 边、7 守卫、7/7 可达终态；`external_action=none`。
- 下载 DOCX `10095` bytes，SHA-256 `40e3c191611a9eb89836f5a90aee1e0f80acfa9594e4b48fd1a29ab208341af0`。独立 ZIP/XML 解析确认 6 张表、规则/节点/边/守卫/终态行数、ID、locator、顺序与完整性均匹配。
- API 进程重启后使用同一 Owner 复读 Run、Artifact、EffectReceipt、`outbound_flow_outcome` 与下载哈希，均与重启前一致。该门只证明顺序 Snapshot 恢复，不证明在途模型/工具续跑或多实例并发安全。
- 脱敏证据：[`tc10-live-source-derived-outbound-flow-20260829.json`](manifests/tc10-live-source-derived-outbound-flow-20260829.json) 与 [`tc10-postgres-restart-source-derived-outbound-flow-20260829.json`](manifests/tc10-postgres-restart-source-derived-outbound-flow-20260829.json)。

## 工程门

- `uv run pytest -q tests/unit`：`257 passed`。
- 配置真实 PostgreSQL 的 `uv run pytest -q`：`266 passed in 314.69s`；TC-10 重启定向门：`1 passed, 8 deselected`。
- `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts`：`50 passed`；其中 TC-10 canonical/dynamic/failure 三条为 `3 passed`。
- `uv run ruff check .`、`pnpm --dir apps/web lint`、`pnpm --dir apps/web build` 与公共 fixture `--check` 均通过。
- 真实模型阶段未触发 deadline 或费用停止：仅 1 轮、Planner/Analyst 各一次。长时间验证来自本地全量工程门，不是持续 Provider 调用。

## 远端门

- [PR #63](https://github.com/Dickey007s/lenovo_agent/pull/63) 的 `durable-agent-control-loop` 在实现提交上通过，job [`98977859750`](https://github.com/Dickey007s/lenovo_agent/actions/runs/33209173403/job/98977859750)，耗时 55 秒。
- 合并后仍须从最新 `master` 以 PostgreSQL 重启服务，并用同一 Owner 复读本 Evidence 的 Run；该最终服务状态写入交付回执，不反向改写历史 manifest。

## 不能支持的结论

当前适配器不构成外呼系统、最新监管验证、正式法律意见或生产审批，不执行拨号、CRM/短信、禁呼写入或转人工，不含 Connector、多 Worker、生产 Permit、多实例高可用或用户研究。
