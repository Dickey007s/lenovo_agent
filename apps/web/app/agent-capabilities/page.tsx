import { HarnessWorkbench } from "../harness-workbench";

export default function AgentCapabilitiesPage() {
  return (
    <main className="agent-capabilities-page" data-testid="agent-capabilities-page">
      <header className="agent-capabilities-header">
        <div className="agent-capabilities-title">
          <a className="agent-capabilities-back" href="/">返回工作现场</a>
          <span className="agent-capabilities-kicker">Agent 能力</span>
          <h1>Agent 能力工作台</h1>
          <p>以同一份服务端 Snapshot 同时检视时间维执行事实与组织维编排事实。</p>
        </div>
        <div className="agent-capabilities-boundary" role="note">
          <b>当前界面</b>
          <span>真实 Run / Task / Snapshot 驱动</span>
        </div>
      </header>
      <nav className="agent-capability-nav" aria-label="Agent 能力维度">
        <a href="#control-loop"><b>A</b><span>Agent Control Loop</span><small>任务、Run、Round、Branch、证据与控制</small></a>
        <a href="#adaptive-swarm"><b>B</b><span>Adaptive Swarm</span><small>准入、WorkUnit、Worker、Contribution 与成果版本</small></a>
      </nav>
      <HarnessWorkbench capabilitiesOnly />
    </main>
  );
}
