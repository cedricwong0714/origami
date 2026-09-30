"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { StudioNav } from "@/components/studio-nav";
import {
  fetchKineticsSchema,
  simulateRecruitment,
  type KineticsSchema,
  type RateSlot,
  type RecruitmentSim,
} from "@/lib/kinetics";

const DEFAULT_C_FREE = 1e-8;

function slotBadge(status: RateSlot["status"]) {
  if (status === "literature") return "Literature Kd";
  if (status === "vacant") return "Vacant";
  return "User supplied";
}

export function KineticsBoard() {
  const [schema, setSchema] = useState<KineticsSchema | null>(null);
  const [sim, setSim] = useState<RecruitmentSim | null>(null);
  const [cFree, setCFree] = useState(String(DEFAULT_C_FREE));
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await fetchKineticsSchema();
        if (!cancelled) setSchema(s);
        const r = await simulateRecruitment(DEFAULT_C_FREE);
        if (!cancelled) setSim(r);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Load failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function runSim() {
    setError(null);
    const parsed = Number(cFree);
    if (!Number.isFinite(parsed) || parsed < 0) {
      setError("Enter a finite non-negative C_free (M).");
      return;
    }
    setLoading(true);
    try {
      setSim(await simulateRecruitment(parsed));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulate failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 font-[family-name:var(--font-inter)] text-[#242220]">
      <StudioNav />
      <header className="mb-8">
        <p className="text-sm uppercase tracking-wide text-[#8A8278]">Dry lab</p>
        <h1 className="mt-1 text-3xl font-semibold">Scaffold kinetics</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
          CaM–M13 recruitment uses the published peptide K<sub>d</sub>. SpyTag association,
          off-rate, and lock-rate slots stay vacant until stage-1 ingestion.{" "}
          <code className="rounded bg-[#F5F0E8] px-1">calibrated = false</code>.
        </p>
      </header>

      {error ? (
        <div className="mb-6 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      {loading && !schema ? (
        <div className="flex items-center gap-2 text-sm text-[#5C564E]">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading schema…
        </div>
      ) : null}

      {schema ? (
        <section className="mb-10 rounded-2xl border border-[#E3D9CC] bg-white p-6 shadow-sm">
          <h2 className="text-lg font-medium">Rate slots</h2>
          <p className="mt-1 text-sm text-[#5C564E]">{schema.note}</p>
          <ul className="mt-4 space-y-3">
            {schema.rate_slots.map((slot) => (
              <li
                key={slot.name}
                className="flex flex-wrap items-baseline justify-between gap-2 border-b border-[#F0E8DC] pb-3 last:border-0"
              >
                <div>
                  <span className="font-mono text-sm">{slot.name}</span>
                  <p className="text-xs text-[#8A8278]">{slot.notes}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{slotBadge(slot.status)}</Badge>
                  <span className="text-sm tabular-nums">
                    {slot.value === null ? "—" : slot.value.toExponential(2)}{" "}
                    {slot.units}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="rounded-2xl border border-[#E3D9CC] bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Recruitment steady state</h2>
        <p className="mt-1 text-sm text-[#5C564E]">
          θ<sub>ss</sub> = C<sub>free</sub> / (C<sub>free</sub> + K<sub>d</sub>). No SpyTag
          rates required.
        </p>
        <label className="mt-4 block text-sm">
          C<sub>free</sub> (M)
          <input
            className="mt-1 w-full max-w-xs rounded-lg border border-[#E3D9CC] px-3 py-2 font-mono text-sm"
            value={cFree}
            onChange={(e) => setCFree(e.target.value)}
          />
        </label>
        <button
          type="button"
          onClick={() => void runSim()}
          className="mt-4 rounded-full bg-[#242220] px-5 py-2 text-sm text-white"
        >
          Run recruitment
        </button>
        {sim ? (
          <dl className="mt-6 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-[#8A8278]">θ_ss</dt>
              <dd className="font-mono text-lg">{sim.recruitment.theta_ss.toExponential(4)}</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">95% band (Kd interval)</dt>
              <dd className="font-mono">
                {sim.recruitment.theta_95_lower.toExponential(3)} –{" "}
                {sim.recruitment.theta_95_upper.toExponential(3)}
              </dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">K<sub>d</sub></dt>
              <dd className="font-mono">{sim.recruitment.kd_M.toExponential(3)} M</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">Tier</dt>
              <dd>{schema?.confidence_tier ?? "hypothesis_only"}</dd>
            </div>
          </dl>
        ) : null}
      </section>
    </main>
  );
}
