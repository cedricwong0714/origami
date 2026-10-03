"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { StudioNav } from "@/components/studio-nav";

type Deps = {
  version: string;
  calibrated: false;
  no_lab_data: string[];
  needs_lab_data: string[];
  team_dry_lab: string[];
  out_of_scope: string[];
};

type ConfigMeta = {
  placeholders_unmeasured: string[];
  config: { version: string };
};

export function GuideBoard() {
  const [deps, setDeps] = useState<Deps | null>(null);
  const [cfg, setCfg] = useState<ConfigMeta | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/api/meta/dependencies").then((r) => r.json()),
      fetch("/api/meta/active-learning-config").then((r) => r.json()),
    ])
      .then(([d, c]) => {
        setDeps(d as Deps);
        setCfg(c as ConfigMeta);
      })
      .catch(() => setError("Could not load metadata. Is the API running on port 41287?"));
  }, []);

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 font-[family-name:var(--font-inter)] text-[#242220]">
      <StudioNav />
      <header className="mb-8">
        <p className="text-sm uppercase tracking-wide text-[#8A8278]">Handoff</p>
        <h1 className="mt-1 text-3xl font-semibold">Data dependencies</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
          A repeat count is scored with the deposited CTPR screw, a Phillips lookup that
          does not blend series, a Cα clash calculation, and kinetics only when the
          concentrations or a named prior are explicit. Surrogate luminescence does not
          edit those outputs. It is a separate Gaussian process: dry scores and wet
          readouts are different fidelities, and a pass uses a threshold marked unmeasured
          until a plate-reader CV exists.{" "}
          <code className="rounded bg-[#F5F0E8] px-1">calibrated = false</code>. Empty lab
          fields stay empty. A recommendation is the next well, not a validated construct.
        </p>
      </header>
      {error ? <p className="text-sm text-red-800">{error}</p> : null}
      {deps ? (
        <div className="space-y-6 text-sm leading-relaxed">
          <ListBlock title="Built without wet-lab data" items={deps.no_lab_data} />
          <ListBlock title="Waiting on lab measurements" items={deps.needs_lab_data} />
          <ListBlock title="Your dry-lab inputs" items={deps.team_dry_lab} />
          <ListBlock title="Out of scope" items={deps.out_of_scope} />
        </div>
      ) : null}
      {cfg ? (
        <section className="mt-8 rounded-xl border border-[#E3D9CC] bg-white p-5 text-sm">
          <h2 className="text-lg font-semibold">Active-learning placeholders</h2>
          <p className="mt-2 text-[#5C564E]">
            Config {cfg.config.version}. Unmeasured:{" "}
            {cfg.placeholders_unmeasured.length
              ? cfg.placeholders_unmeasured.join(", ")
              : "none"}
            .
          </p>
          <p className="mt-2">
            <Link className="underline" href="/ssdk">
              SSDK gates
            </Link>{" "}
            ·{" "}
            <Link className="underline" href="/intake">
              Plate intake
            </Link>{" "}
            ·{" "}
            <Link className="underline" href="/learn">
              Active learning
            </Link>
          </p>
        </section>
      ) : null}
    </main>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-xl border border-[#E3D9CC] bg-[#FBF8F3] p-5">
      <h2 className="text-lg font-semibold">{title}</h2>
      <ul className="mt-2 list-disc pl-5 text-[#5C564E]">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
