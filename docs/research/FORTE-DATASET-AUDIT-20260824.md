# FORTE 公共办公输入数据审计（2026-08-24）

## 状态

`Verified`（仅限“原始公开基准输入导入、来源校验和只读索引”，不表示 Demo 1/2/3 已完成重构，也不表示真实企业数据接入）。

## 场景与问题

目标用户是需要向评审演示办公 Agent 的产品/技术负责人。当前演示使用项目生成的客户 A 仿真文件，用户反馈“数据不对应办公场景，演示像写死的系统”。本次数据纵切的目标是让 Agent 在可追溯的公开办公任务文件夹上执行受控读取和后续 Harness 实验：文件存在、格式真实、跨文件关系由来源任务给出，文件被篡改或越权时不得继续。

完成条件是：固定第三方版本，原样保留 task.md provenance record 和输入字节；不导入 `solution/`、`skills/`，而 task.md front matter 中随原文保留的 rubric/solution 元数据只能留在 provenance 层；保留许可证和 SHA-256 台账；服务端只读 Catalog 能在 manifest、路径、符号链接、大小和哈希任一失败时 fail closed。公共 API/UI 还必须拒绝 raw task、`task_instruction`、rubric、solution 和 grading 内容，Prompt 净化文本只能供内部 Planner。关键异常路径包括缺文件、增加未声明文件、路径逃逸、篡改、不可解析 XLSX 和任务目录符号链接。

## 来源与依据

| Source ID | 类型 | 精确引用 | 采集版本/日期 | 支持判断 | 局限 |
| --- | --- | --- | --- | --- | --- |
| `SRC-FORTE-REPO-20260824` | 官方仓库 | [AGI-Eval-Official/FORTE](https://github.com/AGI-Eval-Official/FORTE)，`data/tasks/<id>.md`、`data/assets/<id>/input/`、顶层 `LICENSE` | commit `345c1ec1487139db9dd319787fa9405ba85d1869`，2026-08-24 | 任务说明与输入文件来自同一公开基准版本；顶层许可证为 MIT | 公开基准不等于 Lenovo、真实客户或实时企业 Connector；仓库内其他 task 的许可证/内容未由本记录推断 |
| `SRC-FORTE-FILE-AUDIT-20260824` | 本地审计证据 | `demo-enterprise-data/forte/manifest.json`、`THIRD_PARTY_LICENSE.txt`、`BenchmarkScenarioCatalog` 及 `tests/unit/test_benchmark_scenario_catalog.py` | 2026-08-24 | 8 个 input 与 3 个 raw task provenance 文件共 11 个原始文件/`115352` bytes 的路径、size、MIME、SHA-256 和解析摘要可复查；篡改、额外文件和路径逃逸被拒绝 | 仅做结构化安全扫描；没有证明文件中的业务主体一定是虚构或真实，也没有证明数据适合生产使用 |

## 导入范围

只导入三个任务的原始 `task.md` provenance record 和 `input/` 文件：

| Task | 输入文件 | 用途候选 |
| --- | --- | --- |
| `Finance-018` | `2025往来明细-上半年.xlsx`、`2025往来明细-下半年.xlsx`、`2026往来明细.xlsx` | 跨期间财务核对、版本/分支与长期任务验证 |
| `pm-014` | `PRD_v2.5.md`、`上线配置清单.xlsx`、`功能测试报告.xlsx`、`线上兼容环境测试报告.xlsx` | 多来源上线审查、冲突卡和复核编排 |
| `Operations-008` | `专业性说明.md` | 受规则约束的操作流程和动作 Gate 验证 |

明确排除 FORTE 的 `solution/` 和 `skills/`。原始 `task.md` 的 front matter 内嵌了 `solution_files`、`rubrics` 等评测元数据；文件保留在仓库中仅作受信 provenance record，并在 manifest 中标记 `role=task_instruction`。Catalog 只取 `## Prompt` 到 `## Grading Criteria` 之前的 planner-facing 文本，剥离 YAML front matter 和 grading/rubric 区段。该净化文本只进入内部 Planner context；raw task、净化文本、`task_instruction`、rubric、solution 和 grading 都不进入公共 API/UI。

## 隐私与文件安全审计

- 三个 Finance/pm 任务共六个 XLSX：均为 OOXML 单工作表、无 VBA project、无 externalLink part、无外部 workbook 关系、无公式、无隐藏 sheet；每个文件的 sheet 名、dimension 和首行表头由 Catalog 做只读摘要。
- 输入 Markdown 和工作簿单元格值未检出邮箱、电话、身份证号、URL、token、password 或 secret。数值列中的金额不按电话或证件号解释。
- 输入包含业务主体名称和负责人姓名字段。审计不能从内容证明这些主体/姓名一定虚构或真实，因此前台必须标注“公开办公基准数据”，不得标注“真实客户资料”或“联想企业文件”。
- 所有导入文件保留原字节；`manifest.json` 对每个文件固定相对 POSIX 路径、大小、MIME、角色和 SHA-256。Catalog 先做 allowlist、非符号链接、路径边界和 hash 校验，再做 Markdown/XLSX 的受限结构摘要。

## 前台和 Harness 影响

这份数据包本身不改变现有 Demo Runtime。DR-0016 的独立 Harness 规划纵切已把来源投影为“公开办公基准数据 / 任务名 / 文件名 / 文件类型 / 短版本”，不显示原始内部路径、solution、rubric、Prompt 或控制 ID。每个 Agent 阶段必须由服务端 Harness 记录读取了哪个 allowlisted 文件、产生了哪个 Artifact、使用了哪个版本；当前只记录文件冻结、动态 Plan 和 validation，尚未产生 Artifact。浏览器只显示业务级事实。

数据校验失败时，服务端返回受控 503，前台显示 Catalog 完整性专用的“工作场景需要更新”恢复状态，不得继续调用模型、显示猜测结果或把静态演示文案当成已完成。本文的来源审计只证明来源和只读索引；另由 DR-0016/0017 Evidence 在固定三场景内 `Limited Verified` 到 `ready_to_execute`。Demo 1/2/3 的 Loop、Worker、Artifact mutation、动作治理和用户理解仍需单独实现和验证。

## 验证

- `uv run pytest -q tests/unit/test_benchmark_scenario_catalog.py`：`4 passed`。
- `uv run ruff check packages/contracts/harness_models.py services/api/app/application/benchmark_scenario_catalog.py tests/unit/test_benchmark_scenario_catalog.py`：通过。
- manifest 中保存了六个 XLSX、两个输入 Markdown 和三个 task.md provenance record 的 SHA-256；原始第三方许可证保存为 `demo-enterprise-data/forte/THIRD_PARTY_LICENSE.txt`。

## DR-0017 字节完整性修订

一次实际 Catalog 失败揭示：旧 `.gitattributes` 将五个上游 CRLF Markdown 当作文本归一化为 LF，而 manifest 绑定的是上游原字节，因此完整性校验按设计 fail closed。修订恢复上游 bytes，并将 FORTE task/input 文件标记为 binary；manifest 与许可证仍按仓库文本规则管理。

在 PR #24 远端分支的 fresh clone verification 中，HEAD `5fab10fb4f638958ff78b39583a4eace2e99396b` 的 11 个文件、`115352` bytes 全部 size/hash 匹配，且当前树不存在 `demo-enterprise-data/customer-a/`。该检查只证明固定分支的字节可复现，不证明 PR 已合并、数据具备生产代表性或三 Demo 已执行。详见 [DR-0017 Evidence](../evidence/FORTE-ONLY-WORKSITE-RETIREMENT-EVIDENCE-20260824.md)。
