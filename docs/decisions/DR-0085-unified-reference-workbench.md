# DR-0085：统一参考界面落地第一阶段

日期：2026-10-23。状态：Limited Verified，仅统一前台与已测操作路径；验证结果见 [Evidence](../evidence/DR-0085-UNIFIED-UI-20261023.md)。
实现：当前未提交工作树，HEAD 基线 fa974ae339c9c4d97d0505eb3eef3e8a81e8ca11；未建立 PR。
场景：[SCENARIO-072](../scenarios/SCENARIO-072-use-unified-task-evidence-results.md)。

## 场景与来源

[USER-FEEDBACK-20261023-UNIFIED-REFERENCE-IMPLEMENTATION](../sources/USER-FEEDBACK-20261023-unified-reference-implementation.md) 授权以三张统一设计及18个状态图重构原系统。
本轮以相同入口、任务列表、原文依据、协作节点和事项流程为第一纵切。设计图不能证明功能存在。
该授权替代旧文档中“前台不能出现 Demo 选择”的展示约束，不替代服务端授权、数据范围和执行约束。

## 前台交互影响

- 原 `/` 改为固定导航、最近任务、任务正文三栏。三个 Demo 使用同一外壳和任务/依据/成果页签。
- 最近任务由最近20个 Run 按 task_id 归组，最高 run_sequence 为列表代表；历史详情仍可打开。不是任务队列。
- 入口切换只进入空白草稿，不创建任务、不取消旧任务、不派发 Worker。未提交的分析指令在当前页面的入口之间保留；不持久化草稿正文。
- 依据页展示公共 Result 的原文引用，按文件和行号并排呈现。点击原文才打开对应安全预览，不附带默认打开的无关资料。
- 缺口必须使用服务端 Branch 关联。歧义优先打开其 Resolution；无 DecisionRequest 的 Worker 问题打开协作回执，不生成假候选或重试授权。
- Agent 分工图显示真实 WorkUnit 和当前采用状态。连接表示协调关系；各工作包文字列出真实依赖，不伪造全并行或时间动画。
- Demo3 继续用原事项组件和独立 action-controls；忙碌、未知请求、已保存事项的编辑中阻止外层入口切换。普通查看页签不提交命令。
- 宽屏保留三栏，窄屏提供可收起的导航/任务层；文件与事件详情保持可达。

## 后端事实映射

无新增 API、权限或状态库。工作区入口是前台能力视图，不是新的服务器 workspace_id；侧栏明确叫“共享资料库”。
任务分类由 office_action、topology_admission.mode 和已有 Worker 回执投影，不能拿分类预测服务端执行路线。
任务、来源和成果继续来自 task_id/run_id/version、Branch、EvidenceAnchor、WorkUnit、Contribution、ArtifactVersion 和 office_action。
当前原件仍是同一只读 FORTE 清单；Demo3 独立目录尚未接入。没有上传或自动派发按钮冒充服务端能力。
原会话 generation、Task GET 当前性、expected_version、幂等键与历史只读不变。

## 验证与边界

验证命令、失败及修复、浏览器截图见 Evidence。本轮自动化包括受控分析回执与实际固定规则 API，两者不混写。
不声明像素级完全一致、18 状态均落地、真实模型成功率、通用多任务蜂群或用户理解改善。
后续仍需独立实现资料导入/版本校验、Demo2 一次授权后的自主多任务调度，以及 Demo3 数据集隔离。
旧版源码与未提交差异存档于 `outputs/archives/unified-ui-20261023-213902/`，其 manifest 明确不包含依赖、环境秘密、数据集或完整 Git 仓库。
