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

const SLOT_LABEL: Record<string, string> = {
  cam_m13_kd_M: "CaM–M13 peptide Kd",
  spy_k_on_per_M_s: "Spy lock rate",
  spy_k_rev_per_s: "Spy reverse rate",
  spy_k_bond_per_s: "Spy bond rate",
  nanobit_kd_M: "LgBiT–SmBiT Kd",
  nanobit_k_on_per_M_s: "LgBiT–SmBiT on-rate",
  nanobit_k_off_per_s: "LgBiT–SmBiT off-rate",
};

function slotBadge(slot: RateSlot) {
  if (slot.origin === "literature_prior" && slot.status === "literature") {
    return "Published value";
  }
  if (slot.status === "vacant") return "Empty until you measure it";
  return "Value you typed";
}

function formatVal(slot: RateSlot) {
  if (slot.value === null) return "—";
  return `${slot.value.toExponential(2)} ${slot.units}`;
}

export function KineticsBoard({ pane = "bound" }: { pane?: "bound" | "spy" | "nanobit" }) {
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
        <p className="text-sm uppercase tracking-wide text-[#8A8278]">Kinetic modelling</p>
        <h1 className="mt-1 text-3xl font-semibold">
          {pane === "spy" ? "SpyCatcher–SpyTag" : pane === "nanobit" ? "LgBiT–SmBiT" : "Bound fraction"}
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
          Type concentrations in moles per litre and run the calculation. None of
          these rates were measured on our protein.
        </p>
        <ul className="mt-3 max-w-2xl list-disc space-y-1 pl-5 text-sm leading-relaxed text-[#5C564E]">
          <li>
            Bound fraction: free CaM–M13 peptide Kd 0.19 nM (Biochemistry 2006).
            The 80 nM fusion figure is not used here.
          </li>
          <li>
            Spy lock over time: Zakeri 2012 rate, 1.4×10³ M⁻¹ s⁻¹. No reverse rate is stored.
          </li>
          <li>
            LgBiT–SmBiT complex: Dixon 2016 on and off rates. The printed Kd is 190 μM.
          </li>
        </ul>
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

      {schema && pane === "bound" ? (
        <section className="mb-10 rounded-2xl border border-[#E3D9CC] bg-white p-6 shadow-sm">
          <h2 className="text-lg font-medium">Rates</h2>
          <p className="mt-1 text-sm text-[#5C564E]">
            Published values are filled in. Empty rows stay empty until you measure them.
          </p>
          <ul className="mt-4 space-y-3">
            {schema.rate_slots.map((slot) => (
              <li
                key={slot.name}
                className="flex flex-wrap items-baseline justify-between gap-2 border-b border-[#F0E8DC] pb-3 last:border-0"
              >
                <div>
                  <span className="text-sm">{SLOT_LABEL[slot.name] ?? slot.name}</span>
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

      {pane === "bound" ? (
      <section className="mb-10 rounded-2xl border border-[#E3D9CC] bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Bound fraction</h2>
        <p className="mt-1 text-sm text-[#5C564E]">
          Fraction bound = free concentration / (free concentration + Kd).
          Kd is 0.19 nM (DOI 10.1021/bi060857u). The 95% band comes from the
          uncertainty on that Kd.
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
          Run bound fraction
        </button>
        {sim ? (
          <dl className="mt-6 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-[#8A8278]">Fraction bound</dt>
              <dd className="font-mono text-lg">{sim.recruitment.theta_ss.toExponential(4)}</dd>
            </div>
            <div>
              <dt className="text-[#8A8278]">95% range from the Kd</dt>
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
              <dt className="text-[#8A8278]">What this is</dt>
              <dd>Literature Kd. Not measured here.</dd>
            </div>
          </dl>
        ) : null}
      </section>
      ) : null}

      {pane === "nanobit" ? (
      <section className="mb-10 rounded-2xl border border-[#E3D9CC] bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">LgBiT–SmBiT complex</h2>
        <p className="mt-1 text-sm text-[#5C564E]">
          Type both starting concentrations. There is no default mix. The
          amount of complex at equilibrium uses Dixon et al. 2016
          (DOI 10.1021/acschembio.5b00753). Printed Kd is 190 μM.
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
          Run complex
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
      ) : null}

      {pane === "spy" ? (
      <section className="rounded-2xl border border-[#E3D9CC] bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Spy lock over time</h2>
        <p className="mt-1 text-sm text-[#5C564E]">
          Starting rate is the Zakeri 2012 value (
          {spyOn ? formatVal(spyOn) : "1.4×10³ M⁻¹ s⁻¹"}). Leave the lab boxes
          empty. Fill a reverse rate and a bond rate only when you have measured them.
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
            Your Spy rate (M⁻¹ s⁻¹). Leave empty to use the published rate.
            <input
              className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2 font-mono text-sm"
              value={labOn}
              onChange={(e) => setLabOn(e.target.value)}
              placeholder="leave empty"
            />
          </label>
          <label className="block text-sm">
            Reverse rate (per second). Leave empty.
            <input
              className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2 font-mono text-sm"
              value={labRev}
              onChange={(e) => setLabRev(e.target.value)}
              placeholder="leave empty"
            />
          </label>
          <label className="block text-sm sm:col-span-2">
            Bond rate (per second). Leave empty.
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
          Run Spy lock
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
              <dt className="text-[#8A8278]">What this is</dt>
              <dd>Literature rate. Not measured here.</dd>
            </div>
          </dl>
        ) : null}
      </section>
      ) : null}
    </main>
  );
}
