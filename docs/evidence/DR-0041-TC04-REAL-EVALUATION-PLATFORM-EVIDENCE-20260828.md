# DR-0041 TC-04 真实评测平台测试与修复 Evidence

## 当前结论

`Limited Verified`。本地确定性 builder、合同 round-trip、真实测试清单、桌面/390px 前台回归、真实 `deepseek-v4-pro` Run、下载后独立复测与 PostgreSQL 顺序重启均已通过。该 Run 的确定性 Artifact 效果通过，但 Analyst 最终输出未采用、整条 Run 为 `failed`；两层事实必须分开报告。远端 PR check 与合并 SHA 在本分支提交后补记。

## 第一层红灯：历史 105 项替身 false green

- Run：`harness:e80512fed92245d79fe24031954927a5`。
- 旧 EffectReceipt 写成 7/7 通过，ZIP 只有 `contracts.py`、动态 `tests/test_contracts.py`、runner、三份 patch 和回执；没有完整 44 文件真实工程。
- 旧 105 项是 35 组索引变换乘三个替身函数，覆盖率只统计 `contracts.py` 的 AST 节点。它不能支持 Service、Engine、Utils 被测试或真实源码增量覆盖率结论。

## 第二层红灯：完整未修复副本

- 新 builder 复制 dev-015 `source-code` 的 44 个文件，加入同一套真实模块测试后，先在未修复副本执行。
- 结果：112 passed，4 failed，1 error，共 5 个目标红灯；分别覆盖模型删除状态、数据集追加序号和 P99 小样本三类缺陷。
- 这层红灯与历史 false green 不同：前者证明新测试能抓住真实项目缺陷，后者证明旧验收对象错误。

## 本地修复后效果

- 三处 unified diff：`model_service.py`、`dataset_service.py`、`evaluation_engine.py`。
- 真实测试：117 collected、117 passed、0 failed、0 error；五类为 15/16/15/23/48。
- 变更源码覆盖率：`model_service.py 97.9%`、`dataset_service.py 97.8%`、`evaluation_engine.py 89.2%`，各自超过 80%；选定真实 Service/Engine/Utils aggregate 为 95.7%。
- 12 个唯一效果检查全部通过；两份 Artifact 共享同一清单，不写成 24 项独立检查。
- 公共清单：[`tc04-public-test-manifest-20260828.json`](manifests/tc04-public-test-manifest-20260828.json)。Unit 将该文件与 builder manifest、Artifact `test_suites[]` 和实际 collected ID 比较。

## 真实 Provider 与下载复测

- 最终 Run：`harness:c4bd926b13a44665aa49429d177305a9`；服务配置为 `deepseek-v4-pro`、`checkpoint=postgres`、`task_store=postgres`。
- Planner 真实调用 `16265 ms` 且输出采用；Analyst 最终回执真实调用 `41661 ms` 但输出未采用。预算共记录 4 次模型调用，受控修复仍未通过结构校验，因此 Run 最终为 `failed`，不是 `completed`。
- 确定性效果在 Analyst 终态前已经生成两份 Artifact 和一份 passed EffectReceipt。两份成果共享 12 项唯一检查；`评测平台真实修复包.zip` 为 `89915` bytes，下载 SHA-256、声明大小和实际 bytes 一致。
- 下载 ZIP 到独立临时目录后，编译退出码 0；自测实际收集 117、通过 117、失败 0、错误 0，声明 ID、归档结果与独立复跑 ID 集合一致。44 个源码文件中 41 个保持原字节，三份目标文件发生预期修改；修复前红灯数仍为 5，逐文件覆盖率仍为 `97.9% / 97.8% / 89.2%`。
- 机器可读 Evidence：[`tc04-live-final-20260828.json`](manifests/tc04-live-final-20260828.json)。其 `summary.passed=1` 只表示固定效果门通过；同一文件保留 `run_status=failed` 与 `model_output_adopted=false`，不能把 Artifact 绿色状态冒充整轮成功。

## 前台验证

