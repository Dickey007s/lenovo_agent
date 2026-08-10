# 未来办公 Agent：Loop、Swarm 与受治理执行

Demo 1 演示一个跨邮件、CRM、项目周报和 PPT 的长期办公任务，如何沿着同一个 Task ID 持续推进。Agent 先建立 Task Contract，再通过 Observe、Plan、Act、Verify、Commit 循环产出中间工件；当 Verify 发现正式版 2,400 万与预测版 2,680 万的口径冲突时，Evidence Gate 只暂停 `revenue-baseline` 分支，客户事实和项目风险分支继续运行。用户可在手机端直接执行 Steer、Pause branch 或 Take over，电脑端与手机端始终共享同一份 Durable State、工件和控制权。最终交付的经营分析、风险页与回复草稿都带有来源、版本、验证结果和 Trace，体现受控持久任务、分支级证据门、跨端连续控制与可验证提交。

Demo 2 继续以智能工作驾驶舱作为用户入口。Agent 先聚合邮件、CRM、项目、报销和日历中的工作信号，生成今日重点排序，解释截止时间、客户等级和业务影响等依据，并允许用户调整本次优先级。每项待办随后进入成本合适的执行方式：简单查证使用 Tool Call，独立草稿使用 Single Agent，稳定重复任务使用 Fixed Workflow，客户 A 经营汇报这类高价值、跨来源、可并行任务进入 Swarm Admission。Admission 通过后，Supervisor 按覆盖度和依赖关系动态生成 Worker，各 Worker 围绕 Shared Artifact Workspace 协作，Verifier 与 Conflict Resolver 负责发现并收敛口径冲突。完成后的经营汇报包继续回到驾驶舱，与其他待办的状态、待我确认事项和 Demo 3 Risk Gate 交接统一呈现。

## P01 未来办公 Agent：从跨端聊天到可治理工作系统

建议时长：2 分钟

各位好，今天汇报的主题是未来五年的办公 Agent。我们把关注点放到一个更具体的问题上：Agent 能否把工作持续推进到完成，并且在这个过程中始终接受证据、预算、权限和用户控制。

这一页中央是统一 Agent Runtime，四周是持续、协作、治理和交付。持续代表同一个 Task ID 在不同设备和时间段里共享状态；协作代表复杂任务可以按需形成 Swarm；治理代表每一步都带有证据门、控制策略和真实动作风险门；交付代表最终产物具备来源、版本和验证记录。

今天的核心判断很简单：未来五年的竞争点，是让工作在约束下持续收敛。后面两组方案会分别回答两个问题。第一，长期任务怎样持续推进并保持方向。第二，复杂任务怎样动态组织协作并收敛到统一结果。

转场：先看这次 Demo 改版究竟改变了什么。

## P02 这次改版带来的能力跃迁

建议时长：2 分钟

这一页用“原方案”和“升级方案”概括本轮修改。Demo 1 原来强调跨端摘要和恢复动作，现在升级为同一 Task ID 的持续运行。用户离开电脑后，任务状态仍然前进；手机端发出的指令直接成为同一任务的控制事件。证据不足时，系统在分支层面暂停和等待，其他工作保持推进。

Demo 2 沿用原方案的信息聚合、今日重点排序、排序解释、用户调序和并行准备，新增执行方式分流。驾驶舱会为每项待办选择 Tool Call、Single Agent、Fixed Workflow 或 Adaptive Swarm。只有高价值、高广度、高并行度任务进入 Swarm Admission；Worker 数量、类型与启动时机由任务覆盖度、依赖关系、截止时间和预算共同决定。Swarm 内部使用共享工件协作，所有事实带来源和版本，冲突由验证器发现并收敛，结果继续回到原驾驶舱。

Demo 3 保留原有 Risk Gate 逻辑，继续负责真实动作前的 L0-L5 风险控制。这样三段演示形成清晰分工：Demo 1 管时间维连续性，Demo 2 管组织维复杂性，Demo 3 管动作维风险。

转场：为了支撑这三类能力，我们先把总体架构说清楚。

