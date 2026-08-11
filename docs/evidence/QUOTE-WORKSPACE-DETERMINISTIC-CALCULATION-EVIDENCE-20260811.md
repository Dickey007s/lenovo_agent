# 报价工作台确定性核算证据

| 字段 | 内容 |
| --- | --- |
| Evidence ID | `QUOTE-WORKSPACE-DETERMINISTIC-CALCULATION-20260811` |
| Date | 2026-08-11 |
| Status | `Verified`（限定于固定演示报价、当前公式、revision/request epoch、Artifact/Action/Thread 绑定和被测浏览器恢复） |
| Decision | [`DR-0006`](../decisions/DR-0006-deterministic-quote-calculation.md) |
| Source | [`USER-FEEDBACK-20260811-QUOTE-CALCULATION-04`](../sources/USER-FEEDBACK-20260811-06-quote-calculation-grounding.md) |
| Scope | 固定演示报价的核算与来源回答、保存复核、版本/晚到结果恢复、受控动作/Thread 绑定与桌面前台输出 |

## 1. 被复现的问题

原始运行页面的三行报价为：

| 项目 | 数量 | 标准价 | 折后比例 | 折后小计 |
| --- | ---: | ---: | ---: | ---: |
| 企业办公 Agent 平台许可 | 100 | 1680 元 | 90% | 151200 元 |
| 实施与知识库集成 | 1 | 68000 元 | 100% | 68000 元 |
| 年度技术支持 | 1 | 36000 元 | 95% | 34200 元 |

逐行重算应得到：标准总价 `168000 + 68000 + 36000 = 272000` 元；折后总价 `151200 + 68000 + 34200 = 253400` 元；优惠金额 `18600` 元；综合折后比例 `253400 / 272000 = 93.16%`（约 `9.32` 折）；优惠率 `6.84%`。原 Agent 却回答 2000000 元、1770000 元和 88.5%，追问来源后又把 253400 元同时当作原价和折后价。

| 原始证据 | 尺寸 | 文件大小 | SHA-256 |
| --- | --- | ---: | --- |
| [`user-feedback-20260811-quote-wrong-calculation.png`](assets/user-feedback-20260811-quote-wrong-calculation.png) | `1820 x 780` | 207234 bytes | `FACD5442C27D6175A7B3BC14600DFEF78E88F0CCD66380DDDFD21D9B4A2DF071` |
| [`user-feedback-20260811-quote-wrong-source-followup.png`](assets/user-feedback-20260811-quote-wrong-source-followup.png) | `601 x 366` | 56367 bytes | `C5773369F568936295D1706890599146BF323CE407E7D52A4AB80052BD1B3E76` |

## 2. 验证问题与成功标准

| 验证问题 | 成功标准 | 自动化或运行入口 |
| --- | --- | --- |
| 基线计算是否精确 | 272000 / 253400 / 18600 / 93.16% / 9.32 折 / 6.84%，各行不低于 88% | `tests/unit/test_quote_calculator.py`、`apps/web/e2e/quote-calculator.spec.ts` |
| 旧小计和总计能否污染结果 | 即使提交错误 `subtotal/total`，仍按当前行重算并报告过期 | Python 单元测试与 Conversation 集成测试 |
| 前后端舍入是否一致 | `10.075` 元等半分边界按逐行 `ROUND_HALF_UP` 得到 10.08 元 | Python/TypeScript 对照用例 |
| 未保存编辑是否进入回答 | 修改数量或折后比例后，DOM 小计与总计即时变化，SSE 请求携带当前行值，Agent 回答同一结果 | `apps/web/e2e/quote-workspace.spec.ts` |
| 非法输入是否 fail closed | 任一行缺失、非数字、越界或超限时，所有聚合值显示“待核对”，回答不使用历史金额 | Python、TypeScript 与浏览器用例 |
| 客户端能否伪造服务端字段 | `quote_id/customer/currency/approved_floor/unit_price/sources/approval` 不被 `workspace_context` 覆盖 | Python 单元与 Conversation 集成测试 |
| 来源追问是否可追溯 | 回答说明当前屏幕、逐行公式、固定演示数据和未访问真实 CRM | Conversation 集成与浏览器用例 |
| 业务动作是否被误拦截 | “把当前总价写进邮件”等进入既有规划/治理路径，不走核算快捷回答 | 意图路由单元测试 |
| 保存后是否撤销基线批准含义 | 规范化保存后 `approval.status=needs_review` 且 `requires_recheck=true` | Conversation/路由集成与浏览器用例 |
| 同线程并发回答是否丢失 | 并发提交后保留两条用户消息和两条完成的 Assistant 消息 | Conversation 集成测试 |
| 旧 revision 是否覆盖新版本 | 保存返回 409；流式处理产生 `workspace.conflict`，不调用 Planner、不创建动作；最新 Artifact 保留 | Conversation 集成与浏览器用例 |
| 前台能否恢复草稿 | 保存 409 后不同字段可三方重应用；同字段双改列出冲突且不静默覆盖 | `apps/web/e2e/quote-workspace.spec.ts` |
| 等待 Agent 时的新编辑是否丢失 | request epoch/edit token 识别请求后的本地修改；不同字段自动保留并保持 dirty，同字段进入显式冲突 | `apps/web/e2e/quote-workspace.spec.ts` |
| Planner 能否伪造来源或动作 | 模型 `sources` 被服务端保留/默认来源覆盖；邮件 payload、目标范围、数据分类、状态变化和可逆性从当前 Artifact 重建，不匹配时 fail closed | Conversation 集成测试 |
| 未解析收件人/附件能否被自证解锁 | 纯文本姓名和不透明附件触发确定性 `DENIED`；Action 自身值、用户自报 evidence 和审批都不能解锁；已知邮箱/报价附件仍可执行 Simulator | Conversation 集成测试 |
| 规划期间目标 Artifact 改变是否安全 | 竞态产生 `workspace.conflict`，并发保存保留，不写旧计划、不产生 Run | Conversation 集成测试 |
| Run 与结果是否写入正确对话 | Conversation Run 保存真实 `thread_id`，graph checkpoint 用 `thread_id:run_id` 隔离；跨 Thread continuation 拒绝 | Conversation 集成测试 |
| 动作结果重试是否重复 | 暂时失败后可重新生成；首次完成后重放同一 `message.completed`，Thread 不追加重复结果 | Conversation 集成测试 |

