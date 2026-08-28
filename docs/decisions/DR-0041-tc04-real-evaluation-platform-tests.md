# DR-0041：TC-04 真实评测平台副本、双阶段测试与可见清单

- 状态：Accepted；真实 Provider、下载复测与 PostgreSQL 顺序门已验证，远端 PR 事实见 Evidence 收尾
- 日期：2026-08-28
- Source：`USER-FEEDBACK-20260828-TC04-REAL-PLATFORM-TESTS`
- Scenario：`SCENARIO-027`

## 决策

1. TC-04 仍从 Workspace-first 通用入口触发，不增加 Scenario 选择器。固定适配器只匹配原始用户指令和 dev-015 的冻结输入。
2. 服务端复制 `input/source-code` 的完整 44 文件到一次性 Run Workspace；PRD 与 technical-design 只是任务上下文，不冒充源码副本内容。所有 Artifact 和 EffectReceipt 绑定 44 个实际内容来源，公开合同上限从 24 提高到 96，覆盖当前整库 96 个输入而不截断。
3. 同一测试清单先运行未修复完整副本，再修改三个真实文件：模型删除只阻止 `RUNNING` 实验；追加导入从 `max_seq + 1` 开始；P99 小样本按最近秩且索引不超过 `n-1`。三处修改必须进入统一 diff。
4. 测试直接导入真实 Service、Engine 与 Utils。当前清单共 117 个具名 case：模型 Service 15、数据集 Service 16、实验 Service 15、执行引擎 23、工具与事务 48；声明、实际 collected、前台公开和 ZIP manifest 四个集合必须一致。
5. 三份变更源码分别以 coverage.py 语句覆盖率不低于 80% 为硬门；选定真实模块汇总覆盖率单独列示。不能用替身模块、AST 节点或较低 aggregate 门替代。
6. Artifact `self_test` 增加结构化 `test_suites[]`、`test_manifest_file` 和集合一致回执。前台首屏显示五类、真实测试文件、数量和总计 117；完整测试 ID 默认折叠、内部滚动，测试文字至少 11px，suite 标题和数量至少 12px。
7. ZIP 包含完整真实工程副本、真实测试、修复后源码、统一 diff、测试 manifest、修复前/后结果、中文报告和自测卡。自测只承诺在本仓库受控 `uv` 环境或已具备 requirements 的 Python 3.12 环境执行；本轮不联网安装依赖。
8. 固定 runner 清除凭据和代理，并在 Python 进程内阻断非 loopback `socket.connect`；HTTP 测试使用 `httpx.MockTransport`。它不是 OS 级断网、任意命令沙箱或完整外部集成测试。
9. Runtime 在 FastAPI 事件循环内完成 Catalog 完整性读取并冻结 46 份 allowlisted bytes（44 份源码加 PRD、technical-design），然后才用 `asyncio.to_thread` 执行固定 builder 与子进程测试。工作线程只能读取不可变冻结视图，不能重新读取现场 Catalog。
10. 长测试开始前写入有序 `deterministic_office_tool_started` 事实，完成后写 Artifact/Verifier 事实，失败则写 `scenario_effect_failed`。不伪造百分比；同一 Run/Capability 在进程内只能有一个在途 effect。

## 前后端事实

| 前台 | 服务端事实 | 不允许推断 |
| --- | --- | --- |
| 完整 44 文件隔离副本 | Artifact 44 个 `source_file_refs`、`check-eval-full-copy`、下载 ZIP 内容门 | PRD/设计稿属于源码副本；FORTE 原树已修改 |
| 修复前先红灯 | `baseline-test-results.json`、`check-eval-baseline-red` | 历史 105 项替身 false green 已经是有效 baseline |
| 三处真实修复 | `changes.patch/changes.json`、`check-eval-real-diff` | 任意缺陷均可自动修复 |
| 117 项真实测试 | `self_test.test_suites[]`、`test-manifest.json`、`test-results.json` | 只根据总数推断覆盖充分 |
| 五类测试清单 | suite 名称、`test_files/test_count/test_ids` | 浏览器自行猜测试名或暴露 benchmark rubric |
| 逐文件覆盖率 | `changes.json.changed_source_coverage_percent`、`check-eval-changed-source-coverage` | aggregate 覆盖率等于增量覆盖门 |
| 可以下载复跑 | Artifact bytes、两条自测命令、失败信号 | 用户已经执行命令或系统已创建 PR |
| 网络与副作用边界 | EffectReceipt、Mock HTTP 检查、`external_action=none` | OS 级断网、生产沙箱或真实 endpoint 集成 |
| 长测试仍可观察 | started 事件、冻结来源数、运行中 Run GET/SSE 与 health 响应 | builder 已完成、虚构百分比、多 Worker 或 durable Tool execution |
| 构建失败 | `scenario_effect_failed`，无 Artifact/EffectReceipt | 失败包已生成或旧结果被覆盖 |

## 拒绝的替代方案

- 保留历史 105 项 `contracts.py` 测试：拒绝。它不导入真实业务模块，覆盖率与真实工程无关。
- 只打包三份 patch：拒绝。用户无法下载完整工程复跑，也无法确认原业务上下文。
- 只把 44 个来源藏进 ZIP：拒绝。公共 Artifact/Receipt 必须无截断绑定服务端来源事实。
- 页面只显示五条摘要：拒绝。用户看不到实际测试名称，仍无法判断测了什么。
- 把客户端 read timeout 从 30 秒改为 180 秒：拒绝作为产品修复。它只能容忍总时长，不能解决主事件循环被同步 builder 占用时 Run、SSE 与 health 一起失去响应。

## 验证门

- 真实 Provider Run 记录 Planner/Analyst 的 `called/output_used/elapsed_ms`，且与确定性 Artifact 效果、Run 终态分开。
- 未修复完整副本必须出现覆盖三类缺陷的五个目标失败/错误；修复后实际 collected 117/117 通过。
- 下载 ZIP 后在独立目录以自测卡同等命令复跑；原 44 文件输入树前后字节不变。
- Unit 比较 Python builder、公共 manifest、Artifact `test_suites[]` 和实际 collected ID；E2E 使用同一真实 manifest，不得生成占位测试名。
- 桌面为可读的 2-3 列，390px 单列；computed font-size 和页面/内层 overflow 都进入回归。
- 受控阻塞探针运行期间，health、Run GET 和 SSE 均须在 1 秒门内返回；并发再次请求同一 Run 的 effect 不得第二次执行或重复生成 Artifact。
- PostgreSQL 重启只恢复已经提交的 Snapshot/Event/Artifact 元数据。线程内在途 builder/子进程不可跨进程续跑，按既有 checkpoint 规则暂停，不能称为 durable Tool Gateway。
