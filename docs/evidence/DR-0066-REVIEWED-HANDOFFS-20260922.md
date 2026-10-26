# DR-0066 Evidence：路线 2、4、6、7 的限定验证

日期：2026-09-22。状态：Limited Verified。基线 HEAD `9a4bbbffe9d3477610718fbba8dae47749ac9aee`；
增量位于已有未提交工作树，未创建新提交或 PR。没有重置历史数据库、源文件或其它用户变更。

## 实现范围

- `output_policy.py` 和 `HarnessRunStart`：显式输出选择、冲突启动前拒绝、旧 auto 序列化兼容。
- `collaboration_review.py`：按真实前序数量分工；绑定逐项前序 ID、Finding 和来源 Anchor。
- `harness_runtime.py`：新合同版本、有界目标 Worker 修复、预算/stop 边界、冲突不采用。
- `readonly_workers.py`：可省略的角色、重试和核对回执，随现有 Snapshot 持久化。
- 原 `HarnessWorkbench`：输入约定、交付清单、核对意见、待办优先；没有新 Demo 路由。
- [Decision](../decisions/DR-0066-reviewed-handoffs-and-output-agreement.md)、
  [Scenario](../scenarios/SCENARIO-053-review-handoffs-and-local-repairs.md)、
  [UI fact matrix](../contracts/UI_SERVER_FACT_MATRIX.md#dr-0066-reviewed-handoffs-and-agreement)。

## 自动化结果

| 门 | 结果 | 工件 / 范围 |
| --- | --- | --- |
| Python 全量 | **499 passed, 25 skipped** | [backend-junit.xml](../reports/demo12-research-20260922/backend-junit.xml)；264.81 秒；未设置测试 DSN |
| 新后端定向 | **21 passed** | `test_demo12_reviewed_collaboration.py` 14 项 + `test_collaboration_review.py` 7 项，包含在全量中，不重复累计 |
| PostgreSQL 单主机 | **12 passed** | [postgres-junit.xml](../reports/demo12-research-20260922/postgres-junit.xml)；Task Ledger + Demo1/2，13.43 秒 |
| 全量浏览器 | **108 passed** | [browser-junit.xml](../reports/demo12-research-20260922/browser-junit.xml)；展示顺序修正后全量复跑，约 3.9 分钟 |
| 视觉补验 | **2 passed** | [visual-junit.xml](../reports/demo12-research-20260922/visual-junit.xml)；重新取完整桌面/移动画面，确认无横向溢出 |
| 静态/构建 | Ruff、TypeScript、Next production build 通过 | 使用独立 `.next-demo12-check`；移除构建自动加入的配置变更 |

25 个 skipped 不等于通过；独立数据库门只补测上述 12 项，不表示其它集成 skip 已完成。
PostgreSQL 17.11 使用隔离 `office_demo12_test`，没有对演示业务库做测试清理。
浏览器使用受控 Snapshot/模型响应，证明 UI/协议行为，不证明真实 Provider 或用户理解。
本轮没有新增真实 Provider 调用。DR-0065 的真实模型证据不能倒用来证明新增核对字段的遵循。

## 关键正例与反例

1. 三个根工作包中只让一个首次结构失败：调用分布 `1 / 1 / 2`，总预算为 Planner 1 + Worker 4；
   成功时三份采用，失败重试不影响两份兄弟成果。
2. 重复结构错误止于第二次；timeout/provider_response 不自动再发；剩余预算不足和 stop 阻止新修复。
3. 原文真实出现两次时保持 ambiguous，无自动改引用，无自动多试一次；其它两包采用保留。
4. 下游缺前序、重复/外来 ID、错误序号、未定位 Finding 或非父来源 Anchor，均不能通过核对结构门。
5. 下游明确 conflict/insufficient 时不自动“修”成 supported，不合入当前简报；父版本逐字不变。
6. 相同 Worker 命令回放不再调用。新 PostgreSQL 用例重启恢复核对意见及 Anchor，保持旧成果，
   不重放模型；沿用既有 checkpoint/version 变化，未要求整个非终态 Snapshot 全等。
7. 输出选择与明确禁文件文字冲突时返回输入错误；浏览器保留草稿，改正选择产生新的请求键。
8. 前台没有叫模型的回执便不画核对意见；没有绑定 Finding 不猜交付；有分歧不画“可执行”或“已批准”。

## 视觉检查与发现的问题

- 初版交付清单默认 5 项，首屏主待办被挤到下面。改为待办优先、清单默认 3 项、其余可展开。
- 核对分歧曾可能沿用 WorkUnit ready 的“可执行”标签；现在等待分支的核对意见优先，未列入当前
  ready 波次的普通 ready 工作包只显示等待派发。重试次数也不再用“已修复”冒充成功。
- 初版截图在自动点击后停在页面中段；补验明确回到顶部，并另取展开视口的桌面完整纵向截图。
  不裁去状态、保留头部与底部。完整图用于检查排版，不是额外产品页。
- 截图反例还补齐了对应 rejected Contribution、WorkUnit 和调用数，避免用“3/3 已采用”掩盖
  额外未采用的下游候选。最终图明确为 5 个 Worker、3/5 采用、2 个待复核；这是 Fixture 一致性修正。
- 初次新 E2E 的输入错误断言误匹配 Next.js 自带 live region，改为定位实际错误区；不是忽略服务端错误。
- 首次核对绑定测试暴露 Finding 缺稳定 ID；在 Anchor 解析前使用现有服务端 Finding ID 逻辑，
  仍严格拒绝错误前序与未定位发现，没有放松来源或不可变校验。

截图为原系统 UI 加受控业务事实，**不是本轮真实模型完成任务证据**：
[进展桌面全图](../reports/demo12-research-20260922/screenshots/delivery-1440-full.png)、
[进展移动全图](../reports/demo12-research-20260922/screenshots/delivery-390.png)、
[协作桌面全图](../reports/demo12-research-20260922/screenshots/reviews-1440-full.png)、
[协作移动全图](../reports/demo12-research-20260922/screenshots/reviews-390.png)。

## 未验证与禁止外推

本轮开发服务仅随 Playwright 临时启动；常驻 3000 前端未作为交付已启动，旧 8010 API 也没有
为本轮重启。上轮后台启动被执行策略拒绝，未通过另一种启动方式绕过；不提供假在线入口。

不证明论文训练方法复现、自由 Agent 协商、独立语义真值、自动业务裁决、分布式 Worker、
多实例 lease、用户认知负担下降或任务质量改善。现有单分支 resume/continue 不等于新的人类
冲突裁决闭环。输出约定只覆盖有限模式与明确短语，未实现通用需求澄清。
完整论文链接、迁移理由、最近邻与实验提案见 [研究地图](../research/HUMAN-AGENT-TOP-VENUE-TO-DEMO12-20260922.md)。
