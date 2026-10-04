"use client";

import { useState, type ReactNode } from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StudioNav } from "@/components/studio-nav";
import { runLab, type LabRun, type Ratio, type SectionResult } from "@/lib/lab";

function pairs(text: string): { left: number[]; right: number[] } | null {
  const left: number[] = [];
  const right: number[] = [];
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const parts = trimmed.split(/[\s,]+/).filter(Boolean);
    if (parts.length !== 2) return null;
    const a = Number(parts[0]);
    const b = Number(parts[1]);
    if (!Number.isFinite(a) || !Number.isFinite(b)) return null;
    left.push(a);
    right.push(b);
  }
  return { left, right };
}

function optionalNumber(text: string): number | undefined {
  const trimmed = text.trim();
  if (!trimmed) return undefined;
  const value = Number(trimmed);
  return Number.isFinite(value) ? value : undefined;
}

function formatNumber(value: unknown, digits = 3): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  if (abs !== 0 && (abs < 0.01 || abs >= 1000)) return value.toExponential(digits);
  return value.toPrecision(digits);
}

function band(result: SectionResult, lowerKey: string, upperKey: string): string {
  const lower = result[lowerKey];
  const upper = result[upperKey];
  if (typeof lower !== "number" || typeof upper !== "number") return "uncertainty omitted";
  return `95% band ${formatNumber(lower)} to ${formatNumber(upper)}`;
}

function ratioLine(label: string, ratio: Ratio | undefined): string {
  if (!ratio) return `${label}: not computed`;
  const spread =
    ratio.sigma === null
      ? "uncertainty omitted"
      : `95% band ${formatNumber(ratio.interval_95_lower)} to ${formatNumber(ratio.interval_95_upper)}`;
  return `${label}: ${formatNumber(ratio.value)} (${spread})`;
}

function missingLine(result: SectionResult): string | null {
  if (result.computable) return null;
  const missing = result.missing ?? [];
  if (missing.length === 0) return "This section was not submitted.";
  return missing.join(" ");
}

