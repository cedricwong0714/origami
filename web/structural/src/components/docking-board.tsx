"use client";

import { useState } from "react";
import { StudioNav } from "@/components/studio-nav";

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
    <main className="mx-auto max-w-4xl px-6 py-10 text-[#242220]">
      <StudioNav />
      <p className="text-[11px] font-semibold tracking-[0.22em] text-[#C45C12] uppercase">
        Docking verification
      </p>
      <h1 className="mt-2 text-3xl font-semibold">
        {pane === "affinity" ? "Does this affinity hold the constructs together?" : "Distance and clash"}
      </h1>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
        {pane === "affinity"
          ? "Type a dissociation constant (Kd) or an association constant (Ka), and a repeat count. The screw gives a local concentration. Bound fraction = local concentration / (local concentration + Kd). At or above one half, the constructs are held together, and that same concentration is applied to LgBiT–SmBiT and SpyCatcher–SpyTag."
          : "Pick a repeat count. You get the straight-line distance between the two docking repeats, the clash probability, and the local concentration. Radii are the deposited SpyCatcher and LgBiT clash radii."}
      </p>

      <section className="mt-8 rounded-2xl border border-[#E3D9CC] bg-white p-6">
        <label className="block text-sm font-medium">
          Repeat count (3–24)
          <input
            className="mt-1 w-32 rounded-lg border border-[#E3D9CC] px-3 py-2"
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
                className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2"
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
                className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2 font-mono"
                value={value}
                onChange={(event) => setValue(event.target.value)}
              />
            </label>
            <label className="block text-sm font-medium">
              Unit
              <select
                className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2"
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
          className="mt-5 rounded-full bg-[#242220] px-5 py-2 text-sm text-white disabled:opacity-50"
          onClick={() => void (pane === "affinity" ? runAffinity() : runGeometry())}
          disabled={running}
        >
          {running ? "Running…" : "Run"}
        </button>
        {error ? <p className="mt-4 text-sm text-[#9B2C2C]">{error}</p> : null}
      </section>

      {affinity && pane === "affinity" ? (
        <section className="mt-6 rounded-2xl border border-[#E3D9CC] bg-white p-6">
          <h2 className="text-lg font-medium">
            {affinity.association_holds ? "Holds together" : "Does not hold together"}
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">{affinity.verdict}</p>
          <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-[#8A8278]">Bound fraction</dt>
              <dd className="font-mono text-lg">{affinity.association_theta.toFixed(3)}</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">Kd used</dt>
              <dd className="font-mono">{sci(affinity.kd_M)} M</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">Local concentration</dt>
              <dd className="font-mono">{sci(affinity.c_eff_M)} M</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">End chord</dt>
              <dd className="font-mono">{affinity.chord_A.toFixed(2)} Å</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">LgBiT–SmBiT occupancy</dt>
              <dd className="font-mono">
                {sci(affinity.nanobit_theta)}{" "}
                {affinity.drives_lgbit_smbit ? "at or above one half" : "below one half"}
              </dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">SpyCatcher–SpyTag</dt>
              <dd className="font-mono">
                k_obs {sci(affinity.spy_k_obs_per_s)} /s, half-life {sci(affinity.spy_half_life_s)} s
              </dd>
            </div>
          </dl>
          {affinity.spy_half_life_note ? (
            <p className="mt-4 text-sm text-[#5C564E]">{affinity.spy_half_life_note}</p>
          ) : null}
          <p className="mt-4 text-sm text-[#5C564E]">{affinity.criterion}</p>
          <p className="mt-2 text-sm text-[#5C564E]">{affinity.conversion}</p>
          <button
            type="button"
            className="mt-4 rounded-full border border-[#E3D9CC] px-4 py-2 text-sm"
            onClick={() => downloadJson(`origami-docking-n${affinity.n_repeats}.json`, affinity)}
          >
            Download summary file
          </button>
        </section>
      ) : null}

      {geometry && pane === "geometry" ? (
        <section className="mt-6 rounded-2xl border border-[#E3D9CC] bg-white p-6">
          <h2 className="text-lg font-medium">n = {geometry.docking.n_repeats}</h2>
          <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-[#8A8278]">Repeats</dt>
              <dd className="font-mono">{geometry.docking.indices.join(" and ")}</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">Straight-line distance</dt>
              <dd className="font-mono">{geometry.docking.chord_A.toFixed(2)} Å</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">95% chord</dt>
              <dd className="font-mono">
                {geometry.docking.chord_95_low_A.toFixed(2)}–{geometry.docking.chord_95_high_A.toFixed(2)} Å
              </dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">Local concentration</dt>
              <dd className="font-mono">{sci(geometry.docking.c_eff_M)} M</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">Clash probability</dt>
              <dd className="font-mono">{sci(geometry.docking.p_clash)}</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">Radii</dt>
              <dd className="font-mono">
                {(geometry.docking.radii_A ?? []).map((radius) => radius.toFixed(2)).join(" Å, ")} Å
              </dd>
            </div>
          </dl>
          <button
            type="button"
            className="mt-4 rounded-full border border-[#E3D9CC] px-4 py-2 text-sm"
            onClick={() => downloadJson(`origami-geometry-n${geometry.docking.n_repeats}.json`, geometry)}
          >
            Download summary file
          </button>
        </section>
      ) : null}
    </main>
  );
}
