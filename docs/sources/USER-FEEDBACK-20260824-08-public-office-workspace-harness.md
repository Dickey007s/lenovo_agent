# Stakeholder feedback: public office workspace and visible Agent Harness

## Source metadata

- Source ID: `USER-FEEDBACK-20260824-WORKSPACE-HARNESS-08`
- Type: Stakeholder product feedback
- Date: 2026-08-24, Asia/Shanghai
- Owner: Office Agent project team
- Related decision: `DR-0016`

## Original feedback

> 我还是觉得有问题，我们重新来设计一下：
>
> 我觉得一个导致演示很不顺利的原因是因为没有对应的数据（企业文件等），导致我看演示都很奇怪，我想你需要去寻找一些类似于一个真实办公场景的文件夹的这种数据集，然后设计一些符合demo1 2 3的示例，然后让我们的agent在这个文件夹数据集中进行演示。
>
> 你派个子agent去搜一下有没有相关的数据集，而不是自己构造。
>
> 好啊，那你继续执行吧，重新设计我们的系统和3个demo，重点体现前端和agent的harness设计，之前完全没这个感觉，就像写死的系统一样。

## Supported judgment

The next version must stop treating renamed fixtures as sufficient evidence. It should use traceable public benchmark input files as a read-only workspace, let one common Harness derive the plan and work graph from that workspace, and expose the actual file, model, tool, verification, control, and receipt facts in the frontend.

## Limitations

This is one stakeholder's direct product feedback. It does not prove that the proposed redesign improves task success, comprehension, trust, or efficiency. Public benchmark inputs are not Lenovo data, production enterprise data, or a real Connector.
