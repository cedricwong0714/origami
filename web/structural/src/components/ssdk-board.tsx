"use client";

import { useState, type ReactNode } from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StudioNav } from "@/components/studio-nav";

type ChassisReport = {
  calibrated: false;
  n_repeats: number;
  structure: {
    contour_nm: number;
    axial_span_A: number;
    rigid_screw: boolean;
    persistence_length_nm: number;
  };
  stability: {
    tm_C: number | null;
    tm_95_lower_C: number | null;
    tm_95_upper_C: number | null;
    past_longest_cited_length: boolean;
    delta_g: number | null;
    lab_tm_C: number | null;
    lab_tm_above_assay: boolean | null;
    t_assay_C: number;
  };
  docking: {
    clash_computable: boolean;
    missing?: string[];
    chord_A: number;
    chord_95_low_A: number;
    chord_95_high_A: number;
    facing_cosine: number;
    indices: number[];
    p_clash?: number;
    c_eff_M?: number;
    c_eff_95_lower_M?: number | null;
    c_eff_95_upper_M?: number | null;
    note?: string;
    local_kinetics?: {
      computable: boolean;
      missing?: string[];
      spy?: {
        k_obs_per_s: number;
        t_half_s: number | null;
        t_half_note: string;
      };
      nanobit?: {
        theta_ss: number;
        printed_kd_M: number;
        kinetic_kd_M: number;
      };
    };
  };
  kinetics: {
    computable: boolean;
    missing?: string[];
    note?: string;
    simulation?: {
      mode?: string;
      recruitment?: { theta_ss: number; theta_95_lower: number; theta_95_upper: number };
      equilibrium_complex_M?: number;
      rates_used?: { kinetic_kd_M?: number; printed_kd_M?: number; path?: string };
    };
  };
};

function formatNumber(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "omitted";
  const abs = Math.abs(value);
  if (abs !== 0 && (abs < 0.01 || abs >= 1000)) return value.toExponential(3);
  return value.toPrecision(4);
}

function optionalPositive(text: string, label: string): number | undefined {
  if (!text.trim()) return undefined;
  const value = Number(text);
  if (!Number.isFinite(value)) throw new Error(`${label} must be a finite number.`);
  return value;
}

