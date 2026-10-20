"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { SeriesChart } from "@/components/model-chart";
import { StudioNav } from "@/components/studio-nav";
import { PageGuide } from "@/components/page-guide";
import {
  fetchScaffoldKinetics,
  simulateCovalent,
  simulateNanoBit,
  simulateRecruitment,
  type CovalentSim,
  type NanoBitSim,
  type RecruitmentSim,
  type ScaffoldKineticSweep,
} from "@/lib/kinetics";

const DEFAULT_C_FREE = 1e-8;
const DEFAULT_TAG = 10e-6;

function formatSeconds(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds)) return "outside linker reach";
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)} min`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)} h`;
  return `${(seconds / 86400).toExponential(2)} d`;
}

export function KineticsBoard({ pane = "bound" }: { pane?: "bound" | "spy" | "nanobit" }) {
  const [sweep, setSweep] = useState<ScaffoldKineticSweep | null>(null);
  const [sim, setSim] = useState<RecruitmentSim | null>(null);
  const [cov, setCov] = useState<CovalentSim | null>(null);
  const [cFree, setCFree] = useState(String(DEFAULT_C_FREE));
  const [tag0, setTag0] = useState(String(DEFAULT_TAG));
  const [catcher0, setCatcher0] = useState(String(DEFAULT_TAG));
  const [labOn, setLabOn] = useState("");
  const [nano, setNano] = useState<NanoBitSim | null>(null);
  const [lg0, setLg0] = useState("1e-6");
  const [sm0, setSm0] = useState("1e-6");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const library = await fetchScaffoldKinetics();
        if (!cancelled) setSweep(library);
        const r = await simulateRecruitment(DEFAULT_C_FREE);
        if (!cancelled) setSim(r);
        const c = await simulateCovalent({
          tag0_M: DEFAULT_TAG,
          catcher0_M: DEFAULT_TAG,
        });
        if (!cancelled) setCov(c);
        const tube = await simulateNanoBit(1e-6, 1e-6);
        if (!cancelled) setNano(tube);
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

  const camPoints = sweep?.rows.map((row) => ({ x: row.n_repeats, y: row.theta_cam })) ?? [];
  const teamHalf = sweep?.rows.flatMap((row) =>
    row.t_half_team_s === null ? [] : [{ x: row.n_repeats, y: row.t_half_team_s }],
  ) ?? [];
  const literatureHalf = sweep?.rows.flatMap((row) =>
    row.t_half_literature_s === null ? [] : [{ x: row.n_repeats, y: row.t_half_literature_s }],
  ) ?? [];
  const nanoKinetic = sweep?.rows.map((row) => ({ x: row.n_repeats, y: row.theta_nanobit_kinetic })) ?? [];
  const nanoPrinted = sweep?.rows.map((row) => ({ x: row.n_repeats, y: row.theta_nanobit_printed })) ?? [];

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 font-[family-name:var(--font-inter)] text-studio-foreground">
      <StudioNav />
      <header className="mb-8">
        <p className="text-sm uppercase tracking-wide text-studio-label">Kinetic modelling</p>
        <h1 className="mt-1 text-3xl font-semibold">
          {pane === "spy" ? "How fast does the Spy lock finish?" : pane === "nanobit" ? "Does the light reporter assemble in a tube?" : "How much of the sensor is bound?"}
        </h1>
        {pane === "spy" ? (
          <PageGuide
            intro="SpyCatcher and SpyTag form a covalent lock. This page runs that lock in a well-mixed tube, not on the scaffold, so you can see whether it finishes during your assay."
            steps={[
              "Check the on-rate. The published value is already filled in.",
              "Type the two concentrations you will actually mix.",
              "Click Run.",
              "Read locked product versus time.",
            ]}
            read={[
              "The curve is locked product versus time.",
              "If it levels off inside your assay window, the lock finishes in time.",
              "If it is still climbing at the end of the plot, you need a longer wait or a higher concentration.",
            ]}
            rules={[
              "The lock is one irreversible step. Reverse and bond rates are omitted because they have not been measured.",
              "This is a mixed solution. It is not the crowding between the two ends of the scaffold.",
            ]}
            next={[
              "If the lock is too slow here, it will be even slower on a long scaffold. Check Choose a length for the tethered half-life.",
            ]}
          />
        ) : pane === "nanobit" ? (
          <PageGuide
            intro="LgBiT and SmBiT are the two halves of the light reporter. This page asks whether they assemble in a well-mixed tube at the concentrations you will use."
            steps={[
              "Type the LgBiT and SmBiT concentrations.",
              "Click Run.",
              "Read complex versus time.",
            ]}
            read={[
              "The curve is reporter complex versus time.",
              "The published tightness is 190 μM. k_off ÷ k_on is shown beside it and is not swapped in.",
              "A low plateau means most of the protein stays apart at those concentrations.",
            ]}
            rules={[
              "This is reversible binding in free solution.",
              "It does not use the scaffold’s crowding. Will it bind? does that.",
            ]}
            next={[
              "If free solution looks dark, the scaffold has to raise crowding a lot before the reporter turns on. Check Choose a length.",
            ]}
          />
        ) : (
          <PageGuide
            intro="Bound fraction is calculated at every scaffold length. The screw sets the distance, the linker turns that distance into a local concentration, and the peptide Kd turns that concentration into a fraction bound."
            steps={[
              "Read the scaffold curve first. It is already calculated.",
              "The drop is where the screw chord leaves the linker.",
              "The box below is a separate well-mixed tube, if you want one free concentration.",
            ]}
            read={[
              "θ = C_eff(n) / (C_eff(n) + Kd).",
              "Kd is 0.19 nM from the peptide titration. It is the parameter, not the result.",
              "A fraction near 1 means the local concentration is still far above that Kd.",
            ]}
            rules={[
              "The scaffold curve uses the screw chord, not a concentration you type.",
              "The tube curve below is well mixed and does not use the scaffold.",
            ]}
            next={[
              "If you are on the steep part of the curve, small concentration errors will change the signal a lot.",
              "Take a concentration you trust into Will it bind? if you want the scaffold version.",
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

      {loading && !sweep ? (
        <div className="flex items-center gap-2 text-sm text-studio-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Calculating every scaffold length…
        </div>
      ) : null}

      {pane === "bound" && sweep ? (
        <section className="mb-10 rounded-2xl border border-studio-border bg-studio-card p-6 shadow-sm">
          <h2 className="text-lg font-medium">Bound fraction on the scaffold</h2>
          <p className="mt-1 text-sm text-studio-muted">
            Each point is θ = C_eff(n) / (C_eff(n) + Kd). The separation is the
            screw chord at that repeat count. Kd is the peptide value{" "}
            {sweep.cam_kd_M.toExponential(2)} M, not a result and not this fusion.
          </p>
          <SeriesChart
            label="Cam occupancy versus repeat count"
            xLabel="CTPR repeats n"
            yLabel="Fraction bound"
            series={[{ color: "#C45C12", points: camPoints }]}
          />
        </section>
      ) : null}

      {pane === "bound" ? (
      <section className="mb-10 rounded-2xl border border-studio-border bg-studio-card p-6 shadow-sm">
        <h2 className="text-lg font-medium">How much is bound?</h2>
        <p className="mt-1 text-sm text-studio-muted">
          Bound fraction = free concentration ÷ (free concentration + Kd). The Kd here is the peptide value, 0.19 nM. Do not type the 80 nM fusion number into this box.
        </p>
        <label className="mt-4 block text-sm">
          Free concentration (M)
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
              <dd>One point on the binding curve. Not a measurement on this fusion.</dd>
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

      {pane === "nanobit" && sweep ? (
        <section className="mb-10 rounded-2xl border border-studio-border bg-studio-card p-6 shadow-sm">
          <h2 className="text-lg font-medium">Reporter occupancy on the scaffold</h2>
          <p className="mt-1 text-sm text-studio-muted">
            Both curves use the screw chord. The solid curve uses k_off / k_on
            ({sweep.nanobit_kinetic_kd_M.toExponential(2)} M). The second curve
            uses the printed Kd ({sweep.nanobit_printed_kd_M.toExponential(2)} M).
            They are not substituted for each other.
          </p>
          <SeriesChart
            label="NanoBiT occupancy versus repeat count"
            xLabel="CTPR repeats n"
            yLabel="Fraction bound"
            series={[
              { color: "#C45C12", points: nanoKinetic },
              { color: "#7A7A7A", points: nanoPrinted },
            ]}
          />
        </section>
      ) : null}

      {pane === "nanobit" ? (
      <section className="mb-10 rounded-2xl border border-studio-border bg-studio-card p-6 shadow-sm">
        <h2 className="text-lg font-medium">Same reporter in a well-mixed tube</h2>
        <p className="mt-1 text-sm text-studio-muted">
          Type both starting concentrations. There is no default mix. The
          amount of complex at equilibrium uses Dixon et al. 2016
          (DOI 10.1021/acschembio.5b00753). Published tightness is 190 μM.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            Starting LgBiT (M)
            <input
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2 font-mono text-sm"
              value={lg0}
              onChange={(e) => setLg0(e.target.value)}
              placeholder="required"
            />
          </label>
          <label className="block text-sm">
            Starting SmBiT (M)
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
              <dt className="text-studio-label">Published Kd</dt>
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

      {pane === "spy" && sweep ? (
        <section className="mb-10 rounded-2xl border border-studio-border bg-studio-card p-6 shadow-sm">
          <h2 className="text-lg font-medium">Tethered lock versus scaffold length</h2>
          <p className="mt-1 text-sm text-studio-muted">
            t½ = ln 2 / (k × C_eff). Orange is the team fit,{" "}
            {sweep.spy_team_per_M_s.toExponential(2)} M⁻¹ s⁻¹. Grey is the
            literature rate, {sweep.spy_literature_per_M_s.toExponential(2)} M⁻¹ s⁻¹.
            The two curves are not averaged.
          </p>
          <SeriesChart
            label="Spy half-life versus repeat count"
            xLabel="CTPR repeats n"
            yLabel="Half-life (s)"
            yLog
            series={[
              { color: "#C45C12", points: teamHalf },
              { color: "#7A7A7A", points: literatureHalf },
            ]}
          />
          <p className="mt-2 text-sm text-studio-muted">
            At n = 8 the team half-life is {formatSeconds(sweep.rows.find((row) => row.n_repeats === 8)?.t_half_team_s ?? null)}
            {" "}and the literature half-life is {formatSeconds(sweep.rows.find((row) => row.n_repeats === 8)?.t_half_literature_s ?? null)}.
          </p>
        </section>
      ) : null}

      {pane === "spy" ? (
      <section className="rounded-2xl border border-studio-border bg-studio-card p-6 shadow-sm">
        <h2 className="text-lg font-medium">Spy lock over time</h2>
        <p className="mt-1 text-sm text-studio-muted">
          The chart is the tethered half-life at each screw length. The time course below is a separate well-mixed tube at the concentrations you type. Reverse and bond rates are not in either calculation: they have not been measured.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            Starting SpyTag (M)
            <input
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2 font-mono text-sm"
              value={tag0}
              onChange={(e) => setTag0(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            Starting SpyCatcher (M)
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
              <dt className="text-studio-label">On-rate used</dt>
              <dd className="font-mono">
                {cov.rates_used.spy_k_on_per_M_s.toExponential(2)} M⁻¹ s⁻¹
              </dd>
            </div>
            <div>
              <dt className="text-studio-label">Final locked product</dt>
              <dd className="font-mono">
                {cov.series.adduct_M[cov.series.adduct_M.length - 1].toExponential(3)} M
              </dd>
            </div>
            <div>
              <dt className="text-studio-label">What this is</dt>
              <dd>The time course at the concentrations you typed. Not a measurement on this fusion.</dd>
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
