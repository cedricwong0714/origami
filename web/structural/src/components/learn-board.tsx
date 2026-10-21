"use client";

import { useEffect, useState } from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StudioNav } from "@/components/studio-nav";
import { readApiJson } from "@/lib/api";

type Row = { n: string; y: string; sigma: string };

type LengthRow = {
  n_repeats: number;
  observed: boolean;
  literature_chord_A: number;
  posterior_mean_A: number;
  posterior_std_A: number;
};

type LengthPosterior = {
  calibrated: false;
  note: string;
  literature_best_n: number;
  issued_next_n: number;
  unconstrained_next_n: { ucb: number; ei: number; entropy: number };
  rows: LengthRow[];
};

type Candidate = {
  n_repeats: number;
  physics_score: number;
  posterior_mean: number;
  posterior_std: number;
  posterior_95_lower: number;
  posterior_95_upper: number;
  interpolated: boolean;
};

type LitPreview = {
  n_repeats: number;
  posterior_mean: number;
  posterior_95_lower: number;
  posterior_95_upper: number;
  in_training_set: boolean;
};

type LitTrack = {
  units: string;
  gp_fitted: boolean;
  training_lengths: number[];
  alpha: number;
  noise_note: string;
  identifiability_note: string;
  training_rows: { n_repeats: number; y: number; sigma: number | null; residual: number }[];
  longest_cited_n: number | null;
  next_n_if_this_observable_were_measured: number;
  next_past_longest_cited_length: boolean;
  next_reason: string;
  preview: LitPreview[];
};

type LiteratureTraining = {
  calibrated: false;
  lab_will_measure_this: false;
  reason: string;
  tm: LitTrack;
  delta_g: LitTrack;
};

type LearnReport = {
  calibrated: false;
  gp_fitted: boolean;
  alpha: number;
  alpha_fixed_at_one: boolean;
  next_n: number;
  next_reason: string;
  radius_origin: string;
  recommendation?: {
    primary_family: string;
    next_n: number;
    design_engine_next_n: number;
    multifidelity_luminescence_n: number | null;
    batch_n: number[];
  };
  chassis_at_next_n?: {
    n_repeats: number;
    calibrated: boolean;
    structure?: { contour_nm: number; rigid_screw: boolean };
    stability?: { tm_C: number; past_longest_cited_length: boolean };
    docking?: { clash_computable: boolean };
    kinetics?: { computable: boolean };
  };
  warnings: string[];
  candidates: Candidate[];
  multifidelity_luminescence?: {
    fitted: boolean;
    model_version: string;
    threshold_luminescence: { value: number; status: string };
    recommended_evaluation: {
      n_repeats: number;
      evaluation_type: string;
      acquisition_score: number;
    } | null;
    candidates: {
      n_repeats: number;
      mu_luminescence: number;
      sigma_luminescence: number;
      pass_luminescence: boolean;
      acquisition_wet_NanoBiT: number | null;
    }[];
    note: string;
  };
  literature_training?: LiteratureTraining;
  slices: {
    structure: { rows: { n_repeats: number; contour_nm: number; rigid_screw: boolean }[] };
    stability: {
      rows: { n_repeats: number; tm_C: number | null; past_longest_cited_length: boolean }[];
    };
    docking: { note: string; radius_origin: string };
    kinetics: { computable: boolean; note?: string };
  };
};

const STARTER: Row[] = [
  { n: "8", y: "", sigma: "" },
  { n: "14", y: "", sigma: "" },
  { n: "17", y: "", sigma: "" },
];

