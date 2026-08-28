# DR-0044 TC-07 来源推导授权核查 Evidence

## 当前结论

`Limited Verified`。来源合同、21 条规则解析、六份 DOCX 包解析、126 条逐项台账、三状态前台、来源变异、负向合同、DOCX/CSV 下载解析、真实 `deepseek-v4-pro` Run、本地完整门、截图和 PostgreSQL 顺序恢复均已通过；实现提交 [`6b0612d`](https://github.com/Dickey007s/lenovo_agent/commit/6b0612d47a0a9b901eeb166a05ac524531a0056f) 与 [PR #59](https://github.com/Dickey007s/lenovo_agent/pull/59) 的首轮远端 PostgreSQL 门通过。

## 历史基线为何不足

历史 `_legal_delegation_review` 把每份文档的预期风险级别、风险项和数量写在适配器中，再检查输出是否等于同一批固定答案。修复一份来源文档后，历史结论仍不变化；空正文甚至可以保持绿色。历史 `check-legal-no-r05` 还因为“样本保留签署栏”强制排除 R05，却没有检查 DOCX 包内是否真的存在签字、盖章或数字签名。委托书 4 缺少律师执业证号的 M03 也被漏掉。

## 来源推导与当前固定事实

- 来源合同只允许固定 Legal-020 的一份规则 Markdown 与六份 DOCX；规则表解析为 21 条，六份文件形成 126 条唯一判断。
- 委托人和受托人身份字段按主体行解析。委托人无证件、受托人有证件仍触发 R01，统一社会信用代码也不会跨主体污染企业判断。
- 六份 DOCX 的签署占位为空，且包内无 media、drawing、pict、嵌入或数字签名；在没有获批草稿例外时，R05 对六份均触发。
- 委托书 4 无律师执业证号，M03 为触发；委托书 2、6 只有证号文本但无 Registry/Connector 回执，M03 为不可验证；字段存在不等于资质已核验。
- 当前动态结果为 6 份高风险、11 条关键资料不足、0/6 可审查签署证据，三条法务业务 Gate 均失败，结论为“不得据此签署，必须法务复核”。

## 可证伪门

- 修复测试副本中的一份委托书，补齐主体字段、转委托、责任条款和显式测试签署对象后，只改变该文件的风险、签署与汇总；其余五份保持不变。
- 规则等级或名称从来源表变化时，对应台账与动态汇总同步变化；重复、未知或歧义规则 fail closed。
- 缺一份、未知第七份、重复逻辑 ID、相同内容冒充两份、空正文、日期非法/倒置和字段冲突全部失败。
- 篡改 DOCX/CSV、缺行、重复行或塞入历史固定结论全部被来源重算 Verifier 拒绝。
- E2E canonical fixture 直接来自服务端公开 manifest；另以 repaired source facts 把 DOC-04 改为无已触发项、签署证据改为 1/6，前台动态显示 5/6 份高风险、1/6 签署证据且不残留旧 6/6、0/6 文案，证明 React 只投影服务端计数。

## 当前工程门

- 全量 Python：`176 passed in 268.26s`；包含 TC-07 来源变异、负向合同、Runtime、公开合同往返和 PostgreSQL 集成。定向真实 PostgreSQL TC-07 门为 `1 passed, 5 deselected`。
- 静态与 Web：`uv run ruff check .`、`pnpm --dir apps/web lint`、`pnpm --dir apps/web build` 全部通过；完整 Playwright `43 passed (1.8m)`，其中 TC-07 canonical、verifier failure、repaired dynamic variant 与 390 px 无溢出均通过。
- 真实 Provider：Run `harness:fa527bfb5b054401a6a16f77bf40f4b9`，Owner `X-User-Id: tc07-live-20260829`；Planner `13085 ms`、Analyst `15866 ms`，均 `called=true/output_used=true`。确定性成果通过，但额外模型 Branch 仍使 Run 保持 `waiting_input`，不改写成 `completed`。
- 下载解析：[`tc07-live-artifact-download-review-20260829.json`](manifests/tc07-live-artifact-download-review-20260829.json) 记录 DOCX `9` 张表、CSV `126` 行与 `126` 个唯一文档/规则组合、六条 R05、DOC-04 M03 和五条 M03 `unverifiable`；两份下载 SHA 与重启前 live manifest 一致。
- PostgreSQL 重启复读：服务重启后 health 为 `deepseek-v4-pro + postgres`，Snapshot version `13`、两份 Artifact、一份 EffectReceipt 与法务结论仍可按同一 Owner 读取。这只证明顺序 Runtime 恢复，不证明多实例 CAS 或在途工具续跑。
- 视觉证据：[`tc07-ui-screenshots-20260829.json`](manifests/tc07-ui-screenshots-20260829.json) 记录普通三栏桌面和 390 px 截图。桌面左栏展开法务规则与六份委托书；目录展开只是浏览器查看状态，不提交 `selected_file_refs`，也不改变 `whole_workspace` Run scope。
- PR、远端 `durable-agent-control-loop`：[PR #59](https://github.com/Dickey007s/lenovo_agent/pull/59) 的实现门 [run `33189927042` / job `98912504839`](https://github.com/Dickey007s/lenovo_agent/actions/runs/33189927042/job/98912504839) 为 `6 passed in 14.26s`；Evidence 回写门 [run `33190097561` / job `98913087056`](https://github.com/Dickey007s/lenovo_agent/actions/runs/33190097561/job/98913087056) 为 `6 passed in 14.82s`，两轮均使用真实 PostgreSQL 17.11。

## 2026-08-29 合并后容器可读性修正

- PR #59 的首张 1440 px 证据图虽然是无 CSS 注入的真实三栏页面，但中央法务结果区只有约 570 px，旧样式仍按 viewport 强制两列。卡片宽度约被减半，文件名拆成四到五行，展开规则的两列事实格也明显过窄。该负例只说明前台布局回归，不改变六份文件、126 条判断或任何后端法务事实。
- 修正后文档列表使用内容宽度驱动的 `auto-fit/minmax`；文档卡低于 340 px 目标时退成一列，展开事实低于 320 px 目标时同样退成一列。文件名禁止按中文字符任意拆词，但仍由 390 px 溢出门保护。
- E2E 在 1440×1100 的普通三栏状态读取真实 grid geometry：列表为一列，或每张卡至少 320 px；展开事实为一列，或每格至少 300 px；所有文件名不超过两行。390×844 必须单列，页面、法务结果区和文档列表的横向溢出均为 0。
- 本地收尾门为 TC-07 Playwright `3 passed`，另有带截图的 canonical `1 passed`；`pnpm --dir apps/web lint`、`pnpm --dir apps/web build`、`uv run ruff check .` 和 `git diff --check` 均通过。
- 新桌面图 SHA-256 为 `a87a6886ed3dc0d725c2417a9e77f3ffe912f849f3b67be01f0d0886e4124faa`，左栏展开法务规则与六份委托书，中央只展开 DOC-02，文件名为一行，规则事实为单列；移动图继续为 390 px 单列。截图与自动化不证明用户理解改善。
- 后续 [PR #60](https://github.com/Dickey007s/lenovo_agent/pull/60) 的远端 `durable-agent-control-loop` [run `33191280014` / job `98917081022`](https://github.com/Dickey007s/lenovo_agent/actions/runs/33191280014/job/98917081022) 使用 PostgreSQL 17.11，结果为 `6 passed in 14.16s`。它证明既有顺序持久化门没有因纯前台修正回归，不证明新的后端能力。

## 不能支持的结论

当前适配器不构成正式法律意见，不验证手写或数字签名真伪，不认定授权生效，不替代律师资格 Registry、法院许可或关联主体材料，不会签署、盖章、发送、修改原件或执行外部动作。自动化和截图不证明真实用户理解、决策质量或生产法律合规，也不证明通用合同审查、多 Worker、多实例并发安全或生产 Connector 已实现。
