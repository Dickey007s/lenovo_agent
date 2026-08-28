# DR-0049 TC-13 来源推导客户画像 Evidence

## 当前结论

`Limited Verified`。固定 Sales-020 纵切已完成严格来源合同、动态清洗与画像裁决、两份成果独立复核、四层前台、真实 `deepseek-v4-pro` 运行和 PostgreSQL 顺序重启复读。该结论只覆盖公开样本与固定适配器，不代表真实客户研究、销售效果、策略批准或 CRM 执行。

## 历史基线为何不足

历史 `_customer_segmentation` 在生产实现中保存固定样本 ID、固定 8 条分类、固定排除名单、阈值、优先级与销售话术，再用同一批内存结果检查自己。固定样本可以显示 6 个绿灯，却不能证明来源阈值、优先级或样本变化会进入结果；来源没有批准的产品功能、话术和跟进顺序也被写成确定性结论。这份 false-green 事实只作为历史负例保留，旧 Evidence、Run 和截图未被改写。

## 来源推导与当前固定事实

- 来源合同只允许 `销售运营/客户画像调研问卷.csv` 与 `销售运营/客户分类画像与差异化销售策略生成规则.md`，并绑定逻辑 ID、filename、display path、allowlist、声明大小、file ref 与冻结字节。
- 当前规则 Markdown 动态解析为 15 条规则；CSV 动态得到 11 个原始行、10 个唯一业务载荷、1 个 `exact_non_id_payload` 重复、8 个分类、2 个无法归类，合计排除 3 个。
- 当前画像分布为技术型 3、安全型 3、敏捷型 2；canonical 没有多标签样本，因此 `priority_witness_count=0`，不能声称当前数据已经验证优先级。
- 每个原始行保留来源行、原始值、清洗值、转换记录、全部命中画像、优先级裁决、最终标签或排除原因、`duplicate_of` 与规则引用。
- 来源只批准报告栏目，没有批准具体话术、产品功能、行业结论或销售排序；成果只给 `draft_template/no_approved_strategy_source`，等待销售负责人补充和批准。
- `customer_segmentation_outcome.status=sales_review_required`，且 `original_inputs_modified=false`、`external_action=none`。

## 可证伪门

- 阈值 8 改为 9、缺失默认值变化、优先级重排、sample ID 重命名、行业/规模变化与合法新样本，均按来源动态改变对应样本、汇总和成果，不依赖固定 ID 集合。
- canonical 如实保持 0 个 priority witness；加入真实多标签样本后，来源优先级被实际应用并进入公共 outcome。
- `exact_non_id_payload` 只保留首条；重复 ID、重复/缺失/额外表头、CSV 注入、未知中文数字、负数、小数、越界、空/损坏/截断来源均 fail closed。
- 第四画像、未知规范、冲突或重复规则、未知报告强制项不能静默通过。
- 独立 Verifier 重读批准源字节，并分别解析最终 Markdown 与 CSV；金额之外的分数、标签、priority、duplicate、排除、计数、分布、locator、rule ref 或边界被篡改时至少一项检查转红。

## 前台与截图

- 首屏先说明这是公开样本的画像清洗与策略草案，不是真实客户研究、销售效果证明或 CRM 执行。
- 四层事实分别来自：Artifact/Effect 的确定性检查、outcome 的清洗事实与重复口径假设、`strategy_evidence_status` 的人工复核状态，以及 `external_action=none` 的无动作回执。
- 用户可展开逐样本查看来源行、原始到清洗值、全部命中画像、优先级裁决、最终标签/排除原因；逐规则 locator 也来自服务端公共事实。
- 桌面截图 [`tc13-customer-segmentation-desktop.png`](screenshots/tc13-customer-segmentation-desktop.png) 为 `1440 x 1100`、`155400` bytes、SHA-256 `aaf9901be6d06ba662cbaab76999d2585c5f19c367f0f391423b78856573a34a`；无 CSS 注入或内容改写，保留文件目录、中央成果区和右侧 Control Loop。
- 移动截图 [`tc13-customer-segmentation-mobile.png`](screenshots/tc13-customer-segmentation-mobile.png) 为 `390 x 844`、`57295` bytes、SHA-256 `99ae9e955e0e4778a8ae399507fe248099d40d75102a9da14b1dff3fc3792c83`；保持单栏且无页面级横向溢出。
- 捕获方式、尺寸与哈希记录在 [`tc13-customer-segmentation-screenshots-20260829.json`](manifests/tc13-customer-segmentation-screenshots-20260829.json)。截图与自动化不证明用户理解或业务价值。

