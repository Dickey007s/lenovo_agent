import { HarnessWorkbench } from "../harness-workbench";
import "./capabilities.css";

export default function AgentCapabilitiesPage() {
  return (
    <main className="agent-capabilities-page" data-testid="agent-capabilities-page">
      <HarnessWorkbench capabilitiesOnly />
    </main>
  );
}