export function LabBoard() {
  const [constructId, setConstructId] = useState("");
  const [nRepeats, setNRepeats] = useState("8");
  const [concentration, setConcentration] = useState("");
  const [expressed, setExpressed] = useState(false);
  const [nativeShift, setNativeShift] = useState(false);
  const [massOk, setMassOk] = useState(false);
  const [standardText, setStandardText] = useState("");
  const [decayText, setDecayText] = useState("");
  const [cvText, setCvText] = useState("");
  const [rluLow, setRluLow] = useState("");
  const [rluHigh, setRluHigh] = useState("");
  const [checkRlu, setCheckRlu] = useState("");
  const [calciumText, setCalciumText] = useState("");
  const [wtRlu, setWtRlu] = useState("");
  const [scrambledRlu, setScrambledRlu] = useState("");
  const [rlu25, setRlu25] = useState("");
  const [rlu30, setRlu30] = useState("");
  const [rlu37, setRlu37] = useState("");
  const [lockText, setLockText] = useState("");
  const [tag0, setTag0] = useState("");
  const [catcher0, setCatcher0] = useState("");
  const [rateLaw, setRateLaw] = useState("second_order");
  const [excess, setExcess] = useState("tag");
  const [sds, setSds] = useState("");
  const [tube1, setTube1] = useState("");
  const [tube2, setTube2] = useState("");
  const [tube3, setTube3] = useState("");
  const [tube4, setTube4] = useState("");
  const [bridgeM, setBridgeM] = useState("5e-8");
  const [hookM, setHookM] = useState("1e-6");
  const [report, setReport] = useState<LabRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function onRun() {
    setError(null);
    const body: Record<string, unknown> = {};
    const prep: Record<string, unknown> = {
      expresses: expressed,
      native_page_shift: nativeShift,
      mass_within_10_percent: massOk,
    };
    if (constructId.trim()) prep.construct_id = constructId.trim();
    const n = optionalNumber(nRepeats);
    if (n !== undefined) prep.n_repeats = Math.round(n);
    const conc = optionalNumber(concentration);
    if (conc !== undefined) prep.concentration_uM = conc;
    body.prep = prep;

    const window: Record<string, unknown> = {};
    if (standardText.trim()) {
      const parsed = pairs(standardText);
      if (!parsed) {
        setError("Standard curve lines must be two numbers: amount, then RLU.");
        return;
      }
      window.standard_curve = { amount: parsed.left, rlu: parsed.right };
    }
    if (decayText.trim()) {
      const parsed = pairs(decayText);
      if (!parsed) {
        setError("Furimazine lines must be two numbers: minutes, then RLU.");
        return;
      }
      window.furimazine = { time_min: parsed.left, rlu: parsed.right };
    }
    if (cvText.trim()) {
      const values = cvText
        .split(/[\s,]+/)
        .filter(Boolean)
        .map(Number);
      if (values.some((value) => !Number.isFinite(value))) {
        setError("CV values must be finite numbers.");
        return;
      }
      window.cv_values = values;
    }
    const low = optionalNumber(rluLow);
    const high = optionalNumber(rluHigh);
    const check = optionalNumber(checkRlu);
    if (low !== undefined) window.rlu_low = low;
    if (high !== undefined) window.rlu_high = high;
    if (check !== undefined) window.check_rlu = check;
    if (Object.keys(window).length > 0) body.assay_window = window;

    const calcium: Record<string, unknown> = {};
    if (calciumText.trim()) {
      const parsed = pairs(calciumText);
      if (!parsed) {
        setError("Calcium lines must be two numbers: concentration in molar, then RLU.");
        return;
      }
      calcium.ca_M = parsed.left;
      calcium.rlu = parsed.right;
    }
    const wt = optionalNumber(wtRlu);
    const scrambled = optionalNumber(scrambledRlu);
    if (wt !== undefined) calcium.wt_rlu = wt;
    if (scrambled !== undefined) calcium.scrambled_rlu = scrambled;
    const t25 = optionalNumber(rlu25);
    const t30 = optionalNumber(rlu30);
    const t37 = optionalNumber(rlu37);
    if (t25 !== undefined) calcium.rlu_25_C = t25;
    if (t30 !== undefined) calcium.rlu_30_C = t30;
    if (t37 !== undefined) calcium.rlu_37_C = t37;
    if (Object.keys(calcium).length > 0) body.calcium = calcium;

    if (lockText.trim() || tag0.trim() || catcher0.trim()) {
      const parsed = pairs(lockText);
      if (!parsed) {
        setError("Lock lines must be two numbers: minutes, then fraction locked.");
        return;
      }
      const tag = optionalNumber(tag0);
      const catcher = optionalNumber(catcher0);
      if (tag === undefined || catcher === undefined) {
        setError("Enter both SpyTag and SpyCatcher starting concentrations in molar.");
        return;
      }
      const lock: Record<string, unknown> = {
        time_min: parsed.left,
        fraction_locked: parsed.right,
        tag0_M: tag,
        catcher0_M: catcher,
        rate_law: rateLaw,
      };
      if (rateLaw === "pseudo_first_order") lock.excess_partner = excess;
      if (sds === "yes") lock.sds_survives = true;
      if (sds === "no") lock.sds_survives = false;
      body.lock = lock;
    }

    const tubes = [tube1, tube2, tube3, tube4].map(optionalNumber);
    if (tubes.some((value) => value !== undefined)) {
      if (tubes.some((value) => value === undefined)) {
        setError("Enter all four bridging RLU values, or leave all four empty.");
        return;
      }
      body.bridging = {
        tube1_rlu: tubes[0],
        tube2_rlu: tubes[1],
        tube3_rlu: tubes[2],
        tube4_rlu: tubes[3],
        streptavidin_bridge_M: optionalNumber(bridgeM),
        streptavidin_hook_M: optionalNumber(hookM),
      };
    }

    setRunning(true);
    try {
      setReport(await runLab(body));
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
        <p className="text-sm uppercase tracking-wide text-[#8A8278]">Dry lab</p>
        <h1 className="mt-1 text-3xl font-semibold">Lab numbers</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
          Paste numbers you have already measured. Empty boxes stay empty.
          The page can fit a calcium curve, a Spy lock time course, and the
          four-tube bridge. A gel or a concentration is recorded as itself.
          It does not become a radius or a melting temperature.
        </p>
      </header>

      {error ? (
        <div className="mb-6 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      <section className="mb-6 rounded-xl border border-[#E3D9CC] bg-white p-5">
        <h2 className="text-lg font-semibold">Prep</h2>
        <p className="mt-1 text-sm leading-relaxed text-[#5C564E]">
          BCA or Bradford concentration, and the gel calls. A checked box only
          records what the gel showed. It does not change the screw.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <Field label="Construct id" value={constructId} onChange={setConstructId} />
          <Field label="Repeat count" value={nRepeats} onChange={setNRepeats} />
          <Field
            label="Concentration (µM)"
            value={concentration}
            onChange={setConcentration}
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-4 text-sm">
          <Check label="Expressed on the gel" checked={expressed} onChange={setExpressed} />
          <Check label="Mass within 10% of predicted" checked={massOk} onChange={setMassOk} />
          <Check label="Native PAGE shifted" checked={nativeShift} onChange={setNativeShift} />
        </div>
      </section>

      <section className="mb-6 rounded-xl border border-[#E3D9CC] bg-white p-5">
        <h2 className="text-lg font-semibold">Assay window</h2>
        <p className="mt-1 text-sm leading-relaxed text-[#5C564E]">
          One line per point. The standard curve is RLU = a + b × amount. The
          furimazine series is minutes and RLU. CV is a list of replicate
          readings of the same sample.
        </p>
        <TextBlock
          label="Standard curve: amount, RLU"
          value={standardText}
          onChange={setStandardText}
          placeholder={"0 100\n1 180\n2 260"}
        />
        <TextBlock
          label="Furimazine: minutes, RLU"
          value={decayText}
          onChange={setDecayText}
          placeholder={"0 1000\n10 500\n20 250"}
        />
        <Field label="CV replicates" value={cvText} onChange={setCvText} />
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <Field label="Linear range low (RLU)" value={rluLow} onChange={setRluLow} />
          <Field label="Linear range high (RLU)" value={rluHigh} onChange={setRluHigh} />
          <Field label="RLU to check" value={checkRlu} onChange={setCheckRlu} />
        </div>
      </section>

      <section className="mb-6 rounded-xl border border-[#E3D9CC] bg-white p-5">
        <h2 className="text-lg font-semibold">Calcium response</h2>
        <p className="mt-1 text-sm leading-relaxed text-[#5C564E]">
          Free calcium in molar, then luminescence. The fit reports an EC50 for
          this curve. That EC50 does not replace the peptide Kd. Four or more
          concentrations are required. Temperatures are 25 °C, 30 °C, and 37 °C
          luminosities, not a melting temperature.
        </p>
        <TextBlock
          label="Calcium (M), RLU"
          value={calciumText}
          onChange={setCalciumText}
          placeholder={"1e-8 20\n1e-6 100\n1e-4 180\n1e-3 190"}
        />
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Field label="Wild-type M13 RLU" value={wtRlu} onChange={setWtRlu} />
          <Field label="Scrambled M13 RLU" value={scrambledRlu} onChange={setScrambledRlu} />
          <Field label="RLU at 25 °C" value={rlu25} onChange={setRlu25} />
          <Field label="RLU at 30 °C" value={rlu30} onChange={setRlu30} />
          <Field label="RLU at 37 °C" value={rlu37} onChange={setRlu37} />
        </div>
      </section>

      <section className="mb-6 rounded-xl border border-[#E3D9CC] bg-white p-5">
        <h2 className="text-lg font-semibold">SpyCatcher lock</h2>
        <p className="mt-1 text-sm leading-relaxed text-[#5C564E]">
          Fraction locked at each minute, plus both starting concentrations in
          molar. The default law is the lumped irreversible step. Choose
          pseudo-first-order only when you know which partner is in excess. A
          flat gel returns no rate.
        </p>
        <TextBlock
          label="Minutes, fraction locked"
          value={lockText}
          onChange={setLockText}
          placeholder={"0 0\n2 0.2\n5 0.4\n10 0.6\n30 0.8\n60 0.9"}
        />
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Field label="SpyTag (M)" value={tag0} onChange={setTag0} />
          <Field label="SpyCatcher (M)" value={catcher0} onChange={setCatcher0} />
        </div>
        <label className="mt-3 block text-sm">
          Rate law
          <select
            className="mt-1 w-full rounded-lg border border-[#E3D9CC] bg-white px-3 py-2"
            value={rateLaw}
            onChange={(event) => setRateLaw(event.target.value)}
          >
            <option value="second_order">Second-order, both partners depleted</option>
            <option value="pseudo_first_order">Pseudo-first-order, one partner in excess</option>
          </select>
        </label>
        {rateLaw === "pseudo_first_order" ? (
          <label className="mt-3 block text-sm">
            Partner in excess
            <select
              className="mt-1 w-full rounded-lg border border-[#E3D9CC] bg-white px-3 py-2"
              value={excess}
              onChange={(event) => setExcess(event.target.value)}
            >
              <option value="tag">SpyTag</option>
              <option value="catcher">SpyCatcher</option>
            </select>
          </label>
        ) : null}
        <label className="mt-3 block text-sm">
          Band still present after EGTA and SDS
          <select
            className="mt-1 w-full rounded-lg border border-[#E3D9CC] bg-white px-3 py-2"
            value={sds}
            onChange={(event) => setSds(event.target.value)}
          >
            <option value="">Not recorded</option>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
        </label>
      </section>

      <section className="mb-6 rounded-xl border border-[#E3D9CC] bg-white p-5">
        <h2 className="text-lg font-semibold">Four-tube bridge</h2>
        <p className="mt-1 text-sm leading-relaxed text-[#5C564E]">
          Tube 1 is background, tube 2 is the bridge, tube 3 is biotin-blocked
          streptavidin, and tube 4 is the hook-effect tube. The streptavidin
          boxes start at the protocol setpoints, 50 nM and 1 µM. Edit them if
          the tube you ran used a different concentration. They are not a fitted
          Kd.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Field label="Tube 1 RLU" value={tube1} onChange={setTube1} />
          <Field label="Tube 2 RLU" value={tube2} onChange={setTube2} />
          <Field label="Tube 3 RLU" value={tube3} onChange={setTube3} />
          <Field label="Tube 4 RLU" value={tube4} onChange={setTube4} />
          <Field label="Bridge streptavidin (M)" value={bridgeM} onChange={setBridgeM} />
          <Field label="Hook streptavidin (M)" value={hookM} onChange={setHookM} />
        </div>
      </section>

      <Button type="button" onClick={onRun} disabled={running}>
        {running ? "Running" : "Fit the numbers you pasted"}
      </Button>

      {report ? <Report report={report} /> : null}
    </main>
  );
}

function Report({ report }: { report: LabRun }) {
  const dose = report.calcium.dose_response;
  const lock = report.lock;
  const bridge = report.bridging;
  const curve = report.assay_window.standard_curve;
  const decay = report.assay_window.furimazine;
  const cv = report.assay_window.cv;
  const range = report.assay_window.linear_range;
  const context = report.prep.structure_context;
  return (
    <section className="mt-8 rounded-xl border border-[#E3D9CC] bg-[#FBF8F3] p-5 text-sm leading-relaxed">
      <h2 className="text-lg font-semibold">Results</h2>
      <p className="mt-2 text-[#5C564E]">
        No luminescence model was fit to these rows. The fit stays unfitted
        {report.residual_gp.n_rows > 0
          ? ` (${report.residual_gp.n_rows} stored rows). `
          : ". "}
        {report.residual_gp.reason}
      </p>
      {context ? (
        <p className="mt-3">
          The screw model for {context.n_repeats} repeats has a contour of{" "}
          {formatNumber(context.contour_nm)} nm and is{" "}
          {context.rigid_screw ? "inside" : "past"} the 15 nm rigid cutoff.{" "}
          {context.source}
        </p>
      ) : null}
      <Block title="Standard curve" result={curve}>
        {curve.computable ? (
          <p>
            Slope {formatNumber(curve.slope)} RLU per amount unit,{" "}
            {band(curve, "slope_95_lower", "slope_95_upper")}. Intercept{" "}
            {formatNumber(curve.intercept)}.
          </p>
        ) : null}
      </Block>
      <Block title="Furimazine half-life" result={decay}>
        {decay.computable ? (
          <p>
            {formatNumber(decay.half_life_min)} min,{" "}
            {band(decay, "half_life_95_lower_min", "half_life_95_upper_min")}.
          </p>
        ) : null}
      </Block>
      <Block title="CV" result={cv}>
        {cv.computable ? <p>CV = {formatNumber(cv.cv)}.</p> : null}
      </Block>
      <Block title="Linear range" result={range}>
        {range.computable ? (
          <p>{range.admissible ? "Inside the stored window." : "Outside the stored window."}</p>
        ) : null}
      </Block>
      <Block title="Calcium EC50" result={dose}>
        {dose.computable ? (
          <p>
            EC50 {formatNumber(dose.ec50_M)} M, {band(dose, "ec50_95_lower_M", "ec50_95_upper_M")}.
            Hill slope {formatNumber(dose.hill)}
            {dose.hill_fixed_at_one ? " (fixed at 1)." : "."} This does not replace the peptide Kd.
          </p>
        ) : null}
      </Block>
      <Block title="Scrambled M13" result={report.calcium.specificity}>
        {report.calcium.specificity.computable ? (
          <p>Ratio {formatNumber(report.calcium.specificity.ratio)}.</p>
        ) : null}
      </Block>
      <Block title="Lock rate" result={lock}>
        {lock.computable ? (
          <p>
            k_lock {formatNumber(lock.k_lock_per_M_s)} M⁻¹ s⁻¹,{" "}
            {band(lock, "k_lock_95_lower_per_M_s", "k_lock_95_upper_per_M_s")}. Literature
            reference beside this fit: {formatNumber(lock.literature_k_on_per_M_s)} M⁻¹ s⁻¹
            (Zakeri 2012). k_rev and k_bond were not fit.
          </p>
        ) : null}
      </Block>
      <Block title="Bridge" result={bridge}>
        {bridge.computable ? (
          <div>
            <p>{ratioLine("Signal / background", bridge.signal_over_background)}</p>
            <p>{ratioLine("Competition / bridge", bridge.competition_over_bridge)}</p>
            <p>{ratioLine("Hook / bridge", bridge.hook_over_bridge)}</p>
            <p>
              {bridge.pattern_holds
                ? "The sign pattern holds: tube 2 is above background, and tubes 3 and 4 are below tube 2."
                : "The sign pattern does not hold."}
            </p>
          </div>
        ) : null}
      </Block>
    </section>
  );
}

function Block({
  title,
  result,
  children,
}: {
  title: string;
  result: SectionResult;
  children: ReactNode;
}) {
  const missing = missingLine(result);
  return (
    <div className="mt-4">
      <h3 className="font-medium">{title}</h3>
      {missing ? <p className="text-[#5C564E]">{missing}</p> : children}
      {result.warnings && result.warnings.length > 0 ? (
        <p className="text-[#5C564E]">{result.warnings[0]}</p>
      ) : null}
    </div>
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
    <label className="block text-sm">
      {label}
      <input
        className="mt-1 w-full rounded-lg border border-[#E3D9CC] bg-white px-3 py-2"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function TextBlock({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <label className="mt-3 block text-sm">
      {label}
      <textarea
        className="mt-1 w-full rounded-lg border border-[#E3D9CC] bg-white px-3 py-2 font-mono text-xs"
        rows={4}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function Check({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      {label}
    </label>
  );
}