## P03 一个底座、两层增强、三类控制

建议时长：2.5 分钟

总体架构可以记成一句话：一个底座、两层增强、三类控制。底座是统一 Agent Runtime，承载任务、状态、上下文、执行、工具、验证、策略和追踪。它是所有场景都需要的常驻能力。

第一层增强是 Agent Control Loop，面向长任务持续推进，重点加入 Durable State、Evidence Gate、预算、停止条件和跨端控制。第二层增强是 Governed Adaptive Swarm，面向高价值、高广度和高并行度任务，重点加入 Admission、Supervisor、动态 Worker、共享工件、冲突收敛和 Control Plane。这两层都通过稳定接口接入底座，根据任务需要启动。

三类控制分别覆盖任务、证据和业务动作。任务控制包括 Steer、Pause branch、Take over；证据控制包括 Evidence Gate、Verifier 和 Conflict Resolver；业务控制沿用 Demo 3 的 L0-L5、Risk Lens 和 Human Gate。

这里要强调一个设计取舍：常驻 Runtime 保持小而稳定，复杂能力按需装配。这个取舍直接回答了最小功能组件是否发生变化的问题。

## P04 Agent 最小运行时组件

建议时长：5 分钟

这一页回答一个基础问题：一个未来办公 Agent 要长期承担真实工作，最小运行时需要哪些稳定职责？我们把底座归纳为八个常驻组件。这里的组件表示清晰的功能边界，部署时可以拆成多个服务，也可以由同一套运行时合并承载。关键是每项任务都能找到对应的责任主体、输入输出和控制接口。

第一，**Task Contract，也就是任务契约**。它负责把用户相对自然的要求整理成系统可以持续执行的任务定义。输入：用户目标、材料范围、截止时间、权限范围和交付要求。输出：唯一 Task ID、交付物清单、任务边界、完成条件以及允许使用的数据来源。工程风险：缺少任务契约时，Agent 容易在长时间运行中扩大范围、偏离目标，也很难判断任务何时真正完成。以客户 A 汇报为例，经营分析、风险页和回复草稿都要进入契约，事实有来源、口径一致和草稿可审阅则作为完成条件。

第二，**Durable Task State，也就是持久任务状态**。它负责保存任务跨时间、跨设备和跨进程运行所需要的结构化状态。输入：执行事件、当前阶段、各分支进度、用户决定、中间工件和版本变化。输出：任务当前处于哪个阶段、哪些分支正在运行或等待、最新工件版本是什么、下一步从哪里继续。工程风险：状态只保存在某次对话或某个进程内时，设备切换、服务重启和长任务中断都会造成进度丢失或状态不一致。Demo 1 能够在手机和电脑上控制同一 Task ID，依赖的就是这层持久状态。

第三，**Context State Manager，也就是上下文状态管理器**。它负责为当前步骤选择真正相关、并且当前身份有权使用的信息。输入：Task Contract、Durable State、邮件和 CRM 等来源、访问权限、当前任务阶段以及上一步结果。输出：提供给本轮模型或工具的上下文投影，其中包含需要的事实、工件、历史决定和控制信息。工程风险：把全部历史和全部材料直接塞进模型，会带来 token 浪费、无关信息干扰、旧版本污染和越权读取。上下文管理器会让核查收入、生成风险页和起草邮件看到各自需要的材料，同时共享已经验证的核心事实。

第四，**Execution Loop，也就是执行循环**。它负责推动任务持续向完成条件收敛，基本节奏是 Observe、Plan、Act、Verify、Commit。输入：当前状态、上下文投影、环境反馈、用户控制事件和剩余预算。输出：下一步计划、工具动作、中间工件、验证请求以及新的状态提交。工程风险：缺少稳定循环时，Agent 容易停在一次回答、重复执行同一动作，或者生成结果后直接向前推进而没有验证和提交点。每次 Commit 都会把有效进展写入 Durable State，下一轮再从最新状态继续。

