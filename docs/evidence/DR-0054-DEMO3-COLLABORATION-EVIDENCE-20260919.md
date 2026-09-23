# DR-0054 Demo3 协作方式运行证据

日期：2026-09-19。状态：Limited Verified，限固定规则、单进程测试记录与下述路径。实现基线为 `1276bc0` 后的本地未提交工作区；未创建 PR，未推送远端。

## 场景与来源

对应 [DR-0065](../decisions/DR-0065-demo3-editable-drafts-and-human-judgment.md)、[SCENARIO-052](../scenarios/SCENARIO-052-demo3-human-judgment-and-return.md)和[用户来源](../sources/USER-FEEDBACK-20260919-demo3-completion.md)。原 DR-0053 的五类事项在当前分支继续有效，新增材料对照人工判断、原位草稿编辑、最近事项找回、差异展示与人工处理说明下载。

## 运行结果

本机 uv 位于 `.venv/Scripts/uv.exe`，下列 Python 命令使用该可执行文件。Playwright 启动前将此 Scripts 目录加入当前测试进程 PATH，不改变系统 PATH；API 使用无模型 Key、无数据库的隔离测试配置。

| 检查 | 结果 | 范围 |
| --- | --- | --- |
| 既有事项单测 | 24 passed | 实现增量后先检查 DR-0053 基线 |
| `uv run pytest tests/unit/test_office_actions.py -q` | 39 passed | 新增 15 项含参数化负向测试 |
| `uv run pytest -q` | 405 passed, 13 skipped，391.87 秒 | 全库；13 项要求真实 PostgreSQL，未配置因此跳过 |
| 首次 `playwright test e2e/office-actions.spec.ts` | 8 passed，48.2 秒 | 真实 API 事项流程，不是静态 UI fixture |
| `playwright test e2e/harness-workbench.spec.ts e2e/office-actions.spec.ts` | 70 passed，约 3.5 分钟 | 62 项既有工作台回归 + 8 项真实 API 事项路径，Edge，单 Worker |
| `pnpm --dir apps/web build` | 通过 | Next.js 16.2.10 生产构建 |
| `uv run ruff check .` | 通过 | 全库 |
| `pnpm --dir apps/web lint` | 通过 | TypeScript |
| 文案修正后单测与治理检查 | 43 passed，1.38 秒 | 39 项事项 + 4 项 reporting governance |
| 草稿文案调整后浏览器复查 | 8 passed，48.2 秒 | 草稿状态文案与修订来源提示调整后的复查，截图同步刷新 |
| 最终定向单测与治理检查 | 91 passed，3.49 秒 | 事项、Runtime 与 reporting governance；覆盖判断完成说明和缺材料暂缓恢复修正 |
| 最终事项浏览器复查 | 9 passed，50.4 秒 | 新增暂缓后重开缺材料事项、补齐并修订的真实 API 路径；截图同步刷新 |
| 最终生产构建 | 通过 | 上述状态修正后的 Next.js 16.2.10 构建 |

完整全库结果对应主要实现；最后的状态修正由 91 项定向检查、9 项事项浏览器测试及生产构建复查。未将这些定向复查记作重新执行全库测试。

## 验证的用户路径与后端事实

草稿：原文摘录之后原位编辑，保存增加 action revision，preview 与 receipt.content 一致，source_excerpt 不变；history 保留修改前后的 content_snapshot。刷新仍显示已保存的人工修订。其它操作不能使用 edit_draft。

人工判断：两份材料均完整才进入 awaiting_decision，A/B 不预选，理由必填。普通 confirm、过期版本或缺材料不能形成判断；record_decision 生成 decision_note 并进入 decided。两份原文不变，模型调用数为零，没有新 Run 被自动启动。

找回：对照事项暂缓后办理另一件个人整理，再从当前 Owner 最近 20 个 Run 中选择原事项。GET 重开不执行动作，重新选择并填写理由才生成判断。单测确认 Owner 不同的列表不可见；复用 InMemory store 的重载保留暂缓内容和人工草稿，不等于真实 PostgreSQL 进程重启。

异常：原发件强确认、内容修改清空勾选、版本冲突、受限绕过、保存失败、重复点击、响应丢失后的同请求重放继续通过。新增命令不能通过附带另一类字段改变含义。

人工说明：受限或暂缓状态可下载说明，测试中观察到真实浏览器下载；没有审批、通知或外部执行回执。下载本身不代表有人接收。

## 页面检查

桌面按 1440×1000，手机按 390×844 验证。图片来自真实 API 的受控测试数据，不是真实企业操作。

- [草稿版本对照](screenshots/DR0054-draft-edit.png)：人工修订与原始文字分开，历史可核查。
- [桌面材料对照](screenshots/DR0054-human-judgment.png)：两份材料并排，状态与右侧轨迹一致。
- [桌面判断操作](screenshots/DR0054-human-controls.png)：选择后理由为空时按钮仍不可用，可修改、暂缓或取消。
- [手机材料判断](screenshots/DR0054-mobile-judgment.png)：两份材料纵向排列，主操作与暂缓入口可用；DOM 检查无页面横向溢出。

已打开检查截图。桌面中心为独立滚动区域，两张判断图展示不同滚动位置，不是全流程拼接。原 DR-0053 历史截图没有被本轮回归覆盖；其测试截图输出改至 outputs/playwright。

## 复查修正与局限

截图复查发现，通用结束文案“本次处理已停止”对可继续编辑的草稿不够准确，已改为“草稿已保存，可继续编辑”；服务端同时将编辑后的 mode 标为“人工修订草稿”。字段差异比较也修正为原目标值与当前目标值，避免把用户输入值与展示标签的差别误报为内容修改。

最后状态核对修正了两处问题：人工判断保存后，详情说明随结果更新，不再保留“尚未选择”；缺材料事项暂缓后重新打开，仍可编辑并补齐材料，不能绕过完整性检查直接记录判断。两条路径均有定向回归覆盖。

没有调用真实模型、读取 API Key 或执行企业业务。仍无生产身份、审批、连接器、多 Worker、跨设备身份、完整历史列表、通用敏感语义识别或模型冲突发现。未决请求仅保留在当前页面内存，关闭标签后的原请求恢复与跨协议版本幂等回执迁移未验证。

[设计方案与评审材料](../design/submission/Demo3设计方案与评审材料_v1.0.md)提供任务方案、边界对照、演示顺序和空白评审记录表。工程检查已执行，正式设计人员评审及目标用户研究尚未进行；不声称效率、理解或安全效果得到验证。
