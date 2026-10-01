"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { StudioNav } from "@/components/studio-nav";
import {
  fetchKineticsSchema,
  simulateCovalent,
  simulateNanoBit,
  simulateRecruitment,
  type CovalentSim,
  type KineticsSchema,
  type NanoBitSim,
  type RateSlot,
  type RecruitmentSim,
} from "@/lib/kinetics";

const DEFAULT_C_FREE = 1e-8;
const DEFAULT_TAG = 10e-6;

function slotBadge(slot: RateSlot) {
  if (slot.origin === "literature_prior" && slot.status === "literature") {
    return "Literature prior (not our assay)";
  }
  if (slot.status === "vacant") return "Vacant lab field";
  return "User supplied";
}

function formatVal(slot: RateSlot) {
  if (slot.value === null) return "—";
  return `${slot.value.toExponential(2)} ${slot.units}`;
}

export function KineticsBoard() {
  const [schema, setSchema] = useState<KineticsSchema | null>(null);
  const [sim, setSim] = useState<RecruitmentSim | null>(null);
  const [cov, setCov] = useState<CovalentSim | null>(null);
  const [cFree, setCFree] = useState(String(DEFAULT_C_FREE));
  const [tag0, setTag0] = useState(String(DEFAULT_TAG));
  const [catcher0, setCatcher0] = useState(String(DEFAULT_TAG));
  const [labOn, setLabOn] = useState("");
  const [labRev, setLabRev] = useState("");
  const [labBond, setLabBond] = useState("");
  const [nano, setNano] = useState<NanoBitSim | null>(null);
  const [lg0, setLg0] = useState("");
  const [sm0, setSm0] = useState("");
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
        const c = await simulateCovalent({
          tag0_M: DEFAULT_TAG,
          catcher0_M: DEFAULT_TAG,
        });
        if (!cancelled) setCov(c);
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

  async function runRecruitment() {
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

  async function runCovalent() {
    setError(null);
    const t = Number(tag0);
    const c = Number(catcher0);
    if (!Number.isFinite(t) || t < 0 || !Number.isFinite(c) || c < 0) {
      setError("Enter finite non-negative Tag0 and Catcher0 (M).");
      return;
    }
    const body: {
      tag0_M: number;
      catcher0_M: number;
      spy_k_on_per_M_s?: number;
      spy_k_rev_per_s?: number;
      spy_k_bond_per_s?: number;
    } = { tag0_M: t, catcher0_M: c };
    if (labOn.trim() !== "") {
      const k = Number(labOn);
      if (!Number.isFinite(k) || k <= 0) {
        setError("Lab k_on must be a positive number if filled.");
        return;
      }
      body.spy_k_on_per_M_s = k;
    }
    if (labRev.trim() !== "" || labBond.trim() !== "") {
      const kr = Number(labRev);
      const kb = Number(labBond);
      if (!Number.isFinite(kr) || kr <= 0 || !Number.isFinite(kb) || kb <= 0) {
        setError("Fill both lab k_rev and k_bond with positive numbers, or leave both empty.");
        return;
      }
      body.spy_k_rev_per_s = kr;
      body.spy_k_bond_per_s = kb;
    }
    setLoading(true);
    try {
      setCov(await simulateCovalent(body));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulate failed");
    } finally {
      setLoading(false);
    }
  }

  async function runNanoBit() {
    setError(null);
    const lg = Number(lg0);
    const sm = Number(sm0);
    if (!Number.isFinite(lg) || lg < 0 || !Number.isFinite(sm) || sm < 0) {
      setError("Enter finite non-negative LgBiT and SmBiT concentrations (M).");
      return;
    }
    setLoading(true);
    try {
      setNano(await simulateNanoBit(lg, sm));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulate failed");
    } finally {
      setLoading(false);
    }
  }

  const spyOn = schema?.rate_slots.find((s) => s.name === "spy_k_on_per_M_s");

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 font-[family-name:var(--font-inter)] text-[#242220]">
      <StudioNav />
      <header className="mb-8">
        <p className="text-sm uppercase tracking-wide text-[#8A8278]">Dry lab</p>
        <h1 className="mt-1 text-3xl font-semibold">Scaffold kinetics</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
          These numbers let the models run so you can test the math. They are
          literature priors, not our assay. In about two weeks, put lab rates in
          the empty override boxes. CaM–M13 uses the peptide K<sub>d</sub>, not a
          fusion K<sub>d</sub>. Spy locking uses Zakeri’s apparent second-order
          rate as a lumped irreversible step. Reversible off-rate and lock-rate
          stay vacant until you measure them. NanoBiT complementation uses the
          Dixon k<sub>on</sub> and k<sub>off</sub>. The printed 190 μM K<sub>d</sub>{" "}
          is shown beside k<sub>off</sub>/k<sub>on</sub> and is not substituted
          into that ODE.{" "}
          <code className="rounded bg-[#F5F0E8] px-1">calibrated = false</code>,{" "}
          <code className="rounded bg-[#F5F0E8] px-1">hypothesis_only</code>.
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
                  <Badge variant="outline">{slotBadge(slot)}</Badge>
                  <span className="text-sm tabular-nums">{formatVal(slot)}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="mb-10 rounded-2xl border border-[#E3D9CC] bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Recruitment steady state</h2>
        <p className="mt-1 text-sm text-[#5C564E]">
          θ<sub>ss</sub> = C<sub>free</sub> / (C<sub>free</sub> + K<sub>d</sub>).
          Uses the Biochemistry 2006 peptide K<sub>d</sub> (DOI 10.1021/bi060857u).
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
          onClick={() => void runRecruitment()}
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
              <dd>{sim.confidence_tier}</dd>
            </div>
          </dl>
        ) : null}
      </section>

      <section className="mb-10 rounded-2xl border border-[#E3D9CC] bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">NanoBiT complementation</h2>
        <p className="mt-1 text-sm text-[#5C564E]">
          d[complex]/dt = k<sub>on</sub> [Lg][Sm] − k<sub>off</sub> [complex].
          Both concentrations are required. There is no default mix. The
          equilibrium uses k<sub>off</sub>/k<sub>on</sub> from Dixon et al. 2016
          (DOI 10.1021/acschembio.5b00753).
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            LgBiT<sub>0</sub> (M)
            <input
              className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2 font-mono text-sm"
              value={lg0}
              onChange={(e) => setLg0(e.target.value)}
              placeholder="required"
            />
          </label>
          <label className="block text-sm">
            SmBiT<sub>0</sub> (M)
            <input
              className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2 font-mono text-sm"
              value={sm0}
              onChange={(e) => setSm0(e.target.value)}
              placeholder="required"
            />
          </label>
        </div>
        <button
          type="button"
          onClick={() => void runNanoBit()}
          className="mt-4 rounded-full bg-[#242220] px-5 py-2 text-sm text-white"
        >
          Run NanoBiT
        </button>
        {nano ? (
          <dl className="mt-6 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-[#8A8278]">Equilibrium complex</dt>
              <dd className="font-mono">{nano.equilibrium_complex_M.toExponential(3)} M</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">Uses</dt>
              <dd className="font-mono">{nano.equilibrium_uses}</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">k_off / k_on</dt>
              <dd className="font-mono">{nano.rates_used.kinetic_kd_M.toExponential(3)} M</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">Printed K<sub>d</sub></dt>
              <dd className="font-mono">{nano.rates_used.printed_kd_M.toExponential(3)} M</dd>
            </div>
          </dl>
        ) : null}
        {nano?.warnings?.length ? (
          <ul className="mt-4 list-disc pl-5 text-sm text-[#5C564E]">
            {nano.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="rounded-2xl border border-[#E3D9CC] bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Spy covalent time course</h2>
        <p className="mt-1 text-sm text-[#5C564E]">
          Pre-filled k<sub>on</sub> is the Zakeri 2012 literature prior (
          {spyOn ? formatVal(spyOn) : "1.4e3 M^-1 s^-1"}), labeled as not our
          assay. Leave lab boxes empty to run the lumped irreversible path.
          Fill both k<sub>rev</sub> and k<sub>bond</sub> only when you have lab
          numbers.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            Tag<sub>0</sub> (M)
            <input
              className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2 font-mono text-sm"
              value={tag0}
              onChange={(e) => setTag0(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            Catcher<sub>0</sub> (M)
            <input
              className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2 font-mono text-sm"
              value={catcher0}
              onChange={(e) => setCatcher0(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            Lab k<sub>on</sub> override (M⁻¹ s⁻¹), empty = literature
            <input
              className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2 font-mono text-sm"
              value={labOn}
              onChange={(e) => setLabOn(e.target.value)}
              placeholder="leave empty"
            />
          </label>
          <label className="block text-sm">
            Lab k<sub>rev</sub> (s⁻¹), empty = vacant
            <input
              className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2 font-mono text-sm"
              value={labRev}
              onChange={(e) => setLabRev(e.target.value)}
              placeholder="leave empty"
            />
          </label>
          <label className="block text-sm sm:col-span-2">
            Lab k<sub>bond</sub> (s⁻¹), empty = vacant
            <input
              className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2 font-mono text-sm"
              value={labBond}
              onChange={(e) => setLabBond(e.target.value)}
              placeholder="leave empty"
            />
          </label>
        </div>
        <button
          type="button"
          onClick={() => void runCovalent()}
          className="mt-4 rounded-full bg-[#242220] px-5 py-2 text-sm text-white"
        >
          Run covalent
        </button>
        {cov ? (
          <dl className="mt-6 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-[#8A8278]">Path</dt>
              <dd className="font-mono">{cov.rates_used.path}</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">k_on used</dt>
              <dd className="font-mono">
                {cov.rates_used.spy_k_on_per_M_s.toExponential(2)} M⁻¹ s⁻¹
              </dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">Final adduct</dt>
              <dd className="font-mono">
                {cov.series.adduct_M[cov.series.adduct_M.length - 1].toExponential(3)} M
              </dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">Tier</dt>
              <dd>{cov.confidence_tier}</dd>
            </div>
          </dl>
        ) : null}
      </section>
    </main>
  );
}
