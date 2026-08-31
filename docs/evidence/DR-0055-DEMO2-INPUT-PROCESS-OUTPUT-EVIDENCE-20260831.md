# DR-0055 Demo 2 输入、过程与输出 Evidence（2026-08-31）

- Evidence ID：`DR-0055-DEMO2-INPUT-PROCESS-OUTPUT-EVIDENCE-20260831`
- 场景：`SCENARIO-042`
- 状态：`Limited Verified`
- 集成分支：`codex/demo2-scenario-io-20260831`
- 场景文档提交：`5556ab3`
- 集成实现提交：`1fcf444`、`c2c04c0`、`eefd21a`、`4f0879e`；全量回归修复
  `13f54ec`
- Luna 开发分支提交：`9f8252981083a1700bae23d293faed580bc9c045`；全量回归修复
  `61eaa9c26d582202347a4cb49fd999400e0f4b81`

## 1. 本 Evidence 回答什么

这次不再只验证“系统里有五个 WorkUnit”，而是固定并核对一条用户能够复述的 Demo 2：

> 请分别核对产品上线、搜索 Agent 运行和用户交互三条工作线中最需要人工处理的风险与
> 证据，形成一份跨职能风险与待办简报。按工作包列出已核对来源、关键发现、缺口、受
> 影响下游和下一步；先独立核对，再统一收敛。不要修改源文件，不要执行代码，不调用
> 外部系统。

验收关注三件事：输入是否属于约定工作线，过程是否按依赖和人工确认执行，输出是否把
逻辑成果、真实办公文件和未采用候选分开。Fixture、DOM 和自动化只能证明合同与界面在
被测路径成立，不能证明真实 Provider 会稳定选择该拓扑或生成正确业务结论。

## 2. 输入 Evidence

固定验收使用 FORTE 公共 Manifest 中十份真实文件的标签、来源组和安全 `file_ref` 形状：

| 工作线 | 文件 | 固定数量 |
| --- | --- | --- |
| 产品管理 | `PRD_v2.5.md`、`上线配置清单.xlsx`、`功能测试报告.xlsx`、`线上兼容环境测试报告.xlsx` | 4 |
| 算法研发 | `workflow.py`、`tools.py`、`search_agent.log` | 3 |
| 用户体验 | `交互行为痛点及优化规则.md`、`用户交互行为日志.xlsx`、`页面级交互规范.docx` | 3 |

Acceptance 明确断言三个根工作包的批准来源为 4/3/3，`source_span=3`；浏览器 Fixture 的
去重输入集合为十份。测试不读取 `task.md`、rubric、solution，不向 DOM 暴露绝对路径、
raw hash、Prompt、CoT 或 raw Provider reply。

## 3. 过程 Evidence

1. 服务端先根据 validated plan 的独立根分支、依赖、来源组、副作用和剩余预算形成
   `TopologyAdmission`，不是因为指令里出现“分别”就强制并行。
2. 用户确认前，三个根 WorkUnit 可以被公开，但 Worker handler 调用数和执行回执均为 0。
3. 第一波只执行产品上线 Gate、搜索 Agent 运行风险、用户交互证据三个根工作包。
4. 第二波的“产品影响与交互优先级”只依赖产品与交互根工作包；“统一待办建议”只依赖
   搜索 Agent 根工作包。依赖集合由服务端 WorkUnit/Branch 事实公开。
5. 每次返回先形成不可变 Contribution，再由来源范围、Evidence Anchor、Branch Gate 和
   叙事对账决定是否进入 ArtifactVersion；`model_called` 与 `output_used` 分开显示。

搜索 Agent 根工作包被构造为 `ambiguous` 时，产品与交互两条 Contribution 仍进入部分
v1，“产品影响与交互优先级”仍可进入第二波；只有“统一待办建议”保持 blocked。非法
客户端请求不能把 blocked 工作包塞入下一波，旧 Snapshot 和 v1 保持不变。

## 4. 输出 Evidence

正向浏览器路径公开：