## 真实 Run、下载与重启

- 历史负例 Run：`harness:3b2588fbe9424e3d9fa7dd7e77e7e69c`。确定性两份成果通过，但 Analyst 两次因引用越出其绑定计划单元而未采用，Run 最终失败；该事实保存在 [`tc13-live-run-initial-20260829.json`](manifests/tc13-live-run-initial-20260829.json)，没有被成果绿灯覆盖。
- 最终 Run：`harness:80a5e5c91a294ee687f28eed731570d3`；精确复读 Header 为 `X-User-Id: tc13-live-owner-20260829`，创建幂等键为 `scenario-effect-live-tc-13-d0686b4400324b9ab18e86d3b5c4812f`。PostgreSQL checkpoint/task store，终态 `completed`，1 轮、2 次模型调用。
- Planner：`called=true`、`output_used=true`、`elapsed_ms=9259`；Analyst：`called=true`、`output_used=true`、`elapsed_ms=16233`。模型回执与确定性 Artifact Effect 分开记录。
- Effect：2 份来源、2 份成果、8/8 唯一检查通过；公共 outcome 为 11/10/1/8/2/3、画像 3/3/2、priority witness 0，`external_action=none`。
- 下载 Markdown `6281` bytes，SHA-256 `d4a23db63598c9ae3bc91b4fe7ee575dbb2766a3c574aad94cfeed7834dc26f4`；CSV `2567` bytes，SHA-256 `b8f38b4c8cd700be5b12fec569a433a303ba140a71b83e5665b49b192d50c004`。独立解析确认逐原始行守恒、动态分布、duplicate、策略来源边界和无动作回执。
- API 进程重启后使用同一 Owner 复读 Run、Artifact、EffectReceipt、`customer_segmentation_outcome` 与下载哈希，均与重启前一致。该门只证明顺序 Snapshot 恢复，不证明多实例协调或在途模型/工具续跑。
- 脱敏证据：[`tc13-live-run-final-20260829.json`](manifests/tc13-live-run-final-20260829.json)、[`tc13-live-artifacts-20260829.json`](manifests/tc13-live-artifacts-20260829.json) 与 [`tc13-live-artifacts-after-restart-20260829.json`](manifests/tc13-live-artifacts-after-restart-20260829.json)。

## 工程门

- TC-13 来源/合同/Runtime 定向集合：`44 passed, 45 deselected`；真实 PostgreSQL TC-13 顺序门：`1 passed, 9 deselected`。
- TC-13 canonical、动态阈值、多标签 witness 与 Verifier failure 浏览器门：`4 passed`；最终截图回归另行通过。
- `uv run pytest -q tests/unit`：`296 passed in 258.40s`。
- 配置真实 PostgreSQL 的 `uv run pytest -q`：`306 passed in 324.88s`。
- `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts`：`54 passed`；其中 TC-13 canonical/threshold/witness/failure 四条全部通过。
- `uv run ruff check .`、`pnpm --dir apps/web lint`、`pnpm --dir apps/web build` 与 TC-13 公共 manifest `--check` 均通过。

## 不能支持的结论

当前只证明固定 Sales-020 的公开样本清洗与画像决策辅助适配器。它不是 CRM、自动营销、销售效果验证、真实客户研究或通用分群引擎；`exact_non_id_payload` 重复口径与策略内容仍需业务负责人批准。系统没有联系客户、写 CRM、创建商机或触发营销，也不含 Connector、多 Worker、多实例高可用或用户研究。