function LiteraturePanel({
  training,
  offline,
}: {
  training: LiteratureTraining | null;
  offline: boolean;
}) {
  if (offline) {
    return (
      <section className="mb-6 rounded-xl border border-studio-border bg-studio-card p-5 text-sm leading-relaxed text-studio-muted">
        The Phillips curves did not load. This host returned a page instead of
        calculator data, so the recommendation cannot run until the Python API
        is connected.
      </section>
    );
  }
  if (!training) {
    return (
      <section className="mb-6 rounded-xl border border-studio-border bg-studio-card p-5 text-sm leading-relaxed text-studio-muted">
        Loading the Phillips 2012 CTPRa DSC residual models.
      </section>
    );
  }
  return (
    <section className="mb-6 rounded-xl border border-studio-border bg-studio-card p-5 text-sm leading-relaxed">
      <h2 className="text-lg font-semibold">Published melting data, already loaded</h2>
      <p className="mt-2 text-studio-muted">
        Phillips 2012 melting temperature and unfolding energy. This lab does
        not measure either one. These rows do not use the luminescence numbers
        below, and they are not a request to run a melt.
      </p>
      <Track title="Melting temperature" track={training.tm} />
      <Track title="Unfolding ΔG at 10 °C, as printed" track={training.delta_g} />
    </section>
  );
}

function Track({ title, track }: { title: string; track: LitTrack }) {
  return (
    <div className="mt-5">
      <h3 className="font-medium">{title}</h3>
      <p className="mt-1 text-studio-muted">
        Published lengths {track.training_lengths.join(", ")}. Units: {track.units}.
        Longest published length: {track.longest_cited_n ?? "not in the table"}.
      </p>
      <ul className="mt-2 list-disc pl-5 text-studio-muted">
        {track.training_rows.map((row) => (
          <li key={row.n_repeats}>
            n = {row.n_repeats}: published {formatNumber(row.y)}
            {row.sigma == null ? ", no uncertainty printed" : ` ± ${formatNumber(row.sigma)}`}.
            Difference from the length fit: {formatNumber(row.residual)}
          </li>
        ))}
      </ul>
      <p className="mt-2">
        If the next length were chosen from this table alone, it would be{" "}
        <strong>{track.next_n_if_this_observable_were_measured}</strong>
        {track.next_past_longest_cited_length ? " (longer than any published row)" : ""}.
        This lab is not measuring melts.
      </p>
      <ul className="mt-2 list-disc pl-5 text-studio-muted">
        {track.preview.map((row) => (
          <li key={row.n_repeats}>
            n = {row.n_repeats}: posterior {formatNumber(row.posterior_mean)} {track.units}, 95% band{" "}
            {formatNumber(row.posterior_95_lower)} to {formatNumber(row.posterior_95_upper)}
            {row.in_training_set ? " (in the Phillips table)" : " (not in the Phillips table)"}
          </li>
        ))}
      </ul>
    </div>
  );
}

function formatNumber(value: number): string {
  const abs = Math.abs(value);
  if (abs !== 0 && (abs < 0.01 || abs >= 1000)) return value.toExponential(3);
  return value.toPrecision(3);
}

