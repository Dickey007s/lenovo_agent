# SCENARIO-048：从任务进展查看协作并确认一处原文

- 状态：`Limited Verified`；参考图驱动的前台纵切。
- 日期：2026-09-11。
- 决策：[DR-0061](../decisions/DR-0061-reference-aligned-capabilities-and-evidence-choice.md)。
- 来源：[用户反馈](../sources/USER-FEEDBACK-20260911-demo12-reference-ui-and-copilot-boundaries.md)。
- Evidence：[验证记录](../evidence/DR-0061-REFERENCE-ALIGNED-CAPABILITIES-EVIDENCE-20260911.md)。

## 主流程

1. 在资料库或能力页提交自己的任务；服务端建立 Run，前台不提交隐藏参考图任务。
2. 默认任务进展显示独立阶段、当前待办、全部真实分支与已有成果。
3. 打开执行记录，按轮核对来源与采用；完整控制与协议仍可展开。
4. 返回任务进展并切换协作方式；依赖、ready 波次与贡献采用来自同一 Snapshot。
5. 如存在 ambiguous Resolution，打开专注核对页；两处或三处候选数量由服务端给定。
6. 查看原文仅改变预览。明确选一处后，携带候选、Resolution、DecisionRequest、Branch、来源 revision、expected version 和幂等键提交。
7. 当前非终态按既有协议继续受影响分支；终态仅记录选择，再从工作面显式 continuation。

## 必须通过的反例

- 同 Finding 两个 Resolution：两个入口必须各自打开正确候选，不能都引用第一项。
- 顶层新来源版本与嵌套旧版本冲突：顶层优先。
- `stale` 待决：不显示可接受的候选单；保留最小分支恢复路径。
- 未选择或仅点预览：accept 禁用，没有控制 POST 或模型调用。
- 409 或网络响应丢失：不能伪造成功，也不将未知结果写成确定未落库。
- defer 409：核对页仍立即关闭，工作面显示未记入错误。
- 历史 Run：只读，Task pointer 未确认时也禁用写操作。
- 已通过文件检查但分析仍在核对：成果先展示，不伪造整体完成。
- 0 个 ready Branch：不出现空 Worker 派发按钮，延后要求仍可单独继续。
- 从页面底部进入执行记录：重置视图滚动，顶部任务和返回入口保持可见。
- 从协作页新建任务，含重复空草稿：返回空白输入框并聚焦，不新增 Task 或停止旧 Run。
- 候选选择前必须显示当前待核对判断的标题/摘要，明确未确认，不能只给多处片段让用户猜。
- 长任务标题可以展开完整目标，不改变任务合同或产生请求。
- 1280×720 与 390×844 核对视口中，未选择及浏览候选之后确认按钮始终可见，未选仍禁用；固定操作条不能遮住可滚动到的最后候选。

## 验证边界

截图与 Playwright 使用受控 Snapshot，证明 UI 映射与请求形状，不证明模型质量或生产效果。
后端既有循环、版本和分支合同通过本轮 Python 回归；数据库条件门的跳过项须单列。

后续 [AC-01 至 AC-05](../testing/DEMO12-ACCEPTANCE-CASES-20260911.md) 增加实际操作。
真实单分支日志任务保留成果并暂停，但内容覆盖验收未通过；详见
[新增 Evidence](../evidence/DEMO12-SELF-TEST-ACCEPTANCE-EVIDENCE-20260911.md)。