第五，**Capability Runtime，也就是能力运行时**。它负责统一调度模型、企业工具、连接器、代码沙箱和临时 Worker。输入：Execution Loop 发出的能力请求、调用参数、身份权限、预算和超时要求。输出：工具结果、执行状态、错误信息以及候选工件。工程风险：工具和连接器各自调用时，权限、重试、超时、数据格式和执行环境很容易失去统一约束。能力运行时为邮件、CRM、OA、文件处理和模型调用提供同一套执行接口；Demo 2 需要临时 Worker 时，也通过这层申请和回收计算能力。

第六，**Evidence & Quality Verifier，也就是证据与质量验证器**。它负责检查事实有没有来源、不同工件的口径是否一致、信息覆盖是否达到完成条件、最终产物是否满足质量要求。输入：候选工件、证据索引、Task Contract 中的完成条件、版本信息和质量规则。输出：验证通过、问题清单、事实冲突、缺失证据或补充工作的请求。工程风险：缺少独立验证时，多个 Agent 可能沿用同一个错误，也可能在来源不足时互相确认。Demo 2 中 2,400 万和 2,680 万的冲突，就是 Verifier 发现后交给 Resolver 处理，再对受影响工件重新验证。

第七，**Control Policy，也就是控制策略**。它负责依据风险、预算、验证结果和用户控制权决定任务下一步怎样运行。输入：风险等级、工具与 token 消耗、截止时间、Verifier 结果、权限规则以及 Steer、Pause branch、Take over 等控制事件。输出：继续执行、暂停某个分支、重新规划、降低自治级别、交给用户接管或停止任务。工程风险：长任务和多 Worker 任务可能出现成本持续增长、方向偏移、权限越界和无法及时终止。Evidence Gate、预算上限、停止条件以及 Demo 3 的 L0-L5 控制，都通过这类策略进入运行过程。

第八，**Trace & Checkpoints，也就是运行追踪与检查点**。它负责记录任务怎样走到当前结果，并在关键状态形成可恢复检查点。输入：状态提交、工具调用、证据引用、模型与 Worker 版本、验证结论、策略决定和用户控制事件。输出：完整 Trace、Checkpoint、审计记录、问题回放信息和恢复位置。工程风险：缺少 Trace 时，团队很难解释某个数字来自哪里、某个动作为什么执行，也无法在故障后定位可信恢复点。它同时服务工程调试、业务审计和人工接管。

把八个模块串起来，就是一条完整的运行链：**Task Contract 定目标 → Durable Task State 记进度 → Context State Manager 组装上下文 → Execution Loop 推进 → Capability Runtime 执行动作 → Verifier 验证 → Control Policy 决定继续或调整 → Trace & Checkpoints 记录全过程**。这条链会持续循环，新的状态、证据和控制事件会进入下一轮 Observe，直到完成条件满足或策略要求停止。

三个 Demo 都运行在这套底座上。Demo 1 重点强化 Durable Task State、Context State Manager、Execution Loop、Verifier、Control Policy 和 Trace，让同一任务可以长期推进并跨端控制。Demo 2 保留八个底座职责，同时按需增加 Swarm Admission、Supervisor、Dynamic Workers、Shared Workspace、Resolver 和 Control Plane，用于复杂任务的动态组队与统一收敛。Demo 3 重点调用 Verifier、Control Policy 和 Trace，在真实动作发生前完成风险分级、人工确认和审计记录。

这一页可以用一句话收束：最小组件数量维持八个，组件内部能力与接口契约已经升级，可以支撑长期运行、动态协作和受控执行。

转场：接下来用五页快速回顾 Loop 工程如何发展到今天。

## P05 Prompt Engineering（2020-2024）

建议时长：1 分钟

第一个阶段是 Prompt Engineering，工程对象是一轮模型调用中的指令、示例、约束和输出格式。GPT-3、In-context Learning 和 Prompt Programming 让团队能够更稳定地表达任务意图，也建立了人与模型协作的第一层工程接口。

这个阶段解决的是单次输出可用性。随着任务变长，上下文、工具状态和中间进度会不断变化，单个 Prompt 很难承载整个工作生命周期。模型需要进入一个能够观察环境、执行动作、接收反馈的循环，Agent Loop 因此成为下一阶段的系统骨架。

