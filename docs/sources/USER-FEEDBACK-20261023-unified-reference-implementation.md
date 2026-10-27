# USER-FEEDBACK-20261023-UNIFIED-REFERENCE-IMPLEMENTATION

日期：2026-10-23。类型：Stakeholder 直接授权、生成式设计参考与本地源码观察。

用户原话：

> 入口和ui要三个demo统一不要一个demo一个样，不能因为重点不同割裂开

> 可以啊，你就按这个来执行、来设计好吗？我觉得如果真能1:1高还原度把它设计成这样，那我觉得非常好了

支持在原 `/` 落地统一三栏、相同任务/依据/成果页签、真实来源和分工展示。允许旧界面存档后重构。
不支持伪造自动并发、源文件上传、隔离文件夹、模型调用或外部动作。单一用户的设计认可不是用户效果研究。

## 设计参考

主参考位于 `docs/design/unified-workbench-image2-20261023/`；18 状态扩展位于 `docs/design/unified-workbench-states-20261023/`。
均为设计图，不是已经实现的系统截图。来源生成信息与局限保留于各目录 README/brief/manifest。

| 文件 | SHA-256 |
| --- | --- |
| demo1-evidence.png | ebe662f9a350a3a4ae4e84f7d0d35d475228be114e44f121ae7a9af4fd26eaa3 |
| demo2-adaptive.png | 06ecaa001a50957893dcb75a26e5f72886a8db0d6783d41099bd9a7535d43ffa |
| demo3-judgment.png | 4ec66da2c48ab16bcfaa01bf0218e379cb03c03c6a93c00c13eea8b559d5ddb6 |

## 原实现边界

原 `HarnessWorkbench` 拥有请求代次、Task 当前指针、SSE 和版本化操作；`OfficeActionWorkbench` 拥有固定规则事项编辑与未知请求重试。
本轮保留这些机制。原 Demo2 只有单 Task 下的显式 Worker 派发，不是多任务无人参与调度。
本轮只实现设计的第一阶段；剩余状态必须继续新增服务端合同与独立验证，不能靠 UI 改名完成。
