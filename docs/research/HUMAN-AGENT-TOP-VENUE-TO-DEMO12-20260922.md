# 从人机共驾论文到 Demo1/2：路线 2、4、6、7

核验日期：2026-09-22。研究是定向选读，不是穷尽综述。正式论文 8 篇，其中 6 篇直接研究
LLM/Agent 的协作、澄清或失败，2 篇 AI Agent 可视分析论文补充交互设计。
会议/期刊身份按正式 proceedings、OpenReview 接收稿或出版机构元数据确认，不把预印本当作顶会。
本次不使用 L0-L5 分级，不替队友规定 Demo3 的任务或接入协议。

## 一句话结论

值得做的不是多加几个 Agent 或确认按钮，而是：**明确交付约定；让局部错误在有限预算内修复；
让下游回到原文核对上游；让人看见仍未解决的分歧和已经保留的成果。**
这是本项目对下述研究的工程取舍，不是任何一篇论文的原话，也不是新算法或效果结论。

## 论文地图

| ID | 论文与正式发表 | 和本项目的关系 | 选读范围 / 入口 |
| --- | --- | --- | --- |
| P1 | **CollabLLM: From Passive Responders to Active Collaborators**，Shirley Wu 等，ICML 2025，PMLR 267:67260-67283 | 人与 LLM 的多轮协作；路线 7、6 | 正式条目、作者稿引言/方法与奖励讨论；[正式页](https://proceedings.mlr.press/v267/wu25i.html)、[作者全文](https://arxiv.org/html/2502.00640v2)、[代码](https://github.com/microsoft/CollabLLM) |
| P2 | **Modeling Future Conversation Turns to Teach LLMs to Ask Clarifying Questions**，Michael J.Q. Zhang、W. Bradley Knox、Eunsol Choi，ICLR 2025 | 何时澄清才对后续回答有帮助；路线 7 | OpenReview 接收稿首页、方法与任务设定；[正式接收稿 PDF](https://openreview.net/notes/edits/attachment?id=T7MiB6jXdl&name=pdf) |
| P3 | **AgentAsk: Multi-Agent Systems Need to Ask**，Bohan Lin 等，ACL 2026，Volume 1: Long Papers，28055-28077 | Agent 交接边上的信息损失与澄清；路线 4、2 | 正式论文摘要、错误分类、方法与成本讨论；[正式页](https://aclanthology.org/2026.acl-long.1294/)、[PDF](https://aclanthology.org/2026.acl-long.1294.pdf) |
| P4 | **Reflexion: Language Agents with Verbal Reinforcement Learning**，Noah Shinn 等，NeurIPS 2023 Main Conference Track | Agent 利用反馈改进下一次尝试；路线 2 | 正式摘要、反馈与反思记忆机制；[正式页](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html)、[PDF](https://proceedings.neurips.cc/paper_files/paper/2023/file/1b44b878bb782e6954cd888628510e90-Paper-Conference.pdf) |
| P5 | **Why Do Multi-Agent LLM Systems Fail?**，Mert Cemri 等，NeurIPS 2025 **Datasets and Benchmarks Track** | 多 Agent 系统设计、对齐与验证失败；路线 2、4 | 正式版本摘要、分类与限制；[正式页](https://papers.nips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html)、[PDF](https://papers.nips.cc/paper_files/paper/2025/file/b1041e52d3be19f0a9bc491657488e4a-Paper-Datasets_and_Benchmarks_Track.pdf) |
| P6 | **Which Agent Causes Task Failures and When? On Automated Failure Attribution of LLM Multi-Agent Systems**，Shaokun Zhang 等，ICML 2025，PMLR 267:76583-76599 | 分清错误发生在哪个 Agent、哪一步；路线 2、4 | 正式摘要、数据与结果范围；[正式页](https://proceedings.mlr.press/v267/zhang25cq.html)、[作者项目](https://ag2ai.github.io/Agents_Failure_Attribution/)、[作者稿](https://arxiv.org/abs/2505.00212) |
| P7 | **Data Formulator 2: Iterative Creation of Data Visualizations, with AI Transforming Data Along the Way**，Chenglong Wang、Bongshin Lee、Steven Drucker、Dan Marshall、Jianfeng Gao，CHI 2025 | 人通过 UI 与语言表达意图、检查和复用 AI 产物；路线 6、7 | 作者机构正式出版条目与论文摘要；[作者机构页](https://www.microsoft.com/en-us/research/publication/data-formulator-2-iteratively-creating-rich-visualizations-with-ai/)、[DOI](https://doi.org/10.1145/3706598.3713296)、[作者稿](https://arxiv.org/abs/2408.16119) |
| P8 | **Data Formulator: AI-powered Concept-driven Visualization Authoring**，Chenglong Wang、John Thompson、Bongshin Lee，IEEE **TVCG**，2023 在线发表 | 高层意图与 AI 数据变换分离，产物可检查；路线 6、7 的期刊补充 | 作者机构摘要、作者稿与出版元数据；[DOI](https://doi.org/10.1109/TVCG.2023.3326585)、[作者机构页](https://www.microsoft.com/en-us/research/publication/data-formulator-ai-powered-concept-driven-visualization-authoring/)、[PDF](https://arxiv.org/pdf/2309.10094)、[Crossref 元数据](https://api.crossref.org/works/10.1109/TVCG.2023.3326585) |

发表口径：P5 是正式 Datasets and Benchmarks Track，不写成普通研究 track；P7/P8 属于 AI Agent
可视分析，不包装成多 Agent 训练方法。P8 本次核验到期刊与在线年份，在线年份不等于卷期年份。
P7 作者页含后续产品视频，后续 Agent mode 不倒算为 CHI 2025 论文贡献。
P1/P6 的 PMLR PDF 抓取未成功，阅读范围分别来自作者稿和正式摘要/项目，不声称两篇均已全文精读。

## 机制如何转成系统设计

### 路线 2：不是反复重跑，而是有边界的局部修复

P4 把任务反馈转成反思文本并用于后续尝试，包含跨尝试的情节记忆；P5 将失败拆成设计、Agent
对齐、验证等类别；P6 说明从长轨迹定位责任 Agent/步骤本身很难。三者都不能推出“让模型再想一次
就一定能修好”。[Reflexion](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html)、[MAST](https://papers.nips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html)、[Who & When](https://proceedings.mlr.press/v267/zhang25cq.html)。

本轮落地：服务端能够观察的 JSON/结构/输出截断、引用未定位、交接结构缺项，只对当前 Worker
最多加 1 次修复调用。反馈说明哪种门未通过，批准来源不扩大，预算继续计数。
Provider 超时、来源越权、重复原文位置、真实冲突不走这条自动修复。
其它已采用贡献不重算、不覆盖。`repair_count` 是重试次数，不是修复成功率。
没有实现 Reflexion 的长期记忆，也没有声称找到了任务失败的因果责任。

### 路线 4：交接要有核对，不是换角色名字

P3 研究消息交接边上的 Data Gap、Signal Corruption、Referential Drift、Capability Gap，并训练
澄清模块在收益与成本间取舍。它直接提醒我们：有依赖图、传过摘要，不等于下游理解或验证了上游。
[AgentAsk](https://aclanthology.org/2026.acl-long.1294/)。

本轮落地：同一只读 Analyst 接口按真实依赖承担三种职责：无前序时来源分析，一个前序时交叉核对，
多个前序时核对并综合。不是凭空增加三个运行中的 Agent。
每份实际提供的前序 Contribution 必须对应一条 `supported / conflict / insufficient` 回执。
支持/冲突必须绑定本次 Finding 和前序来源中可唯一定位的引用；缺项不能合并。
冲突或不足保留意见及旧成果，不自动改成支持、不靠多数表决盖过问题。

这是受限核对协议，不是 AgentAsk 训练方法，也不是自由 Agent 问答、独立真值裁判、分布式蜂群。
复核意见的语义仍来自模型；服务端只证明身份、来源范围和位置。
人可查看分歧并使用现有局部续办；正式业务裁决及其反馈再验证闭环仍未实现。

### 路线 6：先看交付与待办，再看执行过程

P7/P8 把意图表达、AI 生成的可见产物、检查反馈和迭代结合，研究对象是可视分析，不是本项目。
可借鉴的是“人围绕产物判断和修正”，而不是必须先读完一张 Agent 拓扑图。
[Data Formulator 2](https://www.microsoft.com/en-us/research/publication/data-formulator-2-iteratively-creating-rich-visualizations-with-ai/)、[Data Formulator](https://www.microsoft.com/en-us/research/publication/data-formulator-ai-powered-concept-driven-visualization-authoring/)。

本轮落地：原任务进展中保留已生成文件状态，把当前待办放在前面，再展示任务交付清单：
工作项、已保存发现、已核对来源、复核入口。默认显示 3 项，展开不改后端成果。
执行阶段、分支、完整记录与协作页仍在原处，不另建产品入口。
没有可绑定的 Finding 就显示尚无已保存发现，不凭标题猜完成率。

### 路线 7：人先明确交付约定，冲突再澄清

P1 用多轮奖励训练主动协作者；P2 通过未来对话结果构造偏好，判断澄清是否有益，而不是所有请求
都先问一句。两者研究的是学习策略，不是一个确认弹窗。
[CollabLLM](https://proceedings.mlr.press/v267/wu25i.html)、[ICLR 澄清论文](https://openreview.net/notes/edits/attachment?id=T7MiB6jXdl&name=pdf)。

本轮落地：任务输入旁增加“按任务要求 / 仅页面分析 / 允许生成文件”。人选择仅页面分析时不必
写一长段防御性 Prompt。明确禁文件指令与允许文件选项冲突时，在创建 Run、调用模型之前拒绝，
保留输入供纠正；不是悄悄猜一边。没有冲突时不增加必答问卷。
这是有限输出约定，不是通用需求澄清、任意自然语言权限编译或 CollabLLM 训练复现。

## 人机边界与办公案例

| 情况 | Agent 自主做什么 | 交给人的是什么 | 不允许发生 |
| --- | --- | --- | --- |
| 风险分析 Worker 返回破损 JSON | 同一批准范围最多修复一次，计费/预算事实保留 | 两次仍失败时，选择是否局部续办 | 重跑其它成功分支、隐去首次失败 |
| 同一句话在 PRD 出现两次 | 保留歧义与其它成果 | 原有证据核对流程选择真实位置；具体恢复能力按现行协议 | 重试直到碰巧只剩一个候选、默认代选 |
| 上线判断和测试记录口径冲突 | 保存交叉核对意见及引用，暂不采用综合候选 | 查看冲突、明确后续核查方向；业务裁决仍是人负责 | 自动投票批准上线、将“已定位”说成“正确” |
| 人只想在页面看分析 | 输出限制在固定 adapter 写入前生效 | 可直接选择输出方式；冲突时修改选择/文字 | 仍生成报告文件、删除旧成果、冒充无任何持久记录 |
| 下游遗漏一个前序 | 拒绝本次候选，有预算时最多结构修复一次 | 修复失败后只处理目标分支 | 少核对一份但显示“综合完成” |

贯穿用例：输入 PRD、上线配置、搜索日志、用户行为资料；任务是给出跨职能风险简报。
根工作包分别分析来源，依赖工作包核对/综合已采用内容；遇到分歧保留旧版、显示待办。
输出是可复核的页面分析及逻辑版本，允许文件时仍仅限已有固定 adapter；不执行上线或外部动作。
这个例子是测试/验收任务，不是声称最新模型一定按同一拓扑成功执行。

## 最近邻与创新口径

| 直觉上的“创新” | 已有近邻 | 本轮真实增加 | 还不能宣称 |
| --- | --- | --- | --- |
| 会反思重试 | Reflexion、MAST | 服务端失败分类、单包预算化修复与不变成果保护 | 新反思算法、通用故障归因 |
| 多 Agent 协作核对 | AgentAsk、Who & When | 真实输入 ID 与逐项核对/引用绑定，冲突阻止采用 | 独有协作范式、优于强单 Agent |
| 懂得问人 | CollabLLM、ICLR 澄清论文 | 有限输出约定与启动前冲突处理 | 学会主动协作、问得更少且任务更好 |
| 围绕产物协作 | Data Formulator 系列 | 原系统交付清单、待办优先、证据入口 | 可理解性或效率已提升 |

可证伪候选：在固定模型、相同资料和预算下，**身份绑定的交叉核对 + 有界局部修复**能否减少错误
综合被采用，同时不显著增加人的核查时间？当前只能作为候选，不能作为已验证论文贡献。

## 下一步实验，不冒充已有结果

1. 固定同一模型/版本、输入、任务、预算，比较单 Controller、仅摘要交接、多 Agent 逐项核对，
   再分别关闭局部修复、输出约定、交付清单。不要拿不同任务的耗时比当蜂群收益。
2. 预先固定任务变体：格式损坏、引用缺失/多位置、前序遗漏、真实冲突、来源过期、调用/时间不足。
   测误采用率、局部恢复成功、额外调用/延迟、旧成果是否不变；合同测试和真实模型分开记录。
3. 真人小规模试用比较 Human-only、AI-only、Human+AI。分别记录质量、人的主动/等待时间、
   澄清负担、错批率、恢复时间和模型成本。会提问、能接管、会利用反馈与协作后更好分别评价。
4. 对预设效应与置信区间做后续设计；当前工程用例和模拟返回不能证明人机协同收益。

## 本轮工件

- [DR-0066：限定实现合同](../decisions/DR-0066-reviewed-handoffs-and-output-agreement.md)
- [SCENARIO-053：办公任务中的交接分歧与局部修复](../scenarios/SCENARIO-053-review-handoffs-and-local-repairs.md)
- [实现与验收报告](../reports/demo12-research-20260922/README.md)
- [Evidence 与尚未验证项](../evidence/DR-0066-REVIEWED-HANDOFFS-20260922.md)
