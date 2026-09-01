import { HarnessWorkbench } from "../harness-workbench";

export default function AgentCapabilitiesPage() {
  return (
    <main className="agent-capabilities-page" data-testid="agent-capabilities-page">
      <header className="agent-capabilities-header">
        <div className="agent-capabilities-title">
          <a className="agent-capabilities-back" href="/">返回工作现场</a>
          <span className="agent-capabilities-kicker">Agent 能力</span>
          <h1>Agent 能力工作台</h1>
          <p>用一份服务端状态，清晰查看工作进展、协作方式与可核对成果。</p>
        </div>
        <div className="agent-capabilities-boundary" role="note">
          <b>当前界面</b>
          <span>真实服务端状态驱动</span>
        </div>
      </header>
      <HarnessWorkbench capabilitiesOnly />
    </main>
  );
}