export function SsdkBoard() {
  const [n, setN] = useState("8");
  const [indexA, setIndexA] = useState("");
  const [indexB, setIndexB] = useState("");
  const [radiusA, setRadiusA] = useState("");
  const [radiusB, setRadiusB] = useState("");
  const [labTm, setLabTm] = useState("");
  const [mode, setMode] = useState("none");
  const [cFree, setCFree] = useState("1e-8");
  const [tag0, setTag0] = useState("1e-5");
  const [catcher0, setCatcher0] = useState("1e-5");
  const [kLock, setKLock] = useState("");
  const [lg0, setLg0] = useState("");
  const [sm0, setSm0] = useState("");
  const [report, setReport] = useState<ChassisReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function onRun() {
    setError(null);
    const nRepeats = Number(n);
    if (!Number.isInteger(nRepeats) || nRepeats < 3) {
      setError("Repeat count must be an integer of at least 3.");
      return;
    }
    const body: Record<string, unknown> = { n_repeats: nRepeats };
    try {
      if (indexA.trim() || indexB.trim()) {
        const left = Number(indexA);
        const right = Number(indexB);
        if (!Number.isInteger(left) || !Number.isInteger(right)) {
          setError("Docking indexes must both be integers, or both stay empty.");
          return;
        }
        body.indices = [left, right];
      }
      const radii = [optionalPositive(radiusA, "Radius A"), optionalPositive(radiusB, "Radius B")];
      if (radii.some((value) => value !== undefined)) {
        if (radii.some((value) => value === undefined || value <= 0)) {
          setError("Enter both payload radii in angstroms, or leave both empty.");
          return;
        }
        body.radii_A = radii;
      }
      const tm = optionalPositive(labTm, "Lab melting temperature");
      if (tm !== undefined) body.lab_tm_C = tm;
      if (mode === "recruitment") {
        const cFreeM = optionalPositive(cFree, "C_free");
        if (cFreeM === undefined || cFreeM < 0) {
          setError("Recruitment needs a non-negative free concentration in molar.");
          return;
        }
        body.kinetics = { mode: "recruitment_steady", c_free_M: cFreeM };
      }
      if (mode === "covalent") {
        const tag = optionalPositive(tag0, "SpyTag");
        const catcher = optionalPositive(catcher0, "SpyCatcher");
        if (tag === undefined || catcher === undefined || tag <= 0 || catcher <= 0) {
          setError("Covalent locking needs both starting concentrations in molar.");
          return;
        }
        const kinetics: Record<string, unknown> = {
          mode: "covalent_timecourse",
          tag0_M: tag,
          catcher0_M: catcher,
        };
        const rate = optionalPositive(kLock, "k_lock");
        if (rate !== undefined) {
          kinetics.use_literature_priors = false;
          kinetics.spy_k_on_per_M_s = rate;
        }
        body.kinetics = kinetics;
      }
      if (mode === "nanobit") {
        const lg = optionalPositive(lg0, "LgBiT");
        const sm = optionalPositive(sm0, "SmBiT");
        if (lg === undefined || sm === undefined || lg < 0 || sm < 0) {
          setError("NanoBiT needs both starting concentrations in molar.");
          return;
        }
        body.kinetics = { mode: "nanobit_complementation", lg0_M: lg, sm0_M: sm };
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Check the inputs.");
      return;
    }
    setRunning(true);
    try {
      const response = await fetch("/api/ssdk/chassis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string };
        throw new Error(payload.detail || `Run failed (${response.status}).`);
      }
      setReport((await response.json()) as ChassisReport);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Run failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 font-[family-name:var(--font-inter)] text-[#242220]">
      <StudioNav />
      <header className="mb-8">
        <p className="text-sm uppercase tracking-wide text-[#8A8278]">SSDK</p>
        <h1 className="mt-1 text-3xl font-semibold">Four chassis</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
          One length runs the screw, the Phillips melting-temperature model, the
          docking chord, and kinetics. Clash and effective concentration wait
          for both payload radii. A typed melting temperature is compared with
          37 °C and does not replace the literature curve. Kinetics uses a
          concentration you enter, or the Zakeri lock rate until you replace it.
          Empty fields stay empty.{" "}
          <code className="rounded bg-[#F5F0E8] px-1">calibrated = false</code>.
        </p>
      </header>
      {error ? (
        <div className="mb-6 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}
      <section className="mb-6 rounded-xl border border-[#E3D9CC] bg-white p-5">
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Repeat count" value={n} onChange={setN} />
          <Field label="Docking index A, optional" value={indexA} onChange={setIndexA} />
          <Field label="Docking index B, optional" value={indexB} onChange={setIndexB} />
          <Field label="Radius A (Å), optional" value={radiusA} onChange={setRadiusA} />
          <Field label="Radius B (Å), optional" value={radiusB} onChange={setRadiusB} />
          <Field label="Lab Tm (°C), optional" value={labTm} onChange={setLabTm} />
        </div>
        <label className="mt-3 block text-sm">
          Kinetics
          <select
            className="mt-1 w-full rounded-lg border border-[#E3D9CC] bg-white px-3 py-2"
            value={mode}
            onChange={(event) => setMode(event.target.value)}
          >
            <option value="none">Do not run kinetics</option>
            <option value="recruitment">Recruitment steady state</option>
            <option value="covalent">Covalent lock time course</option>
            <option value="nanobit">NanoBiT complementation</option>
          </select>
        </label>
        {mode === "recruitment" ? (
          <Field label="Free concentration (M)" value={cFree} onChange={setCFree} />
        ) : null}
        {mode === "covalent" ? (
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <Field label="SpyTag (M)" value={tag0} onChange={setTag0} />
            <Field label="SpyCatcher (M)" value={catcher0} onChange={setCatcher0} />
            <Field label="Lab k_lock (M⁻¹ s⁻¹), optional" value={kLock} onChange={setKLock} />
          </div>
        ) : null}
        {mode === "nanobit" ? (
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <Field label="LgBiT (M)" value={lg0} onChange={setLg0} />
            <Field label="SmBiT (M)" value={sm0} onChange={setSm0} />
          </div>
        ) : null}
        <Button type="button" className="mt-4" onClick={onRun} disabled={running}>
          {running ? "Running" : "Run four chassis"}
        </Button>
      </section>
      {report ? <Results report={report} /> : null}
      <LearnLuminescencePanel />
    </main>
  );
}

type MfCandidate = {
  n_repeats: number;
  mu_luminescence: number;
  sigma_luminescence: number;
  lower_95_luminescence: number;
  pass_luminescence: boolean;
  acquisition_wet_NanoBiT: number | null;
  physics_score: number;
};

type LearnReport = {
  next_n: number;
  gp_fitted: boolean;
  learner_family?: string;
  learner_requested?: string;
  design_engine_next_n?: number;
  canonical?: {
    sequence_encoding?: string;
    heteroscedastic?: { fitted: boolean };
  };
  multioutput?: {
    overall_status: string;
    omitted_outputs: string[];
    placeholders_unmeasured: string[];
    outputs: Record<string, { fitted: boolean; rows?: { n_repeats: number; mu: number; sigma: number; passes?: boolean }[] }>;
  };
  batch?: {
    selected: { n_repeats: number; score: number; feasibility_weight: number }[];
    reason: string;
  };
  multifidelity_luminescence: {
    fitted: boolean;
    model_version: string;
    threshold_luminescence: { value: number; status: string; units?: string };
    config_placeholders_unmeasured: string[];
    note: string;
    candidates: MfCandidate[];
    recommended_evaluation: {
      n_repeats: number;
      evaluation_type: string;
      acquisition_score: number;
      pass_luminescence_at_recommendation: boolean;
    } | null;
    warnings?: string[];
  };
};

function LearnLuminescencePanel() {
  const [nMin, setNMin] = useState("8");
  const [nMax, setNMax] = useState("14");
  const [obsJson, setObsJson] = useState(
    '[{"n_repeats": 8, "y": 0.4, "fidelity": 1, "source": "surrogate"}]',
  );
  const [learn, setLearn] = useState<LearnReport | null>(null);
  const [learnError, setLearnError] = useState<string | null>(null);
  const [learnRunning, setLearnRunning] = useState(false);

  async function onLearn() {
    setLearnError(null);
    const n_min = Number(nMin);
    const n_max = Number(nMax);
    if (!Number.isInteger(n_min) || !Number.isInteger(n_max) || n_min < 3 || n_max < n_min) {
      setLearnError("n_min and n_max must be integers with n_min ≥ 3 and n_max ≥ n_min.");
      return;
    }
    let observations: unknown;
    try {
      observations = JSON.parse(obsJson);
    } catch {
      setLearnError("Observations must be valid JSON array.");
      return;
    }
    if (!Array.isArray(observations)) {
      setLearnError("Observations must be a JSON array.");
      return;
    }
    setLearnRunning(true);
    try {
      const response = await fetch("/api/ssdk/learn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ n_min, n_max, observations, acquisition: "ei" }),
      });
      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string };
        throw new Error(payload.detail || `Learn failed (${response.status}).`);
      }
      setLearn((await response.json()) as LearnReport);
    } catch (caught) {
      setLearnError(caught instanceof Error ? caught.message : "Learn failed.");
    } finally {
      setLearnRunning(false);
    }
  }

  const mf = learn?.multifidelity_luminescence;

  return (
    <section className="mt-10 rounded-xl border border-[#E3D9CC] bg-white p-5">
      <h2 className="text-lg font-semibold">Predictions &amp; gates (luminescence)</h2>
      <p className="mt-2 max-w-2xl text-sm text-[#5C564E]">
        Two-fidelity GP: dry = docking physics score, wet = your{" "}
        <code className="rounded bg-[#F5F0E8] px-1">y</code> with{" "}
        <code className="rounded bg-[#F5F0E8] px-1">fidelity: 1</code>. Pass uses μ − 1.96σ ≥
        threshold from config (placeholder until measured).{" "}
        <a className="underline" href="/intake">
          Plate intake
        </a>
        . <code className="rounded bg-[#F5F0E8] px-1">calibrated = false</code>.
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Field label="n_min" value={nMin} onChange={setNMin} />
        <Field label="n_max" value={nMax} onChange={setNMax} />
      </div>
      <label className="mt-3 block text-sm">
        Wet observations (JSON)
        <textarea
          className="mt-1 min-h-[88px] w-full rounded-lg border border-[#E3D9CC] px-3 py-2 font-mono text-xs"
          value={obsJson}
          onChange={(event) => setObsJson(event.target.value)}
        />
      </label>
      <Button type="button" className="mt-4" onClick={onLearn} disabled={learnRunning}>
        {learnRunning ? "Learning…" : "Run active learning"}
      </Button>
      {learnError ? (
        <p className="mt-3 text-sm text-red-800">{learnError}</p>
      ) : null}
      {mf ? (
        <div className="mt-4 space-y-3 text-sm">
          <p>
            Model {mf.model_version}. MF fitted: {String(mf.fitted)}. Legacy next_n:{" "}
            {learn?.next_n}. Threshold {formatNumber(mf.threshold_luminescence.value)} (
            {mf.threshold_luminescence.status}).
          </p>
          {mf.config_placeholders_unmeasured.length ? (
            <p className="text-[#8A8278]">
              Unmeasured placeholders: {mf.config_placeholders_unmeasured.join(", ")}
            </p>
          ) : null}
          <p className="text-[#5C564E]">{mf.note}</p>
          {mf.recommended_evaluation ? (
            <p>
              Cost-weighted EI recommends n = {mf.recommended_evaluation.n_repeats} via{" "}
              {mf.recommended_evaluation.evaluation_type} (score{" "}
              {formatNumber(mf.recommended_evaluation.acquisition_score)}).
            </p>
          ) : null}
          {learn?.learner_family ? (
            <p>
              Learner {learn.learner_requested} ran as {learn.learner_family}. Reported next n is{" "}
              {learn.next_n}. Design-engine next n is {learn.design_engine_next_n}. Sequence
              encoding {learn.canonical?.sequence_encoding ?? "none"}. Residual-scatter model{" "}
              {learn.canonical?.heteroscedastic?.fitted ? "fitted" : "not fitted"} (it does not
              replace the assay CV). Multi-output status {learn.multioutput?.overall_status}.
              Omitted assays: {(learn.multioutput?.omitted_outputs || []).join(", ") || "none"}.
            </p>
          ) : null}
          {learn?.multioutput ? (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-[#E3D9CC]">
                    <th className="py-2 pr-2">assay</th>
                    <th className="py-2 pr-2">n</th>
                    <th className="py-2 pr-2">μ</th>
                    <th className="py-2 pr-2">σ</th>
                    <th className="py-2">pass</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(learn.multioutput.outputs)
                    .filter(([, block]) => block.fitted && block.rows)
                    .map(([name, block]) => {
                      const row =
                        block.rows?.find((item) => item.n_repeats === learn.next_n) ??
                        block.rows?.[0];
                      if (!row) return null;
                      return (
                        <tr key={name} className="border-b border-[#F0EBE3]">
                          <td className="py-1.5 pr-2">{name}</td>
                          <td className="py-1.5 pr-2">{row.n_repeats}</td>
                          <td className="py-1.5 pr-2">{formatNumber(row.mu)}</td>
                          <td className="py-1.5 pr-2">{formatNumber(row.sigma)}</td>
                          <td className="py-1.5">
                            {row.passes === undefined ? "—" : row.passes ? "yes" : "no"}
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          ) : null}
          {learn?.batch?.selected?.length ? (
            <p>
              Batch ({learn.batch.selected.length}):{" "}
              {learn.batch.selected.map((item) => item.n_repeats).join(", ")}. {learn.batch.reason}
            </p>
          ) : null}
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-[#E3D9CC]">
                  <th className="py-2 pr-2">n</th>
                  <th className="py-2 pr-2">μ</th>
                  <th className="py-2 pr-2">σ</th>
                  <th className="py-2 pr-2">lower 95%</th>
                  <th className="py-2 pr-2">pass</th>
                  <th className="py-2">EI/cost</th>
                </tr>
              </thead>
              <tbody>
                {mf.candidates.map((row) => (
                  <tr key={row.n_repeats} className="border-b border-[#F0EBE3]">
                    <td className="py-1.5 pr-2">{row.n_repeats}</td>
                    <td className="py-1.5 pr-2">{formatNumber(row.mu_luminescence)}</td>
                    <td className="py-1.5 pr-2">{formatNumber(row.sigma_luminescence)}</td>
                    <td className="py-1.5 pr-2">{formatNumber(row.lower_95_luminescence)}</td>
                    <td className="py-1.5 pr-2">{row.pass_luminescence ? "yes" : "no"}</td>
                    <td className="py-1.5">
                      {row.acquisition_wet_NanoBiT == null
                        ? "—"
                        : formatNumber(row.acquisition_wet_NanoBiT)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function Results({ report }: { report: ChassisReport }) {
  const docking = report.docking;
  const stability = report.stability;
  const kinetics = report.kinetics;
  return (
    <section className="space-y-4 text-sm leading-relaxed">
      <Card title="Structure">
        <p>
          Contour {formatNumber(report.structure.contour_nm)} nm. Axial span{" "}
          {formatNumber(report.structure.axial_span_A)} Å.{" "}
          {report.structure.rigid_screw
            ? `Rigid: the contour is within ${formatNumber(report.structure.persistence_length_nm)} nm.`
            : `Flexible: the contour is past ${formatNumber(report.structure.persistence_length_nm)} nm.`}
        </p>
      </Card>
      <Card title="Stability">
        <p>
          Phillips Tm {formatNumber(stability.tm_C)} °C
          {stability.tm_95_lower_C != null
            ? ` (95% band ${formatNumber(stability.tm_95_lower_C)} to ${formatNumber(stability.tm_95_upper_C)})`
            : ""}
          . Unfolding ΔG {formatNumber(stability.delta_g)} kcal mol⁻¹.
          {stability.past_longest_cited_length
            ? " This length is past the longest cited row."
            : ""}
        </p>
        {stability.lab_tm_C != null ? (
          <p>
            Typed lab Tm {formatNumber(stability.lab_tm_C)} °C is{" "}
            {stability.lab_tm_above_assay ? "above" : "not above"} {stability.t_assay_C} °C.
            The Phillips value is unchanged.
          </p>
        ) : (
          <p>No lab melting temperature was typed.</p>
        )}
      </Card>
      <Card title="Docking">
        <p>
          Indexes {docking.indices.join(" and ")}. Chord {formatNumber(docking.chord_A)} Å
          (95% band {formatNumber(docking.chord_95_low_A)} to {formatNumber(docking.chord_95_high_A)}).
          Facing cosine {formatNumber(docking.facing_cosine)}.
        </p>
        {docking.clash_computable ? (
          <p>
            Clash probability {formatNumber(docking.p_clash)}. Effective concentration{" "}
            {formatNumber(docking.c_eff_M)} M
            {docking.c_eff_95_lower_M != null
              ? ` (95% band ${formatNumber(docking.c_eff_95_lower_M)} to ${formatNumber(docking.c_eff_95_upper_M)})`
              : ""}
            .
          </p>
        ) : (
          <p>Clash and effective concentration were not computed. {docking.missing?.join(" ")}</p>
        )}
        {docking.local_kinetics?.computable && docking.local_kinetics.spy ? (
          <p>
            Tethered Spy k_obs {formatNumber(docking.local_kinetics.spy.k_obs_per_s)} s⁻¹.
            Half-life{" "}
            {docking.local_kinetics.spy.t_half_s == null
              ? docking.local_kinetics.spy.t_half_note
              : `${formatNumber(docking.local_kinetics.spy.t_half_s)} s`}
            . NanoBiT occupancy at this C_eff is{" "}
            {formatNumber(docking.local_kinetics.nanobit?.theta_ss)}. Printed Kd{" "}
            {formatNumber(docking.local_kinetics.nanobit?.printed_kd_M)} M. k_off/k_on{" "}
            {formatNumber(docking.local_kinetics.nanobit?.kinetic_kd_M)} M. k_rev and k_bond
            stay empty.
          </p>
        ) : (
          <p>Tethered rates wait for an effective concentration.</p>
        )}
      </Card>
      <Card title="Kinetics">
        {kinetics.computable ? (
          <p>
            {kinetics.simulation?.mode === "recruitment_steady"
              ? `Steady occupancy ${formatNumber(kinetics.simulation.recruitment?.theta_ss)} (95% band ${formatNumber(kinetics.simulation.recruitment?.theta_95_lower)} to ${formatNumber(kinetics.simulation.recruitment?.theta_95_upper)}).`
              : kinetics.simulation?.mode === "nanobit_complementation"
                ? `Equilibrium complex ${formatNumber(kinetics.simulation.equilibrium_complex_M)} M. k_off/k_on ${formatNumber(kinetics.simulation.rates_used?.kinetic_kd_M)} M. Printed Kd ${formatNumber(kinetics.simulation.rates_used?.printed_kd_M)} M.`
                : "The covalent time course ran from the posted concentrations."}{" "}
            {kinetics.note}
          </p>
        ) : (
          <p>
            {kinetics.missing?.join(" ")} {kinetics.note}
          </p>
        )}
      </Card>
    </section>
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <article className="rounded-xl border border-[#E3D9CC] bg-[#FBF8F3] p-5">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="mt-2 text-[#242220]">{children}</div>
    </article>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="mt-3 block text-sm">
      {label}
      <input
        className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
