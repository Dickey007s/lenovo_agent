# DR-0039 TC-10 流程设计与执行边界 Evidence

## 结论

`Limited Verified`。固定 FORTE `Operations-008` 输入下，真实 `deepseek-v4-pro` Run 已生成并下载可打开 DOCX，独立解析 30 段正文后 13/13 Gate 通过；Artifact 和 EffectReceipt 均为 `external_action=none`。前台自动化覆盖显眼未执行边界、六类终态、人工复核原因、下载和 390 px 无溢出。它不是通用外呼引擎、生产合规审批或真实外部动作证据。

## 保留的修复前负例

- Run：`harness:e9741612bba44444abc15c82d6246dc8`
- Provider：Planner/Analyst 均真实调用且采用；2 次模型调用。
- 效果：DOCX 可打开、13/13 检查通过、Run `waiting_input`。
- 缺口：成果卡的未执行边界不够显眼；DOCX 缺少“回答什么、采用依据、复核责任”的首部结构。
- 原 DOCX SHA-256：`5ea7d59ad84082f9ea7fc438337f20b5c0d56861f0c534f14322277f011b6ba8`。

## 修复后真实运行

- 指令：`根据专业性说明生成信用卡 M1 逾期用户 AI 外呼催收流程图文档。`
- Run：`harness:d1bae6a41cc84004b8db2b1c5be8147b`
- 状态：`completed`，1 轮，2 次模型调用。
- Planner：`deepseek-v4-pro`，called/used=`true/true`，10465 ms。
- Analyst：`deepseek-v4-pro`，called/used=`true/true`，34239 ms。
- Artifact：`workspace-artifact-8f60487282df`，`2047` bytes，DOCX SHA-256 `083f99a496e9ef2bb3e27e4dcd4c8f73e41d0459a47ce39439f6d017bc4ad00e`。
- 下载解析：ZIP 结构有效，`word/document.xml` 可解析，30 段正文，独立 13/13 Gate 全通过。
- 外部动作：Artifact `external_action=none`；EffectReceipt `external_action=none`；禁止副作用为不拨号、不写 CRM、不发送短信。
- 脱敏机器记录：[`tc10-live-effect-20260828.json`](manifests/tc10-live-effect-20260828.json)。

最终源码再次真实运行，避免只用修复过程中的一次 Provider 结果作为结论：

- Run：`harness:bd76d2c8107441f6b4537d00c0242853`，状态 `completed`，Snapshot version `13`。
- 预算：1/12 轮，1/16 文件，2/30 次模型调用，active elapsed `42417 ms`。
- Planner：`deepseek-v4-pro`，called/used=`true/true`，`9846 ms`。
- Analyst：`deepseek-v4-pro`，called/used=`true/true`，`32230 ms`。
- Artifact：`workspace-artifact-b4be7265f477`，`2047` bytes，下载 SHA-256 `b1e54160d72de8b79096e3df73633d6bfbb3196d69f2b2c00950013162b1de22`。
- 独立下载门：HTTP 200、声明大小与下载大小一致、DOCX ZIP/XML 可解析、30 段、唯一 START、18/18 必需正文锚点命中、13/13 服务端规则检查通过。
- EffectReceipt：`passed`，`external_action=none`，明确不拨号、不写 CRM、不发送短信；FORTE 输入树 digest 前后保持不变。
- 可复现机器记录：[`tc10-live-effect-gate-20260828.json`](manifests/tc10-live-effect-gate-20260828.json)。

## 前台验证

- 成果卡显示“本次只生成流程设计 DOCX”，并明确流程节点不是执行回执。
- 成果类型、适用范围、采用依据、使用边界、六类终态和人工复核原因直接可见。
- 页面末尾使用相同服务端 Artifact 事实形成任务结语，不依赖 Run 必须有 `brief`。
- E2E 下载名为 `外呼流程-M1逾期用户AI外呼催收流程图.docx`，并检查 390 px 无页面级横向溢出。
- 成果区桌面投影：[`tc10-outbound-effect-desktop.png`](screenshots/tc10-outbound-effect-desktop.png)，`62797` bytes，SHA-256 `0624289D757FAD69D33ADF63005A4301C9710B4E2EC899162422F2C5C0BF34FC`。
- 任务结语桌面投影：[`tc10-outbound-conclusion-desktop.png`](screenshots/tc10-outbound-conclusion-desktop.png)，`16210` bytes，SHA-256 `FAA9D7CC1EAB960FAEAE413DD6C71EFDCF57C1D4649160A46006D706A2C77F12`。
- 成果区 390 px 投影：[`tc10-outbound-effect-mobile.png`](screenshots/tc10-outbound-effect-mobile.png)，`112300` bytes，SHA-256 `B4D9DC062F8282D39A608AC59C9566313B0DC74FD762E2ABA6506A43008C76D5`。
- 截图由确定性浏览器 fixture 投影相同公开 Snapshot 字段，只证明布局与文案回归；真实 Provider、DOCX 字节和服务端事实以两个 live manifest 为准，截图不证明真实用户理解。

## 本地完整门

- Python：`116 passed, 3 skipped`；3 条跳过均因本机没有 `TEST_DATABASE_DSN`，不能冒充 PostgreSQL 重启证据。
- Ruff：通过。
- Web TypeScript lint：通过。
- Next.js production build：通过。
- Playwright：`33 passed`，含 TC-10 下载、服务端字段、13/13、桌面/390 px 和无横向溢出。
- `scripts/run-live-scenario-effect-gate.py` 的 TC-10 门已升级为下载内容校验，不再只比较 Artifact 元数据和字节大小。

## PR 与 PostgreSQL 门

- 实现提交：[`3f2e3cc`](https://github.com/Dickey007s/lenovo_agent/commit/3f2e3cc)。
- PR：[#50](https://github.com/Dickey007s/lenovo_agent/pull/50)。
- 远端 `durable-agent-control-loop`：[`passed`](https://github.com/Dickey007s/lenovo_agent/actions/runs/33154676600/job/98794501757)，PostgreSQL 17.11 下 `3 passed in 4.72s`。
- 该远端门证明既有 PostgreSQL 顺序重启路径未因本次 Artifact 协议扩展回归；仍不证明多实例 CAS、高可用或在途模型调用续跑。

## 不能证明

- 固定适配器不能推广为通用状态机生成器、外呼执行引擎或生产 Tool Gateway。
- 13 项检查不证明规则仍符合最新法律、监管或企业制度；文档必须人工复核。
- 单次 Provider 成功不证明质量稳定性、SLA、成本优势或用户价值。
- 本机 health 为 `checkpoint=memory/task_store=memory`，不证明 PostgreSQL 重启恢复；远端 PR 门需单独记录。
