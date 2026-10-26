# DR-0079：可撤回偏好、旧草稿取回与待办找回

日期：2026-10-20。状态：Limited Verified，限对应 Evidence 中的工程路径。当前本地工作区，未提交、未创建 PR。

## 场景与来源

Source：[USER-FEEDBACK-20261020-PRINCIPLE-IMPLEMENTATION](../sources/USER-FEEDBACK-20261020-principle-implementation.md)。
Scenario：[SCENARIO-066](../scenarios/SCENARIO-066-personal-preference-and-draft-recovery.md)。
队友手册 R12 明确偏好可撤回且与授权分开；R14 要求实际可恢复；R10 要求能返回同一事项。
这些是设计依据，不是用户效果证据。修改前备份为
`E:/Project/office-agent-archives/20261020-principles-before/` 的三份产品源码；不是数据库备份。

## 前台交互影响

- 个人文本提供“段落间空一行 / 紧凑排列”，显式勾选后才记住。可随时清除。
  仅此浏览器、当前演示身份；只保存枚举值，不保存正文、对象或授权。
  清除不改当前草稿，下次新事项回到默认方式。存储失败显示未保存，不误报成功。
- 历史摘录提供“取回第 N 版内容”。点击仅填入编辑区，明确尚未恢复；允许放弃。
  再次保存才调用现有 edit_draft，形成新版本；当前版本、来源、历史不被覆盖。
  编辑中、忙、未知结果和只读时不能取回；服务端继续版本与 Owner 校验。
- 最近事项增加“全部 / 待处理”筛选及实际列表计数。筛选、重开只 GET 不执行。
  pending 取现有 OPEN 状态，不把拒绝或已完成混作待办。清楚说明最近二十个 Run 的范围。
  当前待确认或未保存编辑仍不能切换，先暂缓或结束；不是全量待办箱。

## 后端事实映射

ActionInput 新增可选 `format_style=spaced|compact`，仅 format_text 可携带非空值。
None 保持旧的双换行行为，并在序列化时省略新字段，保持旧请求摘要和历史 Snapshot 形状。
显式值进入请求摘要及 Snapshot.input；未知枚举和跨操作使用返回校验失败。
固定工具按此值选择换行符，仍只整理文本副本；undo 恢复原始 input.content。
偏好本身仅 localStorage，不能设置风险、核对项、Owner、版本或许可。

草稿恢复复用 edit_draft + edited_content。版本、幂等与历史追加规则不变；旧版本写入仍失败。
历史 content_snapshot 不存在时不提供恢复按钮，也不猜测旧草稿。恢复来源暂存于前端用于提示，
服务端只证明新草稿保存了所提交内容，不额外证明“从某历史版本恢复”的独立审计事件。
待处理筛选只读 GET /runs?limit=20 的 office_action.status，不新增端点或调度能力。

## 验证与边界

[Evidence](../evidence/DR-0079-PRINCIPLES-20261020.md)记录定向单测、真实本地 API 浏览器测试与截图。
需覆盖偏好撤回/刷新/存储失败、确认不旁路、旧草稿预览零写入、新版本保留与过期拒绝、筛选零执行。
不把这些工程检查称为用户理解提升；无付费 Provider、生产审批、外部写入、PG 重启或跨设备验证。
R12 仅覆盖一种个人文本偏好，R14 仅覆盖摘录新版本恢复，R10 仅补最近列表找回。
