"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StudioNav } from "@/components/studio-nav";
import { SERIES_COPY, TEAM_LENGTHS } from "@/lib/stability";
import {
  CURVE_LABEL,
  CURVE_T_MAX_C,
  CURVE_T_MIN_C,
  energyUnitLabel,
  formatQuantity,
  loadSnapshotIndex,
  loadThermoPrefill,
  postEffectiveEnthalpy,
  postThermoCurve,
  repeatCounts,
  seriesTitle,
  type EffectiveEnthalpy,
  type EnergyUnits,
  type ThermoCurve,
  type ThermoPrefill,
} from "@/lib/thermo";

const CHART_FONT = "var(--font-inter), Inter, sans-serif";
const DEFAULT_SERIES_ID = SERIES_COPY.find((item) => item.isDefault)?.id ?? "phillips2012_ctpra_dsc";
const CELSIUS_TO_KELVIN = 273.15;

type LiteratureIndex = Awaited<ReturnType<typeof loadSnapshotIndex>>;

function prettyUnits(text: string): string {
  return text.replaceAll("mol-1", "mol⁻¹").replaceAll("K-1", "K⁻¹");
}

function parseRequired(raw: string): number | null {
  const trimmed = raw.trim();
  if (trimmed === "") return null;
  const value = Number(trimmed);
  if (!Number.isFinite(value)) return null;
  return value;
}

function fieldState(raw: string): "empty" | "invalid" | "ready" {
  if (raw.trim() === "") return "empty";
  return parseRequired(raw) === null ? "invalid" : "ready";
}

function describeCalorimetry(deltaH: string, deltaCp: string): string | null {
  const enthalpy = fieldState(deltaH);
  const heatCapacity = fieldState(deltaCp);
  if (enthalpy === "ready" && heatCapacity === "ready") return null;
  if (enthalpy === "invalid") return "ΔHcal is not a finite number, so no temperature curve is drawn.";
  if (heatCapacity === "invalid") return "ΔCp is not a finite number, so no temperature curve is drawn.";
  if (enthalpy === "empty" && heatCapacity === "empty") {
    return "ΔHcal and ΔCp are empty, so no temperature curve is drawn.";
  }
  if (enthalpy === "empty") return "ΔHcal is empty, so no temperature curve is drawn.";
  return "ΔCp is empty, so no temperature curve is drawn.";
}

function meltingIdentity(tmC: string): { tmC: number; tmK: number } | null {
  const typed = parseRequired(tmC);
  if (typed === null) return null;
  const tmK = typed + CELSIUS_TO_KELVIN;
  if (tmK <= 0) return null;
  return { tmC: typed, tmK };
}

function formatAtTm(value: number): string {
  if (Number.isFinite(value) && Math.abs(value) < 1e-9) return "0";
  return formatQuantity(value);
}

function printedEnergyUnits(units: string | null): "kcal" | "kJ" | null {
  if (!units) return null;
  const token = units.toLowerCase();
  if (token.includes("kj")) return "kJ";
  if (token.includes("kcal")) return "kcal";
  return null;
}

function citedSigmas(
  prefill: ThermoPrefill | null,
  melting: number,
  anchor: number | null,
  anchorUnits: "kcal" | "kJ",
): { deltaGSigma: number | null; tmSigmaC: number | null } | null {
  if (!prefill || anchor === null) return null;
  const tmMatches = prefill.tmC !== null && melting === prefill.tmC;
  const unitsMatch = printedEnergyUnits(prefill.deltaGUnits) === anchorUnits;
  const anchorMatches = prefill.deltaG !== null && anchor === prefill.deltaG && unitsMatch;
  if (!tmMatches || !anchorMatches) return null;
  return {
    deltaGSigma: prefill.deltaGUncertainty,
    tmSigmaC: prefill.tmUncertainty,
  };
}

