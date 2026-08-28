# DR-0042 TC-12 真实看板工具库 Vitest Evidence

## 当前结论

`Limited Verified`。本地确定性 builder、同测集分阶段红灯、最终 71/71、逐文件 V8 coverage、独立解压复跑、合同 round-trip、前台回归、真实 PostgreSQL 顺序恢复和普通 `deepseek-v4-pro` Run 已通过。该 Run 的 Artifact effect 通过，Planner/Analyst 均调用且采用，但整个 Run 因八条未覆盖 Branch 保持 `waiting_input`；三层事实必须分开报告。远端 PR check 与 merge SHA 在本分支提交后补记。

## 历史基线为何不足

历史 TC-12 生成 ZIP 与 `Vitest回执.md`，修复后 9/9 通过。该纵切证明固定命令确实运行，却没有未修复副本红灯、逐文件 coverage、统一 diff、机器可读实际 test ID、下载后独立复跑或精确网络边界。因此它被保留为历史基线，不能作为当前“测试捕获真实缺陷”的证据。

## 同一测试集的红灯到绿灯

- Stage A：原 `vitest.config.js` 的 `@` 指向 `./source`，三个真实模块均解析失败。
- Stage B：只把别名改到真实 `./src` 后，71 项中七项失败，覆盖增长率分母、排序修改调用方数组、相等值稳定性和日期函数未导出。
- Stage C：只补 `filterByDateRange` 导出后，仍有六项失败，包含开始日和结束日被排除。
- Stage D：应用四文件完整修复后 71 collected、71 passed、0 failed。
- 修改范围：`vitest.config.js`、`src/utils/metricsCalculator.js`、`src/utils/dataTransformer.js`、`src/utils/filterEngine.js`，并生成统一 `changes.patch`。

## 测试清单与覆盖率

- 指标计算：`tests/metricsCalculator.test.js`，23 项。
- 数据转换：`tests/dataTransformer.test.js`，20 项。
- 筛选与分页：`tests/filterEngine.test.js`，28 项。
- 公共机器清单：[`tc12-public-test-manifest-20260828.json`](manifests/tc12-public-test-manifest-20260828.json)。Unit 比较 builder、Artifact `test_suites[]`、E2E fixture 和该文件，不允许 placeholder ID。
- 下载独立复跑口径下，`metricsCalculator.js` statements/lines/branches 为 `100/100/100`；`dataTransformer.js` 为 `100/100/91.3`；`filterEngine.js` 为 `100/100/97.5`，均通过逐文件 `85/85/75` 门。服务端成果卡采用同一独立复跑口径，不与初次 Stage D instrumentation 混写。
- 两份 Artifact 共享 12 个唯一 `check_id`，Run 汇总不得乘成 24 项。

## 下载与只读边界

ZIP 包含完整 11 文件修复后副本、三套真实测试、`changes.patch`、四阶段 JSON、coverage JSON、manifest、中文说明、测试报告、自测卡和固定入口。服务端在独立临时目录解压后再次运行；71 个 ID、coverage、退出码与服务端回执一致。四阶段结束后重新读取 11/11 个 FORTE 输入，引用与字节不变。

固定 runner 只使用仓库批准的 Node、Vitest 1.6.1 与 `@vitest/coverage-v8` 1.6.1，不联网安装、不运行来源 package scripts，也不注入 Provider、数据库凭据或代理。当前未实现进程或 OS 级 socket 隔离，因此只能陈述“固定测试未观察到网络调用”。

## 真实 Provider 与下载独立复跑

- 最终 Run：`harness:d9355005af924d57bb1e9c526adca072`；服务配置为 `deepseek-v4-pro`、`checkpoint=postgres`、`task_store=postgres`。
- Planner 调用 `16828 ms` 且输出采用；Analyst 调用 `19454 ms` 且输出采用。预算记录 1 轮、2 次模型调用、3 份本轮已核对文件、`47270 ms` active elapsed。
- 确定性效果产生两份 Artifact、一份 passed EffectReceipt 和 12 个唯一检查。ZIP 为 `44835` bytes，下载大小与声明一致，SHA-256 为 `8fd4ab865217bf64bc487bab7ed16ee9e52db37baeba0080d2b62594c16bf70f`。
- 下载 ZIP 的内容门确认 35 个归档文件、完整 11 个输入副本、七个未改文件字节一致、四个目标文件发生预期修改；Stage A exit 1、Stage B 7 failed、Stage C 6 failed、Stage D 71 passed。
- 独立解压后实际 Vitest exit 0、71 collected、71 passed、0 failed；manifest 同集，逐文件 coverage 与成果卡均为 `100/100/100`、`100/100/91.3`、`100/100/97.5`。
- Run 最终为 `waiting_input`，仍有八条模型计划 Branch 等待补充；这不影响已通过、可下载的固定 Artifact，也不能把 Artifact 绿色冒充 Run `completed`。机器 Evidence 见 [`tc12-live-final-20260828.json`](manifests/tc12-live-final-20260828.json)。

## 前台验证

- 两份成果共享 12 个唯一检查，前台不乘成 24；首屏显示完整 11 文件副本、Stage A-D、四处修复、逐文件 coverage 与人工合并边界。
- 自测卡显示指标计算 23、数据转换 20、筛选与分页 28；展开后为公共 manifest 的真实测试 ID，没有 placeholder。
- 无 CSS 注入的 1440x1100 正常桌面截图为 [`tc12-real-vitest-desktop.png`](screenshots/tc12-real-vitest-desktop.png)；390px 全页面截图为 [`tc12-real-vitest-mobile.png`](screenshots/tc12-real-vitest-mobile.png)。尺寸、捕获方式和 SHA-256 见 [`tc12-ui-screenshots-20260828.json`](manifests/tc12-ui-screenshots-20260828.json)。
- Playwright 与截图是工程代理，只证明被测 DOM、字体、下载和无页面级横向溢出，不证明真实用户理解。
- 负向 UI 路径以受控 Stage D 非零退出事实验证：两份成果显示检查失败与“当前包不得合并”，列出 Stage D JSON、coverage、独立复跑回执和新 Run 恢复动作；成果区不出现 `71/71` 绿灯或“所有确定性效果门通过”。

## 本地验证

- TC-12 builder：Stage D `71/71`，12 个唯一检查全部通过，独立解压复跑通过。
- TC-12 负向门：注入 Stage D coverage 固定命令 exit 9，不抛异常；Scenario、两份 Artifact 与 EffectReceipt 均失败，失败报告/自测卡不显示 `71/71`，并保留阶段 JSON 与恢复动作。
- Python 全量：配置真实 PostgreSQL 测试库后 `132 passed in 226.16s`，且没有 pending Runtime task 提示。
- 真实 PostgreSQL 顺序门：`1 passed, 3 deselected in 11.72s`。它覆盖 Artifact、EffectReceipt、71 项 `self_test` 与下载 bytes 在 Runtime 重启后的恢复；不证明多实例并发或在途 Vitest 子进程续跑。
- Ruff、前端 lint 与 Next.js production build 通过；Harness Playwright 全量 `37 passed`，其中包含成功路径和固定命令失败路径。

## 尚待收尾

- 远端 check、PR、merge SHA 与最新 master PostgreSQL 重启。

## 不能支持的结论

当前证据不证明任意 JavaScript 仓库自动修复、生产代码沙箱、OS 级断网、自动 PR/合并、真实外部 endpoint 集成、多租户隔离、多 Worker、跨进程 Tool execution 恢复、模型稳定质量或用户理解提升。
