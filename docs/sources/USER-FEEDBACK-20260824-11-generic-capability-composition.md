# Stakeholder feedback: generic capability composition

## Source metadata

- Source ID: `USER-FEEDBACK-20260824-CAPABILITY-COMPOSITION-11`
- Type: Stakeholder product and architecture feedback
- Date: 2026-08-24, Asia/Shanghai
- Owner: Office Agent project team
- Related decision: [DR-0019](../decisions/DR-0019-capability-composed-agent-runtime.md)
- Design reference: [`user-feedback-20260824-generic-capability-composition.png`](../evidence/assets/user-feedback-20260824-generic-capability-composition.png), `1270 x 365`, `60459` bytes, SHA-256 `D3984BCB4B25D86BFDB7CC87DED1E5AB859DA553E44A104DD68E3C22C4E33C79`

## Original feedback

> 1. demo1相关：demo1如图所示，相当于把单任务拆解，然后执行，遇到有问题或者需要人来核对的地方就停下，这是我的一个更清晰的想法
>
> 2. demo2相关：demo2突出的主要是多任务自组织执行，具体的你可以翻翻之前的资料
>
> 3. 我们的这个agent要更加通用而不是为了某个demo专门设计，应该是它本身就具备对应的能力，而不是说在某个demo演示的时候才具备这个能力

## Supported judgment

1. Demo 1 is an acceptance scenario for one decomposed task running through a bounded loop. Evidence conflict, uncertainty or a required human judgment pauses only the affected work before continuation.
2. Demo 2 is an acceptance scenario for multiple tasks or work units that organize, schedule, adapt and converge through shared artifacts.
3. Demo 3 is a cross-cutting risk and action-control layer, not a third bespoke task engine.
4. The product and API should describe generic task topology, orchestration and control requirements. Selecting a Demo must not inject capabilities that the Agent otherwise lacks.

## Limitations

This is one stakeholder's clarification of the intended product architecture, not a target-user study or runtime evidence. The attached image is a design reference from an earlier architecture view; it does not prove that bounded execution, adaptive scheduling, durable recovery or governed external actions are currently implemented.
