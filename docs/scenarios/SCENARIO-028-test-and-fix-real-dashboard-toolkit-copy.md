# SCENARIO-028：在真实看板工具库副本上先复现、再修复并复测

## 用户与触发

- 用户：需要审阅、复跑并人工合并看板工具修复的软件工程师。
- 触发：输入“为三个看板工具模块编写 Vitest，修复源码并真实运行测试。”
- 痛点：只看到“9/9 通过”无法判断测试是否抓住原缺陷、修改了什么、coverage 是否过门，也无法自行复跑。

## 主路径

1. Planner 从冻结整库索引选择 qa-003；服务端固定适配器冻结 `dashboard-toolkit` 11/11 个公开输入。
2. Runtime 把完整输入复制到隔离 Run Workspace，并加入由服务端定义的三个真实 Vitest suite；不改 FORTE 原件。
3. Stage A 在未修配置下运行，真实复现 `@` 指向 `./source` 的解析失败。
4. Stage B 只修配置，再运行同一测试清单，复现增长率分母、排序修改原数组、相等值稳定性和日期函数未导出。
5. Stage C 仅补日期函数导出，继续复现开始日和结束日被排除。
6. Stage D 应用四文件完整修复，71 个实际 collected ID 全部通过；V8 coverage 分别核对三份业务源码。
7. Verifier 比较四阶段回执、manifest、diff、逐文件 coverage、完整副本与 Catalog 再读取结果。
8. 服务端打包 ZIP，在独立目录解压并再次运行固定自测。前台显示修复包、测试报告、三套可展开测试和人工合并边界。

## 异常路径

- 任一预期红灯没有出现：效果门失败，说明测试没有证明原缺陷。
- 最终测试、manifest、逐文件 coverage 或独立复跑不一致：Artifact/EffectReceipt 不得显示绿色通过。
- 固定 Vitest/Coverage 版本不可用：效果失败，不能联网安装或执行来源 package scripts 补救。
- Catalog 再读取发现输入变化：完整性门失败，不得声称隔离副本安全。
- Planner/Analyst 未采用或整个 Run 失败：已通过的确定性 Artifact 事实仍单独保留，不能把 Artifact 绿色冒充 Run `completed`。
- 用户下载后自测失败：查看阶段 JSON、coverage 和 `changes.patch`，不要人工合并。
- Stage D coverage 固定命令或独立复跑非零退出：保留 ZIP、阶段 JSON 和 diff，但两份 Artifact/EffectReceipt 均标失败；首屏写“当前包不得合并”，不显示 `71/71` 绿灯，用户修复后启动新的 TC-12 Run。

## 完成条件

- 11/11 文件完整副本可下载，原 FORTE 输入字节不变。
- Stage A 解析红灯、Stage B 七个业务红灯、Stage C 六个边界红灯、Stage D 71/71 全绿。
- 三套测试为 23/20/28，公共 manifest、ZIP manifest、实际 collected 与前台清单一致。
- 三份业务源码 statements/lines 均至少 85%，branches 至少 75%。
- 用户能看见四处修改、业务影响、固定自测命令、失败信号和“人工审查后合并”。
- PostgreSQL 重启后已提交 Artifact 和清单可恢复；不宣称在途子进程可续跑。
- 失败注入门证明固定命令非零退出不会被包装成绿灯；`review_guidance` 指向 Stage D、coverage 与独立复跑证据，并提供新 Run 恢复动作。

## 来源与边界

- 数据来源：FORTE 固定 revision `345c1ec1487139db9dd319787fa9405ba85d1869` 的 `qa-003/input/dashboard-toolkit`。
- 用户来源：`USER-FEEDBACK-20260828-TC12-REAL-VITEST-RED-GREEN`。
- 这是固定 qa-003 纵切，不是任意 JavaScript 沙箱、自动 PR/合并、生产多租户隔离、OS 级断网、多 Worker 或通用 Tool Gateway。
