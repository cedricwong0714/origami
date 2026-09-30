"use client";

import { useEffect, useState, type FormEvent } from "react";
import { SERIES_COPY } from "@/lib/stability";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { StudioNav } from "@/components/studio-nav";
import {
  CALORIMETRY_MISSING,
  CURVE_LABEL,
  CURVE_T_MAX_C,
  CURVE_T_MIN_C,
  THERMO_EQUATION,
  energyUnitLabel,
  formatQuantity,
  loadSnapshotIndex,
  loadThermoPrefill,
  postThermo,
  postThermoCurve,
  repeatCounts,
  seriesTitle,
  type EnergyUnits,
  type ThermoCurve,
  type ThermoPrefill,
  type ThermoReport,
} from "@/lib/thermo";

const CHART_FONT = "var(--font-inter), Inter, sans-serif";
const DEFAULT_SERIES_ID =
  SERIES_COPY.find((item) => item.isDefault)?.id ?? "phillips2012_ctpra_dsc";

const CELSIUS_TO_KELVIN = 273.15;

type FieldErrors = {
  temperature: string | null;
  form: string | null;
};

function emptyErrors(): FieldErrors {
  return { temperature: null, form: null };
}

function tmCaption(tmC: string, prefill: ThermoPrefill | null): string | null {
  const typed = parseRequired(tmC);
  if (typed === null) {
    if (prefill?.tmStatus === "extrapolated") {
      return "No cited Tm. This length stays extrapolated. Type a Tm to calculate; that value is a user-entered Tm, not a cited one.";
    }
    if (prefill && prefill.tmC === null) {
      return "No cited Tm. A temperature you type is a user-entered Tm, not a cited one.";
    }
    return null;
  }
  if (prefill?.tmC != null && typed === prefill.tmC) {
    return "Cited Tm from the selected series. It was copied from the literature row, not calculated.";
  }
  return "User-entered Tm, not a cited melting temperature.";
}

function formatAtTm(value: number): string {
  if (Number.isFinite(value) && Math.abs(value) < 1e-9) return "0";
  return formatQuantity(value);
}

function parseRequired(raw: string): number | null {
  const trimmed = raw.trim();
  if (trimmed === "") return null;
  const value = Number(trimmed);
  if (!Number.isFinite(value)) return null;
  return value;
}

function parseOptionalSigma(raw: string): number | undefined | null {
  const trimmed = raw.trim();
  if (trimmed === "") return undefined;
  const value = Number(trimmed);
  if (!Number.isFinite(value) || value < 0) return null;
  return value;
}

function curveWindow(tmC: number): { tMinC: number; tMaxC: number } {
  return {
    tMinC: Math.min(CURVE_T_MIN_C, tmC),
    tMaxC: Math.max(CURVE_T_MAX_C, tmC),
  };
}