- v1：三个根工作包的业务标题、批准来源、实际调用回执、采用状态和 Anchor；
- v2：追加两个依赖工作包，v1 不被覆盖；
- WorkUnit/Contribution：来源、业务依赖、attempt、返回/采用状态、Gate 原因和成果版本；
- 结果边界：`当前为逻辑成果版本，可审查和恢复；尚未生成 DOCX/CSV 下载文件。`

该提示只在存在逻辑 `artifact_versions[]` 且没有真实 `workspace_artifacts[]` 时出现，不会
把既有已生成、可下载并经过确定性检查的办公文件降级为“尚未生成”。

## 5. 自动化结果

在集成分支完成以下独立复跑：

| 门 | 命令 | 结果 |
| --- | --- | --- |
| Runtime、固定场景与治理 | `uv run pytest -q tests/unit/test_demo2_runtime.py tests/acceptance/test_demo1_demo2_fixed_scenarios.py tests/unit/test_reporting_governance.py tests/unit/test_loop_swarm_prototype.py` | `35 passed in 3.11s` |
| 全量 Python | `uv run pytest -q` | `418 passed, 23 skipped in 302.98s`；skip 不算通过 |
| Python 静态检查 | `uv run ruff check .` | `All checks passed` |
| Web 类型与 lint | `pnpm --dir apps/web lint` | passed |
| Web 生产构建 | `pnpm --dir apps/web build` | passed |
| Demo 2 浏览器 | `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts --grep "Demo 2"` | `2 passed in 16.3s` |
| 全量浏览器 | `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts` | 修复后 `69 passed in 2.7m` |
| Markdown 本地链接 | 变更 Markdown 的相对链接检查 | passed |
| 补丁格式 | `git diff --check` | passed；仅 Git 行尾提示，无 whitespace error |

两条 Playwright 分别覆盖正向两波和搜索 Agent 歧义的局部保留路径；正向用例在桌面视图
检查十份来源、依赖、v1/v2 和逻辑成果边界，并切到 390 px 检查无页面级横向溢出。它是
受控浏览器 Fixture，不是目标用户研究或真实 Provider 运行。

### 5.1 全量回归暴露并修正的问题

第一次全量 Playwright 不是绿灯：`66 passed / 3 failed`。新增产品目录时，Fixture 被错误
扩成 101 份文件，并改变了首页默认财务预览，分别打破 15/96 资料库事实、文档预览和
390 px 移动端回归。修复提交 `61eaa9c`/集成提交 `13f54ec` 恢复财务目录为首个 seed，
把产品目录放在既有命名目录之后，并让 9 个命名目录 32 份文件加 6 个通用目录 64 份
文件重新等于 15 个目录、96 份文件。第二次全量 Playwright 为 `69 passed`。这次红灯与
修复均保留，不能只报告先前两条 Demo 2 定向绿灯。

## 6. 能证明与不能证明

本 Evidence 可以证明：

- 固定十份来源、三根两依赖拓扑和 4/3/3 来源范围在测试合同中一致；
- 确认前零 Worker 调用、返回与采用分离、v1/v2 append-only 和局部失败影响范围在被测
  Runtime 成立；
- 前台能查看业务名称、来源、依赖、回执和逻辑成果边界，且 390 px 无页面级溢出；
- 三期同结构财务反例继续走 `fixed_workflow`，不为展示而创建 Worker 台账；
- 合法 Contribution 的 11 条 Findings 不会被旧的三条显示/合同上限静默截断。

本 Evidence 不能证明：

- 真实 Provider 每次都会选这十份文件、采用 Worker 路线或得到相同 Finding；
- 十份资料来自同一真实公司、同一产品或同一发布时间线；
- 多 Worker 更快、更准、更省钱，或目标用户更容易理解；
- 生成了 DOCX/CSV、修改了源文件、执行了代码、调用了 Connector 或发生外部动作；
- distributed queue/lease、远端 Worker、多实例协调、跨进程在途续跑或生产 HA；
- 本轮重新验证了 PostgreSQL 恢复或真实 Provider；两项均未运行。

形成性用户试用仍需记录：用户能否正确说出“为什么采用这条路线、哪个候选进入成果、
局部失败影响哪个下游、当前得到的是逻辑版本还是办公文件”。自动化不能替代这一步。
