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
  };
  kinetics: {
    computable: boolean;
    missing?: string[];
    note?: string;
    simulation?: {
      mode?: string;
      recruitment?: { theta_ss: number; theta_95_lower: number; theta_95_upper: number };
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
        <Button type="button" className="mt-4" onClick={onRun} disabled={running}>
          {running ? "Running" : "Run four chassis"}
        </Button>
      </section>
      {report ? <Results report={report} /> : null}
    </main>
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
      </Card>
      <Card title="Kinetics">
        {kinetics.computable ? (
          <p>
            {kinetics.simulation?.mode === "recruitment_steady"
              ? `Steady occupancy ${formatNumber(kinetics.simulation.recruitment?.theta_ss)} (95% band ${formatNumber(kinetics.simulation.recruitment?.theta_95_lower)} to ${formatNumber(kinetics.simulation.recruitment?.theta_95_upper)}).`
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