function CurveChart({
  title,
  units,
  color,
  points,
  tmC,
  read,
}: {
  title: string;
  units: string;
  color: string;
  points: ThermoCurve["points"];
  tmC: number;
  read: (point: ThermoCurve["points"][number]) => number;
}) {
  const width = 640;
  const height = 220;
  const pad = { l: 72, r: 16, t: 28, b: 36 };
  const xs = points.map((point) => point.t_c);
  const ys = points.map(read);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  let yMin = Math.min(...ys);
  let yMax = Math.max(...ys);
  if (yMin === yMax) {
    yMin -= 1;
    yMax += 1;
  }
  const yPad = (yMax - yMin) * 0.08;
  yMin -= yPad;
  yMax += yPad;
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const xOf = (value: number) => pad.l + ((value - xMin) / (xMax - xMin || 1)) * innerW;
  const yOf = (value: number) => pad.t + (1 - (value - yMin) / (yMax - yMin || 1)) * innerH;
  const path = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${xOf(point.t_c).toFixed(2)} ${yOf(read(point)).toFixed(2)}`)
    .join(" ");
  const yTicks = [yMin + yPad, (yMin + yMax) / 2, yMax - yPad];
  const showZero = yMin < 0 && yMax > 0;
  const summary = `${title} in ${units}, from ${formatQuantity(xs[0] ?? 0)} °C to ${formatQuantity(xs[xs.length - 1] ?? 0)} °C.`;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" role="img" aria-label={summary} style={{ fontFamily: CHART_FONT }}>
      <text x={pad.l} y={16} fill="#242220" fontSize="13" fontFamily={CHART_FONT}>
        {title} ({units})
      </text>
      {yTicks.map((tick) => (
        <g key={tick}>
          <line x1={pad.l} x2={width - pad.r} y1={yOf(tick)} y2={yOf(tick)} stroke="#E3D9CC" />
          <text x={8} y={yOf(tick) + 4} fill="#8A8175" fontSize="11" fontFamily={CHART_FONT}>
            {formatQuantity(tick)}
          </text>
        </g>
      ))}
      {showZero ? (
        <line x1={pad.l} x2={width - pad.r} y1={yOf(0)} y2={yOf(0)} stroke="#C45C12" strokeDasharray="4 4" />
      ) : null}
      <line x1={xOf(tmC)} x2={xOf(tmC)} y1={pad.t} y2={height - pad.b} stroke="#8A8175" strokeDasharray="3 3" />
      <text x={xOf(tmC) + 4} y={pad.t + 12} fill="#5C564E" fontSize="11" fontFamily={CHART_FONT}>
        Tm
      </text>
      <path d={path} fill="none" stroke={color} strokeWidth="2" />
      <text x={pad.l} y={height - 10} fill="#8A8175" fontSize="11" fontFamily={CHART_FONT}>
        temperature (°C)
      </text>
      <text x={width - pad.r} y={height - 10} textAnchor="end" fill="#8A8175" fontSize="11" fontFamily={CHART_FONT}>
        {formatQuantity(xMax)} °C
      </text>
    </svg>
  );
}

function Band({
  defined,
  sigma,
  low,
  high,
  units,
}: {
  defined: boolean;
  sigma: number | null;
  low: number | null;
  high: number | null;
  units: string;
}) {
  if (!defined || sigma === null || low === null || high === null) return null;
  return (
    <p className="text-sm text-[#5C564E]">
      95% band {formatQuantity(low)} to {formatQuantity(high)} {units} (± 1.96 × {formatQuantity(sigma)})
    </p>
  );
}

export function ThermoCalculator() {
  const [units, setUnits] = useState<EnergyUnits>("kcal");
  const [tC, setTC] = useState("");
  const [tmC, setTmC] = useState("");
  const [deltaH, setDeltaH] = useState("");
  const [deltaCp, setDeltaCp] = useState("");
  const [deltaHSigma, setDeltaHSigma] = useState("");
  const [deltaCpSigma, setDeltaCpSigma] = useState("");
  const [tmSigmaC, setTmSigmaC] = useState("");
  const [seriesId, setSeriesId] = useState<string>(DEFAULT_SERIES_ID);
  const [nText, setNText] = useState("3");
  const [seriesIds, setSeriesIds] = useState<string[]>(SERIES_COPY.map((item) => item.id));
  const [nOptions, setNOptions] = useState<number[]>([]);
  const [prefill, setPrefill] = useState<ThermoPrefill | null>(null);
  const [result, setResult] = useState<ThermoReport | null>(null);
  const [curve, setCurve] = useState<ThermoCurve | null>(null);
  const [curveNote, setCurveNote] = useState(CALORIMETRY_MISSING);
  const [errors, setErrors] = useState<FieldErrors>(emptyErrors());
  const [pending, setPending] = useState(false);

  function clearComputed(note: string = CALORIMETRY_MISSING) {
    setResult(null);
    setCurve(null);
    setCurveNote(note);
  }

  useEffect(() => {
    let alive = true;
    loadSnapshotIndex().then((index) => {
      if (!alive) return;
      setSeriesIds(index.seriesIds);
    });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    if (!seriesId) {
      setNOptions([]);
      setPrefill(null);
      return () => {
        alive = false;
      };
    }
    const n = Number(nText);
    loadSnapshotIndex().then(async (index) => {
      if (!alive) return;
      setSeriesIds(index.seriesIds);
      setNOptions(repeatCounts(index, seriesId));
      if (!Number.isInteger(n) || n < 1) {
        setPrefill(null);
        return;
      }
      const next = await loadThermoPrefill(seriesId, n, index);
      if (!alive) return;
      setPrefill(next);
      setTmC(next.tmC === null ? "" : String(next.tmC));
      setDeltaH(next.deltaH === null ? "" : String(next.deltaH));
      setDeltaCp(next.deltaCp === null ? "" : String(next.deltaCp));
      setResult(null);
      setCurve(null);
      setCurveNote(CALORIMETRY_MISSING);
      setErrors(emptyErrors());
    });
    return () => {
      alive = false;
    };
  }, [seriesId, nText]);

  function chooseUnits(next: EnergyUnits) {
    setUnits(next);
    clearComputed();
    setErrors(emptyErrors());
  }

  function chooseSeries(next: string) {
    setSeriesId(next);
    clearComputed();
    setErrors(emptyErrors());
    if (!next) {
      setPrefill(null);
      return;
    }
    if (nText.trim() !== "") return;
    loadSnapshotIndex().then((index) => {
      const first = repeatCounts(index, next)[0];
      if (first !== undefined) setNText(String(first));
    });
  }

  async function onCalculate(event: FormEvent) {
    event.preventDefault();
    const temperature = parseRequired(tC);
    const melting = parseRequired(tmC);
    const enthalpy = parseRequired(deltaH);
    const heatCapacity = parseRequired(deltaCp);
    if (enthalpy === null || heatCapacity === null) {
      clearComputed(CALORIMETRY_MISSING);
      setErrors({
        temperature: null,
        form: CALORIMETRY_MISSING,
      });
      return;
    }
    if (melting === null || melting + CELSIUS_TO_KELVIN <= 0) {
      clearComputed();
      setErrors({
        temperature:
          melting === null
            ? "Enter a melting temperature in °C. An empty Tm is not taken from a literature default."
            : `Tm must be above absolute zero (−273.15 °C). ${formatQuantity(melting)} °C is ${formatQuantity(melting + CELSIUS_TO_KELVIN)} K.`,
        form: null,
      });
      return;
    }
    const wantsPoint = tC.trim() !== "";
    if (wantsPoint && (temperature === null || temperature + CELSIUS_TO_KELVIN <= 0)) {
      setResult(null);
      setErrors({
        temperature:
          temperature === null
            ? "Enter a temperature in °C. An empty temperature is not treated as 0 °C."
            : `Temperature must be above absolute zero (−273.15 °C). ${formatQuantity(temperature)} °C is ${formatQuantity(temperature + CELSIUS_TO_KELVIN)} K.`,
        form: null,
      });
      return;
    }
    const enthalpySigma = parseOptionalSigma(deltaHSigma);
    const heatSigma = parseOptionalSigma(deltaCpSigma);
    const meltingSigma = parseOptionalSigma(tmSigmaC);
    if (wantsPoint && (enthalpySigma === null || heatSigma === null || meltingSigma === null)) {
      setResult(null);
      setErrors({
        temperature: null,
        form: "A sigma must be a finite number ≥ 0. Leave the field blank when you do not have one. Blank is not zero.",
      });
      return;
    }
    setPending(true);
    setErrors(emptyErrors());
    let drawn = false;
    try {
      const window = curveWindow(melting);
      const nextCurve = await postThermoCurve({
        tmC: melting,
        deltaH: enthalpy,
        deltaCp: heatCapacity,
        units,
        tMinC: window.tMinC,
        tMaxC: window.tMaxC,
      });
      drawn = true;
      setCurve(nextCurve);
      setCurveNote(nextCurve.result_label || CURVE_LABEL);
      if (wantsPoint && temperature !== null) {
        const report = await postThermo({
          tC: temperature,
          tmC: melting,
          deltaH: enthalpy,
          deltaCp: heatCapacity,
          units,
          deltaHSigma: typeof enthalpySigma === "number" ? enthalpySigma : undefined,
          deltaCpSigma: typeof heatSigma === "number" ? heatSigma : undefined,
          tmSigmaC: typeof meltingSigma === "number" ? meltingSigma : undefined,
        });
        setResult(report);
      } else {
        setResult(null);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "The calculator did not return a result.";
      if (!drawn) {
        setCurve(null);
        setCurveNote(message);
      }
      setResult(null);
      setErrors({
        temperature: null,
        form: message,
      });
    } finally {
      setPending(false);
    }
  }

  const energy = energyUnitLabel(units, "energy");
  const entropy = energyUnitLabel(units, "entropy");

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 md:px-8">
      <StudioNav />
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold tracking-[0.22em] text-[#FF8000] uppercase">
            Gibbs–Helmholtz arithmetic
          </p>
          <h1 className="mt-2 font-heading text-4xl text-[#242220] md:text-5xl">ΔG, ΔH, ΔS calculator</h1>
          <p className="mt-3 text-sm leading-relaxed text-[#5C564E] md:text-[15px]">
            Two-state Gibbs–Helmholtz arithmetic on the ΔHcal, ΔCp, and Tm you enter. calibrated stays false. This is not a measurement of the Hong Kong team fusion.
          </p>
        </div>
        <Badge className="rounded-full bg-[#242220] text-white">
          calibrated = {curve ? String(curve.calibrated) : "false"}
        </Badge>
      </header>

      <Card className="mt-6 border-[#E3D9CC] bg-[#FFF7EF] shadow-none">
        <CardHeader>
          <CardTitle className="text-[#242220]">Equation</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="font-sans text-sm leading-relaxed whitespace-pre-wrap text-[#242220]">{THERMO_EQUATION}</pre>
          <p className="mt-3 text-sm leading-relaxed text-[#5C564E]">
            This is the relation Phillips et al. 2012 (DOI 10.1002/pro.2018) used to obtain unfolding ΔG at 10 °C from ΔHcal, Tm, and ΔCp. It is not a new fit. Outputs are kcal mol⁻¹ for ΔG and ΔH, and kcal mol⁻¹ K⁻¹ for ΔS. A kJ input is converted with 1 kcal = 4.184 kJ, and that conversion is reported.
          </p>
        </CardContent>
      </Card>

      <form onSubmit={onCalculate} className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <Card className="border-[#E3D9CC] shadow-none">
          <CardHeader>
            <CardTitle className="text-[#242220]">Inputs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2" role="group" aria-label="Energy unit">
              <Button
                type="button"
                variant={units === "kcal" ? "default" : "outline"}
                aria-pressed={units === "kcal"}
                onClick={() => chooseUnits("kcal")}
              >
                kcal
              </Button>
              <Button
                type="button"
                variant={units === "kJ" ? "default" : "outline"}
                aria-pressed={units === "kJ"}
                onClick={() => chooseUnits("kJ")}
              >
                kJ
              </Button>
            </div>
            <p className="text-sm text-[#5C564E]">
              Switching units does not convert the numbers already typed. Check that ΔH and ΔCp are in {energy} and {entropy}.
            </p>
            <label className="block text-sm font-medium text-[#242220]">
              Evaluation temperature (°C, optional)
              <Input
                className="mt-1 border-[#E3D9CC]"
                inputMode="decimal"
                value={tC}
                aria-invalid={errors.temperature ? true : undefined}
                onChange={(event) => {
                  setTC(event.target.value);
                  setResult(null);
                }}
              />
            </label>
            <label className="block text-sm font-medium text-[#242220]">
              Melting temperature Tm (°C)
              <Input
                className="mt-1 border-[#E3D9CC]"
                inputMode="decimal"
                value={tmC}
                aria-invalid={errors.temperature ? true : undefined}
                onChange={(event) => {
                  setTmC(event.target.value);
                  clearComputed();
                }}
              />
            </label>
            {tmCaption(tmC, prefill) ? (
              <p className="text-sm leading-relaxed text-[#5C564E]">{tmCaption(tmC, prefill)}</p>
            ) : null}
            <label className="block text-sm font-medium text-[#242220]">
              ΔHcal, ΔH at Tm ({energy})
              <Input
                className="mt-1 border-[#E3D9CC]"
                inputMode="decimal"
                value={deltaH}
                onChange={(event) => {
                  setDeltaH(event.target.value);
                  clearComputed();
                }}
              />
            </label>
            <label className="block text-sm font-medium text-[#242220]">
              ΔCp ({entropy})
              <Input
                className="mt-1 border-[#E3D9CC]"
                inputMode="decimal"
                value={deltaCp}
                onChange={(event) => {
                  setDeltaCp(event.target.value);
                  clearComputed();
                }}
              />
            </label>
            <fieldset className="space-y-3 rounded-xl border border-[#E3D9CC] p-3">
              <legend className="px-1 text-sm font-medium text-[#242220]">Optional sigmas</legend>
              <p className="text-sm text-[#5C564E]">
                Leave a sigma blank when you do not have one. A blank sigma is not zero, and the 95% band stays hidden.
              </p>
              <label className="block text-sm text-[#242220]">
                ΔH sigma ({energy})
                <Input className="mt-1 border-[#E3D9CC]" inputMode="decimal" value={deltaHSigma} onChange={(event) => setDeltaHSigma(event.target.value)} />
              </label>
              <label className="block text-sm text-[#242220]">
                ΔCp sigma ({entropy})
                <Input className="mt-1 border-[#E3D9CC]" inputMode="decimal" value={deltaCpSigma} onChange={(event) => setDeltaCpSigma(event.target.value)} />
              </label>
              <label className="block text-sm text-[#242220]">
                Tm sigma (°C)
                <Input className="mt-1 border-[#E3D9CC]" inputMode="decimal" value={tmSigmaC} onChange={(event) => setTmSigmaC(event.target.value)} />
              </label>
            </fieldset>
            <p className="text-sm text-[#5C564E]">
              An evaluation temperature is optional. The curves use the whole window. Leave it blank if you only want ΔH(T), ΔS(T), and ΔG(T) versus temperature.
            </p>
            <Button type="submit" disabled={pending} className="bg-[#FF8000] text-white">
              {pending ? "Calculating…" : "Calculate curves"}
            </Button>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="border-[#E3D9CC] shadow-none">
            <CardHeader>
              <CardTitle className="text-[#242220]">Literature prefill</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <label className="block text-sm font-medium text-[#242220]">
                Series
                <select
                  className="mt-1 h-8 w-full rounded-lg border border-[#E3D9CC] bg-white px-2.5 text-sm text-[#242220]"
                  value={seriesId}
                  onChange={(event) => chooseSeries(event.target.value)}
                >
                  <option value="">No literature prefill</option>
                  {seriesIds.map((id) => (
                    <option key={id} value={id}>
                      {seriesTitle(id)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm font-medium text-[#242220]">
                Repeat count n
                <Input
                  className="mt-1 border-[#E3D9CC]"
                  inputMode="numeric"
                  list="thermo-repeat-counts"
                  value={nText}
                  onChange={(event) => setNText(event.target.value)}
                />
                <datalist id="thermo-repeat-counts">
                  {nOptions.map((n) => (
                    <option key={n} value={n} />
                  ))}
                </datalist>
              </label>
              {seriesId && nText.trim() !== "" && !Number.isInteger(Number(nText)) ? (
                <p className="text-sm text-[#5C564E]">n has to be an integer. A fractional length is not interpolated.</p>
              ) : null}
              {prefill ? (
                <div className="space-y-2 text-sm leading-relaxed text-[#5C564E]">
                  <p>{prefill.message}</p>
                  <p>
                    Printed ΔG:{" "}
                    {prefill.deltaG === null
                      ? "not printed for this series and n."
                      : `${formatQuantity(prefill.deltaG)} ${prefill.deltaGUnits ?? ""}`.trim() +
                        ". That is the table entry, not a calculator result."}
                  </p>
                  <p>ΔHcal and ΔCp from this table: blank. They are not back-calculated from ΔG and Tm.</p>
                </div>
              ) : (
                <p className="text-sm leading-relaxed text-[#5C564E]">
                  Choose a series and a repeat count to copy a cited Tm and the printed ΔG. ΔHcal and ΔCp stay empty unless that lookup returns them.
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="border-[#E3D9CC] shadow-none">
            <CardHeader>
              <CardTitle className="text-[#242220]">Curves</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm leading-relaxed text-[#5C564E]">{curveNote}</p>
              {curve && curve.points.length > 0 ? (
                <div className="space-y-4">
                  <p className="text-sm text-[#242220]">
                    ΔG(Tm) = {formatAtTm(curve.delta_g_at_tm)} {curve.delta_g_units}. ΔH(Tm) = {formatQuantity(curve.delta_h_at_tm)} {curve.delta_h_units}. ΔS(Tm) = {formatQuantity(curve.delta_s_at_tm)} {curve.delta_s_units}. Tm = {formatQuantity(curve.tm_c)} °C = {formatQuantity(curve.tm_k)} K.
                  </p>
                  <CurveChart
                    title="ΔG(T)"
                    units={curve.delta_g_units}
                    color="#FF8000"
                    points={curve.points}
                    tmC={curve.tm_c}
                    read={(point) => point.delta_g}
                  />
                  <CurveChart
                    title="ΔH(T)"
                    units={curve.delta_h_units}
                    color="#242220"
                    points={curve.points}
                    tmC={curve.tm_c}
                    read={(point) => point.delta_h}
                  />
                  <CurveChart
                    title="ΔS(T)"
                    units={curve.delta_s_units}
                    color="#266FB1"
                    points={curve.points}
                    tmC={curve.tm_c}
                    read={(point) => point.delta_s}
                  />
                  <p className="text-sm text-[#242220]">calibrated = {String(curve.calibrated)}</p>
                  {curve.warnings.length > 0 ? (
                    <ul className="list-disc space-y-1 pl-5 text-sm text-[#5C564E]">
                      {curve.warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : (
                <p className="text-sm leading-relaxed text-[#5C564E]">
                  No ΔH(T), ΔS(T), or ΔG(T) curve is drawn. Missing ΔHcal or ΔCp is not plotted as zero.
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="border-[#E3D9CC] shadow-none">
            <CardHeader>
              <CardTitle className="text-[#242220]">Value at one temperature</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {errors.temperature ? (
                <p role="alert" className="rounded-lg border border-[#E3D9CC] bg-[#FFF7EF] px-3 py-3 text-sm text-[#9B2C2C]">
                  {errors.temperature}
                </p>
              ) : null}
              {errors.form ? (
                <p role="alert" className="rounded-lg border border-[#E3D9CC] bg-white px-3 py-3 text-sm text-[#9B2C2C]">
                  {errors.form}
                </p>
              ) : null}
              {result ? (
                <div className="space-y-4">
                  <p className="text-sm text-[#5C564E]">
                    T = {formatQuantity(result.t_c)} °C = {formatQuantity(result.t_k)} K. Tm = {formatQuantity(result.tm_c)} °C = {formatQuantity(result.tm_k)} K.
                  </p>
                  <div>
                    <p className="text-sm font-medium text-[#242220]">
                      ΔG = {formatQuantity(result.delta_g)} {result.delta_g_units}
                    </p>
                    <Band
                      defined={result.uncertainty_defined}
                      sigma={result.delta_g_sigma}
                      low={result.delta_g_95_lower}
                      high={result.delta_g_95_upper}
                      units={result.delta_g_units}
                    />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[#242220]">
                      ΔH = {formatQuantity(result.delta_h)} {result.delta_h_units}
                    </p>
                    <Band
                      defined={result.uncertainty_defined}
                      sigma={result.delta_h_sigma}
                      low={result.delta_h_95_lower}
                      high={result.delta_h_95_upper}
                      units={result.delta_h_units}
                    />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[#242220]">
                      ΔS = {formatQuantity(result.delta_s)} {result.delta_s_units}
                    </p>
                    <Band
                      defined={result.uncertainty_defined}
                      sigma={result.delta_s_sigma}
                      low={result.delta_s_95_lower}
                      high={result.delta_s_95_upper}
                      units={result.delta_s_units}
                    />
                  </div>
                  <p className="text-sm leading-relaxed text-[#5C564E]">{result.uncertainty_note}</p>
                  {result.warnings.length > 0 ? (
                    <ul className="list-disc space-y-1 pl-5 text-sm text-[#5C564E]">
                      {result.warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  ) : null}
                  <p className="text-sm text-[#242220]">calibrated = {String(result.calibrated)}</p>
                </div>
              ) : null}
              {!result && !errors.temperature && !errors.form ? (
                <p className="text-sm leading-relaxed text-[#5C564E]">
                  {curve
                    ? "No single temperature was requested. The curves above are the temperature dependence. Type an evaluation temperature and calculate again to read ΔG, ΔH, and ΔS at that one temperature."
                    : "No result yet. The curves need Tm, ΔHcal, and ΔCp. An evaluation temperature is only for this single-point readout."}
                </p>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </form>
    </div>
  );
}
