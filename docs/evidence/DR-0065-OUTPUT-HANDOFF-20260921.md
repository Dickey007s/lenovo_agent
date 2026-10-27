# DR-0065 Evidence：输出限制、传递与历史兼容

日期：2026-09-21。状态：Limited Verified。当前未提交，无 PR。

## 实现与界面

- `output_policy.py` 编译有限明示禁止文件语句，Runtime 冻结合同并在固定 adapter freeze/write 前
  拦截；原计划写入意图转为只读。默认规则和正向文件生成路径保留。
- `ReadonlyDependencyContext` 经 Owner/Task/Run、采用状态、模型回执、版本和来源范围验证，
  进入真实 Analyst user payload。摘要是数据，不是原文或指令。下游仍需独立通过原文引用门。
- WorkUnit/Contribution 输入 ID 由实际请求派生；为空不写入历史 payload，严格不可变检查不变。
- `HarnessWorkbench` 在原进展/协作位置投影这些事实，无新入口、假 Worker 对话或新权限。
- 对应：[SCENARIO-052](../scenarios/SCENARIO-052-readonly-analysis-and-versioned-handoffs.md)、
  [UI fact matrix](../contracts/UI_SERVER_FACT_MATRIX.md#dr-0065-output-and-handoff-facts)。

## 自动化

| 门 | 结果 / 工件 |
| --- | --- |
| Python 全量 | `478 passed, 24 skipped`；[backend-junit.xml](../reports/demo12-handoff-20260921/backend-junit.xml) |
| 新输出/依赖 + 序列化兼容 | `30 passed`；包括模式正/负例、adapter freeze=0、真实分析器参数、两波、旧命令幂等回放、7 类无预算变化拒绝、父限制继承、旧 digest/CAS/schema 保留 |
| 隔离 PostgreSQL 17.11 | `11 passed`；[postgres-junit.xml](../reports/demo12-handoff-20260921/postgres-junit.xml)，包括旧根回执跨重启、第二波输入 ID 落库、终态幂等回放无模型调用 |
| 浏览器 | `106 passed`；[browser-junit.xml](../reports/demo12-handoff-20260921/browser-junit.xml)。随后修正测试 Fixture 的 waiting_input 等一致性，新增两用例单独 `2 passed` |
| 静态 / 构建 | Ruff、TypeScript、Next 生产 build 通过；临时 build 导致的配置变化已移除 |

全量未设置 TEST_DATABASE_DSN 的跳过项不能视为通过；独立 PG 门只验证被列出的 Task/Demo 路径，
不覆盖所有数据库故障或多实例。浏览器 Fixture 是 UI/协议检查，不是 Provider、语义或用户研究。
截图为原页面完整纵向截图：[桌面](../reports/demo12-handoff-20260921/fixtures/handoff-1440.png)、
[移动](../reports/demo12-handoff-20260921/fixtures/handoff-390.png)，已人工目视检查传递行与文字边界。

## 真实 Provider 与恢复

只用公开 API 和用户式指令，Provider=`deepseek-v4-pro`，PostgreSQL，原始文件未写入，外部业务动作 none。

| Run | 条件 | 结果 |
| --- | --- | --- |
| `harness:2518bc5cf6514d32be89ccba471c11c7` | 五项三根两依赖只读核查，两次明确派发 | 6 次总模型调用；5 Worker；两个下游收到 1 / 2 份输入；4 采用 / 1 定位等待；0 文件；waiting_input |
| `harness:3aae3e1e5dfc4e4eb2bc2845e8b3146d` | 上轮复杂只读指令、切回单 Controller | 3 次模型调用；office_output_suppressed；0 文件；waiting_input |

[实时回执目录](../reports/demo12-handoff-20260921/live/) 保存 start、waiting、actions、snapshot、receipt，
无 Provider 原始响应/密钥。[GET-only 审计](../reports/demo12-handoff-20260921/runtime-audit.json) 对照
昨日工件，确认 11 个旧 Run 可读取、10 个逻辑版本及 6 个旧贡献内容未变。新运行也跨 API 重启
保留输入 ID；恢复没有自动重放。非终态会追加 checkpoint 事件，因此不声称整体 Snapshot 不变。

## 发现的失败与处理

1. 新默认空字段导致旧 PostgreSQL 行被误判不可变冲突。没有重置数据库或删除历史行；通过省略
   空新字段保持旧序列化/hash/CAS，非空变更仍被严格拒绝。包装序列化同时保留字段化 JSON schema。
2. 空 branch_ids 重试原波次时曾转向当前 ready 集合；测试失败后改为恢复原波次身份。
   旧下游命令只在完全匹配已保存 digest 时走兼容回放，错误版本依然拒绝，不能触发无输入新派发。
3. 首次 PG 门在数据库尚未就绪时 1 失败 / 9 通过，记录保留于
   [postgres-before-ready-junit.xml](../reports/demo12-handoff-20260921/postgres-before-ready-junit.xml)。
   数据库就绪后新增恢复门，最终 11 通过。新测试初版误要求非终态恢复 Snapshot 全等，已改为
   明确允许既定 checkpoint/version 变化，仍逐字核对不可变行与 digest。
4. 真实下游一个原文位置不明确：仍待核对，不选候选、不伪造完成、不丢弃其他采用成果。
5. 常驻前端后台启动被本机执行策略拦截；未改用其他方式绕过。生产构建与临时浏览器服务门通过，
   但未完成本轮“真实 API + 常驻前端”的新截图，不将 Fixture 图作为替代证据。

## 禁止外推

不是通用语言权限编译器、全文推理移交、协商型智能体、分布式 Worker、语义正确性或性能优势。
没有目标用户可理解性研究，没有外部办公动作，没有新增 Demo3 接入合同。
两次任务指令/来源/拓扑不同，不能以耗时比宣传蜂群收益。
