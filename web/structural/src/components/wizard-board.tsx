"use client";

import { useState } from "react";
import { StudioNav } from "@/components/studio-nav";
import { readApiJson } from "@/lib/api";

const STEPS = [
  "What this is",
  "Repeat count",
  "Scores",
  "Summary file",
];

export function WizardBoard() {
  const [step, setStep] = useState(0);
  const [n, setN] = useState(8);
  const [chassis, setChassis] = useState<Record<string, unknown> | null>(null);
  const [passport, setPassport] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runChassis() {
    setError(null);
    try {
      const res = await fetch("/api/ssdk/chassis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ n_repeats: n }),
      });
      setChassis(await readApiJson<Record<string, unknown>>(res));
      setStep(2);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Chassis request failed.");
    }
  }

  async function runPassport() {
    setError(null);
    try {
      const res = await fetch("/api/export/passport", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ n_repeats: n }),
      });
      const data = await readApiJson<Record<string, unknown>>(res);
      setPassport(data);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `origami-summary-n${n}.json`;
      link.click();
      URL.revokeObjectURL(url);
      setStep(3);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Summary request failed.");
    }
  }

  const structure = chassis?.structure as { contour_nm?: number } | undefined;
  const stability = chassis?.stability as { tm_C?: number; delta_g?: number } | undefined;
  const docking = chassis?.docking as { chord_A?: number; clash_computable?: boolean } | undefined;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 font-[family-name:var(--font-inter)] text-studio-foreground">
      <StudioNav />
      <h1 className="text-2xl font-semibold">Step through one length</h1>
      <p className="mt-2 text-sm text-studio-muted">
        Pick a repeat count from 3 to 24. You get the screw, the melting
        temperature, and the straight-line docking distance, then a summary
        file. No radii means no clash. Nothing here is a lab measurement.
      </p>
      <ol className="mt-4 flex flex-wrap gap-2">
        {STEPS.map((label, i) => (
          <li
            key={label}
            className={
              i === step
                ? "rounded-full bg-studio-button px-3 py-1 text-sm text-studio-button-text"
                : "rounded-full border border-studio-border px-3 py-1 text-sm"
            }
          >
            {i + 1}. {label}
          </li>
        ))}
      </ol>
      {error ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
      {step === 0 ? (
        <section className="mt-6 space-y-3">
          <p>
            Wet payload is CaM–M13 only. SpyCatcher and LgBiT are core modules.
            Next: pick a planned length (3, 8, or 14).
          </p>
          <button
            className="rounded-full bg-studio-button px-4 py-2 text-sm text-studio-button-text"
            onClick={() => setStep(1)}
            type="button"
          >
            Continue
          </button>
        </section>
      ) : null}
      {step === 1 ? (
        <section className="mt-6 space-y-3">
          <label className="block text-sm">
            Repeat count
            <input
              className="ml-2 border px-2 py-1"
              type="number"
              min={3}
              max={24}
              value={n}
              onChange={(e) => setN(Number(e.target.value))}
            />
          </label>
          <button
            className="rounded-full bg-studio-button px-4 py-2 text-sm text-studio-button-text"
            onClick={runChassis}
            type="button"
          >
            Score this length
          </button>
        </section>
      ) : null}
      {step >= 2 ? (
        <section className="mt-6">
          <h2 className="font-medium">Scores for this length</h2>
          <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-studio-label">Length along repeats</dt>
              <dd className="font-mono">{structure?.contour_nm?.toFixed(3) ?? "—"} nm</dd>
            </div>
            <div>
              <dt className="text-studio-label">Melting temperature</dt>
              <dd className="font-mono">{stability?.tm_C?.toFixed(2) ?? "—"} °C</dd>
            </div>
            <div>
              <dt className="text-studio-label">ΔG</dt>
              <dd className="font-mono">{stability?.delta_g?.toFixed(2) ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-studio-label">Docking distance</dt>
              <dd className="font-mono">
                {docking?.chord_A?.toFixed(2) ?? "—"} Å
                {docking?.clash_computable ? "" : " (clash needs two radii)"}
              </dd>
            </div>
          </dl>
          <button
            className="mt-3 rounded-full bg-studio-button px-4 py-2 text-sm text-studio-button-text"
            onClick={runPassport}
            type="button"
          >
            Build summary file
          </button>
        </section>
      ) : null}
      {step >= 3 ? (
        <section className="mt-6">
          <h2 className="font-medium">Summary file</h2>
          <p className="mt-2 text-sm text-studio-muted">
            Saved as origami-summary-n{n}.json. Repeat count {String(passport?.n_repeats ?? n)}.
          </p>
          <p className="mt-2 text-sm">
            Downloads:{" "}
            <a className="underline" href={`/api/export/genbank/${n}`}>
              GenBank
            </a>
            {" · "}
            <a className="underline" href={`/api/export/sbol/${n}`}>
              SBOL
            </a>
          </p>
        </section>
      ) : null}
    </main>
  );
}
