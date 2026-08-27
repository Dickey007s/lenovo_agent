# SCENARIO-019：退出证据审查，并从分支路径继续

## 用户与触发

办公用户查看一条跨文件任务。Agent 已完成部分 Branch，另有三条路径停在 Evidence Gate；其中一条
quote 在日志中出现多次，需要用户确认真实位置。用户打开处置页后可能暂时不想决定，也可能遇到
Snapshot 已变化导致 defer 回执冲突。

## 主路径

1. Evidence Gap 区按 Branch 行展示：分支名称、当前材料、证据门原因和下一步。
2. 用户点击“确认原文位置”，比较真实候选与安全 Preview。
3. 用户关闭页面。浏览器立即返回 Loop，服务端同时写入 versioned `defer` 回执。
4. 分支行仍显示“需要你确认”，用户稍后可再次打开并 accept/decline/cancel。
5. accept 后只恢复绑定 Branch；其他 Branch 和已有 ArtifactVersion 保留。

## 异常路径

| 异常 | 前台反馈 | 后端事实与恢复 |
| --- | --- | --- |
| 顶层待决单存在、旧轮次没有副本 | 仍能显示候选和正确动作 | 从 Snapshot `decision_requests[]` 绑定 Resolution |
| 关闭时 expected version 已旧 | 页面仍关闭；主区提示暂缓回执未写入 | 409 后 GET 最新 Snapshot，待决单不被伪造为 deferred |
| 网络中断 | 页面仍关闭；显示控制命令失败 | 重连后 Snapshot 恢复开放待决项 |
| Gap 没有 Resolution | 分支行显示证据待补齐和“查看并处理” | 不显示候选选择，不伪造 Anchor |
| 终态 Run | 分支行显示“查看后创建新任务” | 不向旧 Run 发送 resume |

## 完成条件与边界

- 用户在任何回执状态下都能退出审查页；回执结果保持诚实可见。
- 每条 Gap 在点开前可回答“哪条分支、哪些材料、为何停下、下一步是什么”。
- 本场景不证明分支并行执行、Finding 正确、文件修改、外部动作或目标用户效率改善。
