# FORTE Workspace + Agent Harness 工程证据（2026-08-24）

> 生命周期说明：本文件仍是 DR-0016 的限定基础证据。DR-0017 后续将 FORTE 设为唯一产品入口，并退役截图中仍存在的旧工作区共存状态。原运行、测试数字与 hash 保持历史事实；这 6 张截图不是当前最终 UI。

## 状态

`Limited Verified`。结论严格限定为固定 FORTE revision、当前单 API 进程 memory Runtime、三项固定场景，以及终止于 `ready_to_execute` 的统一规划纵切：公开文件工作区、真实模型动态计划、确定性校验、Snapshot/SSE 和前台业务回执已有可复查运行工件、截图、自动化、实现提交、首份证据文档提交与 PR。三 Demo 的执行迁移仍为 `Draft`。

## 场景与完成条件

目标用户是需要在同一办公工作现场中理解 Agent 如何读取资料、形成计划并接受控制的产品评审者。触发问题来自 `USER-FEEDBACK-20260824-WORKSPACE-HARNESS-08`：原演示的数据、三个固定 Runtime 和前台编排让系统更像写死脚本，用户难以判断 Agent 使用了什么资料、是否真的调用模型、计划为何可信以及执行是否已经发生。

本轮完成条件限定为第一纵切：

1. 三个 Demo 从同一份可追溯的 FORTE 公开办公输入包选择场景。
2. 公共场景目录只展示业务标签和安全文件摘要，原始 `task.md` 仅作 provenance。
3. 内部 Planner 只接收净化后的 Prompt 与 allowlisted 文件索引；公共 API、SSE 和普通 UI 不出现 `task_instruction`、rubric、solution 或 benchmark grading 内容。
4. 一个统一 Harness 把工作区冻结、任务契约、模型规划、服务端校验和有序事件投影到前台。
5. 终态只到 `ready_to_execute`，并明确任何工具、run-workspace 写入和外部动作均未执行。
6. 桌面与移动工程代理测试通过，但目标用户理解仍保持未验证。

## 来源与原字节

