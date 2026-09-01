# Agent 能力页四层渐进披露验收门

- 日期：2026-09-01
- 状态：`Limited Verified`；前台工程门通过，体验与真实 Provider 未验证
- 决策：`DR-0058`
- 场景：`SCENARIO-045`

## 一、用户可直接试的用例

### TC-PD-01：默认首屏不再同时铺开两种能力

打开一条 current Adaptive Run 的 `/agent-capabilities`。预期默认只展开“执行进展”，能看见
任务身份、进度、主要待办、Branch 摘要和当前成果；完整 Swarm、Worker 回执、事件与后端
字段不在首屏展开。

### TC-PD-02：同一 Run 下切换协作方式

切换“协作方式”。预期 Task/Run 身份不变，显示该 Snapshot 的 TopologyAdmission、
WorkUnit 依赖、Contribution 采用和当前 Artifact。Adaptive 正例必须在一个工作面内显示
左侧阶段轨、中央真实依赖图、右侧当前影响和底部协作结果；返回“执行进展”不重新选择 Run。

### TC-PD-03：完整执行记录按需展开

点击“查看完整执行记录”。预期默认定位当前 Round 或等待 Branch，显示局部恢复和版本历史；
事件、模型回执与后端字段默认收起。

### TC-PD-04：单一待办使用普通用户语言

构造一个 open DecisionRequest。预期首屏说明系统发现什么和影响什么，不显示 raw
`candidate_id`、`branch_id`、`source_revision` 或“缺一份引用/重试此分支”等协议文案。

### TC-PD-05：候选选择与安全原文

打开核对页，确认候选、文件和摘录均来自公共 packet 与安全 preview。未选择时确认按钮
禁用；选择后可用。accept 继续携带服务端要求的版本、幂等、request 和 revision 字段。

### TC-PD-06：局部恢复与成果保留

确认歧义候选后，只有受影响 Branch/WorkUnit 恢复；其他完成项和旧 ArtifactVersion 不变，
新结果追加为下一版本。前台不得写成整条任务重跑。

### TC-PD-07：Adaptive 与 Fixed 正反例

Adaptive Fixture 显示真实工作包和“受限只读 Worker、单进程、每波最多 3 个”。Fixed 或
Single Controller Fixture 显示真实 route/reason，零 Worker 且无假 WorkUnit。3 root +
2 dependent Fixture 必须得到 5 个节点和 2 条真实依赖；一个 waiting/blocked 工作包只能
影响其依赖下游，兄弟分支和已采用成果继续保留。

### TC-PD-08：历史 Run 只读

切到同 Task 历史 Run。四层均只读，不连接 EventSource，不显示可执行的 Evidence accept、
Branch continue 或 Worker confirmation。切回 current 后再恢复 SSE。

### TC-PD-09：无 Run 与错误边界

无 Run、Task pointer 失败、Catalog integrity failure、preview failure 和 Run failure 分别显示
真实空态/错误；不得填入概念图中的任务、状态或工作包。

### TC-PD-10：桌面与 390 px

桌面保持宽松主列；390 px 标签、进度、待办、分支、拓扑和核对操作均无横向溢出、遮挡或
不可达按钮。正文不低于现有可读字号门。

### TC-PD-11：键盘与可访问关系

Tab 键进入能力标签时只聚焦当前 tab；左右方向键移动并切换执行进展/协作方式，Enter 或
Space 可激活；每个 tab 的 `aria-controls` 与 panel 的 `aria-labelledby` 双向一致。完整
执行记录和 Worker 记录的 disclosure 可用 Enter/Space 展开，并同步 `aria-expanded`。

## 二、自动化与隐私门

- 断言 Loop 与 Swarm 不再作为两块完整列同时可见；
- tab 切换只改变表现层，不混用两个 Snapshot；
- open decision 为零、一个和多个时均有确定性投影且不静默丢失；
- locator label 按文本行、表格行、页或文件级退化显示；
- history/current、SSE sequence/version 和 final GET 语义保持；
- DOM 不暴露 owner、raw ID、digest、绝对路径、Prompt、CoT 或 raw provider response；
- Workspace 的 15/96、安全预览、任务输入、成果和审查回归通过；
- 页面不出现假驾驶舱队列或分布式 Swarm 声明。
- tab 与 disclosure 符合本轮采用的 WAI-ARIA APG 关系和键盘门。

## 三、工程门

```powershell
uv run pytest -q
uv run ruff check .
pnpm --dir apps/web lint
pnpm --dir apps/web build
pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts
git diff --check
```

实现若只改前端，Python/Ruff 可复用同一基线但仍需明确本轮是否重跑。真实 PostgreSQL、
真实 Provider、目标用户走查和业务正确性必须单列，不能由 Fixture 或 Image2 概念图替代。

## 四、结果

- 四层与恢复定向 Playwright：`7 passed`；截图捕获定向：`4 passed`；
- 最终全量 Playwright：`77 passed`；第一次全量为 `75 passed, 2 failed`，修复可访问名称后
  才通过；
- `pnpm lint`、`pnpm build`、`uv run ruff check .`、`git diff --check`：通过；
- 全量 Python：`418 passed, 23 skipped`；汇报治理：`4 passed`；
- 五张运行截图、hash、测试边界和未验证项见 DR-0058 Evidence。
- 视觉重构收尾：capability 定向 `4 passed`、最终全量 Playwright `77 passed`、Web
  lint/build/diff-check 通过；新增四张受控 Fixture 截图。纯前端收尾没有重跑
  Python、Ruff、Provider 或 PostgreSQL，初版基线不得冒充本提交的新验证。
- Adaptive 执行工作面：定向 `9 passed`、最终全量 Playwright `80 passed`、Web
  lint/build/diff-check 通过；最终状态一致性定向 `3 passed`、截图相关 `8 passed`，可见
  方向连线微调定向 `3 passed`，最后一次渲染微调沿用同日 `80 passed` 基线而未重复全量；
  新增 1440 与 390 px 受控 Fixture 截图。未重跑 Python、Ruff、Provider 或 PostgreSQL。