function tmCaption(tmC: string, prefill: ThermoPrefill | null): string | null {
  const typed = parseRequired(tmC);
  if (typed === null) {
    if (!prefill) return null;
    if (prefill.tmStatus === "extrapolated") {
      return "This paper has no row for this length, so no melting temperature was filled in. A temperature you type is not a cited one.";
    }
    if (prefill.tmC === null) {
      return "No cited melting temperature at this repeat count. Nothing was interpolated. A temperature you type is not a cited one.";
    }
    return null;
  }
  if (prefill?.tmC != null && typed === prefill.tmC) {
    return "Cited melting temperature, copied from the paper. It was not calculated.";
  }
  return "Typed melting temperature. It is not a cited one.";
}

function tableSentence(prefill: ThermoPrefill): string {
  if (prefill.deltaGTemperatureC === null) {
    return "The paper’s number, not a result of the Tm box.";
  }
  return `The paper’s number at ${formatQuantity(prefill.deltaGTemperatureC)} °C, not a result of the Tm box.`;
}

function printedTableValue(prefill: ThermoPrefill): string {
  const units = prettyUnits(prefill.deltaGUnits ?? "");
  const value = formatQuantity(prefill.deltaG ?? 0);
  if (prefill.deltaGUncertainty != null) {
    return `${value} ± ${formatQuantity(prefill.deltaGUncertainty)} ${units}`.trim();
  }
  return `${value} ${units}`.trim();
}

function seriesPrintsDeltaG(snapshot: LiteratureIndex | null, seriesId: string): boolean | null {
  if (!snapshot) return null;
  const rows = snapshot.rows.get(seriesId);
  if (!rows) return null;
  return rows.some((row) => typeof row.delta_g === "number" && Number.isFinite(row.delta_g));
}

function missingTableSpeech(printsColumn: boolean | null, extrapolated: boolean): string {
  if (printsColumn === null) return "Not printed.";
  if (!printsColumn) return "Not printed. This series has no ΔG column.";
  if (extrapolated) {
    return "Not printed for this length. This paper has no row here, so no table value was copied.";
  }
  return "Not printed for this length.";
}

function curveWindow(tmC: number): { tMinC: number; tMaxC: number } {
  return {
    tMinC: Math.min(CURVE_T_MIN_C, tmC),
    tMaxC: Math.max(CURVE_T_MAX_C, tmC),
  };
}

function finiteBand(value: number | null): value is number {
  return value !== null && Number.isFinite(value);
}

