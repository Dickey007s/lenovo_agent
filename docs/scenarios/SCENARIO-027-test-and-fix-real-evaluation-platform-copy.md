# SCENARIO-027：在真实评测平台副本上先复现、再修复并复测

## 用户与触发

- 用户：需要审阅、复测并人工合并评测平台修复的软件工程师。
- 触发：输入“为评测平台补充单元测试，覆盖 Service、执行引擎和工具类；真实运行测试，修复失败，并给出覆盖率与修改文件。”
- 痛点：一个替身模块即使 105 项全绿，也不能回答真实 Service/Engine/Utils 是否被测试、缺陷是否先复现、下载后能否复跑。

## 主路径

1. Planner 在冻结整库索引中选择 dev-015 任务资料；服务端固定适配器在主事件循环内完成完整性读取，冻结 44 个源码文件与两份任务上下文，共 46 份 allowlisted bytes。
2. Runtime 先发布“正在复制并运行真实测试”事件，再把固定 builder 移到工作线程；该线程只能读取冻结视图，用户同时仍可查看资料、Run Snapshot 与 SSE。
3. Runtime 把 44 文件复制到隔离 Run Workspace，加入真实模块测试、manifest 与自测入口，不改 FORTE 原件。
4. 未修复副本先运行同一 117 项清单，三类缺陷对应五个目标测试出现红灯。
5. 服务端在副本内修改三个真实文件并生成 unified diff；随后编译和复跑，同一 117 个 collected ID 全部通过。
6. Verifier 检查五类测试、清单一致、三份变更文件各自覆盖率、Mock HTTP、完整包与输入只读。
7. 前台分别显示“评测平台真实修复包”和“TC-04 真实测试报告”；自测卡显示五类数量与真实文件，用户可展开 117 个公开测试 ID，下载后复跑并人工决定是否合并。

## 异常路径

- 未修复副本没有目标红灯：效果门失败，说明回归测试没有证明缺陷。
- 编译、测试、清单或逐文件覆盖率任一失败：两份 Artifact 都保持红灯，明确“不要合并”，保留失败包排查。
- 44 个源码来源被截断或原输入 digest 改变：完整性门失败，不得生成绿色 EffectReceipt。
- 测试尝试真实 endpoint、安装依赖、运行前端脚本或创建 PR：超出固定适配器权限，不能伪造成已执行。
- builder 或子进程失败：追加 `scenario_effect_failed`，不生成绿色 Artifact/EffectReceipt；此前 Snapshot 和事件保留。
- API 进程在 builder 运行中重启：线程和子进程不续跑；PostgreSQL 只按既有 checkpoint 规则恢复并暂停，等待用户从安全点继续。

## 完成条件

- 完整 44 文件真实副本可下载；PRD/technical-design 不计入源码文件数。
- 修复前五个目标失败/错误；修复后 117/117，五类分别 15/16/15/23/48。
- `test_suites[]`、公共 manifest、ZIP manifest 与实际 collected ID 集合一致。
- 三个变更文件逐文件 coverage.py 语句覆盖率均不低于 80%，aggregate 单列。
- 前台可见真实测试文件、名称、自测命令、失败信号、人工合并与禁止副作用；桌面/390px 无页面级横向溢出。
- builder 被受控阻塞时，health、Run GET 和 SSE 仍可在 1 秒门内响应；同一 Run 不重复调度，Artifact 只生成一次。

## 来源与边界

- 数据来源：FORTE 固定 revision `345c1ec1487139db9dd319787fa9405ba85d1869` 的 `dev-015/input/source-code`。
- 用户来源：`USER-FEEDBACK-20260828-TC04-REAL-PLATFORM-TESTS`。
- 这是固定 dev-015 纵切，不是任意代码沙箱、OS 级网络隔离、自动 PR、真实外部模型 endpoint 集成、多 Worker 或可跨进程续跑的 Tool Gateway。
