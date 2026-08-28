# DR-0045 TC-06 来源推导双岗位辅助筛选 Evidence

## 当前结论

`Limited Verified`。严格七份来源合同、两份 JD 条件解析、五份简历事实隔离、110 条四状态台账、来源变异、负向合同、隐私检查、三状态前台、真实 `deepseek-v4-pro` Run、三份下载物独立解析和 PostgreSQL 顺序恢复均已通过。实现由 [PR #61](https://github.com/Dickey007s/lenovo_agent/pull/61) 交付；远端门及合并状态以该 PR 的不可变记录为准，不在本文复制易漂移的瞬时状态。不把当前结论扩写为通用 ATS、正式招聘决定或公平性证明。

## 历史基线为何不足

历史 `_candidate_review` 保存固定姓名对应的岗位判断，再检查输出是否等于同一批答案。它没有从冻结 JD 与简历重新推导每条条件，来源中某一事实发生合法变化后，结论不会按影响范围变化；因此历史绿色只证明固定样本文字相互一致，不能证明真实岗位匹配效果。历史成果也只有两份固定段落 DOCX，没有联合逐条件台账、四状态、双来源位置、隐私扫描和失败 Verifier 前台。

## 来源推导与当前固定事实

- 来源合同只允许固定 `hr-001` 的两份 JD DOCX 与五份简历 PDF。逻辑 ID、文件名、展示路径、allowlist、大小和原始内容必须唯一；姓名与文件不一致、缺失/额外来源、同内容冒充、空或损坏文档均失败。
- 外卖商户 BD JD 动态解析为 14 条条件；文本评测 JD 动态解析为 8 条条件。五名候选人形成 110 条唯一岗位/候选人/条件记录。
- 当前动态结果为 `met=32`、`not_met=6`、`unverifiable=71`、`human_exception_required=1`。结果来自来源事实，不是前端或测试中的固定通过名单。
- 王琳达学历低于 BD 默认门槛，但 JD 明示“优秀者可放宽”，因此为人工例外；孙博文 AI 经历 8 个月低于当前 1 年门槛；周伦文本评测必要项有来源支持；赵晨曦明确“无”的能力可判不满足；未陈述事实保持资料不足。
- 三份成果均说明只是人工复核建议，不作录用或淘汰决定，也没有公平性、背景调查、身份核验、ATS 写入或通知动作。

## 可证伪门

- 把孙博文 AI 经历改为超过 1 年，只改变孙博文×文本评测相关条件和建议，其他候选与 BD 岗位不变。
- 把文本评测经验阈值合法改为 6 个月或 2 年，相关候选判断动态变化；移除王琳达来源 JD 的例外条款，其学历条件变为明确硬缺口。
- 去除李雨桐 BD 来源事实，只改变李雨桐 BD 支持项；周伦明确 Python/AI 为无时，相应文本评测条件变化；未陈述仍不被推断为否定。
- 姓名/身份字段串线、重复/缺/多来源、同内容冒充、空或损坏 PDF/DOCX、日期非法或倒置、学历/年限冲突全部 fail closed。
- 泄漏邮箱、手机号、地址、性别、年龄、民族、婚姻、籍贯、政治面貌或照片值，篡改 DOCX/CSV、缺行、重复行或写入旧固定名单，均使三份 Artifact 与 EffectReceipt 失败。
- E2E canonical fixture 直接来自服务端公开 manifest；另有孙博文 16 个月动态变体和强制 Verifier 失败，前台计数与颜色随服务端事实变化，不保留旧常量。

## 真实 Run 与下载复核

- Run：`harness:fa72afd2610040deba68671233936b47`；请求头 `X-User-Id: tc06-live-20260829`；幂等键 `tc06-live-source-derived-20260829-0001`。
- Planner `called=true/output_used=true/13602 ms`；Analyst `called=true/output_used=true/24881 ms`。确定性效果门 `11/11` 通过、`external_action=none`；模型回执与本地来源重算效果分开记录。
- Run 当前为 `waiting_input`，重启后 version `13`，有 3 个额外模型 Evidence Gap。三份确定性成果已经通过，但整个 Agent Control Loop 没有改写成 `completed`。
- [`tc06-live-source-derived-candidate-review-20260829.json`](manifests/tc06-live-source-derived-candidate-review-20260829.json) 记录下载与独立解析：BD DOCX `8` 张表、文本评测 DOCX `8` 张表、CSV `110` 行和 `110` 个唯一组合；两份报告均含五名候选人、人工决策边界、公平性边界与无外部动作边界。
- 三份下载 SHA-256：BD 报告 `07a9f003979a02ebf6833a1826bdd8dd04356bbb1072dcb486df5ef87c8a9ffe`，文本评测报告 `471baf69d224b7b020d80400b68fed26b095e4c4bc83efde339d0a05a49b936a`，联合台账 `17283e6fc1e5c673203ca96003d83193d725f150af68b15a32c24d08916aa20c`。
- 服务重启后 health 为 `deepseek-v4-pro + postgres`，同一 Owner 可读取 Snapshot、EffectReceipt、三份 Artifact 和 `candidate_review_outcome`；重启前后下载 SHA 一致。这只证明顺序 Runtime 的已提交恢复，不证明多实例 CAS、在途工具续跑或生产高可用。

## 前台与截图

- 首屏明确显示“这是人工复核建议，不是录用或淘汰决定”，并把确定性来源/成果检查、岗位匹配建议、最终 HR 待决拆为三个状态。
- 用户可按岗位和候选人展开，查看每条条件的 JD 位置、简历位置、来源事实、规则判断、面试或补证动作与退出条件；浏览器不重算匹配。
- [`tc06-ui-screenshots-20260829.json`](manifests/tc06-ui-screenshots-20260829.json) 记录普通 1440×1100 三栏和 390 px full-page 截图。左栏展开人力招聘的两份 JD 与五份简历；目录展开只是浏览器查看状态，不提交 `selected_file_refs`。
- 截图与自动化只证明被测 DOM、字号、几何和无横向溢出，不证明招聘人员理解、效率、信任或决策质量改善。

## 工程验证

- `uv run pytest -q`：`207 passed`；其中真实 PostgreSQL TC-06 顺序恢复定向门为 `1 passed, 6 deselected`。
- `uv run ruff check .`、`pnpm --dir apps/web lint`、`pnpm --dir apps/web build` 均通过。
- `pnpm --dir apps/web exec playwright test e2e/harness-workbench.spec.ts`：`46 passed`，包含 TC-06 canonical、孙博文来源变异和 Verifier failure 三条前台门。
- 隐私集成断言只扫描候选人成果、EffectReceipt 与 `candidate_review_outcome` 的公开投影；Run/Owner 随机标识不属于候选人内容，不能因偶然形成手机号样式而制造假红灯。完整公开 Snapshot 仍单独断言不含内部 `content_sha256`。

## 不能支持的结论

当前适配器不构成通用 ATS、正式录用或淘汰决定、公平性证明、背景调查、身份核验、候选人通知、生产多租户隔离、多 Worker 或 Connector。来源位置和四状态台账不证明简历陈述真实，也不证明任何候选人适合或不适合岗位；最终判断仍由 HR 复核。