## 3. 最终运行记录

以下结果针对实现提交 `2f9866f + fe865bd` 及其文档封口工作树：

| 检查 | 命令 | 最终结果 |
| --- | --- | --- |
| Python 全量 | `uv run pytest -q` | `105 passed, 1 skipped in 2.63s` |
| 报价/Conversation 聚焦 | `uv run pytest -q tests/unit/test_quote_calculator.py tests/integration/test_conversation_service.py` | `51 passed in 1.55s` |
| Python 静态检查 | `uv run ruff check .` | `Passed` |
| 前端 lint | `pnpm --dir apps/web lint` | `Passed` |
| Next.js 构建 | `pnpm --dir apps/web build` | `Passed` |
| Diff whitespace | `git diff --check` | `Passed` |
| 报价浏览器 E2E | `pnpm --dir apps/web exec playwright test e2e/quote-calculator.spec.ts e2e/quote-workspace.spec.ts` | `14 passed (23.5s)` |
| 完整浏览器 E2E | `pnpm --dir apps/web exec playwright test` | `26 passed (59.6s)` |
| 最新本地 live smoke | 重启 API `8013` / Web `3000` 后调用 health、创建 Thread、读取报价并发送真实 HTTP/SSE 核算问题 | `status=ok`，`model=deepseek-v4-pro`，checkpoint/task_store 均为 postgres；`Q-991-V3 revision=1`；观察 `assistant.status=calculating` 与 `message.completed` |

上述浏览器运行启动真实本地 FastAPI 与 Next.js、使用内存 Store 和 system Edge。它覆盖请求/响应/SSE/DOM 的纵向路径，但不覆盖 PostgreSQL、多 API 实例或真实 Connector。

2026-08-11 的附加 live smoke 在最新代码上通过真实 HTTP/SSE 询问“总折扣多少，你再算一下”。完成消息精确包含 `272,000 / 253,400 / 18,600 / 93.16% / 9.32 折 / 6.84%`，说明绑定当前屏幕且未使用历史金额，并排除 `2,000,000 / 1,770,000 / 88.5%`。health 中两个 postgres 标记只说明该次进程的配置与可用性；此单次 smoke 不是独立 Verified 判据，不证明 Workspace revision 数据库 CAS、跨重启 Conversation、生产持久化语义或真实 CRM/CPQ/ERP 连接。

## 4. 视觉证据

稳定实现截图路径为 [`quote-workspace-deterministic-calculation-1440.png`](screenshots/quote-workspace-deterministic-calculation-1440.png)。

| 截图 | 尺寸 | SHA-256 | 支持的判断 |
| --- | --- | --- | --- |
| `quote-workspace-deterministic-calculation-1440.png` | `1440 x 900`，164869 bytes | `3BDA0E2F2C5E34F0624349E26D977D37F5B5FA1D1169AD9D72EFDD41D14F69ED` | 四项汇总、最低折后比例、行级折后比例、确定性 Agent 回答与演示来源边界同时可见 |

本轮没有把报价专用窄屏截图列为证据。完整浏览器回归保留项目既有响应式用例，但不能据此扩展为报价工作台已完成专门移动端可用性验证。

## 5. 当前边界

- 这是固定客户 A 演示报价，不访问真实 CRM、CPQ、ERP 或审批系统。
- 公式只覆盖数量、标准价和单行折后比例，不含税费、汇率、阶梯价、最低购买量、跨行套餐依赖或尾差分摊。
- 前端 BigInt 投影改善未保存编辑反馈，但服务端保存结果和 Conversation 确定性回答才是跨界核算事实；前端不能据此宣布审批已通过。
- Conversation Thread/Message 和同线程锁仍在单个 API 进程内；没有跨进程顺序保证、SSE 游标恢复或后台队列。
- Workspace 锁、revision 比较和动作完成消息重放也只在单个 API 进程内；没有数据库原子 compare-and-swap、多实例锁、跨实例重放或并发写证明。
- 所有副作用工具结果来自 Simulator；恶意 Action/source 回归证明当前服务端信任边界，不证明真实邮件、CRM、CPQ 或 ERP 集成。
- 未解析收件人/附件使用固定字符串规则和 Mock Evidence 的保守 deny；这不是企业通讯录解析、真实附件扫描或可由用户补证恢复的完整产品流程。
- 自动化证明固定输入、协议和 UI 投影符合预设，不证明目标用户已经理解“折后比例”“优惠率”或审批边界。

## 6. 提交与 PR

- Implementation commits：`2f9866f + fe865bd`
- PR：[`#11`](https://github.com/Dickey007s/lenovo_agent/pull/11)
