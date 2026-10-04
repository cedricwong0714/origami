"use client";

import { useState } from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StudioNav } from "@/components/studio-nav";
import {
  comparePlateToFrozen,
  importPlate,
  runAblation,
  type Ablation,
  type PlateImport,
  type PlateVsFrozen,
} from "@/lib/intake";

const TEMPLATE =
  "well,construct,n_repeats,batch,role,rlu\n" +
  "A1,CTPR8,8,b1,blank,\n" +
  "B1,CTPR8,8,b1,sample,\n";

function fmt(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  if (abs !== 0 && (abs < 0.01 || abs >= 10000)) return value.toExponential(digits - 1);
  return value.toPrecision(digits);
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="mb-6 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
      <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
      <span>{message}</span>
    </div>
  );
}

export function IntakeBoard() {
  const [csv, setCsv] = useState(TEMPLATE);
  const [plate, setPlate] = useState<PlateImport | null>(null);
  const [plateError, setPlateError] = useState<string | null>(null);
  const [frozen, setFrozen] = useState<PlateVsFrozen | null>(null);
  const [frozenError, setFrozenError] = useState<string | null>(null);
  const [ablationText, setAblationText] = useState("");
  const [ablation, setAblation] = useState<Ablation | null>(null);
  const [ablationError, setAblationError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onImport() {
    setBusy(true);
    setPlateError(null);
    try {
      setPlate(await importPlate(csv, "pasted.csv"));
    } catch (caught) {
      setPlate(null);
      setPlateError(caught instanceof Error ? caught.message : "Import failed.");
    } finally {
      setBusy(false);
    }
  }

  async function onFrozen() {
    setBusy(true);
    setFrozenError(null);
    try {
      setFrozen(await comparePlateToFrozen(csv, "pasted.csv"));
    } catch (caught) {
      setFrozen(null);
      setFrozenError(caught instanceof Error ? caught.message : "Frozen comparison failed.");
    } finally {
      setBusy(false);
    }
  }

  async function onAblation() {
    setBusy(true);
    setAblationError(null);
    try {
      setAblation(await runAblation(JSON.parse(ablationText)));
    } catch (caught) {
      setAblation(null);
      setAblationError(caught instanceof Error ? caught.message : "Ablation failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 font-[family-name:var(--font-inter)] text-[#242220]">
      <StudioNav />
      <header className="mb-8">
        <p className="text-sm uppercase tracking-wide text-[#8A8278]">Dry lab</p>
        <h1 className="mt-1 text-3xl font-semibold">Plate file</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
          Paste one row per well. Blank wells are subtracted within each batch.
          Several wells give an uncertainty. One well does not. Nothing is saved
          on this page. Scoring against a saved prediction needs a calcium_uM
          column. That saved luminescence band is a ±30% placeholder, so a pass
          or fail is not a result.
        </p>
      </header>

      <section className="mb-10">
        <h2 className="mb-2 text-lg font-semibold">1. Plate CSV</h2>
        <label className="mb-1 block text-sm text-[#5C564E]" htmlFor="plate-csv">
          Columns: well, construct, n_repeats, batch, role (sample or blank), rlu.
          Optional calcium_uM matches a frozen dose. Without it, the row is not scored.
        </label>
        <textarea
          id="plate-csv"
          value={csv}
          onChange={(event) => setCsv(event.target.value)}
          rows={8}
          className="w-full rounded-lg border border-[#E3D9CC] bg-white p-3 font-mono text-xs"
        />
        <div className="mt-3">
          <Button onClick={onImport} disabled={busy}>
            Blank-correct and import
          </Button>
          <Button onClick={onFrozen} disabled={busy} variant="outline" className="ml-2">
            Score against frozen scaffolds
          </Button>
        </div>
        {plateError ? <div className="mt-4"><ErrorBox message={plateError} /></div> : null}
        {frozenError ? <div className="mt-4"><ErrorBox message={frozenError} /></div> : null}
        {frozen ? (
          <div className="mt-5 overflow-x-auto rounded-lg border border-[#E3D9CC] bg-white">
            <p className="px-3 py-2 text-xs text-[#5C564E]">
              Parameter error propagated: {frozen.parameter_error.parameter_error_propagated ? "yes" : "no"}.{" "}
              {frozen.parameter_error.reason} {frozen.note}
            </p>
            <table className="w-full text-left text-sm">
              <thead className="bg-[#F5F0E8] text-xs uppercase text-[#8A8278]">
                <tr>
                  {["construct", "n", "calcium µM", "status", "observed", "predicted", "interval"].map((h) => (
                    <th key={h} className="px-3 py-2">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {frozen.comparisons.map((row) => (
                  <tr key={`${row.construct}-${row.n_repeats}-${row.batch}-${row.calcium_uM}`} className="border-t border-[#E3D9CC]">
                    <td className="px-3 py-2">{row.construct}</td>
                    <td className="px-3 py-2">{row.n_repeats}</td>
                    <td className="px-3 py-2">{row.calcium_uM === null ? "—" : row.calcium_uM}</td>
                    <td className="px-3 py-2">{row.status}</td>
                    <td className="px-3 py-2">{fmt(row.observed)}</td>
                    <td className="px-3 py-2">{fmt(row.predicted)}</td>
                    <td className="px-3 py-2">
                      {row.status === "compared" ? (row.within_95ci ? "inside" : "outside") : "not scored"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="border-t border-[#E3D9CC] px-3 py-2 text-xs text-[#8A8278]">
              {frozen.untested_predictions.length} saved predictions have no matching plate column or calcium.
              The luminescence band is still the ±30% placeholder.
            </p>
          </div>
        ) : null}
        {plate ? (
          <div className="mt-5 overflow-x-auto rounded-lg border border-[#E3D9CC] bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#F5F0E8] text-xs uppercase text-[#8A8278]">
                <tr>
                  {["construct", "n", "batch", "wells", "blank mean", "signal (RLU)", "SEM"].map((h) => (
                    <th key={h} className="px-3 py-2">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {plate.observations.map((o) => (
                  <tr key={o.source} className="border-t border-[#E3D9CC]">
                    <td className="px-3 py-2">{o.construct}</td>
                    <td className="px-3 py-2">{o.n_repeats}</td>
                    <td className="px-3 py-2">{o.batch}</td>
                    <td className="px-3 py-2">{o.n_wells}</td>
                    <td className="px-3 py-2">{fmt(o.blank_mean_rlu)}</td>
                    <td className="px-3 py-2">{fmt(o.y)}</td>
                    <td className="px-3 py-2">{o.sigma === null ? "not available (one well)" : fmt(o.sigma)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="border-t border-[#E3D9CC] px-3 py-2 text-xs text-[#8A8278]">
              Method: {plate.normalization_method}. Input SHA-256: {plate.input_sha256 ?? "—"}.
              Gain differences between plates and furimazine decay are not corrected here.
            </p>
          </div>
        ) : null}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">2. Grouped ablation</h2>
        <p className="mb-2 text-sm text-[#5C564E]">
          Optional. Paste a table of inputs, observed readings, model readings, and
          group names. Each group is left out in turn. Use this only when you
          already have those columns. It does not replace the screw or the melt.
        </p>
        <textarea
          aria-label="Ablation JSON"
          value={ablationText}
          onChange={(event) => setAblationText(event.target.value)}
          rows={6}
          placeholder='{"X": [[0.1],[0.2]], "y_obs": [1.1,1.3], "y_mech": [1.0,1.2], "groups": ["b1","b2"]}'
          className="w-full rounded-lg border border-[#E3D9CC] bg-white p-3 font-mono text-xs"
        />
        <div className="mt-3">
          <Button onClick={onAblation} disabled={busy || !ablationText.trim()}>
            Run ablation
          </Button>
        </div>
        {ablationError ? <div className="mt-4"><ErrorBox message={ablationError} /></div> : null}
        {ablation ? (
          <div className="mt-5 overflow-x-auto rounded-lg border border-[#E3D9CC] bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#F5F0E8] text-xs uppercase text-[#8A8278]">
                <tr>
                  {["model", "RMSE", "MAE", "Spearman", "95% coverage", "mean half-width"].map((h) => (
                    <th key={h} className="px-3 py-2">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(ablation.results).map(([name, m]) => (
                  <tr key={name} className="border-t border-[#E3D9CC]">
                    <td className="px-3 py-2">{name}</td>
                    <td className="px-3 py-2">{fmt(m.rmse)}</td>
                    <td className="px-3 py-2">{fmt(m.mae)}</td>
                    <td className="px-3 py-2">{fmt(m.spearman)}</td>
                    <td className="px-3 py-2">{m.coverage_95 === null ? "no interval" : fmt(m.coverage_95)}</td>
                    <td className="px-3 py-2">{fmt(m.mean_half_width)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="border-t border-[#E3D9CC] px-3 py-2 text-xs text-[#5C564E]">
              {ablation.n_rows} rows, {ablation.groups.length} groups, XGBoost active in{" "}
              {ablation.xgb_active_folds} folds.{" "}
              {ablation.xgb_justified
                ? "XGBoost lowered held-out error in every fold."
                : "XGBoost is not justified on this data."}{" "}
              {ablation.note}
            </p>
          </div>
        ) : null}
      </section>
    </main>
  );
}
