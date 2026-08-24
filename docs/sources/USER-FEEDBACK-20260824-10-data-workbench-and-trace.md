# Stakeholder feedback: data workbench and verifiable Agent trace

## Source metadata

- Source ID: `USER-FEEDBACK-20260824-DATA-WORKBENCH-10`
- Type: Stakeholder product feedback
- Date: 2026-08-24, Asia/Shanghai
- Owner: Office Agent project team
- Related decision: [DR-0018](../decisions/DR-0018-forte-data-workbench-and-verifiable-trace.md)
- Screenshot: none

## Original feedback

> 1. 我觉得整个页面的文字太多了，让人找不到重点
>
> 2. 我觉得现在太刻意关注demo的展示了，我希望呢，要有一个空间我能自由的查看基准数据集中的数据，然后在能查看数据的同时，我自己也能下达一些指令，比如说要查一个什么数据或者完成一个什么任务，我作为用户能够有地方自己设定。同时呢，我能看到agent的执行路径，它做了什么，它尝试了什么，能看到轨迹。
>
> 先做这些

## Supported judgment

1. The default product should be a data workbench rather than a Demo-oriented explanation page.
2. The user needs to browse actual allowlisted FORTE file content, explicitly choose the files in scope, and enter a free-form office task.
3. The foreground should prioritize the data, task composer, result and a compact server-backed trajectory instead of long explanatory prose.
4. The trace should show meaningful steps, model-call receipts, validation and the final no-external-action boundary; it should not expose Prompt, chain of thought or raw internal logs.

## Limitations

This is one stakeholder's product feedback, not a target-user study. It supports the design direction and the need for a testable interaction slice, but does not prove that the resulting interface is easier to understand, more efficient, more trustworthy or more useful. There is no screenshot attached to this Source; visual implementation claims require separate Evidence.
