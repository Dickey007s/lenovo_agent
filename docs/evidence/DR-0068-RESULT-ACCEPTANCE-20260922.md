# DR-0068 Evidence：成果阅读与独立验收

2026-09-22；实现位于未提交工作树，HEAD `9a4bbbffe9d3477610718fbba8dae47749ac9aee`。
未提交、未建 PR；没有回滚此前工作。Decision/Scenario 为 Limited Verified，范围仅如下。

## 场景与来源

[Source](../sources/USER-FEEDBACK-20260922-result-acceptance.md)、
[Decision](../decisions/DR-0068-result-reading-and-independent-task-acceptance.md)、
[Scenario](../scenarios/SCENARIO-055-read-results-and-check-office-delivery.md)、
[简短报告](../reports/demo12-outcomes-20260922/README.md)。

本轮只是原系统成果密度与固定任务验收。财务用例在当前源码的临时 memory API 中真实启动，
跨领域同样真实启动并确认批准的只读波次；没有自动选择歧义证据，也没有外部业务动作。

## 前台交互与权威事实

修改 `apps/web/app/harness-workbench.tsx`、`styles.css` 及其浏览器用例。API/Runtime 不改。
保存记录、文件确定性验证、业务复核和 Run 状态分别展示。顶层 pending/deferred 决定优先于
旧嵌入 request；普通来源默认收起，所有需决定的发现不受前三条显示限制。
财务失败文件不折叠处置；通过文件仅折叠补充口径，不改变服务器计算或文件字节。

## 真实任务

| 任务 | Run | 实际调用 | 结果 |
| --- | --- | --- | --- |
| 财务 | `harness:be337dc6daee48a2b9c7b2482ca1fd91` | 2 | completed；3 文件独立核对通过；仍需财务处理 |
| 跨领域 | `harness:279ca084f42d46529421b99470e36417` | 6 | waiting_input；4 回执、2 采用；业务结论验收失败 |

两个任务分别限定 3 轮、12 次调用、600 秒 active time；使用已有 Provider 配置，没有增加
并发/预算上限。总计 8 次真实调用，不是零成本离线测试。每次启动、最终公共 Snapshot 和
回执保存在报告 `live/`，下载字节和大小/hash 一并保留。没有保存私有 Prompt、CoT 或密钥。

独立财务脚本 `scripts/audit_finance_delivery.py` 用 bundled Python 的 openpyxl 与 Decimal，
逐行校验金额、方向、来源 ref/位置、排序、期间覆盖和三期候选；不调用生产 adapter。原始
96 input 均匹配 pinned manifest。更新回执后的金额/locator/缺行三个篡改副本也被拒绝。

跨领域 [内容审计](../reports/demo12-outcomes-20260922/swarm-content-audit.md) 保留两个已采用
数字错误、未采用下游的规则口径问题、截断输入和等待状态。这不是完成的协作任务；没有用
“位置校验通过”代替算术/语义正确。没有把候选选择默认为同意来强行跑完。

## 工程门

| 门 | 结果与回执 |
| --- | --- |
| 定向浏览器开发门 | 11 passed，`browser-targeted.xml`；发生在财务文件密度二次调整之前 |
| 受控 Runtime/API | 49 passed，`runtime-acceptance.xml`；无 Provider/PG；含新增 stop + HTTP continue，不手工植入历史 |
| 独立财务下载核对 | passed；31/2 行、金额 3,984,606.46 / 4,992,891.47；三期候选 0；3 个篡改负例拒绝 |
| 当前生产构建 | passed，`build.txt`；包含本轮 UI 代码 |
| 首次全部浏览器 | 118 passed / 4 failed，`browser-full.xml` / `.txt`，完整保留失败 |
| 第二次原系统浏览器 | 116 passed / 1 failed，`browser-product-final.xml` / `.txt`；保留这份曾拟作为 final 的失败回执 |
| 最终原系统浏览器 | 117 passed，`browser-product-verified.xml` / `.txt`，4.1 分钟；仅原产品，不含旧独立报告页 |
| 最终 TypeScript | 配置恢复到本轮之前的 include 后 `pnpm exec tsc --noEmit` 通过，`typecheck.txt` |
| 汇报治理 | 4 passed，`reporting-governance.xml` |
| Python 静态检查 | `ruff check scripts/audit_finance_delivery.py tests/acceptance/test_demo12_reviewed_collaboration.py` 通过 |

首轮两个产品测试失败：恢复版本仍断言旧标题；新财务断言误把混合 fixture 中另外两份通过
文件的详情也要求消失。已改为检查新的中性标题，以及只对真实失败文件验证提示可见，未删
恢复命令/历史断言，未减弱失败字段检查。

第二轮发现新测试选择器把财务总览的红色状态行误当成失败文件卡；已改为只选择直接文件列表
的失败项，再全量跑完 117 项。没有删除失败提示的可见性断言，也没有修改 Snapshot fixture
以迎合测试。所有尝试各自保留，不覆盖失败 XML。

另两个失败在旧独立 `copilot-boundary-design-20260911` 报告页：桌面旧文案断言“引导后样本”
与实际“完成引导后”不符；手机程序选择情境后焦点断言失败。该 HTML/测试不在本轮原系统
改动范围，未为凑总绿灯修改或跳过。不能将整库浏览器套件汇报为全通过。

## 截图、服务与限制

`capture_demo12_live.cjs` 原接口取真实 Run，四组页面均在 1920/390 宽检查无水平溢出、无
pageerror、刷新仍能取回当前 Run、浏览截图 POST 为 0。完整截图展开内部滚动容器，原视口
图同时保留。`result-*` 为受控 fixture，不能作为真实 Provider 业务成果证明。

临时 3022/8022 服务已退出；原 8010 未重启，常驻 3000 未恢复。最终 Playwright 使用自己
的 3011/8011，也已随测试退出；最终端口核对仅保留旧 8010。memory 记录已保存为本轮文件，
不能声称它们跨服务重启恢复。

无新 PG 门、无真人理解试验、无付费额度统计、无跨供应商重复试验、无蜂群收益比较。
本轮交付不包含解决任意文本语义错误、完成 Demo3 或生产上线。
