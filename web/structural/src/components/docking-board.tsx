"use client";

import { useState } from "react";
import { StudioNav } from "@/components/studio-nav";
import { PageGuide } from "@/components/page-guide";

type AffinityReport = {
  n_repeats: number;
  indices: number[];
  chord_A: number;
  c_eff_M: number;
  kd_M: number;
  ka_per_M: number;
  conversion: string;
  association_theta: number;
  association_holds: boolean;
  nanobit_theta: number | null;
  nanobit_printed_kd_M: number | null;
  drives_lgbit_smbit: boolean;
  spy_half_life_s: number | null;
  spy_half_life_note: string | null;
  spy_k_obs_per_s: number | null;
  drives_spycatcher_spytag: boolean;
  p_clash: number | null;
  radii_A: number[];
  radius_origin: string;
  criterion: string;
  verdict: string;
  calibrated: boolean;
};

type GeometryReport = {
  calibrated: boolean;
  radius_origin: string;
  docking: {
    n_repeats: number;
    indices: number[];
    chord_A: number;
    chord_95_low_A: number;
    chord_95_high_A: number;
    c_eff_M?: number;
    p_clash?: number;
    radii_A?: number[];
    clash_computable: boolean;
  };
};

function sci(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return value.toExponential(3);
}

function ConcentrationRuler({
  cEff,
  kd,
  nanoKd,
}: {
  cEff: number;
  kd: number;
  nanoKd: number | null;
}) {
  const marks = [
    { label: "Local concentration", value: cEff, color: "#C45C12" },
    { label: "Your Kd", value: kd, color: "var(--studio-foreground)" },
    ...(nanoKd !== null && nanoKd > 0
      ? [{ label: "LgBiT–SmBiT Kd", value: nanoKd, color: "#266FB1" }]
      : []),
  ].filter((mark) => mark.value > 0);
  if (marks.length < 2) return null;
  const logs = marks.map((mark) => Math.log10(mark.value));
  const min = Math.min(...logs) - 0.4;
  const max = Math.max(...logs) + 0.4;
  const span = max - min || 1;
  const width = 640;
  const height = 96;
  const xOf = (value: number) => 16 + ((Math.log10(value) - min) / span) * (width - 32);
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="mt-4 h-auto w-full" role="img" aria-label="Log concentration comparison of local concentration, your Kd, and the LgBiT–SmBiT Kd">
      <line x1={16} x2={width - 16} y1={36} y2={36} stroke="var(--studio-chart-grid)" />
      {marks.map((mark) => (
        <g key={mark.label}>
          <circle cx={xOf(mark.value)} cy={36} r={6} fill={mark.color} />
          <text x={xOf(mark.value)} y={18} fill={mark.color} fontSize="11" textAnchor="middle">
            {mark.label}
          </text>
          <text x={xOf(mark.value)} y={78} fill="var(--studio-muted)" fontSize="11" textAnchor="middle">
            {mark.value.toExponential(1)} M
          </text>
        </g>
      ))}
    </svg>
  );
}