## P06 Agent Loop 技术基础（2022-2024）

建议时长：1.5 分钟

第二个阶段把工程对象扩展到 Reasoning、Action、Observation 循环。ReAct、Tool Use、Function Calling 和早期 AutoGPT 让模型能够调用外部工具，并依据环境反馈决定下一步。Agent 从回答问题走向执行任务。

这一阶段已经出现 Loop 的基本形态，但状态、验证、停止条件和失败恢复通常由各个应用临时实现。长期任务一旦跨越多个分支和多个工具，应用很难回答“当前事实是什么、哪一步通过验证、何时应该停止”。因此完整的推理状态开始成为核心工程对象。

转场：模型每一步能看到什么，直接决定每一步会做什么。

## P07 Context Engineering（2025）

建议时长：2 分钟

Context Engineering 把上下文从聊天记录扩展为完整的推理与执行状态，包括指令、工具、MCP、历史、记忆、检索结果和工件。工程团队开始系统管理 token 分配、信息相关性和结构化记忆，让模型在当前步骤看到真正需要的信息。

这解决了“把什么放进上下文”的问题，同时暴露出另一个层次：权限、沙箱、执行可靠性、环境反馈和检查点仍然分散在模型外部。要让 Agent 长时间工作，模型需要进入一套稳定、可观测、可约束的工作环境，于是 Harness Engineering 走到前台。

## P08 Harness Engineering（2025-2026）

建议时长：2 分钟

Harness Engineering 的工程对象是模型周围的工作环境，包括工具、沙箱、权限、文件系统、持久工作区、检查点、观测和评测。Coding Agent、Computer Use、Policy Harness 等实践说明，模型能力只有进入稳定环境，才能转化为可运行的系统能力。

可以把 Harness 理解为模型的手、眼、工作台和护栏。它解决执行接入与环境控制，随后又提出生命周期问题：任务何时触发，如何持续运行，何时重规划，怎样验证整体结果，什么事件会再次触发任务。完整 Loop 生命周期由此成为独立工程命题。

## P09 Loop Engineering 集中命名（2026）

建议时长：2 分钟

Loop Engineering 把 Trigger、Discover、Dispatch、Verify、Record、Re-trigger 串成一个持续闭环。长期任务 Agent、后台执行、事件驱动重规划和可验证交付，都可以放进这个生命周期理解。

它的目标是让每一轮循环增加有效证据，并接近 Task Contract 中的完成条件。到了这里，工程问题已经从“模型会不会做一步”扩展为“整个循环能否持续收敛”。方向漂移、证据不足、预算失控和跨端控制成为下一组关键问题。

转场：循环能够持续运行之后，可控性就成为核心指标。

## P10 长任务 Loop 的方向漂移风险

建议时长：3 分钟

长任务的危险来自错误方向被循环不断放大。第一类是方向漂移，中间目标逐步偏离 Task Contract。第二类是上下文退化，关键约束在压缩、覆盖或记忆更新中丢失。第三类是错误复利，未经验证的事实进入后续工件，后续分支继续引用它。

第四类是成本扩张，重试、工具调用和分支数量持续增长。第五类是权限漂移，工具链扩展后，动作范围可能超过原始授权。第六类是停止困难，局部失败牵连整任务，用户缺少分支级暂停和接管点。

因此未来办公 Agent 需要五项运行时控制：状态可持久、证据可验证、预算有上限、分支可暂停、用户可接管。风险感知需要进入每一轮循环，和 Observe、Plan、Act、Verify、Commit 一起运行。

这里可以结合联想对可控性和 Risk-aware Agent 的关注来讲：Control 是前沿能力的组成部分，它决定了持续执行能否进入企业环境。

## P11 Agent Control Loop

建议时长：3.5 分钟

这页是 Demo 1 的方案核心。中心五段循环从 Observe 开始，读取事件、状态、来源和环境反馈。Plan 根据 Task Contract 生成分支、依赖、预算和完成条件。Act 调用工具并提交中间工件。Verify 检查来源、一致性、质量和风险。Commit 将通过验证的状态、工件和 Trace 写入 Durable State。