- 自测卡首屏显示五类测试、真实测试文件、15/16/15/23/48 和总计 117；每类展开后显示真实 collected test ID，内部区域滚动。
- E2E fixture 直接读取同一公共 manifest，不生成占位测试名；代表性模型、数据集、实验、引擎和事务 case 均进入断言。
- 测试 ID 与辅助文字至少 11px，suite 标题与数量至少 12px；桌面使用三列、窄屏两列、390px 单列，computed font-size 和 overflow 均进入 Playwright。
- 自动化截图只能证明被测渲染，不能证明真实用户理解改善。
- 无 CSS 注入的实际桌面截图为 [`tc04-real-platform-tests-desktop.png`](screenshots/tc04-real-platform-tests-desktop.png)；成果聚焦图为 [`tc04-real-platform-tests-artifact-focus.png`](screenshots/tc04-real-platform-tests-artifact-focus.png)，只能作为局部放大；390px 路径为 [`tc04-real-platform-tests-mobile.png`](screenshots/tc04-real-platform-tests-mobile.png)。尺寸、捕获方式与 SHA-256 见 [`tc04-ui-screenshots-20260828.json`](manifests/tc04-ui-screenshots-20260828.json)。

## 长耗时效果的响应性负例与修复

真实 TC-04 builder 约需 60 秒。修复前它在 FastAPI 主事件循环中同步复制、运行 baseline、打补丁和复测；验证脚本对 Run GET 的单次读取会超时，health 与 SSE 也不能及时返回。把客户端 read timeout 放宽到 180 秒只证明脚本愿意等更久，不能证明产品仍可使用。

修复后，Runtime 先在事件循环线程完成 allowlist、大小和摘要校验，冻结 44 个 `source-code` 文件与 PRD/technical-design 共 46 份 bytes 及所需安全预览，再持久化 `deterministic_office_tool_started`。固定 builder 在 `asyncio.to_thread` 中只读取冻结 Catalog；同一 `(owner, run, capability)` 的第二次调度立即返回。完成后再写 Artifact/Verifier，异常则写 `scenario_effect_failed`，不生成绿色 Artifact/EffectReceipt，也不显示虚构百分比。

受控阻塞测试把 effect 工作线程停住，随后以 1 秒门分别读取 `/v1/health`、Run GET 和公开 SSE body；三者均返回 started 事实，Snapshot 尚无 Artifact。并发再次调用同一 effect 时 `execute_calls` 保持 1；释放后只生成 1 份测试 Artifact 和 1 份 EffectReceipt。该测试证明单进程事件循环响应性和进程内去重，不证明生产 SLA、多 Worker、跨主机队列或 durable tool execution。

真实 Run 总场景耗时 `165360 ms`，这不是单次 API 请求时长。验证脚本在全过程采样 286 次 Run GET，最大 `578 ms`；effect started 到 receipt 之间采样 61 次，Run GET 最大 `47 ms`、health 最大 `16 ms`；从 started sequence 前一位连接公开 SSE，`deterministic_office_tool_started` 首事件在计时精度内返回。客户端仍保留 180 秒总任务容忍，但响应性门独立要求单次 Run GET、health 和 SSE 不超过 5 秒。因此该证据证明本次真实长任务没有再阻塞 API 事件循环，而不是用 read timeout 掩盖问题。

## 安全边界

固定测试进程不继承 Provider 凭据或代理，在 Python 进程内允许 asyncio 所需 loopback 并阻断非 loopback `socket.connect`；HTTP 测试使用 `httpx.MockTransport`。这不是 OS 级断网、生产多租户沙箱或完整外部 HTTP 集成。本轮不安装依赖、不运行前端 package script、不调用真实模型 endpoint、不修改 FORTE 原件，也不自动创建 PR。

工作线程与其子进程仍是 API 进程内的在途执行，不能跨进程续跑。进程退出后，PostgreSQL 只恢复已提交的 Snapshot/Event/Artifact 元数据，丢弃未完成轮次并按既有 checkpoint 规则暂停；它不是持久工具租约、独立任务队列或多实例 CAS。

最终 Run 结束后实际停止并重启 API/Web；`/v1/health` 仍返回 PostgreSQL checkpoint/task store，使用同一 Owner 读取到 Snapshot v18、2 份 Artifact、1 份 EffectReceipt、19 条事件及 1 条 started 事实。这个门只证明已提交状态顺序恢复，不证明在途线程或子进程续跑。

## 验证门

- Python：配置真实 PostgreSQL 17.11 测试库后最终 `127 passed in 184.12s`，包含 TC-04 响应性、去重与 PostgreSQL 顺序恢复路径。
- Ruff、前端 lint、Next.js production build 均通过；Harness Playwright `35 passed in 1.4m`。
- 桌面、成果聚焦与 390px 截图、SHA-256 manifest 已保存；聚焦图不冒充实际桌面布局。
- 远端 PR/check/merge SHA 与合并后最新 master 健康状态待提交阶段补记。
