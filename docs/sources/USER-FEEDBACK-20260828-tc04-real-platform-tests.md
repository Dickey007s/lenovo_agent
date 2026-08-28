# 用户反馈：TC-04 必须测试真实评测平台而不是替身函数

## 来源

- Source ID：`USER-FEEDBACK-20260828-TC04-REAL-PLATFORM-TESTS`
- 类型：Stakeholder 场景验收、源码审计与前台可理解性反馈
- 日期：2026-08-28，Asia/Shanghai
- 关联：`DR-0041`、`SCENARIO-027`、TC-04

## 用户要求

用户要求以原始指令“为评测平台补充单元测试，覆盖 Service、执行引擎和工具类；真实运行测试，修复失败，并给出覆盖率与修改文件。”运行真实 `deepseek-v4-pro`。Agent 必须把 FORTE dev-015 的完整 `input/source-code` 复制到隔离 Run Workspace，在真实模块上先复现失败、再修复并复跑；下载 ZIP 后还要独立解压、编译和执行同一测试命令。

测试不能继续调用另造的 `contracts.py`。必须直接导入真实 `app.services.*`、`app.engine.evaluation_engine` 和 `app.utils.*`，覆盖模型 Service、数据集 Service、实验 Service、执行引擎、工具与事务五类对象。真实任务要求不少于 100 项测试；参数化可以复用结构，但每个 case 必须具有不同输入和业务断言，声明 ID、实际 collected ID 与前台公开 ID 必须是同一集合。

前台不能只显示“117 项通过”。普通用户应直接看到五类 suite、真实测试文件和 15/16/15/23/48 的数量；每类可以展开查看真实测试名称，完整清单仍可在 ZIP 的 `test-manifest.json` 中核对。长 ID 采用内部滚动，不把页面撑宽，也不能回到 9px 字号。

后续真实运行又暴露出一个 P0 交互负例：TC-04 builder 在 API 进程事件循环内同步执行约 60 秒，期间用户无法继续读取 Run Snapshot、SSE 或 health。把客户端单次等待从 30 秒改到 180 秒只会掩盖阻塞，不能让用户看到进展。服务端必须先冻结本轮 allowlisted bytes，再把固定 builder 和子进程测试移到受控工作线程；前台至少看到“正在复制并运行真实测试”以及完成或失败的有序事实，不显示虚构百分比。

## 两层触发负例

1. 历史 Run `harness:e80512fed92245d79fe24031954927a5` 生成 105 项绿色测试，但 ZIP 只有自建 `contracts.py`、一个动态测试文件和三份 patch。它没有完整真实工程，覆盖率只统计替身模块，因此属于 false green。
2. 新验收必须在完整未修复副本上运行同一套真实测试。三处缺陷对应的目标测试若没有先红灯，即使修复后全绿也不能证明回归测试抓住了缺陷。

## 支持的判断

- TC-04 的效果门必须同时检查完整副本、真实模块导入、修复前红灯、真实 diff、测试 ID 集合、逐文件覆盖率、下载后复跑和原输入只读。
- 两份 Artifact 可以共享同一组服务端检查；Run 汇总按 `check_id` 去重，不能把同一清单乘二。
- 44 个源码文件都是成果内容来源，Artifact/EffectReceipt 协议必须能够无截断地公开全部 `file_ref`。
- 三份变更源码各自语句覆盖率必须不低于 80%；选定 Service/Engine/Utils 的汇总覆盖率另列，不能替代逐文件门。
- 长耗时确定性效果不能占住 FastAPI 主事件循环；用户等待时仍应能查看资料、Run Snapshot 和 SSE。该改动只证明单进程 API 响应性，不等于多 Worker、可恢复 Tool Gateway 或跨进程续跑子进程。

## 不能支持的判断

- 固定 dev-015 适配器不证明任意仓库测试、通用代码执行沙箱、自动 PR 或生产外部 HTTP 集成。
- Python 进程内阻断非 loopback `socket.connect` 不是 OS 级断网；测试只证明本轮没有调用真实模型 endpoint，且 HTTP 使用 Mock。
- 单一 Stakeholder 反馈和自动化截图不证明真实用户理解、效率、信任或业务价值提高。