| 事实 | 可复查依据 | 当前判断 | 局限 |
| --- | --- | --- | --- |
| 上游来源 | [AGI-Eval-Official/FORTE](https://github.com/AGI-Eval-Official/FORTE) 固定 commit `345c1ec1487139db9dd319787fa9405ba85d1869` | `Verified` 来源版本 | 公开 benchmark 不是 Lenovo、真实客户、生产企业数据库或实时 Connector |
| 许可证 | 上游顶层 MIT；本地保存 `demo-enterprise-data/forte/THIRD_PARTY_LICENSE.txt` | `Verified` 限定导入范围 | 不从顶层许可证外推仓库外材料或未导入数据的权利状态 |
| 原始导入字节 | `demo-enterprise-data/forte/manifest.json` 固定 11 个原始文件、总计 `115352` bytes：8 个 input 为 `85475` bytes，3 个 `task.md` provenance record 为 `29877` bytes；逐文件记录 size、MIME 和 SHA-256 | `Verified` 文件台账 | 只证明 vendored bytes 与 manifest 一致，不证明内容主体真实、准确或适合生产 |
| 排除范围 | 未导入 FORTE `solution/` 和 `skills/` | `Verified` 本地目录范围 | raw `task.md` front matter 仍原样含 benchmark 元数据，因此只能留在 provenance 层 |

原始 `task.md` 不属于用户工作现场，也不是公共场景协议。Catalog 只抽取 `## Prompt` 与 `## Grading Criteria` 之间的净化文本供内部 Planner 使用，并拒绝 `solution_files`、`rubrics:`、`rubric_file_paths` 等标记。该净化文本不得回传浏览器；普通 UI 只显示来源类型、任务业务名、文件业务名、文件类型和来源版本。

## 统一八模块

本轮固定以下名称，后续设计、代码、PR 和汇报不得再使用另一套同名成熟度表：

| 模块 | 第一纵切可验证范围 | 本轮之后仍为 Draft |
| --- | --- | --- |
| Scenario Pack & Workspace Catalog | 固定 FORTE manifest、原字节、allowlist/hash/size/path/symlink/解析校验和只读来源快照 | 任意企业文件夹、运行时下载、生产 Connector、通用解析器 |
| Task Contract | 每个公共场景的目标、交付物、数据边界、允许能力与人工 Gate 摘要 | 可编辑契约、生产权限、预算/截止时间和 Worker 子契约 |
| Planner | `deepseek-v4-pro` 生成有界 DAG 候选；只接收内部净化任务和文件索引 | 规划质量、任意任务泛化、成本或 SLA |
| Admission & Plan Validator | 确定性校验路径、工具、副作用枚举、Artifact 名称、依赖、环和外部动作人工 Gate | 运行资源 Admission、生产策略、通用预算和质量评分 |
| Scheduler & Worker Manager | 第一纵切不启动 Scheduler 或 Worker | 三 Demo 的执行迁移、动态 Worker、暂停/恢复、重排和跨进程 lease |
| Tool Gateway | 第一纵切只校验计划中的工具 allowlist；不调用工具 | 统一 read/write 工具执行、真实 Connector 和生产凭据边界 |
| Artifact Workspace & Verifier | 第一纵切只校验计划声明的受控 Artifact 元数据；不创建 Artifact | SharedArtifactVersion、业务工件验证、冲突收敛和最终 Commit |
| Checkpoint, Event & Governance Control | 单 API 进程 memory Snapshot、有序 HarnessEvent、Owner scope、幂等 start 和 SSE 对账 | 持久化恢复、暂停/分支/审批/Permit、跨进程幂等和多实例事件 |

## 第一纵切事实链

```text
public scenario projection
  -> POST /v1/harness/runs
  -> workspace_index
  -> planning_started
  -> planning_completed
  -> plan_validation
  -> ready_to_execute
```

`ready_to_execute` 只证明计划候选已经通过服务端路径、工具、依赖和人工 Gate 校验。当前 Runtime 没有 execution command；计划中即使出现 `artifact.write` 或 `external_action`，也只是一条被校验的候选工作单元。`execution_started=false` 是终态回执边界，不能改写为“任务完成”“工件已生成”或“外部动作已执行”。

## 模型事实、采纳与验证

| 判断 | 服务端事实 | 可以说 | 不能说 |
| --- | --- | --- | --- |
| 模型是否实际调用 | `HarnessModelReceipt.called/model/elapsed_ms` 和对应事件 `details.model_called` | “模型已调用”或“模型未调用” | 只凭加载动画或配置模型名宣布调用 |
| 模型输出是否被采用 | `HarnessModelReceipt.output_used`；只有结构解析和完整服务端 plan validation 后才为 `true` | “模型计划已采用” | 把 HTTP 200 或合法 JSON 等同于采用 |
| 服务端校验是否通过 | `HarnessRunSnapshot.status=ready_to_execute`、非空 `plan`、`plan_validation` 与 `ready_to_execute` 事件 | “计划已通过服务端校验，尚未执行” | 把采用等同于业务正确、质量通过或任务完成 |

模型返回非法 JSON、未知路径、未知工具、非法副作用、Artifact 路径、未知依赖、依赖环或没有人工 Gate 的外部动作时，运行进入 `failed`，保留来源快照和模型调用事实，`output_used=false`，任何执行仍未开始。

### 可复核真实模型三场景运行

2026-08-24 的同一开发运行中，配置模型 `deepseek-v4-pro` 完成三次规划。运行 Snapshot、模型回执、事件序列、health、截图 hash 和验证数字绑定在 [`dr-0016-harness-live-runs.json`](manifests/dr-0016-harness-live-runs.json)。Manifest 是本轮主要可复核运行工件；它证明这三次观测，不构成重复实验、质量基准或生产 SLA。

| Demo / Scenario | 公开 input | 终态 | Snapshot | 计划单元 | elapsed | 模型输出 | 执行边界 |
| --- | ---: | --- | --- | ---: | ---: | --- | --- |
| Demo 1 / `Finance-018` | 3 | `ready_to_execute` | v6 / seq 5 | 10 | 17112 ms | `called=true, output_used=true` | `validation_errors=[]`、`execution_started=false` |
| Demo 2 / `pm-014` | 4 | `ready_to_execute` | v6 / seq 5 | 6 | 13577 ms | `called=true, output_used=true` | `validation_errors=[]`、`execution_started=false` |
| Demo 3 / `Operations-008` | 1 | `ready_to_execute` | v6 / seq 5 | 4 | 10243 ms | `called=true, output_used=true` | `validation_errors=[]`、`execution_started=false` |

三次成功均记录 `workspace_index -> planning_started -> planning_completed -> plan_validation -> ready_to_execute`。这些运行只证明该次模型响应被服务端接受为安全计划；不证明工作单元正确、规划质量优于基线、三 Demo 已执行、工件已产出或用户价值已提升。同日一个旧合同迭代曾因模型提出向源目录写入而 fail closed，但只有交互式文字记录、没有独立仓库工件，因此不计入本轮成功证据或正式通过率。

## 前台目标与当前事实

前台目标不是 Harness debugger，而是默认的“工作现场”：左侧展示本轮公开来源与文件业务标签；中间依次展示读取、生成计划、服务端校验和准备执行，并用动态 DAG 解释依赖与允许能力；右侧只展示服务端活动回执、模型调用事实、等待/失败和恢复，不展示 Prompt、CoT、Worker 对话、绝对路径、完整 hash 或 benchmark 内部字段。

当前实现已把工作现场设为默认首屏，三 Demo 切换读取安全公共 Scenario；左侧只消费 `file_ref/display_label/display_group/display_summary`，中间动态 DAG 只消费 `input_file_refs`，右侧按 Snapshot/Event 显示模型调用、采纳、校验和未执行边界。start、GET 和 SSE 均使用公共 projection；API/DOM 断言拒绝 raw `task.md`、Prompt、rubric/solution、内部 path/hash。不存在或非当前 Owner 的 Run 在建立 SSE 前统一返回 404；终态 SSE 只连接一次并执行最终 GET 对账，非终态断流才按 `after=N` 恢复。390px 视口无横向溢出。任何截图或 E2E 通过仍只证明被测工程投影，不是用户研究，也不能证明理解、信任、效率或任务成功率改善。

## 三 Demo 迁移状态

| Demo | FORTE 场景 | 目标执行策略 | 当前状态 |
| --- | --- | --- | --- |
| Demo 1 | `Finance-018` 跨期财务证据核对 | `durable_task` | 场景、来源和统一动态规划纵切；执行迁移 `Draft` |
| Demo 2 | `pm-014` 上线资料协作核验 | `adaptive_team` | 场景、来源和统一动态规划纵切；Scheduler/Worker/共享工件迁移 `Draft` |
| Demo 3 | `Operations-008` 受约束运营流程 | `governed_action` | 场景、来源和统一动态规划纵切；Risk/Approval/Permit/Simulator 迁移 `Draft` |

旧 Demo 1/2/3 的限定 Verified 事实仍可作为独立历史纵切引用，但不能用于宣称 FORTE 场景已执行，也不能把固定客户 A 的 Worker/Artifact/动作事实移植到新场景。

## 工程验证与交付绑定

| 证据项 | 结果 | 边界 |
| --- | --- | --- |
| Python 全量 | `199 passed, 1 skipped in 7.93s` | 覆盖当前工程回归；不等于生产恢复或效果评测 |
| Ruff | `passed` | 静态工程检查 |
| Web lint | `passed` | 前端静态工程检查 |
| Next build | `passed`；compile `6.7s`、TypeScript `7.8s`、static generation `619ms` | 当前构建环境观测 |
| Browser 全量 | `48 passed (3.6m)` | 工程代理，不是用户研究 |
| Harness 浏览器专项 | `7 passed` | 覆盖默认入口、安全投影、动态计划、终态/失败、幂等、乱序、断流续传和移动布局 |
| Governance / Markdown links / hash / diff-check | Governance `4 passed in 0.03s`；17 份本轮文档本地链接通过；6 张截图 hash/尺寸通过；FORTE 11 文件/`115352` bytes hash/size 通过；diff-check 通过 | 只验证记录完整性、文件身份、链接和空白错误 |
| 真实 `deepseek-v4-pro` 三场景 | Manifest 已绑定 | 三场景均 `ready_to_execute`、`output_used=true`、`execution_started=false`；精确数字见上表 |
| 桌面与移动截图 | Manifest 已绑定 6 张 | 3 张 `1440x900` desktop、3 张 `390x844` mobile；逐图 SHA-256 见 Manifest |
| 实现提交 | [`fdcc3d819686b0d0afd99fcd0b637b5329607835`](https://github.com/Dickey007s/lenovo_agent/commit/fdcc3d819686b0d0afd99fcd0b637b5329607835) | 已 push |
| 首份证据文档提交 | [`265ffb6f1e4f35416b0020deff9becee9a3a26a2`](https://github.com/Dickey007s/lenovo_agent/commit/265ffb6f1e4f35416b0020deff9becee9a3a26a2) | 当前补丁只回填该已落库提交，不反向改写其历史内容 |
| PR | [#23](https://github.com/Dickey007s/lenovo_agent/pull/23) | 已由 `0001a85533409150b1da735263fc1c9e389d8539` 合并到 `master` |

截图清单如下；这里登记显示状态，像素和完整 SHA-256 以 Manifest 为准：

| 文件 | 前台事实 |
| --- | --- |
| `dr-0016-harness-demo1-ready-desktop.png` | Demo 1 来源、契约、10 单元动态计划与模型回执 |
| `dr-0016-harness-demo2-ready-desktop.png` | Demo 2 来源、契约、6 单元动态计划与未执行边界 |
| `dr-0016-harness-demo3-ready-desktop.png` | Demo 3 来源、契约、4 单元计划与人工 Gate |
| `dr-0016-harness-demo3-ready-mobile.png` | 390px 默认工作现场与终态入口 |
| `dr-0016-harness-demo3-plan-mobile.png` | 390px 动态计划纵向呈现 |
| `dr-0016-harness-demo3-agent-mobile.png` | 390px 右侧 Agent 活动回执呈现 |

## 已知边界

- `X-User-Id` 仍是未签名的 P0 占位，不是生产身份。
- Harness Run、幂等表、事件和规划任务只在单 API 进程 memory；API 重启不恢复。
- 本轮 live health 为 `model=deepseek-v4-pro`、`checkpoint=memory`、`task_store=memory`；它不证明持久化已配置。
- 第一纵切没有 Scheduler、Worker、Tool execution、Artifact write、Verifier commit、审批、Permit 或外部动作。
- FORTE 是公开 benchmark input，不是生产企业文件；应用启动时读取本地固定包，不在运行时下载。
- `elapsed_ms` 只表示本次观测，不是供应商 SLA、生产时延或成本效果。
- 没有真实 Connector、后台队列、跨进程 lease、多实例、数据库恢复、任意文件夹泛化或生产安全认证证据。
- 没有目标用户研究；E2E、截图和 Stakeholder 试用不能替代形成性/可用性研究。