function CurveChart<T extends { t_c: number }>({
  title,
  units,
  color,
  points,
  tmC,
  read,
  readLow,
  readHigh,
}: {
  title: string;
  units: string;
  color: string;
  points: T[];
  tmC: number;
  read: (point: T) => number;
  readLow?: (point: T) => number | null;
  readHigh?: (point: T) => number | null;
}) {
  const width = 640;
  const height = 220;
  const pad = { l: 72, r: 16, t: 28, b: 36 };
  const xs = points.map((point) => point.t_c);
  const ys = points.map(read);
  const lows = readLow ? points.map(readLow) : [];
  const highs = readHigh ? points.map(readHigh) : [];
  const hasBand =
    lows.length === points.length && highs.length === points.length && lows.every(finiteBand) && highs.every(finiteBand);
  const bandNumbers = [...lows, ...highs].filter(finiteBand);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  let yMin = Math.min(...ys);
  let yMax = Math.max(...ys);
  if (hasBand && bandNumbers.length > 0) {
    yMin = Math.min(yMin, ...bandNumbers);
    yMax = Math.max(yMax, ...bandNumbers);
  }
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
  const bandPath = hasBand
    ? [
        ...highs.map((value, index) => {
          const point = points[index];
          if (!point || !finiteBand(value)) return "";
          return `${index === 0 ? "M" : "L"} ${xOf(point.t_c).toFixed(2)} ${yOf(value).toFixed(2)}`;
        }),
        ...lows
          .slice()
          .reverse()
          .map((value, index) => {
            const point = points[points.length - 1 - index];
            if (!point || !finiteBand(value)) return "";
            return `L ${xOf(point.t_c).toFixed(2)} ${yOf(value).toFixed(2)}`;
          }),
        "Z",
      ].join(" ")
    : null;
  const yTicks = [yMin + yPad, (yMin + yMax) / 2, yMax - yPad];
  const showZero = yMin < 0 && yMax > 0;
  const summary = `${title} in ${units}, from ${formatQuantity(xs[0] ?? 0)} °C to ${formatQuantity(xs[xs.length - 1] ?? 0)} °C.${
    hasBand ? " Shaded band is a linear approximation." : ""
  }`;
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
      {showZero ? <line x1={pad.l} x2={width - pad.r} y1={yOf(0)} y2={yOf(0)} stroke="#C45C12" strokeDasharray="4 4" /> : null}
      <line x1={xOf(tmC)} x2={xOf(tmC)} y1={pad.t} y2={height - pad.b} stroke="#8A8175" strokeDasharray="3 3" />
      <text x={xOf(tmC) + 4} y={pad.t + 12} fill="#5C564E" fontSize="11" fontFamily={CHART_FONT}>
        Tm
      </text>
      {bandPath ? <path d={bandPath} fill={color} fillOpacity={0.18} stroke="none" /> : null}
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

function ChoiceButton({
  pressed,
  onClick,
  children,
}: {
  pressed: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={
        pressed
          ? "rounded-full bg-[#242220] px-4 py-2.5 text-left text-sm text-white"
          : "rounded-full border border-[#E3D9CC] bg-white px-4 py-2.5 text-left text-sm text-[#3F3A34] hover:border-[#C45C12]"
      }
    >
      {children}
    </button>
  );
}

function UnitSwitch({
  value,
  onChange,
  label,
}: {
  value: EnergyUnits;
  onChange: (next: EnergyUnits) => void;
  label: string;
}) {
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label={label}>
      {(["kcal", "kJ"] as const).map((unit) => (
        <Button
          key={unit}
          type="button"
          variant={value === unit ? "default" : "outline"}
          aria-pressed={value === unit}
          onClick={() => onChange(unit)}
        >
          {unit}
        </Button>
      ))}
    </div>
  );
}

function ResultBlock({ title, warm, children }: { title: string; warm?: boolean; children: ReactNode }) {
  return (
    <section className={warm ? "rounded-2xl border border-[#E3D9CC] bg-[#FFF7EF] p-5 md:p-6" : "rounded-2xl border border-[#E3D9CC] bg-white p-5 md:p-6"}>
      <h3 className="font-heading text-xl font-semibold tracking-tight text-[#242220]">{title}</h3>
      <div className="mt-4 space-y-3">{children}</div>
    </section>
  );
}