外围四类控制贯穿每一轮。Task Contract 保持方向；Evidence Gate 管理事实阈值和分支状态；Budget & Stop 管理资源与停止条件；Steer、Pause branch、Take over 让用户随时调整方向、暂停局部分支或接管执行。

当证据冲突只影响金额口径时，Evidence Gate 将 `revenue-baseline` 标记为 `waiting-input`。客户事实和项目风险继续推进。这个分支级行为很重要，它同时避免整任务卡死和错误事实扩散。

Durable State 与 Trace 贯穿全流程。电脑、手机和后台 Runtime 看到同一状态版本，跨端行为表现为控制事件的实时写入。用户无需管理恢复按钮，系统持续维护任务连续性。

转场：下面切到 HTML，现场完整走一遍 Demo 1。

## P12 Demo 1：受控持久任务的完整演示

建议时长：7 分钟

先在 PPT 上说明整体流程。任务目标是完成客户经营分析、风险页和回复草稿，Task ID 是 `office-task-0615`。五个阶段依次读取邮件、CRM、项目周报和现有 PPT，建立分支与预算，并行整理事实、风险和金额口径，然后进入 Verify 与 Commit。

现场操作一：打开新版 HTML，点击顶部 `Demo 1` 场景页签。先让评审看页面保持了参考 HTML 的板块：顶部八个最小组件，中间场景步骤条，左侧能力层，中央用户输入和 Agent 反馈界面，右侧 Trace 与 JSON。强调这次改版集中在场景逻辑，原有演示骨架和操作节奏保持一致。

现场操作二：点击步骤条“建立任务契约”。在 Agent 反馈界面指出 Task Contract 已经写入目标、交付物和完成条件。右侧依次展开输入 JSON、输出 JSON、状态 JSON、风险 JSON，让评审看到每一次界面变化都有结构化状态支撑。此时状态版本为 1，三个分支都处于 queued。

现场操作三：点击“持续推进”。说明用户离开电脑后，Execution Loop 仍然运行 Observe、Plan、Act，持续写入 `facts_v1`、`risks_v1`、`revenue_notes_v1` 和 checkpoint。左侧能力高亮会切到 State & Memory、Loop & Orchestration、Capability & Collaboration。右侧 Trace 显示工具预算和当前进度。

现场操作四：点击“发现证据冲突”。在 Agent 反馈界面同时展示正式版 2,400 万和预测版 2,680 万。再看风险 JSON，此时决策是 `pause_affected_branch_only`。点击下一步“局部分支暂停”，指出 `revenue-baseline` 进入 `waiting-input`，`customer-issues` 和 `project-risk` 继续生成可核查工件。

现场操作五：点击“跨端共享控制权”。手机端指令采用正式口径，同时保留预测版差异说明。这个动作在输入 JSON 中是 `Steer`，状态 JSON 写入 `mobile-steer-01`，任务版本更新为 5。这里请明确说：手机端直接操作同一任务，Durable State 立即记录新方向，电脑端返回时已经看到更新后的状态。

现场操作六：点击“Commit 可追溯工件”。展示最终经营分析、风险页和回复草稿，验证状态为 passed，三个分支全部 committed。再点击“查看完整 Trace”，强调完成依据来自验证通过的工件、来源和状态版本。

这一页的收束可以这样说：Demo 1 展示的是同一任务在证据门、预算和用户控制下持续推进。跨端共享状态与控制权，局部分支可暂停，最终交付可验证、可追溯。

转场：长期任务解决以后，下一类挑战来自复杂任务的组织方式。

## P13 经典 Swarm Intelligence（1989-1999）

建议时长：1 分钟

Swarm 的源头是经典群体智能。Ant Colony Optimization 和 Particle Swarm Optimization 通过分散个体、局部感知、简单规则和环境反馈，形成去中心化搜索与整体涌现。它们擅长组合优化和复杂空间探索。

