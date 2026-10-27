# DR-0076：Demo1 终态减法与证据 / 协作讲解

日期：2026-10-10。状态：Limited Verified，限定前台回归与离线汇报验证。前置 DR-0073 / 0074 / 0075。
来源：[用户反馈](../sources/USER-FEEDBACK-20261010-evidence-swarm-and-simple-ui.md)。
场景：[SCENARIO-063](../scenarios/SCENARIO-063-read-evidence-and-calm-task.md)。
验收：[Evidence](../evidence/DR-0076-CALM-EVIDENCE-20261010.md)。

## 场景与来源

原任务区重复展示单流程调度、终态禁用控件、单轮切换及通过文件的长解释。用户希望保持原入口而更简洁。
已有汇报没有讲清证据来自何处、谁生成位置以及多 Agent 交接的实际边界。
定位以 DR-0029 / 0036 与 Runtime resolver 为准，交接以 DR-0065 / 0066 与真实 9.21 Snapshot 为准。

## 前台交互影响

- 只在根工作区 compact 投影收起非协作、非历史只读的执行方式说明；协作派发确认和历史只读提示不收起。
- compact 终态不渲染原本均不可操作的 pause / stop / steer 控件；非终态可用控制保持原位置。预算停止后的续办不受影响。
- 只有一个轮次时省略无切换意义的页签；零轮启动提示、多轮历史切换和能力页完整记录保留。
- compact 中已通过、非财务特殊投影且无代码自测卡的文件，其用途 / 口径 / 复核长说明按需展开。失败处置、自测卡、业务结果面板、下载和所有待决保留。完整成果视图不收起这些说明。
- 预算从色块变为行内事实，执行区减少框线，成果按钮突出；窄屏自然换行，不缩小字体强行塞入。
- 原汇报新增证据捕获五步、真实锚点摘录、三种定位状态讲解、六步协作与实际两波记录。机制示意、真实记录、9.22 新协议严格分开。

## 后端事实映射

没有后端修改。折叠条件分别取 compact、readOnly、topology_admission.mode、TERMINAL_STATUSES、rounds.length、verifier_status 与 self_test。
展开不发 POST、不更改 SSE / 来源 / Budget / Branch。原权限、版本、幂等和恢复合同不变。
汇报摘录由脚本读取 9.21 保存的 Snapshot：Finding anchors、Branch depends_on、Contribution gate_status / input_contribution_ids。
证据位置不等于语义或业务正确；9.21 交接运行不证明 9.22 reviewed_handoffs_v1 真实闭环。

## 验证与边界

固定浏览器用例覆盖终态、失败、单 / 多轮、键盘展开、结果访问与无附加 POST；沿用全量回归检查等待 / 暂停 / Worker 派发 / 历史 / 原文核对。
只读回看已有真实 Run，不执行新模型任务；本轮不声称恢复闭环、协作优势、目标用户理解或生产安全得到验证。

## 汇报追加：改善前后

同日用户进一步要求具体前后例子。原 HTML 新增 #improvements，按输出约束、数字核对、材料覆盖、
贡献交接、局部恢复、交付 UI 六例展示；默认仅展开第一例。不同日期的旧实现不是统一旧版本。
每例标识真实历史 / 保存错误回放 / 受控恢复 / 同任务 UI，详见
[来源、字段、验收和边界](../reports/september-progress-20261010/BEFORE-AFTER.md)。
这次追加不修改产品代码，不重新调用 Provider；不把八月已有框架算作九月新增。
