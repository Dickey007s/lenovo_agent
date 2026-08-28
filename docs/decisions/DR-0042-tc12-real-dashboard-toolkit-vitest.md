# DR-0042：TC-12 真实看板工具库、分阶段红灯与可复跑 Vitest

- 状态：Accepted；本地 builder、真实 Vitest、公共清单、前台回归与 PostgreSQL 顺序恢复已验证，真实 Provider 与远端 PR 事实见 Evidence 收尾
- 日期：2026-08-28
- Source：`USER-FEEDBACK-20260828-TC12-REAL-VITEST-RED-GREEN`
- Scenario：`SCENARIO-028`

## 决策

1. TC-12 继续从 Workspace-first 通用入口触发，不增加 Scenario 选择器。固定适配器只匹配用户普通指令与 qa-003 冻结输入。
2. 服务端冻结并复制 `dashboard-toolkit` 的 11/11 个 allowlisted 输入到隔离 Run Workspace；运行前后重新读取 Catalog，原输入引用与字节必须不变。`task.md`、rubric、solution 不进入模型、普通 API、DOM 或 Artifact。
3. 同一套真实 Vitest 按 Stage A/B/C/D 运行：A 保留原别名配置并复现模块解析红灯；B 只修配置，复现增长率、排序副作用、相等值稳定性和日期函数未导出；C 只增加导出，复现日期起止边界被排除；D 应用完整四文件修复并全绿。静态字符串匹配不能代替红灯。
4. 真实修改限定为 `vitest.config.js`、`metricsCalculator.js`、`dataTransformer.js`、`filterEngine.js`，统一写入 `changes.patch`。未被先红后绿证明的源码不顺手修改。
5. 当前 manifest 由实际 suite 定义生成，共 71 个具名 case：指标计算 23、数据转换 20、筛选与分页 28。公共 manifest、Artifact `self_test.test_suites[]`、ZIP manifest 与实际 collected ID 必须同集，不把数量写成业务上限。
6. 三份变更业务源码分别以 V8 coverage 的 statements/lines 不低于 85%、branches 不低于 75% 为硬门；汇总覆盖率单列，`vitest.config.js` 的加载成功不冒充源码 coverage。
7. 固定 runner 只调用服务端批准的 Node、Vitest 1.6.1 和 `@vitest/coverage-v8` 1.6.1，不运行来源 package scripts、不联网安装、不注入 Provider/数据库凭据或代理。当前只证明固定测试没有观察到网络调用，不是进程或 OS 级 socket 隔离。
8. ZIP 包含完整修复后副本、真实测试、统一 diff、四阶段 JSON、coverage、manifest、中文说明、测试报告、自测卡和固定入口。服务端在独立解压目录再次运行并核对 ID、coverage 与退出码。
9. 前台成果卡必须说明“修复包”和“测试报告”各自用途、改的是隔离副本、四处问题及业务影响、Stage A-D 红绿事实、逐文件 coverage、下载复跑和人工合并边界。测试清单默认折叠，390px 不横向溢出。
10. Artifact effect、Planner/Analyst `called/output_used/elapsed_ms` 与整个 Run 终态是三组不同事实；任何一组不能冒充另外两组。
11. 最终 coverage 固定命令或独立解压复跑非零退出时，两份 Artifact 与 EffectReceipt 均为失败；前台不得显示 `71/71` 绿灯。`review_guidance` 必须明确“当前包不得合并”，指向 Stage D JSON、coverage 与独立复跑回执，并要求修复后创建新的 TC-12 Run。

## 前后端事实

| 前台 | 服务端事实 | 不允许推断 |
| --- | --- | --- |
| 完整 11 文件隔离副本 | Artifact 11 个 `source_file_refs`、`check-tc12-complete-copy`、下载 ZIP | FORTE 原树已修改；任意项目都可复制执行 |
| Stage A/B/C 红灯 | 四份 stage result JSON 与对应 `check-tc12-stage-*` | 静态扫描或编写测试即证明缺陷存在 |
| Stage D 71/71 | `check-tc12-final-green`、实际 collected IDs、零失败 | 测试总数越多就越正确 |
| 三套真实测试 | `self_test.test_suites[]`、公共 manifest、ZIP `test-manifest.json` | 浏览器自己生成或填充测试名 |
| 四文件修复 | `changes.patch`、`changes.json`、`check-tc12-diff-scope` | 系统已修改原文件或创建 PR |
| 逐文件 coverage | coverage JSON 与 `check-tc12-coverage` | aggregate 可以替代逐文件阈值 |
| 可以下载复跑 | Artifact bytes、自测命令、独立解压回执 | 用户已经执行或已经决定合并 |
| 没有外部动作 | EffectReceipt `external_action=none` 与精确 runner 边界 | OS 级断网、生产沙箱、多租户隔离 |
| 固定命令失败 | failed `checks[]/verifier_status`、失败 EffectReceipt、条件化 `review_guidance` | 71/71 绿灯、可以合并、原地改写本轮或只因 ZIP 已生成就算成功 |

## 拒绝的替代方案

- 继续使用历史 9/9 绿灯：拒绝。它没有证明未修复副本能被同一测试捕获。
- 为凑数复制同构用例：拒绝。每个 case 必须有公开名称、不同输入与业务断言。
- 只在报告中写 coverage：拒绝。逐文件数值与阈值必须进入机器可读回执和确定性 Gate。
- 只打包修复后几个文件：拒绝。用户需要完整 11 文件副本、diff、阶段证据和自测入口。
- 把“未注入代理”写成“网络访问已禁用”：拒绝。当前没有进程或 OS 级网络隔离。

## 验证门

- Stage A 因原 `@ -> ./source` 真实解析失败；Stage B 有七个目标红灯；Stage C 有六个目标红灯；Stage D 71/71。
- 三套测试直接导入三个真实模块；manifest、实际 collected 与前台公开 ID 完全一致。
- 三份变更业务源码逐文件 statements/lines/branches 通过 `85/85/75` 门。
- 下载 ZIP 独立解压后用同一固定入口复跑通过；11 个输入前后字节不变。
- PostgreSQL 重启后 Artifact、EffectReceipt、self-test 清单和下载 bytes 保留；这只证明顺序 Runtime 已提交状态恢复。
- 桌面和 390px 前台显示分阶段证据、三套测试与人工合并边界，无页面级横向溢出。
- 负向门注入 Stage D coverage 固定命令非零退出：Scenario、两份 Artifact 与 EffectReceipt 保持失败，报告和首屏不显示 `71/71` 绿灯，并给出证据路径与新 Run 恢复动作。