经典 Swarm 的个体能力相对固定，也没有语言推理、企业工具和知识工作语义。大模型出现以后，每个协作单元都具备推理、角色和工具调用能力，群体机制开始进入知识工作场景。

## P14 LLM 多 Agent 角色协作（2023-2024）

建议时长：2 分钟

CAMEL、ChatDev、MetaGPT、AutoGen 等实践，把复杂任务拆给产品、开发、测试、评审等角色。工程对象包括角色提示词、对话协议、顺序协作和评审机制。多 Agent 由此进入软件工程和知识工作。

这类方案常采用固定角色和预设流程，事实通过对话在角色间传递，成本随轮次增长。任务变化后，角色数量和依赖关系也很难实时调整。生产系统因此需要统一调度器，管理并行工作包、依赖关系和结果聚合。

## P15 Orchestrator-Worker 生产模式（2024-2025）

建议时长：2 分钟

Orchestrator-Worker 建立了动态并行执行的工程骨架。Orchestrator 先规划，再 Fan-out 到多个 Worker。每个 Worker 使用独立子上下文处理一个工作包，完成后由调度器 Aggregate 和 Verify。分支数量可以随任务变化，适合研究、编码、检索和评审。

生产化以后，新的治理问题出现了：什么时候值得组队，所有 Worker 应该共享什么，事实冲突如何收敛，Worker 和工具调用上限如何设定。Admission、Shared Workspace 和 Control Plane 因此成为动态组织能力的必要部分。

## P16 OpenAI Swarm 框架与术语边界（2024）

建议时长：1 分钟

OpenAI Swarm 是一个实验性教育框架，核心概念是 Agents、Handoffs 和客户端编排。它用很简洁的方式表达 Agent 指令、functions、handoffs 和 routines，帮助开发者理解轻量多 Agent 协作。

汇报时需要澄清术语边界：这里的 Swarm 首先是框架名称，指向轻量 Agent 与 Handoff 范式。动态横向扩展、复杂任务图、资源治理和持久任务状态属于后续产品化能力。这个澄清能避免把框架名、经典群体智能和动态产品形态混为一谈。

## P17 动态横向扩展的 Agent Swarm（2026）

建议时长：2 分钟

到 2026 年，Kimi Agent Swarm 等产品形态把协作单元升级为运行时资源。Supervisor 根据任务结构生成异构子任务和 Worker，按 Wave 推进；中间结果达到覆盖阈值后，系统可以继续 Spawn、Replan、Scale，并在完成条件下 Converge。

这种形态适合复杂研究和知识工作，因为任务可以按覆盖度、依赖关系和截止时间动态展开。企业办公还需要统一控制组织收益、事实一致性、成本、权限和停止条件。我们的方案在动态扩展之上加入治理层，形成 Governed Adaptive Office Swarm。

## P18 Adaptive Swarm 的启动边界与 Admission

建议时长：2.5 分钟

Swarm 的第一道门是 Admission。系统从六个维度判断组队收益。Value 看任务价值和交付影响；Breadth 看来源广度和专业跨度；Parallelism 看可独立并行的工作包数量；Deadline 看截止压力；Risk 看事实冲突、权限和真实动作风险；Budget 看 Worker、工具、时间和 token 上限。

评分门会把任务路由到 Tool Call、Single Agent、Fixed Workflow 或 Adaptive Swarm。简单查询进入工具调用，稳定重复流程进入固定 Workflow，高价值、高广度、高并行度且预算可承受的任务进入 Swarm。

Admission 的通过条件是增量质量与速度收益高于额外协调成本。这样可以控制“为了多 Agent 而多 Agent”的倾向，让 Swarm 成为复杂任务的按需组织能力。

## P19 Governed Adaptive Office Swarm

建议时长：3 分钟

这一页把方案拆成六段架构链。Swarm Admission 决定是否启动以及规模上限。Supervisor 创建动态任务图和 Wave。Dynamic Workers 根据覆盖度、依赖和中间结果生成异构 Worker。Shared Artifact Workspace 统一保存事实、来源、版本、负责人和状态。

