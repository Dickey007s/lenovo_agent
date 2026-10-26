# SCENARIO-072：在统一界面查看任务、依据与成果

| 字段 | 内容 |
| --- | --- |
| target user | 需要核对办公任务进展、原文与交付物的演示者和知识工作者 |
| trigger | 从一条办公目标开始，任务产生引用疑问或协作工作包 |
| current pain | 入口和视图分散；资料预览不等于结论依据；很难看懂调用与采用的区别 |
| goal | 在同一外壳中提交、查看依据、处理原有待决、读取成果 |
| completion condition | 入口切换不执行；引用与原文相符；候选不预选；协作派发仍受原授权控制 |
| happy path | 新任务输入 -> 原 POST /runs -> 查看任务 -> 依据页查看引用 -> 明确选择候选 -> 原局部恢复 -> 成果查看 |
| exception path | 历史只读；来源无锚点不假造；Worker 歧义无决定只看回执；请求未知保留原请求；修改清空旧确认 |
| source | USER-FEEDBACK-20261023-UNIFIED-REFERENCE-IMPLEMENTATION；生成参考图不是运行证据 |
| frontend impact | 三栏共用；依据默认展示原文引用；普通记录按需；小屏导航收起 |
| backend facts | 同一 Task/Run/Snapshot、Branch/Resolution、WorkUnit/Contribution 与 office_action；无新增 API |
| evidence status | Limited Verified；20项定向浏览器门，范围以 DR-0085 Evidence 为准 |

## 禁止推断

工作区页签不是隔离文件系统；最近20个 Run 不是批次调度；协调图不是分布式或全自动蜂群。
测试固定回执不是新模型运行，办公事项回执不是企业审批或外部发送。
