# DR-0065：Demo3 草稿编辑、人工判断与事项找回

合并说明：本记录从 Demo3 分支旧编号迁入，原实现提交为 `f01a903`。主分支原有编号不变；历史 Evidence 保留当时的编号和测试范围。最新兼容性检查见[主分支合并记录](../evidence/DEMO3-MASTER-MERGE-20260919.md)。

- 状态：Limited Verified；限固定规则、单进程测试记录和已验证界面路径，运行结果见 [Evidence](../evidence/DR-0054-DEMO3-COLLABORATION-EVIDENCE-20260919.md)。
- 日期：2026-09-19
- Source：`USER-FEEDBACK-20260919-DEMO3-COMPLETION`
- Scenario：[SCENARIO-052](../scenarios/SCENARIO-052-demo3-human-judgment-and-return.md)
- 实现基线：`1276bc0`；首次汇总提交 `f01a903`，包含 DR-0064 的单步事项基础；未建立 PR。主分支整合证据单列。

## 场景与来源

用户要求继续完成“最新todo.png”中 Demo3 设计落地和方案评审两项，保持统一工作台及不同简单任务的单步办理。[来源记录](../sources/USER-FEEDBACK-20260919-demo3-completion.md)关联最新手册、v7 需求和历史原型。调研指导交互选择，不能证明新界面带来用户收益。

## 前台交互影响

沿用文件目录、中心工作区和右侧轨迹，不增加 Demo 编号入口或自动串行播放。五类原有操作加上“核对材料分歧”，共六类事项。

摘录可原位编辑并保存，原文和各版草稿分别保留。材料对照只接受用户提供的两段非敏感文字，并列展示，要求明确选择 A/B 和填写理由；没有默认选择，不自动推荐、判断真伪或启动下一任务。“暂时无法判断”保存为暂缓。

最近事项从当前 Owner 最近 20 个 Run 中读取，已暂缓事项可以在办理另一件之后重新打开；列表不是完整待办系统。编辑未保存或事项仍待确认时禁止从列表切换。下载人工处理说明只产生本地文本，不模拟审批受理或通知。

内容变化后展示真实字段差异，旧核对清空。浏览器的“你正在编辑”和“请求结果未知”是本地交互/传输状态，不冒充服务端业务事实。未知请求仍复用原请求与幂等键，不允许新建或切换事项。

## 后端事实映射

仍用模块 2 的严格 ActionInput、模块 4 的固定策略和模块 8 的 Snapshot/事件/版本/幂等提交。新增 `compare_materials`、`alternative_content`；新增 `edit_draft` 与 `record_decision` 命令。普通研究协议不变，不启动 Planner/Analyst 或 Worker。

`edit_draft` 仅接受 extract_excerpt/draft_ready，增加 revision，修改 preview 和草稿回执正文，保留 source_excerpt、原输入及每次 content_snapshot。`record_decision` 仅接受完整的 compare_materials/awaiting_decision 或 deferred，需 first/second 和非空 rationale；形成 decision、decision_note 回执和 decided 终态。confirm 不能替代判断，编辑草稿不能修改发件内容。

两个命令同样检查 Owner、expected_version、action_revision、幂等键和历史上限，并原子提交 Snapshot、事件和回执。新增字段默认值兼容旧 Snapshot；策略记录使用 v2，旧 v1 Snapshot 仍可读取。旧版已保存请求的幂等摘要跨协议版本重放未作为本轮迁移保证。

`awaiting_decision` 映射 Run waiting_input；`decided` 映射 completed，但只表示人工判断记录已保存。两份材料、源文件和外部业务均未改变。事件为 office_action_edit_draft/office_action_record_decision，仍走已有 SSE 与最终 GET。最近事项复用 GET /runs，不增加公开 API 路径。

## 验证与边界

[Evidence](../evidence/DR-0054-DEMO3-COLLABORATION-EVIDENCE-20260919.md)分别记录 Python、浏览器、构建与截图；[开发手册](../design/DEMO3-DEVELOPMENT-HANDBOOK-20260918.md)记录 R/C 对应。设计材料已具备评审条件，正式设计人员评审与目标用户研究仍未进行。

本次没有企业连接器、模型语义冲突检测、敏感资料自动分类、生产身份、审批授权、跨设备身份接续或完整待办历史。人工说明下载不构成系统内委派。内存 store 重载测试不是 PostgreSQL 进程重启保证。