Verifier 持续检查事实一致性和交付质量，发现冲突后按需调用 Conflict Resolver，解决方案会回写所有受影响工件并重新验证。Control Plane 限制 Worker 数量、工具调用、时间、权限和停止条件，也提供暂停扩展和人工接管能力。

最终只有一个结果出口，用户看到邮件草稿、风险页、证据包和完整 Trace。动态组织负责扩大覆盖和速度，共享工件与治理控制负责收敛结果。

转场：下面进入 HTML，走一遍 Demo 2 的完整过程。

## P20 Demo 2：智能工作驾驶舱

建议时长：7 分钟

这一页要先交代清楚 Demo 2 的产品形态：主界面始终是智能工作驾驶舱，Swarm 是驾驶舱提供的一种复杂任务执行方式。完整流程包括信息聚合、今日重点排序、排序解释、调整优先级、执行方式分流、复杂任务动态组队，以及结果返回驾驶舱。

现场操作一：在新版 HTML 点击顶部 `Demo 2` 场景页签，再点击步骤条“信息聚合”。Agent 反馈界面展示邮件、CRM、项目、报销和日历五类来源，17 条工作信号经过归并和去重后形成 8 项统一任务。右侧输入 JSON 展示五类工具查询，输出 JSON 展示来源数量、原始信号和标准化任务数；状态 JSON 显示驾驶舱已完成聚合，`swarm_started: false`。

现场操作二：依次点击“今日重点排序”“排序解释”和“调整优先级”。先展示系统按截止时间、客户等级、业务影响和依赖关系生成的今日重点排序；再打开客户 A 经营汇报的排序解释，说明它因今日 18:00 截止、客户等级 A、影响明日经营会而排在第一位；最后把“周报格式统一”拖到第二位并设置为仅本次生效。这里要让评审看到，排序可解释，用户也可以直接修正当前计划。

现场操作三：点击“执行方式分流”。驾驶舱同时展示四项工作及建议路由：报销异常核查进入 Tool Call，供应商邮件回复进入 Single Agent，周报格式统一进入 Fixed Workflow，客户 A 经营汇报进入 Adaptive Swarm 候选。请强调，系统根据任务复杂度和交付要求选择执行方式；Swarm 承接其中需要跨来源并行查证的复杂任务。

现场操作四：点击“Swarm Admission”。这一页只评估客户 A 经营汇报，展示 value、breadth、parallelizable branches、deadline pressure 和 budget。输出 JSON 将 route 设为 `adaptive_swarm`，同时给出 `max_workers: 5` 和 `max_tool_calls: 30`。驾驶舱中的其余三项待办继续沿各自路由执行，Control Plane 从 Swarm 启动时刻开始限制预算、权限和停止条件。

现场操作五：点击“Wave 1 · 事实覆盖”。Supervisor 创建 `customer-facts`、`project-risk`、`expense-evidence` 三个工作包。每个 Worker 使用独立 context，结果写入同一个 Shared Artifact Workspace。再点击“Wave 2 · 动态生成”，当事实与风险覆盖度达到 86%，系统生成 `draft-worker` 和 `slide-worker`。Worker 数量随覆盖度和依赖关系动态变化，写作任务在证据基础达到阈值后启动。

现场操作六：先点击“共享工件协同”，展示 12 条事实、9 个来源、1 份草稿、1 张风险页、1 个 open issue 和 7 个版本；右侧 Trace 展示各 Worker 的输入、输出和合并动作。再点击“验证与冲突收敛”，Verifier 发现正式版 2,400 万与预测版 2,680 万冲突，Conflict Resolver 被按需调用。解决结果采用正式口径并保留预测差异说明，受影响工件更新到 v2 后重新通过验证。

现场操作七：点击“返回驾驶舱”。客户 A 经营汇报卡显示 Adaptive Swarm 已完成并解决 1 个口径冲突；周报格式统一显示 Fixed Workflow 已完成；供应商邮件显示 Single Agent 草稿进入“待我确认”；报销异常显示 Tool Call 已找到证据，并交给 Demo 3 Risk Gate。最后展示输出 JSON、状态 JSON 和风险 JSON，说明不同执行方式都回到同一个任务入口、确认队列和 Trace。