function downloadJson(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function DockingBoard({ pane }: { pane: "affinity" | "geometry" }) {
  const [n, setN] = useState(8);
  const [kind, setKind] = useState<"kd" | "ka">("kd");
  const [value, setValue] = useState("0.19");
  const [unit, setUnit] = useState("nM");
  const [affinity, setAffinity] = useState<AffinityReport | null>(null);
  const [geometry, setGeometry] = useState<GeometryReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function runAffinity() {
    setError(null);
    const parsed = Number(value);
    if (!Number.isInteger(n) || n < 3 || n > 24) {
      setError("Repeat count must be an integer from 3 to 24.");
      return;
    }
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setError("Type a finite affinity greater than zero.");
      return;
    }
    setRunning(true);
    try {
      const res = await fetch("/api/docking/affinity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          n_repeats: n,
          affinity: kind,
          value: parsed,
          unit,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "Affinity check failed.");
      }
      setAffinity(data as AffinityReport);
    } catch (err: unknown) {
      setAffinity(null);
      setError(err instanceof Error ? err.message : "Affinity check failed.");
    } finally {
      setRunning(false);
    }
  }

  async function runGeometry() {
    setError(null);
    if (!Number.isInteger(n) || n < 3 || n > 24) {
      setError("Repeat count must be an integer from 3 to 24.");
      return;
    }
    setRunning(true);
    try {
      const res = await fetch(`/api/docking/geometry?n=${n}`);
      const data = await res.json();
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "Geometry request failed.");
      }
      setGeometry(data as GeometryReport);
    } catch (err: unknown) {
      setGeometry(null);
      setError(err instanceof Error ? err.message : "Geometry request failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 text-studio-foreground">
      <StudioNav />
      <p className="text-[11px] font-semibold tracking-[0.22em] text-studio-accent uppercase">
        Docking verification
      </p>
      <h1 className="mt-2 text-3xl font-semibold">
        {pane === "affinity" ? "Will this Kd hold the two ends together?" : "How far apart are the ends?"}
      </h1>
      {pane === "affinity" ? (
        <PageGuide
          intro="This page checks one scaffold length and one Kd or Ka. Use it when you already have a length in mind and want to know if the sensor is tight enough."
          steps={[
            "Type a repeat count from 3 to 24.",
            "Pick Kd or Ka, then type the value and the unit.",
            "Click Run.",
            "Read the verdict, then the ruler under it.",
          ]}
          read={[
            "Local concentration is how crowded the two ends are on this scaffold. It comes from the screw distance and the payload sizes.",
            "Bound fraction is local concentration divided by local concentration plus your Kd. 0.5 means half the pairs are together.",
            "LgBiT–SmBiT occupancy uses the published reporter Kd at that same local concentration. Near zero means the reporter stays off.",
            "Spy half-life is how long the covalent lock takes at that concentration. Clash is the chance the two spheres overlap.",
          ]}
          rules={[
            "The ends hold when your Kd is at or below the local concentration.",
            "The reporter is driven only if the ends hold and its occupancy is at least 0.5.",
            "The Spy lock is scored only when the ends hold.",
          ]}
          next={[
            "If the ends do not hold, try a tighter Kd or a shorter length.",
            "If the ends hold but the reporter stays off, binding is fine and the reporter Kd is the limit. Try Choose a length to see whether another repeat count turns NanoBiT on.",
          ]}
        />
      ) : (
        <PageGuide
          intro="This page shows the straight-line distance between the two docking sites, and whether the payloads are likely to bump into each other."
          steps={[
            "Type a repeat count from 3 to 24.",
            "Click Run.",
            "Read the chord, the clash chance, and the local concentration.",
          ]}
          read={[
            "The chord is the straight-line distance between the two sites, in angstroms.",
            "The blue segment is the low end of the 95% range up to that distance.",
            "Local concentration falls as the chord gets longer. Clash near zero means the spheres barely overlap.",
          ]}
          rules={[
            "Radii are the deposited SpyCatcher and LgBiT sizes.",
            "A missing radius would stop the clash calculation. These defaults are filled in.",
          ]}
          next={[
            "Take a chord that looks usable into the affinity check on the other docking tab.",
          ]}
        />
      )}

      <section className="mt-8 rounded-2xl border border-studio-border bg-studio-card p-6">
        <label className="block text-sm font-medium">
          Repeat count (3–24)
          <input
            className="mt-1 w-32 rounded-lg border border-studio-border px-3 py-2"
            type="number"
            min={3}
            max={24}
            value={n}
            onChange={(event) => setN(Number(event.target.value))}
          />
        </label>
        {pane === "affinity" ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <label className="block text-sm font-medium">
              Constant
              <select
                className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2"
                value={kind}
                onChange={(event) => setKind(event.target.value === "ka" ? "ka" : "kd")}
              >
                <option value="kd">Dissociation, Kd</option>
                <option value="ka">Association, Ka</option>
              </select>
            </label>
            <label className="block text-sm font-medium">
              Value
              <input
                className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2 font-mono"
                value={value}
                onChange={(event) => setValue(event.target.value)}
              />
            </label>
            <label className="block text-sm font-medium">
              Unit
              <select
                className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2"
                value={unit}
                onChange={(event) => setUnit(event.target.value)}
              >
                {["M", "mM", "uM", "nM", "pM"].map((item) => (
                  <option key={item} value={item}>
                    {kind === "ka" ? `per ${item}` : item}
                  </option>
                ))}
              </select>
            </label>
          </div>
        ) : null}
        <button
          type="button"
          className="mt-5 rounded-full bg-studio-button px-5 py-2 text-sm text-studio-button-text disabled:opacity-50"
          onClick={() => void (pane === "affinity" ? runAffinity() : runGeometry())}
          disabled={running}
        >
          {running ? "Running…" : "Run"}
        </button>
        {error ? <p className="mt-4 text-sm text-destructive">{error}</p> : null}
      </section>

      {affinity && pane === "affinity" ? (
        <section className="mt-6 rounded-2xl border border-studio-border bg-studio-card p-6">
          <h2 className="text-lg font-medium">
            {affinity.association_holds ? "Holds together" : "Does not hold together"}
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-studio-muted">{affinity.verdict}</p>
          <ConcentrationRuler
            cEff={affinity.c_eff_M}
            kd={affinity.kd_M}
            nanoKd={affinity.nanobit_printed_kd_M}
          />
          <p className="mt-2 text-sm text-studio-muted">
            On this log scale, your Kd has to sit at or left of the local concentration. The reporter Kd is usually far to the right, which is why occupancy stays low.
          </p>
          <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-studio-label">Bound fraction</dt>
              <dd className="font-mono text-lg">{affinity.association_theta.toFixed(3)}</dd>
            </div>
            <div>
              <dt className="text-studio-label">Kd used</dt>
              <dd className="font-mono">{sci(affinity.kd_M)} M</dd>
            </div>
            <div>
              <dt className="text-studio-label">Local concentration</dt>
              <dd className="font-mono">{sci(affinity.c_eff_M)} M</dd>
            </div>
            <div>
              <dt className="text-studio-label">End chord</dt>
              <dd className="font-mono">{affinity.chord_A.toFixed(2)} Å</dd>
            </div>
            <div>
              <dt className="text-studio-label">LgBiT–SmBiT occupancy</dt>
              <dd className="font-mono">
                {sci(affinity.nanobit_theta)}{" "}
                {affinity.drives_lgbit_smbit ? "at or above one half" : "below one half"}
              </dd>
            </div>
            <div>
              <dt className="text-studio-label">SpyCatcher–SpyTag</dt>
              <dd className="font-mono">
                k_obs {sci(affinity.spy_k_obs_per_s)} /s, half-life {sci(affinity.spy_half_life_s)} s
              </dd>
            </div>
          </dl>
          {affinity.spy_half_life_note ? (
            <p className="mt-4 text-sm text-studio-muted">{affinity.spy_half_life_note}</p>
          ) : null}
          <p className="mt-4 text-sm text-studio-muted">{affinity.criterion}</p>
          <p className="mt-2 text-sm text-studio-muted">{affinity.conversion}</p>
          <button
            type="button"
            className="mt-4 rounded-full border border-studio-border px-4 py-2 text-sm"
            onClick={() => downloadJson(`origami-docking-n${affinity.n_repeats}.json`, affinity)}
          >
            Download summary file
          </button>
        </section>
      ) : null}

      {geometry && pane === "geometry" ? (
        <section className="mt-6 rounded-2xl border border-studio-border bg-studio-card p-6">
          <h2 className="text-lg font-medium">n = {geometry.docking.n_repeats}</h2>
          <svg viewBox="0 0 640 72" className="mt-3 h-auto w-full" role="img" aria-label="Chord and its 95% band">
            <line x1={40} x2={600} y1={28} y2={28} stroke="var(--studio-chart-grid)" />
            <line
              x1={40 + (geometry.docking.chord_95_low_A / Math.max(geometry.docking.chord_95_high_A, 1)) * 520}
              x2={40 + (geometry.docking.chord_A / Math.max(geometry.docking.chord_95_high_A, 1)) * 520}
              y1={28}
              y2={28}
              stroke="#266FB1"
              strokeWidth={4}
            />
            <circle
              cx={40 + (geometry.docking.chord_A / Math.max(geometry.docking.chord_95_high_A, 1)) * 520}
              cy={28}
              r={6}
              fill="#C45C12"
            />
            <text x={40} y={56} fill="var(--studio-muted)" fontSize="12">
              0
            </text>
            <text x={560} y={56} fill="var(--studio-muted)" fontSize="12">
              {geometry.docking.chord_95_high_A.toFixed(0)} Å
            </text>
          </svg>
          <p className="mt-1 text-sm text-studio-muted">Orange dot: the distance. Blue: the low end of the 95% range up to that distance.</p>
          <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-studio-label">Repeats</dt>
              <dd className="font-mono">{geometry.docking.indices.join(" and ")}</dd>
            </div>
            <div>
              <dt className="text-studio-label">Straight-line distance</dt>
              <dd className="font-mono">{geometry.docking.chord_A.toFixed(2)} Å</dd>
            </div>
            <div>
              <dt className="text-studio-label">95% chord</dt>
              <dd className="font-mono">
                {geometry.docking.chord_95_low_A.toFixed(2)}–{geometry.docking.chord_95_high_A.toFixed(2)} Å
              </dd>
            </div>
            <div>
              <dt className="text-studio-label">Local concentration</dt>
              <dd className="font-mono">{sci(geometry.docking.c_eff_M)} M</dd>
            </div>
            <div>
              <dt className="text-studio-label">Clash probability</dt>
              <dd className="font-mono">{sci(geometry.docking.p_clash)}</dd>
            </div>
            <div>
              <dt className="text-studio-label">Radii</dt>
              <dd className="font-mono">
                {(geometry.docking.radii_A ?? []).map((radius) => radius.toFixed(2)).join(" Å, ")} Å
              </dd>
            </div>
          </dl>
          <button
            type="button"
            className="mt-4 rounded-full border border-studio-border px-4 py-2 text-sm"
            onClick={() => downloadJson(`origami-geometry-n${geometry.docking.n_repeats}.json`, geometry)}
          >
            Download summary file
          </button>
        </section>
      ) : null}
    </main>
  );
}
