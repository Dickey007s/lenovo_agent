# DR-0034-ONE-ACTION-RECOVERY-EVIDENCE-20260827

## 状态

`Limited Verified`。确定性浏览器回归、全量静态/构建门和真实 PostgreSQL 顺序回归支持本轮前台
事实投影；不升级为用户理解、业务价值、模型质量或新 Runtime 能力证据。

## 变更与可观察事实

- Branch 总览在同一组中区分“无需核对文件，建议重试”和“需要从 N 个原文位置中选 1 个”，
  并明确每次只处理一条，未选分支不启动也不消耗下一轮预算。
- 普通恢复首屏把唯一推荐动作写成“继续任务，只重试此分支”；文件修改和输入都不是前置条件。
  可选线索、停下原因、调用/采用回执和安全 Preview 默认折叠。
- ambiguous 首屏只解释人工判断的必要性、选择对象和局部恢复后果；未选择候选前 accept 禁用，
  没有默认候选或随机定位。
- terminal Run 明确改为新建独立任务，不向旧 Run 发送 resume；本轮没有修改服务端协议。
- 390 px 的长标题会收缩，关闭按钮和主次动作保持可见；测试同时检查页面和审查页无横向溢出。

## 证据账本

| Evidence | 结果 | 能证明 | 不能证明 |
| --- | --- | --- | --- |
| Stakeholder 两张负例截图 | 已登记 | 旧页面把两类人机任务混在一起，解释和输入压过下一步 | 新设计有效 |
| Python | `83 passed, 2 skipped` | 既有契约与 Runtime 单元回归未退化 | PostgreSQL 路径、前端理解 |
| PostgreSQL 顺序门 | `2 passed in 8.92s` | Decision/Resolution/Branch 局部恢复与重启路径未因前台改动退化 | CAS、多实例高可用 |
| Ruff / Web lint / build | 通过 | 静态检查、TypeScript 和生产构建成立 | 浏览器动作和用户效果 |
| Playwright | `25 passed` | retry/ambiguous 分流、默认折叠、禁用态、terminal 新 Run、关闭/重连和 390 px 回归成立 | 真实模型质量或用户理解 |
| `dr-0034-mixed-branch-actions-desktop.png` | 已捕获 | 一个分支组内的两类 Gate 和动作被明确区分 | 多 Worker 并行或任务完成 |
| `dr-0034-retry-action-mobile.png` | 已捕获 | 390 px 首屏可见唯一推荐重试动作、次动作和折叠入口 | 目标用户一定会点击正确 |
| `dr-0034-ambiguous-choice-mobile.png` | 已捕获 | 390 px 首屏解释为什么由人选择、选什么、选后发生什么，关闭按钮可见 | 候选蕴含 Finding 或选择正确 |

## 截图清单

| 文件 | 尺寸 / 字节 | SHA-256 |
| --- | --- | --- |
| `dr-0034-mixed-branch-actions-desktop.png` | `761 x 361` / `39457` | `8D1C1725B10C83D343CC5E82705E884CE3AE4D8FECC6EE989E318515C549B899` |
| `dr-0034-retry-action-mobile.png` | `390 x 844` / `39132` | `7F0459C82649EAB285884FDE38A50D42C5BE111364F5447557A54C1A7AEBC44B` |
| `dr-0034-ambiguous-choice-mobile.png` | `390 x 844` / `45953` | `EEAA848A3D478F187436B8DB3539B976AC5B3633821D550EBEB582FABEEECDFA` |

## 事实边界

- E2E 使用确定性 mock Snapshot 和请求记录，证明前后端字段映射，不是真实 Provider 运行。
- `EvidenceResolution` 仍只证明位置/成员关系，不证明语义蕴含、算术或完整性。
- retry 点击前不会调用模型；点击后的实际质量仍取决于 Provider 与下一轮可用资料。
- 当前仍没有可写 Office Artifact、Worker、Tool Gateway、Connector 或外部动作。
- 自动化和截图不是用户研究。“3 秒内知道点哪里”仍是待目标用户验证的产品假设。