这一页的收束可以这样说：Demo 2 的主体是智能工作驾驶舱，它负责信息聚合、今日重点排序、排序解释、用户调序和多任务状态管理。Adaptive Swarm 扩展了驾驶舱处理复杂工作的能力，共享工件、Verifier、Resolver 和 Control Plane 让动态协作形成统一、可验证的结果。

## P21 Demo 3：真实动作前的 Risk Gate

建议时长：2.5 分钟

Demo 3 保持原有业务逻辑。Risk Lens 从动作影响、数据敏感度、可逆性、权限和缺失槽位五个维度评估风险，再映射到 L0-L5。L0 可以自动执行，L1 自动完成并通知，L2 生成草稿，L3 要求普通确认，L4 要求强确认，L5 直接拒绝。

在 HTML 中点击 `Demo 3` 场景页签，沿用原来的步骤条和交互。重点展示 Demo 2 交来的报销异常如何进入预览、确认或拒绝。Agent 反馈界面继续显示动作对象、金额、影响范围和可逆性，右侧风险 JSON 给出 risk level、缺失槽位和决策理由。

这里的价值是业务级动作控制。Demo 1 和 Demo 2 可以持续推进知识工作，涉及付款、发送、提交和权限变更的真实动作仍然在 Risk Gate 前停靠，保证用户看得见影响并拥有最终决定权。

## P22 三个 Demo 的边界、接口与端到端任务链

建议时长：1.5 分钟

三个 Demo 分别处理三个维度。Demo 1 是时间维控制，让同一任务持续推进，输出已验证工件和 Trace。Demo 2 是组织维控制，让复杂任务动态组队，输出统一工件包和冲突记录。Demo 3 是动作维控制，对真实动作进行风险分级，输出自动、草稿、确认、强确认或拒绝。

它们共享 Task Contract、Durable State、Artifact Schema、Evidence、Control Event 和 Trace。端到端任务链可以这样理解：持续 Loop 推进主任务，Swarm 处理复杂分支，Risk Gate 控制真实动作，最后进入 Verified Commit。三个 Demo 共同形成时间、组织、动作三维治理闭环。

## P23 未来三年演进路线

建议时长：1 分钟

2026 年先完成受控运行底座。统一 Agent Runtime 承载 Task Contract、Durable State、Context、Execution Loop、Risk Gate 和 Trace，让个人办公 Agent 可以长期工作，并且随时接受暂停、纠偏和接管。

2027 年进入自适应团队协作。Swarm Admission 根据任务价值和复杂度决定是否组队，Dynamic Workers 按依赖关系生成，Shared Workspace 统一事实、来源与版本，Verifier 推动复杂任务收敛。

2028 年进入可信组织自治。跨系统任务链、策略联邦和 Evidence Trace 支撑团队与组织持续协同，权限边界、人工接管和审计能力贯穿全过程。三年始终沿用同一条治理主线：Task Contract、Durable State、Evidence、Control 和 Trace。

## P24 结论：让 Agent 成为受治理的工作系统

建议时长：1 分钟

最后用五个词收束。持续，让同一 Task ID 跨端共享状态、工件和控制权。收敛，让 Evidence Gate 推动每一轮循环增加有效证据。协作，让 Admission 驱动动态组队，让 Workspace 汇聚事实和版本。治理，让预算、停止、接管、Verifier 和 Risk Gate 全程在线。交付，让最终结果可验证、可追溯、可审计、可复用。

整套方案保持一个最小 Runtime，通过按需增强承载 Control Loop、Adaptive Swarm 和 Risk Gate。我们的目标是让智能持续工作，同时让用户始终掌握方向与决定权。

建议最后停在这一页，等待评审提问。若评审追问最小组件，回到 P04；追问 Loop 前沿性，回到 P09-P11；追问 Swarm 启动边界，回到 P18；追问三个 Demo 如何串联，回到 P22。
