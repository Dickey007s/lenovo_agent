# 最终版本参考材料

本目录保存 2026-07 阶段评审后指定的最终参考材料，用于后续产品、交互和工程实现对齐。三个源文件均按原始内容保留，不在复制过程中改写。

当前可执行事实仍以源码、测试和仓库根目录技术文档为准；参考材料中描述但尚未实现的 Loop、Adaptive Swarm、跨端控制和真实 Connector 不应被表述为当前能力。

## 文件清单

| 文件 | 用途 | SHA-256 |
| --- | --- | --- |
| `未来办公Agent_一小时汇报讲稿_v5.md` | 最终汇报讲稿与逐页叙事 | `E346EEF04935BF2095E37B6E153183901B0192B06901C7A1D6AAB3A66F0937D2` |
| `office_agent_demo_showcase_v5_reference_layout.html` | 三个 Demo 的离线交互参考原型 | `0E9C9EA49AEA838C9B05DB80E44BF6C7E88EA9691BE4D2E2AF77D9B362E6D535` |
| `0716-v2.pptx` | 36 页阶段汇报及现有工程实现说明 | `A768EFA7412F35FD65FCFDE61DA4DA616066999E157DEC64AE3DD79F6C5E0B8B` |

HTML 与 `docs/prototypes/loop-swarm-showcase.html` 内容完全相同。本目录保留原始文件名用于版本追溯，`docs/prototypes/` 中的副本继续作为当前仓库的原型入口。

## “下一步重点”覆盖矩阵

| 评审要求 | 仓库落点 | 工程输出要求 |
| --- | --- | --- |
| 技术对比及其交互影响 | `docs/TARGET_ARCHITECTURE.md` 第 7 节；PPT 的 Loop/Swarm 演进与 Admission 页面 | 对同一任务比较 Tool Call、Single Agent、Fixed Workflow、Adaptive Swarm，并记录质量、时延、成本、风险和确认负担 |
| 具体用户场景与设计来源 | 目标架构第 6、9 节；讲稿；三个 Demo 页面 | 每个场景必须注明用户目标、来源、完成条件、异常路径及研究或实践依据 |
| AI 与交互方式的共同演进 | 目标架构第 8 节；HTML 驾驶舱、分支和 Risk Gate | 验证 Steer、Pause branch、Take over、冲突理解和 Human Gate 对用户决策的影响 |
| 技术落地后的前台输出 | 目标架构第 8 节；PPT 中任务驾驶舱、分支状态和确认卡 | 前端展示 Task ID、来源、预算、状态、冲突、验证结果和待用户决定节点，不展示虚假完成状态 |
| 前端与后端统一策略 | 目标架构第 8 节及现有 API/治理文档 | 进度、分支真值、风险、Permit、预算和执行结果全部由服务端状态或事件驱动 |
| 基于 8 个最小模块继续 Demo | 目标架构第 3、10 节；PPT 的 8 组件页；HTML 原型 | 先实现 Task Contract、Durable State 和单任务 Loop，再接 Verifier、Control、Swarm 与驾驶舱 |

## 已知内容边界

- `0716-v2.pptx` 封面写有 `2025年7月16日`，而文件版本与阶段评审上下文指向 2026-07。原件未被擅自修改，正式对外使用前需要项目负责人确认年份。
- PPT 中的 L0-L5 页面是交互说明；规范实现仍以当前确定性风险算法为准：普通累计风险最高 L4，L5 仅由既有硬条件触发。
- PPT 和 HTML 中的邮箱、客户、金额及动作内容均为演示 Fixture，不得替换为真实客户数据后提交到 Git。
- HTML 是离线参考原型，不连接当前 API；交互完成状态不能作为服务端已提交或已执行的证据。
