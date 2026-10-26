# DR-0076：界面减法与证据协作讲解验证

日期：2026-10-10。状态：Limited Verified，限定前台回归与离线汇报验证。

## 场景与来源

[Source](../sources/USER-FEEDBACK-20261010-evidence-swarm-and-simple-ui.md)、[Decision](../decisions/DR-0076-calm-demo1-and-evidence-explanation.md)、[Scenario](../scenarios/SCENARIO-063-read-evidence-and-calm-task.md)。
在原有未提交工作上修改，无 commit / push。只改前台投影与报告，不改模型 Prompt 或服务端状态。

## UI 与权威事实

依 DR-0076 对 compact、终态、轮数、拓扑和文件检查状态分层；所有可用控制、失败、业务否决和输入限制保留。
真实只读回看仍用 `harness:a5dcf10ef0d44af6ae9de95d13fcee64`，不新建 Run。

## 本轮验证

- 最终 TypeScript 通过；治理文档单测 4 项通过；修改文件 `git diff --check` 通过（仅 CRLF 提示）。
- 1920 / 390 真实 API 回看：无 POST、pageerror、横向溢出；成果与两项下载入口可达。见 `outputs/demo1-calm-20261010/live-checks.json` 与 `live-*.png`。
- 报告 1920 / 1440 / 390：65 处链接 / 资源引用、三种证据状态、四张截图对照、两种流程切换、讲稿、弹窗和两段视频验证；无 HTTP 请求。详见报告 `report-checks.json`。已目视检查证据链桌面截图与两波协作移动截图。
- 首轮完整浏览器回归 153 通过 / 9 失败，记录 `outputs/demo1-calm-20261010/browser-first.xml`。3 项暴露代码成果自测卡不应随长说明折叠，已保留可见；4 项是新增测试错误假设旧 Fixture 只有一轮，改为按真实轮数断言；2 项是旧测试仍期待终态禁用按钮或未展开执行方式。
- 第一次定向回归 4 通过 / 5 失败，记录 `browser-targeted.xml`。自测展示与历史只读修复已通过；新增用例截图前切回页签的精确名称遗漏轮数，另一个旧用例仍未展开执行方式。修正定位与操作顺序后再跑完整回归，不修改服务端状态以迁就测试。
- 最终完整浏览器回归 **162 / 162 通过，0 跳过**，7.8 分钟，记录 `outputs/demo1-calm-20261010/browser-final.xml`。含新增四个桌面 / 手机、文件通过 / 失败用例，以及原证据核对、暂停恢复、Worker 确认、历史只读、六类事项和迟到响应。隔离端口 3011 / 8011；没有配置模型密钥。
- 本轮未重新执行 Provider、PostgreSQL 或真实外部业务，不声明用户可理解性提升或完整 Worker 人工恢复。

## 同日追加：实际改善前后

用户追问改善前后的效果。此追加只修改既有报告与核验脚本，不修改产品。
六例证据分级和字段映射见 [BEFORE-AFTER](../reports/september-progress-20261010/BEFORE-AFTER.md)。
重新运行四份定向 Runtime 验收：52 通过、0 失败、0 跳过；JUnit 在
`outputs/demo12-before-after-20261010/regression.xml`，不调用 Provider。
保存记录 JSON 审计通过；输出案例 instruction 逐字相同，2 文件变 0 文件；
同 UX 表 60/212 变 212/212；真实交接与父子保留字段吻合。没有运行旧 Git checkout。
追加后离线报告 1920 / 1440 / 390 全部通过：83 处页面链接 / 资源引用、六案例键盘开合、
逐例无溢出，原图片 / 流程 / 视频 / 讲稿功能仍通过。无脚本错误与 HTTP 请求。
目视复核改善章节桌面 / 手机截图。原 162 项产品浏览器结果没有在此次追加重新运行。
