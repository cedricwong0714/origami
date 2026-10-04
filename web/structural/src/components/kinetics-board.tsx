"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { SeriesChart } from "@/components/model-chart";
import { StudioNav } from "@/components/studio-nav";
import { PageGuide } from "@/components/page-guide";
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
    <main className="mx-auto max-w-4xl px-6 py-10 font-[family-name:var(--font-inter)] text-studio-foreground">
      <StudioNav />
      <header className="mb-8">
        <p className="text-sm uppercase tracking-wide text-studio-label">Kinetic modelling</p>
        <h1 className="mt-1 text-3xl font-semibold">
          {pane === "spy" ? "How fast does SpyCatcher lock?" : pane === "nanobit" ? "Does LgBiT–SmBiT assemble?" : "How much of the sensor is bound?"}
        </h1>
        {pane === "spy" ? (
          <PageGuide
            intro="This page runs the SpyCatcher–SpyTag lock in a well-mixed tube. Use it to see if the covalent link finishes during your assay."
            steps={[
              "Check the on-rate. The published value is already filled in.",
              "Type the two concentrations you will actually mix.",
              "Click Run.",
              "Read the adduct curve against time.",
            ]}
            read={[
              "The curve is locked product versus time.",
              "A curve that levels off inside your assay window means the lock finishes in time.",
              "A curve that is still climbing at the end of the plot needs a longer incubation or higher concentration.",
            ]}
            rules={[
              "The default path is one irreversible step. The reverse rate and the bond rate stay empty until you supply both.",
              "This is a mixed solution. It is not the local concentration on the scaffold.",
            ]}
            next={[
              "If the lock is too slow here, it will be even slower on a long scaffold. Check Choose a length for the tethered half-life.",
            ]}
          />
        ) : pane === "nanobit" ? (
          <PageGuide
            intro="This page runs LgBiT and SmBiT binding in a well-mixed tube. Use it to see if the reporter assembles at the concentrations you will use."
            steps={[
              "Type the LgBiT and SmBiT concentrations.",
              "Click Run.",
              "Read complex versus time.",
            ]}
            read={[
              "The curve is reporter complex versus time.",
              "The printed Kd is 190 μM. k_off divided by k_on is shown beside it and is not swapped in.",
              "A low plateau means most of the protein stays apart at those concentrations.",
            ]}
            rules={[
              "This is reversible binding in free solution.",
              "It does not use the scaffold’s local concentration. Docking does that.",
            ]}
            next={[
              "If free solution looks dark, the scaffold has to raise the local concentration a lot before the reporter turns on. Check Choose a length.",
            ]}
          />
        ) : (
          <PageGuide
            intro="This page shows how much of the CaM–M13 sensor is bound at a free concentration you choose. Use it before you pick a working concentration."
            steps={[
              "Look at the filled-in Kd. Empty rate rows stay empty.",
              "Type a free concentration in molar.",
              "Click Run bound fraction.",
              "Find your concentration on the curve.",
            ]}
            read={[
              "Bound fraction is free concentration divided by free concentration plus Kd.",
              "The peptide Kd is 0.19 nM. The 80 nM fusion number is a different measurement and is not used here.",
              "The shaded range on the point comes from the uncertainty on that Kd.",
              "Near 1 means the sensor is saturated. Near 0.5 means you are at the Kd. Near 0 means almost nothing is bound.",
            ]}
            rules={[
              "Higher free concentration binds more sensor.",
              "This is well mixed. It is not the concentration between the two ends of the scaffold.",
            ]}
            next={[
              "If you are on the steep part of the curve, small concentration errors will change the signal a lot.",
              "Take a concentration you trust into the docking page if you want the scaffold version.",
            ]}
          />
        )}
      </header>

      {error ? (
        <div className="mb-6 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      {loading && !schema ? (
        <div className="flex items-center gap-2 text-sm text-studio-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading schema…
        </div>
      ) : null}

      {schema && pane === "bound" ? (
        <section className="mb-10 rounded-2xl border border-studio-border bg-studio-card p-6 shadow-sm">
          <h2 className="text-lg font-medium">Rates</h2>
          <p className="mt-1 text-sm text-studio-muted">
            Published numbers are already filled in. Leave a row blank if you have not measured it.
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
      <section className="mb-10 rounded-2xl border border-studio-border bg-studio-card p-6 shadow-sm">
        <h2 className="text-lg font-medium">Bound fraction</h2>
        <p className="mt-1 text-sm text-studio-muted">
          Bound fraction = free concentration / (free concentration + Kd). The Kd here is the peptide value, 0.19 nM. Do not type the 80 nM fusion number into this box.
        </p>
        <label className="mt-4 block text-sm">
          C<sub>free</sub> (M)
          <input
            className="mt-1 w-full max-w-xs rounded-lg border border-studio-border px-3 py-2 font-mono text-sm"
            value={cFree}
            onChange={(e) => setCFree(e.target.value)}
          />
        </label>
        <button
          type="button"
          onClick={() => void runRecruitment()}
          className="mt-4 rounded-full bg-studio-button px-5 py-2 text-sm text-studio-button-text"
        >
          Run bound fraction
        </button>
        {sim ? (
          <dl className="mt-6 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-studio-label">Fraction bound</dt>
              <dd className="font-mono text-lg">{sim.recruitment.theta_ss.toExponential(4)}</dd>
            </div>
            <div>
              <dt className="text-studio-label">95% range from the Kd</dt>
              <dd className="font-mono">
                {sim.recruitment.theta_95_lower.toExponential(3)} –{" "}
                {sim.recruitment.theta_95_upper.toExponential(3)}
              </dd>
            </div>
            <div>
              <dt className="text-studio-label">K<sub>d</sub></dt>
              <dd className="font-mono">{sim.recruitment.kd_M.toExponential(3)} M</dd>
            </div>
            <div>
              <dt className="text-studio-label">What this is</dt>
              <dd>One point on the isotherm. Not a measurement on this fusion.</dd>
            </div>
          </dl>
        ) : null}
        {sim ? (
          <SeriesChart
            label="Bound fraction versus free concentration"
            xLabel="Free concentration (M)"
            yLabel="Fraction bound"
            xLog
            markerX={sim.recruitment.c_free_M}
            series={[
              {
                color: "#C45C12",
                points: Array.from({ length: 41 }, (_, index) => {
                  const c = sim.recruitment.kd_M * 10 ** (-2 + index * 0.1);
                  return { x: c, y: c / (c + sim.recruitment.kd_M) };
                }),
              },
            ]}
          />
        ) : null}
      </section>
      ) : null}

      {pane === "nanobit" ? (
      <section className="mb-10 rounded-2xl border border-studio-border bg-studio-card p-6 shadow-sm">
        <h2 className="text-lg font-medium">LgBiT–SmBiT complex</h2>
        <p className="mt-1 text-sm text-studio-muted">
          Type both starting concentrations. There is no default mix. The
          amount of complex at equilibrium uses Dixon et al. 2016
          (DOI 10.1021/acschembio.5b00753). Printed Kd is 190 μM.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            LgBiT<sub>0</sub> (M)
            <input
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2 font-mono text-sm"
              value={lg0}
              onChange={(e) => setLg0(e.target.value)}
              placeholder="required"
            />
          </label>
          <label className="block text-sm">
            SmBiT<sub>0</sub> (M)
            <input
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2 font-mono text-sm"
              value={sm0}
              onChange={(e) => setSm0(e.target.value)}
              placeholder="required"
            />
          </label>
        </div>
        <button
          type="button"
          onClick={() => void runNanoBit()}
          className="mt-4 rounded-full bg-studio-button px-5 py-2 text-sm text-studio-button-text"
        >
          Run complex
        </button>
        {nano ? (
          <dl className="mt-6 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-studio-label">Equilibrium complex</dt>
              <dd className="font-mono">{nano.equilibrium_complex_M.toExponential(3)} M</dd>
            </div>
            <div>
              <dt className="text-studio-label">Uses</dt>
              <dd className="font-mono">{nano.equilibrium_uses}</dd>
            </div>
            <div>
              <dt className="text-studio-label">k_off / k_on</dt>
              <dd className="font-mono">{nano.rates_used.kinetic_kd_M.toExponential(3)} M</dd>
            </div>
            <div>
              <dt className="text-studio-label">Printed K<sub>d</sub></dt>
              <dd className="font-mono">{nano.rates_used.printed_kd_M.toExponential(3)} M</dd>
            </div>
          </dl>
        ) : null}
        {nano?.time_s && nano.series.complex_M.length === nano.time_s.length ? (
          <SeriesChart
            label="LgBiT–SmBiT complex versus time"
            xLabel="Time (s)"
            yLabel="Complex (M)"
            series={[{ color: "#C45C12", points: nano.time_s.map((time, index) => ({ x: time, y: nano.series.complex_M[index] ?? 0 })) }]}
          />
        ) : null}
        {nano?.warnings?.length ? (
          <ul className="mt-4 list-disc pl-5 text-sm text-studio-muted">
            {nano.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        ) : null}
      </section>
      ) : null}

      {pane === "spy" ? (
      <section className="rounded-2xl border border-studio-border bg-studio-card p-6 shadow-sm">
        <h2 className="text-lg font-medium">Spy lock over time</h2>
        <p className="mt-1 text-sm text-studio-muted">
          Default path: one irreversible step, adduct grows as k_on times Tag times Catcher. The starting k_on is{" "}
          {spyOn ? formatVal(spyOn) : "the Zakeri 2012 rate"}. Leave the reverse and bond boxes empty. Filling both switches the model to reversible binding plus an irreversible lock.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            Tag<sub>0</sub> (M)
            <input
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2 font-mono text-sm"
              value={tag0}
              onChange={(e) => setTag0(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            Catcher<sub>0</sub> (M)
            <input
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2 font-mono text-sm"
              value={catcher0}
              onChange={(e) => setCatcher0(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            Your Spy rate (M⁻¹ s⁻¹). Leave empty to use the published rate.
            <input
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2 font-mono text-sm"
              value={labOn}
              onChange={(e) => setLabOn(e.target.value)}
              placeholder="leave empty"
            />
          </label>
          <label className="block text-sm">
            Reverse rate (per second). Leave empty.
            <input
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2 font-mono text-sm"
              value={labRev}
              onChange={(e) => setLabRev(e.target.value)}
              placeholder="leave empty"
            />
          </label>
          <label className="block text-sm sm:col-span-2">
            Bond rate (per second). Leave empty.
            <input
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2 font-mono text-sm"
              value={labBond}
              onChange={(e) => setLabBond(e.target.value)}
              placeholder="leave empty"
            />
          </label>
        </div>
        <button
          type="button"
          onClick={() => void runCovalent()}
          className="mt-4 rounded-full bg-studio-button px-5 py-2 text-sm text-studio-button-text"
        >
          Run Spy lock
        </button>
        {cov ? (
          <dl className="mt-6 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-studio-label">Path</dt>
              <dd className="font-mono">{cov.rates_used.path}</dd>
            </div>
            <div>
              <dt className="text-studio-label">k_on used</dt>
              <dd className="font-mono">
                {cov.rates_used.spy_k_on_per_M_s.toExponential(2)} M⁻¹ s⁻¹
              </dd>
            </div>
            <div>
              <dt className="text-studio-label">Final adduct</dt>
              <dd className="font-mono">
                {cov.series.adduct_M[cov.series.adduct_M.length - 1].toExponential(3)} M
              </dd>
            </div>
            <div>
              <dt className="text-studio-label">What this is</dt>
              <dd>The ODE at the concentrations you typed. Not a measurement on this fusion.</dd>
            </div>
          </dl>
        ) : null}
        {cov && cov.time_s.length > 0 ? (
          <SeriesChart
            label="Spy adduct versus time"
            xLabel="Time (s)"
            yLabel="Adduct (M)"
            series={[
              {
                color: "#C45C12",
                points: cov.time_s.map((time, index) => ({ x: time, y: cov.series.adduct_M[index] ?? 0 })),
              },
            ]}
          />
        ) : null}
      </section>
      ) : null}
    </main>
  );
}
