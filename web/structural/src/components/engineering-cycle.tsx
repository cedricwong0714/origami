"use client";

import { useState } from "react";

const STAGES = ["design", "build", "test", "learn"] as const;
type StageId = (typeof STAGES)[number];

const CYCLES = [1, 2, 3, 4, 5] as const;

/** Design and Test use the orange accent. Build and Learn use the blue accent. */
const TONE: Record<StageId, string> = {
  design: "text-studio-accent",
  build: "text-studio-blue",
  test: "text-studio-accent",
  learn: "text-studio-blue",
};

export function EngineeringCycle() {
  const [stage, setStage] = useState<StageId>("learn");
  const [cycle, setCycle] = useState<(typeof CYCLES)[number]>(1);

  return (
    <div className="w-fit shrink-0 bg-transparent text-studio-foreground">
      <div className="grid grid-cols-[auto_4.75rem_auto] grid-rows-[auto_4.75rem_auto] items-center justify-items-center gap-x-3 gap-y-1 bg-transparent">
        <StageButton id="design" active={stage === "design"} className="col-start-2 row-start-1" onSelect={setStage} />
        <StageButton id="learn" active={stage === "learn"} className="col-start-1 row-start-2" onSelect={setStage} />
        <div className="col-start-2 row-start-2 flex size-[4.75rem] flex-col items-center justify-center gap-1 bg-transparent">
          <p className="text-[9px] leading-none tracking-[0.2em] text-studio-label uppercase">Cycle</p>
          <p className="text-[22px] leading-none font-light tabular-nums">{cycle}</p>
        </div>
        <StageButton id="build" active={stage === "build"} className="col-start-3 row-start-2" onSelect={setStage} />
        <StageButton id="test" active={stage === "test"} className="col-start-2 row-start-3" onSelect={setStage} />
      </div>
      <div className="mt-3 flex items-center justify-center gap-1.5 bg-transparent">
        <span className="mr-1 text-[11px] text-studio-label">Jump</span>
        {CYCLES.map((item) => {
          const on = item === cycle;
          return (
            <button
              key={item}
              type="button"
              aria-pressed={on}
              aria-label={`Jump to cycle ${item}`}
              onClick={() => setCycle(item)}
              className={
                on
                  ? "grid size-5 place-items-center bg-transparent text-[12px] leading-none font-medium tabular-nums text-studio-accent"
                  : "grid size-5 place-items-center bg-transparent text-[12px] leading-none tabular-nums text-studio-muted hover:text-studio-foreground"
              }
            >
              {item}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function StageButton({
  id,
  active,
  className,
  onSelect,
}: {
  id: StageId;
  active: boolean;
  className: string;
  onSelect: (id: StageId) => void;
}) {
  const label = id.charAt(0).toUpperCase() + id.slice(1);
  return (
    <button
      type="button"
      aria-pressed={active}
      aria-label={`${label} stage`}
      onClick={() => onSelect(id)}
      className={`bg-transparent text-[12px] leading-none whitespace-nowrap focus-visible:underline focus-visible:outline-none ${className} ${TONE[id]} ${
        active ? "font-medium" : "font-normal"
      }`}
    >
      {label}
    </button>
  );
}
