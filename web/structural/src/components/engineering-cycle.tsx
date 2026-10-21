"use client";

import { useState } from "react";

const STAGES = ["design", "build", "test", "learn"] as const;
type StageId = (typeof STAGES)[number];

const CYCLES = [1, 2, 3, 4, 5] as const;

const PLACE: Record<StageId, string> = {
  design: "top-0 left-1/2 -translate-x-1/2",
  build: "top-1/2 right-0 -translate-y-1/2",
  test: "bottom-0 left-1/2 -translate-x-1/2",
  learn: "top-1/2 left-0 -translate-y-1/2",
};

export function EngineeringCycle() {
  const [stage, setStage] = useState<StageId>("learn");
  const [cycle, setCycle] = useState<(typeof CYCLES)[number]>(1);

  return (
    <div className="w-52 shrink-0 text-studio-foreground">
      <div className="relative mx-auto h-44 w-44">
        <svg viewBox="0 0 176 176" className="absolute inset-3 h-[calc(100%-1.5rem)] w-[calc(100%-1.5rem)]" aria-hidden="true">
          <circle cx="88" cy="88" r="62" fill="none" stroke="currentColor" strokeWidth="1" className="text-studio-border" />
        </svg>
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-center">
          <div>
            <p className="text-[10px] tracking-[0.22em] text-studio-label uppercase">Cycle</p>
            <p className="mt-1 text-2xl leading-none font-light tabular-nums">{cycle}</p>
          </div>
        </div>
        {STAGES.map((id) => (
          <StageButton key={id} id={id} active={stage === id} className={PLACE[id]} onSelect={setStage} />
        ))}
      </div>
      <div className="mt-2 flex items-center justify-center gap-2">
        <span className="text-[10px] tracking-[0.18em] text-studio-label uppercase">Jump</span>
        {CYCLES.map((item) => {
          const on = item === cycle;
          return (
            <button
              key={item}
              type="button"
              aria-pressed={on}
              onClick={() => setCycle(item)}
              className={
                on
                  ? "text-[13px] text-studio-accent"
                  : "text-[13px] text-studio-muted hover:text-studio-foreground"
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
      onClick={() => onSelect(id)}
      className={`absolute bg-background px-1 text-[11px] tracking-[0.16em] uppercase ${className} ${
        active ? "text-studio-accent" : "text-studio-muted hover:text-studio-foreground"
      }`}
    >
      {label}
    </button>
  );
}
