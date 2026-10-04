"use client";

import { useState } from "react";
import { StudioNav } from "@/components/studio-nav";

const STEPS = [
  "Objective",
  "Scaffold n",
  "Chassis",
  "Passport / export",
];

export function WizardBoard() {
  const [step, setStep] = useState(0);
  const [n, setN] = useState(8);
  const [chassis, setChassis] = useState<string>("");
  const [passport, setPassport] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  async function runChassis() {
    setError(null);
    try {
      const res = await fetch("/api/ssdk/chassis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ n_repeats: n }),
      });
      const data = await res.json();
      setChassis(JSON.stringify(data, null, 2));
      setStep(2);
    } catch {
      setError("Chassis request failed. Is the API on port 41287?");
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
      const data = await res.json();
      setPassport(JSON.stringify(data, null, 2));
      setStep(3);
    } catch {
      setError("Passport request failed.");
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 font-[family-name:var(--font-inter)] text-[#242220]">
      <StudioNav />
      <h1 className="text-2xl font-semibold">Guided chassis snapshot</h1>
      <p className="mt-2 text-sm text-[#5C564E]">
        Objective → repeat count → structure/stability/docking → passport. This
        does not invent wet data. calibrated stays false.
      </p>
      <ol className="mt-4 flex flex-wrap gap-2">
        {STEPS.map((label, i) => (
          <li
            key={label}
            className={
              i === step
                ? "rounded-full bg-[#242220] px-3 py-1 text-sm text-white"
                : "rounded-full border border-[#E3D9CC] px-3 py-1 text-sm"
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
            className="rounded-full bg-[#242220] px-4 py-2 text-sm text-white"
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
            n_repeats
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
            className="rounded-full bg-[#242220] px-4 py-2 text-sm text-white"
            onClick={runChassis}
            type="button"
          >
            Evaluate chassis
          </button>
        </section>
      ) : null}
      {step >= 2 ? (
        <section className="mt-6">
          <h2 className="font-medium">Chassis JSON</h2>
          <pre className="mt-2 max-h-64 overflow-auto rounded bg-[#F7F1E8] p-3 text-xs">
            {chassis}
          </pre>
          <button
            className="mt-3 rounded-full bg-[#242220] px-4 py-2 text-sm text-white"
            onClick={runPassport}
            type="button"
          >
            Build passport
          </button>
        </section>
      ) : null}
      {step >= 3 ? (
        <section className="mt-6">
          <h2 className="font-medium">Passport</h2>
          <pre className="mt-2 max-h-64 overflow-auto rounded bg-[#F7F1E8] p-3 text-xs">
            {passport}
          </pre>
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