export function ThermoCalculator() {
  const [units, setUnits] = useState<EnergyUnits>("kcal");
  const [tmC, setTmC] = useState("");
  const [deltaH, setDeltaH] = useState("");
  const [deltaCp, setDeltaCp] = useState("");
  const [seriesId, setSeriesId] = useState<string>(DEFAULT_SERIES_ID);
  const [nText, setNText] = useState("3");
  const [seriesIds, setSeriesIds] = useState<string[]>(SERIES_COPY.map((item) => item.id));
  const [nOptions, setNOptions] = useState<number[]>([]);
  const [snapshot, setSnapshot] = useState<LiteratureIndex | null>(null);
  const [prefill, setPrefill] = useState<ThermoPrefill | null>(null);
  const [anchorG, setAnchorG] = useState("");
  const [anchorTRef, setAnchorTRef] = useState("");
  const [anchorUnits, setAnchorUnits] = useState<EnergyUnits>("kcal");
  const [curve, setCurve] = useState<ThermoCurve | null>(null);
  const [curveNote, setCurveNote] = useState("ΔHcal and ΔCp are empty, so no temperature curve is drawn.");
  const [effective, setEffective] = useState<EffectiveEnthalpy | null>(null);
  const [effectiveNote, setEffectiveNote] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let alive = true;
    loadSnapshotIndex().then((index) => {
      if (!alive) return;
      setSeriesIds(index.seriesIds);
      setSnapshot(index);
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
      setSnapshot(index);
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
      setAnchorG(next.deltaG === null ? "" : String(next.deltaG));
      setAnchorTRef(next.deltaGTemperatureC === null ? "" : String(next.deltaGTemperatureC));
      setAnchorUnits(next.deltaGUnits?.toLowerCase().includes("kj") ? "kJ" : "kcal");
      setEffective(null);
      setEffectiveNote(null);
      setCurve(null);
    });
    return () => {
      alive = false;
    };
  }, [seriesId, nText]);

  useEffect(() => {
    let alive = true;
    const melting = parseRequired(tmC);
    if (melting === null || melting + CELSIUS_TO_KELVIN <= 0) {
      setEffective(null);
      setEffectiveNote(null);
      return () => {
        alive = false;
      };
    }
    const anchor = parseRequired(anchorG);
    if (anchor !== null) {
      const tRef = parseRequired(anchorTRef);
      if (tRef === null || tRef + CELSIUS_TO_KELVIN <= 0) {
        setEffective(null);
        setEffectiveNote("An anchor ΔG needs the temperature of that value. None was assumed, so the ΔCp = 0 estimate was not calculated.");
        return () => {
          alive = false;
        };
      }
    }
    const tRef = parseRequired(anchorTRef);
    const sigmas = citedSigmas(prefill, melting, anchor, anchorUnits);
    postEffectiveEnthalpy({
      tmC: melting,
      deltaGRef: anchor,
      tRefC: anchor === null ? null : tRef,
      units: anchorUnits,
      deltaGSigma: sigmas ? sigmas.deltaGSigma : null,
      tmSigmaC: sigmas ? sigmas.tmSigmaC : null,
    })
      .then((next) => {
        if (!alive) return;
        setEffective(next);
        setEffectiveNote(next.has_effective_enthalpy ? null : next.message);
      })
      .catch((err: unknown) => {
        if (!alive) return;
        setEffective(null);
        setEffectiveNote(err instanceof Error ? err.message : "The ΔCp = 0 estimate did not return a result.");
      });
    return () => {
      alive = false;
    };
  }, [tmC, anchorG, anchorTRef, anchorUnits, prefill]);

  useEffect(() => {
    const missing = describeCalorimetry(deltaH, deltaCp);
    if (missing) {
      setCurve(null);
      setCurveNote(missing);
      setPending(false);
      return;
    }
    const melting = parseRequired(tmC);
    const enthalpy = parseRequired(deltaH);
    const heatCapacity = parseRequired(deltaCp);
    if (melting === null || enthalpy === null || heatCapacity === null || melting + CELSIUS_TO_KELVIN <= 0) {
      setCurve(null);
      setPending(false);
      setCurveNote(
        melting === null
          ? "A melting temperature is required before a curve can be drawn."
          : `${formatQuantity(melting ?? 0)} °C is not above absolute zero, so no curve is drawn.`,
      );
      return;
    }
    let alive = true;
    setCurve(null);
    setCurveNote("Drawing the temperature curves from the ΔHcal and ΔCp you typed.");
    const span = curveWindow(melting);
    const timer = window.setTimeout(() => {
      setPending(true);
      postThermoCurve({
        tmC: melting,
        deltaH: enthalpy,
        deltaCp: heatCapacity,
        units,
        tMinC: span.tMinC,
        tMaxC: span.tMaxC,
      })
        .then((next) => {
          if (!alive) return;
          setCurve(next);
          setCurveNote("");
        })
        .catch((err: unknown) => {
          if (!alive) return;
          setCurve(null);
          setCurveNote(err instanceof Error ? err.message : "The calculator did not return a curve.");
        })
        .finally(() => {
          if (alive) setPending(false);
        });
    }, 400);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [deltaH, deltaCp, tmC, units]);

  const identity = meltingIdentity(tmC);
  const anchorValue = parseRequired(anchorG);
  const anchorTemperature = parseRequired(anchorTRef);
  const estimateReady =
    identity !== null && anchorValue !== null && anchorTemperature !== null && anchorTemperature + CELSIUS_TO_KELVIN > 0;
  const showEstimate = Boolean(effective?.has_effective_enthalpy && effective.delta_h_eff !== null && effective.points.length > 0);
  const sigmas = identity ? citedSigmas(prefill, identity.tmC, anchorValue, anchorUnits) : null;
  const bothPrinted = sigmas !== null && sigmas.deltaGSigma !== null && sigmas.tmSigmaC !== null;
  const printsColumn = seriesPrintsDeltaG(snapshot, seriesId);
  const otherCounts = nOptions.filter((n) => !(TEAM_LENGTHS as readonly number[]).includes(n));
  const energy = energyUnitLabel(units, "energy");
  const entropy = energyUnitLabel(units, "entropy");
  const anchorEnergy = energyUnitLabel(anchorUnits, "energy");
  const zeroUnits = prefill?.deltaGUnits ? prettyUnits(prefill.deltaGUnits) : energyUnitLabel("kcal", "energy");
  const caption = tmCaption(tmC, prefill);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 md:px-8 md:py-12">
      <StudioNav />
      <header className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold tracking-[0.22em] text-[#C45C12] uppercase">Stability</p>
          <h1 className="mt-2 font-heading text-4xl leading-[1.1] font-semibold tracking-tight text-[#242220] md:text-5xl">
            Estimate ΔG at other temperatures
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-[#5C564E]">
            ΔG at the melting temperature is 0 for a two-state melt. The paper’s number stays what the table printed. calibrated stays false.
          </p>
        </div>
        <Badge className="rounded-full bg-[#242220] text-white">calibrated = false</Badge>
      </header>

      <div className="mt-10 grid items-start gap-8 lg:grid-cols-2 lg:gap-10">
        <section className="rounded-2xl border border-[#E3D9CC] bg-white p-5 md:p-8" aria-label="Inputs">
          <h2 className="font-heading text-2xl font-semibold tracking-tight text-[#242220]">Inputs</h2>
          <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">
            A cited melting temperature is filled in when the paper has one. ΔHcal and ΔCp stay empty until you type them.
          </p>

          <div className="mt-8">
            <h3 className="text-sm font-semibold text-[#242220]">Series</h3>
            <p className="mt-1 text-sm leading-relaxed text-[#5C564E]">Phillips CTPRa DSC is the default series.</p>
            <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Series">
              {seriesIds.map((id) => {
                const known = SERIES_COPY.find((item) => item.id === id);
                return (
                  <ChoiceButton key={id} pressed={seriesId === id} onClick={() => setSeriesId(id)}>
                    <span className="block">{seriesTitle(id)}</span>
                    {known?.isDefault ? <span className="mt-0.5 block text-[11px] opacity-80">Default series</span> : null}
                  </ChoiceButton>
                );
              })}
            </div>
          </div>

          <div className="mt-8 border-t border-[#E3D9CC] pt-8">
            <h3 className="text-sm font-semibold text-[#242220]">Repeat count</h3>
            <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Repeat count">
              {TEAM_LENGTHS.map((n) => (
                <ChoiceButton key={n} pressed={nText === String(n)} onClick={() => setNText(String(n))}>
                  n = {n}
                </ChoiceButton>
              ))}
            </div>
            <p className="mt-3 text-sm leading-relaxed text-[#5C564E]">
              n = 3, n = 8, and n = 14 are the lengths on the confirmation page. Other lengths appear when this paper measured them.
            </p>
            {otherCounts.length > 0 ? (
              <label className="mt-4 block text-sm font-medium text-[#242220]">
                Other repeat count in this paper
                <select
                  className="mt-2 h-11 w-full rounded-lg border border-[#E3D9CC] bg-white px-3 text-base text-[#242220]"
                  value={(TEAM_LENGTHS as readonly number[]).includes(Number(nText)) ? "" : nText}
                  onChange={(event) => {
                    if (event.target.value) setNText(event.target.value);
                  }}
                >
                  <option value="">Choose a measured length</option>
                  {otherCounts.map((n) => (
                    <option key={n} value={n}>
                      n = {n}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>

          <div className="mt-8 border-t border-[#E3D9CC] pt-8">
            <label className="block text-sm font-semibold text-[#242220]" htmlFor="tm-c">
              Melting temperature (°C)
            </label>
            <Input
              id="tm-c"
              className="mt-2 h-11 border-[#E3D9CC] bg-white text-base"
              inputMode="decimal"
              value={tmC}
              onChange={(event) => setTmC(event.target.value)}
            />
            {caption ? <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">{caption}</p> : null}
          </div>

          <div className="mt-8 border-t border-[#E3D9CC] pt-8">
            <h3 className="text-sm font-semibold text-[#242220]">Anchor ΔG, optional</h3>
            <p className="mt-1 text-sm leading-relaxed text-[#5C564E]">
              Starts as the table value when that cell exists. Clearing it hides the ΔCp = 0 estimate. Editing it does not change the paper’s number.
            </p>
            <div className="mt-3">
              <UnitSwitch value={anchorUnits} onChange={setAnchorUnits} label="Anchor energy unit" />
              <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">Switching units does not convert the number already typed.</p>
            </div>
            <label className="mt-4 block text-sm font-medium text-[#242220]" htmlFor="anchor-g">
              Anchor ΔG ({anchorEnergy})
              <Input
                id="anchor-g"
                className="mt-2 h-11 border-[#E3D9CC] bg-white text-base"
                inputMode="decimal"
                value={anchorG}
                onChange={(event) => setAnchorG(event.target.value)}
              />
            </label>
            <label className="mt-4 block text-sm font-medium text-[#242220]" htmlFor="anchor-t">
              Temperature of the anchor ΔG (°C)
              <Input
                id="anchor-t"
                className="mt-2 h-11 border-[#E3D9CC] bg-white text-base"
                inputMode="decimal"
                value={anchorTRef}
                onChange={(event) => setAnchorTRef(event.target.value)}
              />
            </label>
            <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">
              {prefill?.deltaGTemperatureC != null
                ? `The paper states this value at ${formatQuantity(prefill.deltaGTemperatureC)} °C. It is not the melting temperature.`
                : "This is the temperature of the anchor ΔG. It is not the melting temperature, and none is assumed if you leave it blank."}
            </p>
            {prefill?.deltaG != null && anchorValue === prefill.deltaG ? (
              <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">This anchor matches the paper’s number.</p>
            ) : null}
            {prefill?.deltaG != null && anchorValue !== null && anchorValue !== prefill.deltaG ? (
              <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">This is a typed anchor. The paper’s number does not change.</p>
            ) : null}
          </div>

          <div className="mt-8 border-t border-[#E3D9CC] pt-8">
            <h3 className="text-sm font-semibold text-[#242220]">ΔHcal and ΔCp, optional</h3>
            <p className="mt-1 text-sm leading-relaxed text-[#5C564E]">
              Full temperature curves are drawn only after both of these are typed.
            </p>
            <div className="mt-3">
              <UnitSwitch value={units} onChange={setUnits} label="Calorimetry energy unit" />
              <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">
                Switching units does not convert the numbers already typed. ΔHcal is in {energy}. ΔCp is in {entropy}.
              </p>
            </div>
            <label className="mt-4 block text-sm font-medium text-[#242220]" htmlFor="delta-h">
              ΔHcal ({energy})
              <Input
                id="delta-h"
                className="mt-2 h-11 border-[#E3D9CC] bg-white text-base"
                inputMode="decimal"
                value={deltaH}
                onChange={(event) => setDeltaH(event.target.value)}
              />
            </label>
            <label className="mt-4 block text-sm font-medium text-[#242220]" htmlFor="delta-cp">
              ΔCp ({entropy})
              <Input
                id="delta-cp"
                className="mt-2 h-11 border-[#E3D9CC] bg-white text-base"
                inputMode="decimal"
                value={deltaCp}
                onChange={(event) => setDeltaCp(event.target.value)}
              />
            </label>
          </div>
        </section>

        <section className="space-y-6" aria-label="Results">
          <h2 className="font-heading text-2xl font-semibold tracking-tight text-[#242220]">Results</h2>

          <ResultBlock title="At the melting temperature" warm>
            {identity ? (
              <>
                <p className="font-heading text-5xl font-semibold tabular-nums tracking-tight text-[#242220]">0</p>
                <p className="text-sm text-[#5C564E]">{zeroUnits}</p>
                <p className="text-sm leading-relaxed text-[#242220]">ΔG at the melting temperature is 0 for a two-state melt.</p>
                <p className="text-sm leading-relaxed text-[#5C564E]">
                  Melting temperature {formatQuantity(identity.tmC)} °C ({formatQuantity(identity.tmK)} K).
                </p>
              </>
            ) : (
              <p className="text-sm leading-relaxed text-[#5C564E]">
                ΔG at the melting temperature is 0 for a two-state melt. No melting temperature is filled in, so that zero is not reported for this length.
              </p>
            )}
          </ResultBlock>

          <ResultBlock title="The paper’s number">
            {prefill?.deltaG != null ? (
              <>
                <p className="font-heading text-4xl font-semibold tabular-nums tracking-tight text-[#242220]">{printedTableValue(prefill)}</p>
                <p className="text-sm leading-relaxed text-[#242220]">{tableSentence(prefill)}</p>
              </>
            ) : prefill ? (
              <>
                <p className="font-heading text-3xl font-semibold tracking-tight text-[#C45C12]">Not printed</p>
                <p className="text-sm leading-relaxed text-[#5C564E]">
                  {missingTableSpeech(printsColumn, prefill.tmStatus === "extrapolated" || prefill.tmC === null)}
                </p>
              </>
            ) : (
              <p className="text-sm leading-relaxed text-[#5C564E]">
                The paper’s number appears here when this series prints an unfolding ΔG. It is not calculated from the melting temperature.
              </p>
            )}
          </ResultBlock>

          <ResultBlock title="ΔCp = 0 estimate">
            {showEstimate && effective?.delta_h_eff != null ? (
              <>
                <p className="text-xs font-medium tracking-[0.14em] text-[#8A8175] uppercase">Effective ΔH</p>
                <p className="font-heading text-4xl font-semibold tabular-nums tracking-tight text-[#242220]">
                  {formatQuantity(effective.delta_h_eff)}{" "}
                  <span className="text-lg font-medium text-[#5C564E]">{prettyUnits(effective.delta_h_units ?? "")}</span>
                </p>
                <p className="text-sm leading-relaxed text-[#242220]">This is an assumption, not the calorimetric ΔH from Phillips.</p>
                {effective.uncertainty_defined ? (
                  <div className="space-y-2 text-sm leading-relaxed text-[#5C564E]">
                    {effective.delta_h_eff_95_lower != null && effective.delta_h_eff_95_upper != null ? (
                      <p>
                        95% band for effective ΔH: {formatQuantity(effective.delta_h_eff_95_lower)} to{" "}
                        {formatQuantity(effective.delta_h_eff_95_upper)} {prettyUnits(effective.delta_h_units ?? "")}.
                      </p>
                    ) : null}
                    {effective.delta_g_at_t_ref_95_lower != null && effective.delta_g_at_t_ref_95_upper != null ? (
                      <p>
                        95% band for ΔG at {formatQuantity(effective.t_ref_c ?? 0)} °C: {formatQuantity(effective.delta_g_at_t_ref_95_lower)} to{" "}
                        {formatQuantity(effective.delta_g_at_t_ref_95_upper)} {prettyUnits(effective.delta_g_units ?? "")}.
                      </p>
                    ) : null}
                    <p>The band is a linear approximation.</p>
                  </div>
                ) : (
                  <p className="text-sm leading-relaxed text-[#5C564E]">
                    {bothPrinted
                      ? "No 95% band is drawn."
                      : "No 95% band is drawn. It appears only when both printed uncertainties are still the ones from the paper. A missing uncertainty is not zero."}
                  </p>
                )}
                <div className="rounded-xl border border-[#E3D9CC] bg-[#FBF8F3] p-3">
                  <CurveChart
                    title="ΔG(T)"
                    units={prettyUnits(effective.delta_g_units ?? "kcal mol⁻¹")}
                    color="#FF8000"
                    points={effective.points}
                    tmC={effective.tm_c ?? identity?.tmC ?? 0}
                    read={(point) => point.delta_g}
                    readLow={effective.uncertainty_defined ? (point) => point.delta_g_95_lower : undefined}
                    readHigh={effective.uncertainty_defined ? (point) => point.delta_g_95_upper : undefined}
                  />
                </div>
                <p className="text-sm leading-relaxed text-[#5C564E]">ΔG(T) under the assumption that ΔCp is 0.</p>
                <p className="text-sm leading-relaxed text-[#5C564E]">This estimate is an extrapolation. calibrated is false.</p>
                {effective.human_review_required ? (
                  <p className="text-sm leading-relaxed text-[#5C564E]">A person should review this estimate before it is used.</p>
                ) : null}
                {effective.warnings.length > 0 ? (
                  <ul className="list-disc space-y-1 pl-5 text-sm leading-relaxed text-[#5C564E]">
                    {effective.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                ) : null}
              </>
            ) : (
              <p className="text-sm leading-relaxed text-[#5C564E]">
                {!estimateReady
                  ? anchorValue !== null && (anchorTemperature === null || anchorTemperature + CELSIUS_TO_KELVIN <= 0)
                    ? "An anchor ΔG needs the temperature of that value. None was assumed, so the ΔCp = 0 estimate was not calculated."
                    : "The ΔCp = 0 estimate is shown only when a melting temperature and an anchor ΔG are both filled in."
                  : (effectiveNote ??
                    "Calculating the ΔCp = 0 estimate from the melting temperature and the anchor ΔG.")}
              </p>
            )}
          </ResultBlock>

          <ResultBlock title="Temperature curves">
            {curve && curve.points.length > 0 ? (
              <div className="space-y-4">
                <p className="text-sm leading-relaxed text-[#5C564E]">
                  These curves use the ΔHcal and ΔCp you typed. They are not the ΔCp = 0 estimate.
                </p>
                <p className="text-sm leading-relaxed text-[#242220]">
                  ΔG at the melting temperature on this curve is {formatAtTm(curve.delta_g_at_tm)} {prettyUnits(curve.delta_g_units)}. ΔH at the melting temperature is {formatQuantity(curve.delta_h_at_tm)} {prettyUnits(curve.delta_h_units)}.
                </p>
                <CurveChart title="ΔG(T)" units={prettyUnits(curve.delta_g_units)} color="#FF8000" points={curve.points} tmC={curve.tm_c} read={(point) => point.delta_g} />
                <CurveChart title="ΔH(T)" units={prettyUnits(curve.delta_h_units)} color="#242220" points={curve.points} tmC={curve.tm_c} read={(point) => point.delta_h} />
                <CurveChart title="ΔS(T)" units={prettyUnits(curve.delta_s_units)} color="#266FB1" points={curve.points} tmC={curve.tm_c} read={(point) => point.delta_s} />
                <p className="text-sm leading-relaxed text-[#5C564E]">{curve.result_label || CURVE_LABEL}</p>
                <p className="text-sm text-[#242220]">calibrated is false.</p>
                {pending ? <p className="text-sm text-[#8A8175]">Updating the curves…</p> : null}
                {curve.warnings.length > 0 ? (
                  <ul className="list-disc space-y-1 pl-5 text-sm leading-relaxed text-[#5C564E]">
                    {curve.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : (
              <p className="text-sm leading-relaxed text-[#5C564E]">{curveNote}</p>
            )}
          </ResultBlock>
        </section>
      </div>
    </div>
  );
}