function LengthPosteriorPanel() {
  const [report, setReport] = useState<LengthPosterior | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/ssdk/length-posterior")
      .then((response) => readApiJson<LengthPosterior>(response))
      .then((payload) => {
        if (!cancelled) setReport(payload);
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "The length table is unavailable.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="mb-6 rounded-xl border border-studio-border bg-studio-card p-5">
      <h2 className="text-lg font-semibold">Dry-lab end-to-end lengths</h2>
      <p className="mt-1 text-sm leading-relaxed text-studio-muted">
        Crystal chord beside the trajectory posterior, in angstroms. This table
        is not a light reading.
      </p>
      {error ? <p className="mt-3 text-sm text-red-800">{error}</p> : null}
      {report ? (
        <div className="mt-4 space-y-3 text-sm">
          <p>
            The crystal screw ranks n={report.literature_best_n} first. The issued
            next assay, after the stability gate, is n={report.issued_next_n}.
            Without that gate, upper confidence bound and expected improvement
            name n={report.unconstrained_next_n.ucb} and n=
            {report.unconstrained_next_n.ei}. Entropy names n=
            {report.unconstrained_next_n.entropy}. None of these is a validated
            construct.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-studio-label">
                  <th className="py-1 pr-3">n</th>
                  <th className="py-1 pr-3">Screw chord (Å)</th>
                  <th className="py-1 pr-3">Posterior (Å)</th>
                  <th className="py-1">In the trajectory table</th>
                </tr>
              </thead>
              <tbody>
                {report.rows.map((row) => (
                  <tr key={row.n_repeats} className="border-t border-studio-border">
                    <td className="py-1 pr-3">{row.n_repeats}</td>
                    <td className="py-1 pr-3">{row.literature_chord_A.toFixed(1)}</td>
                    <td className="py-1 pr-3">
                      {row.posterior_mean_A.toFixed(1)} ± {row.posterior_std_A.toFixed(1)}
                    </td>
                    <td className="py-1">{row.observed ? "yes" : "no"}</td>
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

export function LearnBoard() {
  const [rows, setRows] = useState<Row[]>(STARTER);
  const [radiusA, setRadiusA] = useState("");
  const [radiusB, setRadiusB] = useState("");
  const [acquisition, setAcquisition] = useState("ucb");
  const [report, setReport] = useState<LearnReport | null>(null);
  const [literature, setLiterature] = useState<LiteratureTraining | null>(null);
  const [literatureOffline, setLiteratureOffline] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadLiterature() {
      try {
        const response = await fetch("/api/ssdk/learn", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ observations: [] }),
        });
        const payload = await readApiJson<LearnReport>(response);
        if (!cancelled && payload.literature_training) {
          setLiterature(payload.literature_training);
        }
      } catch {
        if (!cancelled) setLiteratureOffline(true);
      }
    }
    void loadLiterature();
    return () => {
      cancelled = true;
    };
  }, []);

  function update(index: number, key: keyof Row, value: string) {
    setRows((current) => current.map((row, i) => (i === index ? { ...row, [key]: value } : row)));
  }

  async function onRun() {
    setError(null);
    const observations = [];
    for (const row of rows) {
      if (!row.y.trim()) continue;
      const n = Number(row.n);
      const y = Number(row.y);
      if (!Number.isInteger(n) || !Number.isFinite(y)) {
        setError("Each filled row needs an integer length and a finite surrogate reading.");
        return;
      }
      const item: {
        n_repeats: number;
        y: number;
        sigma?: number;
        source: string;
        fidelity: number;
      } = {
        n_repeats: n,
        y,
        source: "surrogate",
        fidelity: 1,
      };
      if (row.sigma.trim()) {
        const sigma = Number(row.sigma);
        if (!Number.isFinite(sigma) || sigma <= 0) {
          setError("A sigma must be a positive number, or the box stays empty.");
          return;
        }
        item.sigma = sigma;
      }
      observations.push(item);
    }
    const body: Record<string, unknown> = {
      n_min: 3,
      n_max: 24,
      acquisition,
      observations,
    };
    if (radiusA.trim() || radiusB.trim()) {
      const a = Number(radiusA);
      const b = Number(radiusB);
      if (!Number.isFinite(a) || !Number.isFinite(b) || a <= 0 || b <= 0) {
        setError("Enter both payload radii in angstroms, or leave both empty.");
        return;
      }
      body.payload_radii_A = [a, b];
    }
    setRunning(true);
    try {
      const response = await fetch("/api/ssdk/learn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await readApiJson<LearnReport>(response);
      setReport(payload);
      if (payload.literature_training) setLiterature(payload.literature_training);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Run failed.");
    } finally {
      setRunning(false);
    }
  }

  const observed = new Set(
    rows
      .filter((row) => row.y.trim())
      .map((row) => Number(row.n))
      .filter((n) => Number.isInteger(n)),
  );

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 font-[family-name:var(--font-inter)] text-studio-foreground">
      <StudioNav />
      <header className="mb-8">
        <p className="text-sm uppercase tracking-wide text-studio-label">Which length next</p>
        <h1 className="mt-1 text-3xl font-semibold">Next length to measure</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-studio-muted">
          The box below is a light reading, not a distance. An end-to-end length
          in angstroms belongs in the dry-lab table on this page, which is loaded
          separately and is not mixed into the light reading. Leave a light
          reading blank and you still get a suggestion from the docking score.
          Type a luminescence reading and an optional uncertainty to adjust that
          score. The number to use is the first next length. Other methods may
          name a different length. They are not averaged. A pass uses a cutoff
          we have not measured. Do not put that pass on the wiki. The screw and
          the melting temperature are shown beside the suggestion and are not
          changed by the reading.
        </p>
      </header>
      <LengthPosteriorPanel />

      <LiteraturePanel training={literature} offline={literatureOffline} />

      {error ? (
        <div className="mb-6 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      <section className="mb-6 rounded-xl border border-studio-border bg-studio-card p-5">
        <h2 className="text-lg font-semibold">Luminescence readings</h2>
        <p className="mt-1 text-sm leading-relaxed text-studio-muted">
          Repeat count, light reading, optional uncertainty. This number is not
          an angstrom length. Leave the reading blank if that length has not
          been measured.
        </p>
        <div className="mt-4 space-y-2">
          {rows.map((row, index) => (
            <div key={index} className="grid grid-cols-[5rem_1fr_1fr_auto] gap-2">
              <input
                aria-label={`Length ${index + 1}`}
                className="rounded-lg border border-studio-border px-3 py-2"
                value={row.n}
                onChange={(event) => update(index, "n", event.target.value)}
              />
              <input
                aria-label={`Surrogate reading ${index + 1}`}
                className="rounded-lg border border-studio-border px-3 py-2"
                placeholder="Reading"
                value={row.y}
                onChange={(event) => update(index, "y", event.target.value)}
              />
              <input
                aria-label={`Sigma ${index + 1}`}
                className="rounded-lg border border-studio-border px-3 py-2"
                placeholder="Uncertainty, optional"
                value={row.sigma}
                onChange={(event) => update(index, "sigma", event.target.value)}
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => setRows((current) => current.filter((_, i) => i !== index))}
                disabled={rows.length === 1}
              >
                Remove
              </Button>
            </div>
          ))}
        </div>
        <Button
          type="button"
          variant="outline"
          className="mt-3"
          onClick={() => setRows((current) => [...current, { n: "", y: "", sigma: "" }])}
        >
          Add length
        </Button>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            Payload radius A (Å), optional
            <input
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2"
              value={radiusA}
              onChange={(event) => setRadiusA(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Payload radius B (Å), optional
            <input
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2"
              value={radiusB}
              onChange={(event) => setRadiusB(event.target.value)}
            />
          </label>
        </div>
        <label className="mt-3 block text-sm">
            How to pick the next length
          <select
            className="mt-1 w-full rounded-lg border border-studio-border bg-studio-card px-3 py-2"
            value={acquisition}
            onChange={(event) => setAcquisition(event.target.value)}
          >
            <option value="ucb">High score and high uncertainty</option>
            <option value="ei">Largest expected gain</option>
            <option value="entropy">Highest uncertainty</option>
          </select>
        </label>
        <Button type="button" className="mt-4" onClick={onRun} disabled={running}>
          {running ? "Running" : "Recommend next length"}
        </Button>
      </section>

      {report ? (
        <section className="rounded-xl border border-studio-border bg-studio-surface p-5 text-sm leading-relaxed">
          <h2 className="text-lg font-semibold">Next measurement</h2>
          <p className="mt-2">
            Measure repeat count <strong>{report.next_n}</strong>. This is the length to run next. It is not a claim that the design works.
          </p>
          {report.recommendation ? (
            <p className="mt-2 text-studio-muted">
              Luminescence fit: n = {report.recommendation.next_n}. Docking-score
              fit: n = {report.recommendation.design_engine_next_n}. Luminescence
              with dry and lab readings: n = {report.recommendation.multifidelity_luminescence_n ?? "none"}.
              Lengths to run together: {report.recommendation.batch_n.join(", ") || "none"}.
              Use the first. They are not averaged.
            </p>
          ) : null}
          {report.chassis_at_next_n ? (
            <p className="mt-2 text-studio-muted">
              At n = {report.chassis_at_next_n.n_repeats}: length along the repeats{" "}
              {report.chassis_at_next_n.structure
                ? `${formatNumber(report.chassis_at_next_n.structure.contour_nm)} nm`
                : "omitted"}
              ,{" "}
              {report.chassis_at_next_n.structure?.rigid_screw
                ? "rigid under the 15 nm cutoff"
                : "past the 15 nm cutoff"}
              . Melting temperature{" "}
              {report.chassis_at_next_n.stability?.tm_C == null
                ? "omitted"
                : `${formatNumber(report.chassis_at_next_n.stability.tm_C)} °C`}
              . Clash{" "}
              {report.chassis_at_next_n.docking?.clash_computable ? "computed" : "not computed (no radii)"}.
              Binding{" "}
              {report.chassis_at_next_n.kinetics?.computable ? "computed" : "not computed"}.
            </p>
          ) : null}
          <p className="mt-2 text-studio-muted">
            {report.radius_origin === "caller"
              ? "Clash used the radii you typed."
              : "No radii were typed, so clash used the CaM–M13 size from PDB 2BBM only inside the docking score. It is not a measured radius."}{" "}
            {report.slices.docking.note}
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-studio-muted">
                  <th className="py-1 pr-3">n</th>
                  <th className="py-1 pr-3">Physics</th>
                  <th className="py-1 pr-3">Posterior</th>
                  <th className="py-1">95% band</th>
                </tr>
              </thead>
              <tbody>
                {report.candidates
                  .filter(
                    (row) =>
                      observed.has(row.n_repeats) ||
                      row.n_repeats === report.next_n ||
                      row.n_repeats === 8 ||
                      row.n_repeats === 14 ||
                      row.n_repeats === 17,
                  )
                  .map((row) => (
                    <tr key={row.n_repeats}>
                      <td className="py-1 pr-3">{row.n_repeats}</td>
                      <td className="py-1 pr-3">{formatNumber(row.physics_score)}</td>
                      <td className="py-1 pr-3">{formatNumber(row.posterior_mean)}</td>
                      <td className="py-1">
                        {formatNumber(row.posterior_95_lower)} to {formatNumber(row.posterior_95_upper)}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          <h3 className="mt-4 font-medium">Structure and stability at the highlighted lengths</h3>
          <ul className="mt-2 list-disc pl-5 text-studio-muted">
            {report.slices.structure.rows.map((row) => {
              const tm = report.slices.stability.rows.find((item) => item.n_repeats === row.n_repeats);
              return (
                <li key={row.n_repeats}>
                  n = {row.n_repeats}: contour {formatNumber(row.contour_nm)} nm,{" "}
                  {row.rigid_screw ? "rigid under the 15 nm cutoff" : "past the 15 nm cutoff"}.
                  Phillips Tm {tm?.tm_C == null ? "omitted" : `${formatNumber(tm.tm_C)} °C`}
                  {tm?.past_longest_cited_length ? " (past the longest cited length)." : "."}
                </li>
              );
            })}
          </ul>
          {report.multifidelity_luminescence &&
          report.multifidelity_luminescence.fitted &&
          report.multifidelity_luminescence.threshold_luminescence.status !== "unmeasured" ? (
            <div className="mt-6 border-t border-studio-border pt-4">
              <h3 className="font-medium">Multi-fidelity luminescence gates</h3>
              <p className="mt-1 text-studio-muted">{report.multifidelity_luminescence.note}</p>
              {report.multifidelity_luminescence.recommended_evaluation ? (
                <p className="mt-2">
                  EI/cost → n ={" "}
                  {report.multifidelity_luminescence.recommended_evaluation.n_repeats} (
                  {report.multifidelity_luminescence.recommended_evaluation.evaluation_type})
                </p>
              ) : null}
              <p className="mt-1 text-xs text-studio-label">
                Threshold {report.multifidelity_luminescence.threshold_luminescence.value} (
                {report.multifidelity_luminescence.threshold_luminescence.status})
              </p>
            </div>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}
