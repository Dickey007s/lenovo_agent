# DR-0040 TC-02 真实项目有界 ReAct 控制结构 Evidence

## 结论

`Limited Verified`。修复后的固定 TC-02 纵切从 FORTE algorithm-013 复制完整真实项目，在隔离副本内改造主入口为有界、可插拔的 ReAct 控制结构，生成可下载 ZIP、diff、中文说明、自测卡和真实测试回执。一次真实 `deepseek-v4-pro` Run 的下载后独立内容门通过。默认策略仍确定性执行已规划工具；本证据不证明模型在副本内自主 ReAct，也不等于通用代码沙箱、自动 PR、生产网络隔离或任意仓库重构能力。

## 修复前红灯

- Run：`harness:b294f7feadd64c5196ce04982761b6b2`。
- 旧 ZIP 只有 9 个文件，包含自建 `react_agent.py` 与 8 项 unittest，但缺真实 `workflow.py` 和 `search_agent.log`；`config.py/llm.py/tools.py/main.py` 也不是对输入项目的保留与改造。
- 旧 Validator 的 7 项检查仅证明迷你包可编译运行和源码里出现若干类名。旧 manifest 把固定效果记为通过，这是验收定义不足的历史负例，不能支持“真实副本已重构”。
- 证据：[`tc02-live-baseline-mini-package-20260828.json`](manifests/tc02-live-baseline-mini-package-20260828.json)。

## 修复后真实运行

- Run：`harness:2a00cdea6c7848c8aede34b594470638`。
- 用户输入：`把搜索 Agent 从固定 Workflow 重构为带迭代上限和轨迹的 ReAct 结构。`
- Planner：`deepseek-v4-pro`，`called=true`、`output_used=true`、`20114 ms`。
- Analyst：`deepseek-v4-pro`，`called=true`、`output_used=true`、`31515 ms`。
- Run 状态：`waiting_input`、Snapshot v12；Artifact 效果门：通过。二者分开记录，等待 Evidence Gate 不抹去已验证成果。
- 两份 Artifact、每份 12 项检查，共 24 项；其中 `check-react-policy-boundary` 明确验证默认策略与可替换接口，不把外层模型回执算作包内策略。
- 原输入树前后 SHA-256 均为 `2c19e31a8e437f8ccb0ab811ba20a940f022a5bea69bcc750574d753f10a250d`。
- 服务本轮为 `checkpoint=memory/task_store=memory`，因此该 Run 不用于声称 PostgreSQL 重启恢复。
- 证据：[`tc02-live-real-project-refactor-20260828.json`](manifests/tc02-live-real-project-refactor-20260828.json)。

## 下载后独立内容门

- ZIP 有效，15 个文件，无缺失成员、路径穿越或 symlink。
- `workflow.py`、`llm.py`、`tools.py`、`requirements.txt`、`search_agent.log` 与冻结输入逐字一致。
- 独立临时目录编译退出码 0，125 ms；unittest 退出码 0，141 ms。
- 当前 20 个声明测试 ID 与实际执行集合一致，覆盖 1/20 边界、0/21 拒绝、正常 finish、达到上限、非法 action、未知 tool、真实 ToolRegistry、公开 action/observation 轨迹、漂移回退、质量降级、来源配额与句界截断。
- 新 `main.py` 使用 `ReActSearchAgent`，不再只调用 `SearchWorkflow`。

## 策略边界

- `DefaultReActPolicy` 确定性地依次选择 `selected_tools`，20 项测试中的 `test_default_policy_is_deterministic_and_replaceable` 验证了该行为和注入接口。
- `changes.json` 记录 `internal_action_policy=deterministic_default_with_injected_policy_interface` 与 `model_driven_internal_react_verified=false`。
- 外层真实 Planner/Analyst 只证明 Office Agent Run 使用了 `deepseek-v4-pro`；它们不是下载代码包内部的 action policy。
- 因此当前结论是“真实项目副本具有有界、可插拔 ReAct 控制结构”，而不是“模型已在副本内依据 Observation 自主决策”。

## 前台验证

- 服务端 Artifact 提供 `deliverable_type/key_outputs_label/self_test/review_guidance/execution_summary`；浏览器不从场景名猜事实。
- E2E 覆盖两类成果、隔离副本、文件变更、自测命令、失败信号、人工合并边界、下载文件名和 390 px 无横向溢出。
- 截图：`tc02-real-project-refactor-desktop.png`、`tc02-real-project-refactor-mobile.png`；尺寸、字节数和 SHA-256 见 [`tc02-ui-screenshots-20260828.json`](manifests/tc02-ui-screenshots-20260828.json)。截图证明被测渲染，不证明真实用户理解。

## 工程回归

- 全量 Python：`118 passed, 3 skipped in 37.14s`；三个 skip 是未向该通用命令注入 `TEST_DATABASE_DSN` 的 PostgreSQL 集成门。
- 真实 PostgreSQL 17.11 顺序 Runtime：单独注入本机临时 DSN 后 `3 passed in 22.91s`。该门回归 Snapshot、Artifact 与 Decision/Branch 恢复，不证明多实例并发或本次 live Run 使用了 PostgreSQL。
- Ruff：通过；Web TypeScript lint：通过；Next.js production build：通过。
- Playwright：`34 passed`，包括 TC-02 桌面/390 px、下载名、策略边界、自测卡和无页面级横向溢出。
- `git diff --check`：通过。远端 check、PR 与合并状态仍在收尾前保持待定。

## 网络与安全边界

本次固定 runner 只执行编译和 unittest，未调用网络或生产搜索，未安装依赖，且没有注入凭据和代理。它没有 OS 级 socket 隔离，因此不能写成“网络访问已从系统层禁用”，也不能当成任意代码的生产安全沙箱。

## 待收尾

本 Evidence 在 PR 合并前保持 `Limited Verified / local`。PR、远端 checks、合并 SHA、服务重启和最终存储后端将于收尾时追加；没有实际远端 check 时必须如实记录。
