# DR-0081 验证记录

日期：2026-10-22。基于既有未提交工作树继续；未提交、未推送、未重置其他修改。
状态：Limited Verified，限定本记录列明的前端和报告验证。

## 范围

修改原 harness-workbench.tsx 与 styles.css 的根页投影，不修改 Runtime/API 或 Demo3。
截图来自真实前端加受控 API Snapshot，不调用付费模型，不冒充真实办公任务运行。
本轮主流程截图与机器回执输出到 `outputs/task-overview-20261022`，不覆盖先前报告图片。
旧整合测试最初仍写入历史 outputs 缓存目录，已补环境变量重定向；不改过去报告附件。

## 初步检查

- 初版新增 4 项测试：2 项通过，2 项失败。失败原因是折叠判断把历史已解决缺口也当成当前阻塞。
  修正为全部当前 Branch/开放决定，加所选轮次的缺口、覆盖与延后要求。未放松待办或风险检查。
- 修正后的 12 项定向测试通过，含等待/完成、桌面/手机、失败文件、键盘与原结果入口。
- 后续调整桌面业务结论与文件并列、任务设置同行。第一次组合门为 151 passed / 1 failed；
  旧测试直接点击已折叠轮次而超时。补上展开操作后保留原断言，不绕过行为验证。
- 增加两项负向测试：成功状态但存在受限输入或轮次级开放决定时，记录不得折叠。
  判断同时覆盖 Run/轮次决定与未解决定位，不只检查 Run 顶层决定列表。
- 最终组合门：154 passed，0 failed，0 skipped，424.036 秒。146 项 harness-workbench + 8 项 office-integration。
  机器回执：`outputs/task-overview-20261022/regression.xml`；首次失败回执另存 `regression-initial.xml`。
- TypeScript 检查通过；治理文档单测 4 passed。本轮未执行全部后端或所有浏览器测试文件。
- 独立目录 `.next-ui-refinement-build` 的 Next.js production webpack build 通过。
  构建自动添加的 tsconfig 路径已还原，未留下无关配置修改。
- 整合测试截图路径改为当前输出目录后，单独重跑 8 项通过；不与 154 项加总。
- HTML 报告在 1440/390 px 均无横向溢出，2 张内嵌图片加载、6 个本地链接可达、无页面错误。
  回执为 `outputs/task-overview-20261022/report-checks.json`。
- `http://localhost:3000/` 原系统入口与 `8000/v1/health` 均返回 200；空白任务页查看零 POST。
  继续使用原先 memory 预览服务，模型访问关闭，不冒充真实任务执行验收。

## 截图与走查

- 最终主流程图片：`screenshots/6385-root-terminal-false-1920.png` 与 `...-390.png`。
  同一发布复核受控状态；桌面并列结论和下载，手机顺序排列。
- `screenshots/5737-delivery-overview-1672.png` 检查独立文件入口、键盘展开、公式查看和零额外 POST。
- `screenshots/5776-pending-overview-1672.png` / `...-390.png` 验证当前轮外待办与超过前三项的未完成项。
  截图中另展开已完成项，用于核对保留事实，不代表默认全部展开。
- 开发者逐图查看了桌面/手机输出。截图不证明用户理解或所有内容组合无溢出。
- 对照报告：`docs/reports/task-overview-20261022/index.html`；不是新的产品入口。

## 不证明

不是目标用户实验，不证明效率改善、模型质量、业务批准、完整下游人工恢复或生产就绪。
