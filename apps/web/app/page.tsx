"use client";

import {
  type CSSProperties,
  type KeyboardEvent,
  type PointerEvent as ReactPointerEvent,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  HarnessActivityPane,
  HarnessWorkbench,
  type HarnessActivityState,
} from "./harness-workbench";

const DESKTOP_AGENT_MIN = 300;
const DESKTOP_AGENT_MAX = 520;
const MOBILE_AGENT_MIN = 240;
const MOBILE_AGENT_MAX = 420;

function bounded(value: number, minimum: number, maximum: number) {
  return Math.min(maximum, Math.max(minimum, value));
}

export default function Page() {
  const shellRef = useRef<HTMLElement | null>(null);
  const [activity, setActivity] = useState<HarnessActivityState | null>(null);
  const [agentWidth, setAgentWidth] = useState(360);
  const [agentHeight, setAgentHeight] = useState(290);
  const [mobile, setMobile] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(max-width: 760px)");
    const update = () => setMobile(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  function startResize(event: ReactPointerEvent<HTMLDivElement>) {
    event.preventDefault();
    const startX = event.clientX;
    const startY = event.clientY;
    const startWidth = agentWidth;
    const startHeight = agentHeight;
    const isMobile = mobile;
    const previousCursor = document.body.style.cursor;
    const previousSelection = document.body.style.userSelect;
    document.body.style.cursor = isMobile ? "row-resize" : "col-resize";
    document.body.style.userSelect = "none";

    const move = (moveEvent: PointerEvent) => {
      if (isMobile) {
        const maximum = Math.min(MOBILE_AGENT_MAX, window.innerHeight * 0.48);
        setAgentHeight(bounded(startHeight + startY - moveEvent.clientY, MOBILE_AGENT_MIN, maximum));
      } else {
        const maximum = Math.min(DESKTOP_AGENT_MAX, window.innerWidth * 0.48);
        setAgentWidth(bounded(startWidth + startX - moveEvent.clientX, DESKTOP_AGENT_MIN, maximum));
      }
    };
    const stop = () => {
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousSelection;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
      window.removeEventListener("pointercancel", stop);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop, { once: true });
    window.addEventListener("pointercancel", stop, { once: true });
  }

  function resizeWithKeyboard(event: KeyboardEvent<HTMLDivElement>) {
    const step = event.shiftKey ? 40 : 20;
    if (mobile && ["ArrowUp", "ArrowDown"].includes(event.key)) {
      event.preventDefault();
      setAgentHeight((current) => bounded(current + (event.key === "ArrowUp" ? step : -step), MOBILE_AGENT_MIN, MOBILE_AGENT_MAX));
    }
    if (!mobile && ["ArrowLeft", "ArrowRight"].includes(event.key)) {
      event.preventDefault();
      setAgentWidth((current) => bounded(current + (event.key === "ArrowLeft" ? step : -step), DESKTOP_AGENT_MIN, DESKTOP_AGENT_MAX));
    }
  }

  const style = {
    "--harness-agent-width": `${agentWidth}px`,
    "--harness-agent-height": `${agentHeight}px`,
  } as CSSProperties;

  return (
    <main className="harness-app-shell" ref={shellRef} style={style}>
      <section className="harness-workspace-shell" aria-label="工作现场">
        <HarnessWorkbench onActivityChange={setActivity} />
      </section>
      <div
        className="harness-app-divider"
        role="separator"
        aria-label="调整 Agent 面板大小"
        aria-orientation={mobile ? "horizontal" : "vertical"}
        aria-valuemin={mobile ? MOBILE_AGENT_MIN : DESKTOP_AGENT_MIN}
        aria-valuemax={mobile ? MOBILE_AGENT_MAX : DESKTOP_AGENT_MAX}
        aria-valuenow={mobile ? agentHeight : agentWidth}
        tabIndex={0}
        onPointerDown={startResize}
        onKeyDown={resizeWithKeyboard}
      >
        <span aria-hidden="true">•••</span>
      </div>
      <aside className="harness-agent-shell" aria-label="Agent 进度">
        <HarnessActivityPane state={activity} />
      </aside>
    </main>
  );
}
