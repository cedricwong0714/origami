"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StudioNav } from "@/components/studio-nav";
import { PageGuide } from "@/components/page-guide";
import { CANONICAL_SERIES_ID, SERIES_COPY, TEAM_LENGTHS } from "@/lib/stability";
import {
  CURVE_LABEL,
  CURVE_T_MAX_C,
  CURVE_T_MIN_C,
  energyUnitLabel,
  formatQuantity,
  loadSnapshotIndex,
  loadThermoPrefill,
  PHILLIPS_PRINTED_DELTA_G_T_C,
  postEffectiveEnthalpy,
  postThermoCurve,
  type EffectiveEnthalpy,
  type EnergyUnits,
  type ThermoCurve,
  type ThermoPrefill,
} from "@/lib/thermo";

const CHART_FONT = "var(--font-inter), Inter, sans-serif";
const CANONICAL_COPY =
  SERIES_COPY.find((item) => item.id === CANONICAL_SERIES_ID) ?? SERIES_COPY[0];
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
      <text x={pad.l} y={16} fill="var(--studio-foreground)" fontSize="13" fontFamily={CHART_FONT}>
        {title} ({units})
      </text>
      {yTicks.map((tick) => (
        <g key={tick}>
          <line x1={pad.l} x2={width - pad.r} y1={yOf(tick)} y2={yOf(tick)} stroke="var(--studio-chart-grid)" />
          <text x={8} y={yOf(tick) + 4} fill="var(--studio-chart-label)" fontSize="11" fontFamily={CHART_FONT}>
            {formatQuantity(tick)}
          </text>
        </g>
      ))}
      {showZero ? <line x1={pad.l} x2={width - pad.r} y1={yOf(0)} y2={yOf(0)} stroke="var(--studio-accent)" strokeDasharray="4 4" /> : null}
      <line x1={xOf(tmC)} x2={xOf(tmC)} y1={pad.t} y2={height - pad.b} stroke="var(--studio-chart-label)" strokeDasharray="3 3" />
      <text x={xOf(tmC) + 4} y={pad.t + 12} fill="var(--studio-muted)" fontSize="11" fontFamily={CHART_FONT}>
        Tm
      </text>
      {bandPath ? <path d={bandPath} fill={color} fillOpacity={0.18} stroke="none" /> : null}
      <path d={path} fill="none" stroke={color} strokeWidth="2" />
      <text x={pad.l} y={height - 10} fill="var(--studio-chart-label)" fontSize="11" fontFamily={CHART_FONT}>
        temperature (°C)
      </text>
      <text x={width - pad.r} y={height - 10} textAnchor="end" fill="var(--studio-chart-label)" fontSize="11" fontFamily={CHART_FONT}>
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
          ? "rounded-full bg-studio-button px-4 py-2.5 text-left text-sm text-studio-button-text"
          : "rounded-full border border-studio-border bg-studio-card px-4 py-2.5 text-left text-sm text-studio-foreground hover:border-studio-accent"
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
    <section className={warm ? "rounded-2xl border border-studio-border bg-studio-accent-soft p-5 md:p-6" : "rounded-2xl border border-studio-border bg-studio-card p-5 md:p-6"}>
      <h3 className="font-heading text-xl font-semibold tracking-tight text-studio-foreground">{title}</h3>
      <div className="mt-4 space-y-3">{children}</div>
    </section>
  );
}

export function ThermoCalculator() {
  const [units, setUnits] = useState<EnergyUnits>("kcal");
  const [tmC, setTmC] = useState("");
  const [deltaH, setDeltaH] = useState("");
  const [deltaCp, setDeltaCp] = useState("");
  const [nText, setNText] = useState("3");
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
  const [modelNote, setModelNote] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    loadSnapshotIndex().then((index) => {
      if (!alive) return;
      setSnapshot(index);
    });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    const n = Number(nText);
    loadSnapshotIndex().then(async (index) => {
      if (!alive) return;
      setSnapshot(index);
      if (!Number.isInteger(n) || n < 1) {
        setPrefill(null);
        return;
      }
      const next = await loadThermoPrefill(CANONICAL_SERIES_ID, n, index);
      if (!alive) return;
      setPrefill(next);
      setTmC(next.tmC === null ? "" : String(next.tmC));
      setDeltaH(next.deltaH === null ? "" : String(next.deltaH));
      setDeltaCp(next.deltaCp === null ? "" : String(next.deltaCp));
      setAnchorG(next.deltaG === null ? "" : String(next.deltaG));
      setAnchorTRef(next.deltaGTemperatureC === null ? "" : String(next.deltaGTemperatureC));
      setAnchorUnits(next.deltaGUnits?.toLowerCase().includes("kj") ? "kJ" : "kcal");
      setModelNote(null);
      if (next.tmC === null && Number.isInteger(n) && n >= 3 && n <= 24) {
        const response = await fetch(`/api/stability/predict?n=${n}&t_assay_C=37`);
        if (!alive) return;
        if (response.ok) {
          const body = (await response.json()) as {
            anchor_temperature_C?: number;
            row?: {
              tm_C?: number | null;
              delta_g?: number | null;
              past_longest_cited_length?: boolean;
            };
          };
          const row = body.row;
          if (row && typeof row.tm_C === "number") {
            setTmC(String(row.tm_C));
            if (typeof row.delta_g === "number") {
              setAnchorG(String(row.delta_g));
              setAnchorTRef(String(body.anchor_temperature_C ?? PHILLIPS_PRINTED_DELTA_G_T_C));
              setAnchorUnits("kcal");
            }
            setModelNote(
              row.past_longest_cited_length
                ? "No paper row at this length. Melting temperature and anchor ΔG are the length model, past the longest cited length."
                : "No paper row at this length. Melting temperature and anchor ΔG are the length model.",
            );
          }
        }
      }
      setEffective(null);
      setEffectiveNote(null);
      setCurve(null);
    });
    return () => {
      alive = false;
    };
  }, [nText]);

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
  const printsColumn = seriesPrintsDeltaG(snapshot, CANONICAL_SERIES_ID);
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
          <p className="text-[11px] font-semibold tracking-[0.22em] text-studio-accent uppercase">Stability</p>
          <h1 className="mt-2 font-heading text-4xl leading-[1.1] font-semibold tracking-tight text-studio-foreground md:text-5xl">
            How stable is it at another temperature?
          </h1>
          <PageGuide
            intro="This page turns a melting temperature into unfolding energy at the temperature you care about. Use it when 37 °C is not the only temperature you will run."
            steps={[
              "Pick a repeat count from 3 to 24.",
              "Check the melt and the anchor energy. They fill in from the paper when a row exists, and from the length model when it does not.",
              "Type ΔH and ΔCp only if you have them. Leave them blank if you do not.",
              "Read ΔG at the melt first. It should be zero for a two-state unfold.",
            ]}
            read={[
              "ΔG is unfolding energy. At the melting temperature it is zero.",
              "Away from the melt, the curve needs ΔH at the melt and a heat capacity change, ΔCp.",
              "If you only have an anchor ΔG, the page can estimate an effective ΔH by assuming ΔCp is zero. That estimate is labeled as an assumption.",
              "With the stored heat-capacity values, calculated ΔG at 10 °C sits 0.5–5.0 kcal/mol above the printed number. That gap is still unexplained.",
            ]}
            rules={[
              "A paper cell is used when one exists. A missing cell is not left blank.",
              "Switching units does not convert a number you already typed.",
              "These curves are calculations. They are not a melt of our fusion.",
            ]}
            next={[
              "If ΔH and ΔCp are empty, do not treat the temperature curve as measured.",
              "Use the melting-temperature page when you only need pass or fail at 37 °C.",
            ]}
          />
        </div>
        <Badge
          className="rounded-full bg-studio-button text-studio-button-text"
          title="Calculated from published table values. Not measured on this fusion."
        >
          Not a lab measurement
        </Badge>
      </header>

      <div className="mt-10 grid items-start gap-8 lg:grid-cols-2 lg:gap-10">
        <section className="rounded-2xl border border-studio-border bg-studio-card p-5 md:p-8" aria-label="Inputs">
          <h2 className="font-heading text-2xl font-semibold tracking-tight text-studio-foreground">Inputs</h2>
          <p className="mt-2 text-sm leading-relaxed text-studio-muted">
            The melt and the anchor fill in for you. ΔH and ΔCp stay empty until you type them.
          </p>

          <div className="mt-8 rounded-xl border border-studio-border bg-studio-surface p-4">
            <h3 className="text-sm font-semibold text-studio-foreground">{CANONICAL_COPY.title}</h3>
            <p className="mt-1 text-sm leading-relaxed text-studio-muted">{CANONICAL_COPY.detail}</p>
          </div>

          <div className="mt-8 border-t border-studio-border pt-8">
            <h3 className="text-sm font-semibold text-studio-foreground">Repeat count</h3>
            <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Repeat count">
              {TEAM_LENGTHS.map((n) => (
                <ChoiceButton key={n} pressed={nText === String(n)} onClick={() => setNText(String(n))}>
                  n = {n}
                </ChoiceButton>
              ))}
            </div>
            <label className="mt-4 block text-sm font-medium text-studio-foreground">
              Any repeat count from 3 to 24
              <input
                className="mt-2 h-11 w-full rounded-lg border border-studio-border bg-studio-card px-3 text-base text-studio-foreground"
                type="number"
                min={3}
                max={24}
                value={nText}
                onChange={(event) => setNText(event.target.value)}
              />
            </label>
            <p className="mt-3 text-sm leading-relaxed text-studio-muted">
              A paper cell is filled in when one exists. Otherwise the length model supplies the melting temperature and the anchor ΔG, including n = 14.
            </p>
            {modelNote ? <p className="mt-2 text-sm leading-relaxed text-studio-muted">{modelNote}</p> : null}
          </div>

          <div className="mt-8 border-t border-studio-border pt-8">
            <label className="block text-sm font-semibold text-studio-foreground" htmlFor="tm-c">
              Melting temperature (°C)
            </label>
            <Input
              id="tm-c"
              className="mt-2 h-11 border-studio-border bg-studio-card text-base"
              inputMode="decimal"
              value={tmC}
              onChange={(event) => setTmC(event.target.value)}
            />
            {modelNote ? (
              <p className="mt-2 text-sm leading-relaxed text-studio-muted">{modelNote}</p>
            ) : caption ? (
              <p className="mt-2 text-sm leading-relaxed text-studio-muted">{caption}</p>
            ) : null}
          </div>

          <div className="mt-8 border-t border-studio-border pt-8">
            <h3 className="text-sm font-semibold text-studio-foreground">Anchor ΔG, optional</h3>
            <p className="mt-1 text-sm leading-relaxed text-studio-muted">
              Starts as the table value when that cell exists. Clearing it hides the ΔCp = 0 estimate. Editing it does not change the paper’s number.
            </p>
            <div className="mt-3">
              <UnitSwitch value={anchorUnits} onChange={setAnchorUnits} label="Anchor energy unit" />
              <p className="mt-2 text-sm leading-relaxed text-studio-muted">Switching units does not convert the number already typed.</p>
            </div>
            <label className="mt-4 block text-sm font-medium text-studio-foreground" htmlFor="anchor-g">
              Anchor ΔG ({anchorEnergy})
              <Input
                id="anchor-g"
                className="mt-2 h-11 border-studio-border bg-studio-card text-base"
                inputMode="decimal"
                value={anchorG}
                onChange={(event) => setAnchorG(event.target.value)}
              />
            </label>
            <label className="mt-4 block text-sm font-medium text-studio-foreground" htmlFor="anchor-t">
              Temperature of the anchor ΔG (°C)
              <Input
                id="anchor-t"
                className="mt-2 h-11 border-studio-border bg-studio-card text-base"
                inputMode="decimal"
                value={anchorTRef}
                onChange={(event) => setAnchorTRef(event.target.value)}
              />
            </label>
            <p className="mt-2 text-sm leading-relaxed text-studio-muted">
              {prefill?.deltaGTemperatureC != null
                ? `The paper states this value at ${formatQuantity(prefill.deltaGTemperatureC)} °C. It is not the melting temperature.`
                : "This is the temperature of the anchor ΔG. It is not the melting temperature, and none is assumed if you leave it blank."}
            </p>
            {prefill?.deltaG != null && anchorValue === prefill.deltaG ? (
              <p className="mt-2 text-sm leading-relaxed text-studio-muted">This anchor matches the paper’s number.</p>
            ) : null}
            {prefill?.deltaG != null && anchorValue !== null && anchorValue !== prefill.deltaG ? (
              <p className="mt-2 text-sm leading-relaxed text-studio-muted">This is a typed anchor. The paper’s number does not change.</p>
            ) : null}
          </div>

          <div className="mt-8 border-t border-studio-border pt-8">
            <h3 className="text-sm font-semibold text-studio-foreground">ΔHcal and ΔCp, optional</h3>
            <p className="mt-1 text-sm leading-relaxed text-studio-muted">
              Full temperature curves are drawn only after both of these are typed.
            </p>
            <div className="mt-3">
              <UnitSwitch value={units} onChange={setUnits} label="Calorimetry energy unit" />
              <p className="mt-2 text-sm leading-relaxed text-studio-muted">
                Switching units does not convert the numbers already typed. ΔHcal is in {energy}. ΔCp is in {entropy}.
              </p>
            </div>
            <label className="mt-4 block text-sm font-medium text-studio-foreground" htmlFor="delta-h">
              ΔHcal ({energy})
              <Input
                id="delta-h"
                className="mt-2 h-11 border-studio-border bg-studio-card text-base"
                inputMode="decimal"
                value={deltaH}
                onChange={(event) => setDeltaH(event.target.value)}
              />
            </label>
            <label className="mt-4 block text-sm font-medium text-studio-foreground" htmlFor="delta-cp">
              ΔCp ({entropy})
              <Input
                id="delta-cp"
                className="mt-2 h-11 border-studio-border bg-studio-card text-base"
                inputMode="decimal"
                value={deltaCp}
                onChange={(event) => setDeltaCp(event.target.value)}
              />
            </label>
          </div>
        </section>

        <section className="space-y-6" aria-label="Results">
          <h2 className="font-heading text-2xl font-semibold tracking-tight text-studio-foreground">Results</h2>

          <ResultBlock title="At the melting temperature" warm>
            {identity ? (
              <>
                <p className="font-heading text-5xl font-semibold tabular-nums tracking-tight text-studio-foreground">0</p>
                <p className="text-sm text-studio-muted">{zeroUnits}</p>
                <p className="text-sm leading-relaxed text-studio-foreground">ΔG at the melting temperature is 0 for a two-state melt.</p>
                <p className="text-sm leading-relaxed text-studio-muted">
                  Melting temperature {formatQuantity(identity.tmC)} °C ({formatQuantity(identity.tmK)} K).
                </p>
              </>
            ) : (
              <p className="text-sm leading-relaxed text-studio-muted">
                ΔG at the melting temperature is 0 for a two-state melt. No melting temperature is filled in, so that zero is not reported for this length.
              </p>
            )}
          </ResultBlock>

          <ResultBlock title="The paper’s number">
            {prefill?.deltaG != null ? (
              <>
                <p className="font-heading text-4xl font-semibold tabular-nums tracking-tight text-studio-foreground">{printedTableValue(prefill)}</p>
                <p className="text-sm leading-relaxed text-studio-foreground">{tableSentence(prefill)}</p>
              </>
            ) : prefill ? (
              <>
                <p className="font-heading text-3xl font-semibold tracking-tight text-studio-accent">Not printed</p>
                <p className="text-sm leading-relaxed text-studio-muted">
                  {missingTableSpeech(printsColumn, prefill.tmStatus === "extrapolated" || prefill.tmC === null)}
                </p>
              </>
            ) : (
              <p className="text-sm leading-relaxed text-studio-muted">
                The Phillips 2012 CTPRa DSC table prints unfolding ΔG at 10 °C when a cell exists. It is not calculated from the melting temperature.
              </p>
            )}
          </ResultBlock>

          <ResultBlock title="ΔCp = 0 estimate">
            {showEstimate && effective?.delta_h_eff != null ? (
              <>
                <p className="text-xs font-medium tracking-[0.14em] text-studio-label uppercase">Effective ΔH</p>
                <p className="font-heading text-4xl font-semibold tabular-nums tracking-tight text-studio-foreground">
                  {formatQuantity(effective.delta_h_eff)}{" "}
                  <span className="text-lg font-medium text-studio-muted">{prettyUnits(effective.delta_h_units ?? "")}</span>
                </p>
                <p className="text-sm leading-relaxed text-studio-foreground">This is an assumption, not the calorimetric ΔH from Phillips.</p>
                {effective.uncertainty_defined ? (
                  <div className="space-y-2 text-sm leading-relaxed text-studio-muted">
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
                  <p className="text-sm leading-relaxed text-studio-muted">
                    {bothPrinted
                      ? "No 95% band is drawn."
                      : "No 95% band is drawn. It appears only when both printed uncertainties are still the ones from the paper. A missing uncertainty is not zero."}
                  </p>
                )}
                <div className="rounded-xl border border-studio-border bg-studio-surface p-3">
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
                <p className="text-sm leading-relaxed text-studio-muted">ΔG(T) under the assumption that ΔCp is 0.</p>
                <p className="text-sm leading-relaxed text-studio-muted">
                  This curve assumes heat capacity does not change with temperature. It is a calculation, not a measurement on our protein.
                </p>
                {effective.human_review_required ? (
                  <p className="text-sm leading-relaxed text-studio-muted">A person should review this estimate before it is used.</p>
                ) : null}
                {effective.warnings.length > 0 ? (
                  <ul className="list-disc space-y-1 pl-5 text-sm leading-relaxed text-studio-muted">
                    {effective.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                ) : null}
              </>
            ) : (
              <p className="text-sm leading-relaxed text-studio-muted">
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
                <p className="text-sm leading-relaxed text-studio-muted">
                  These curves use the ΔHcal and ΔCp you typed. They are not the ΔCp = 0 estimate.
                </p>
                <p className="text-sm leading-relaxed text-studio-foreground">
                  ΔG at the melting temperature on this curve is {formatAtTm(curve.delta_g_at_tm)} {prettyUnits(curve.delta_g_units)}. ΔH at the melting temperature is {formatQuantity(curve.delta_h_at_tm)} {prettyUnits(curve.delta_h_units)}.
                </p>
                <CurveChart title="ΔG(T)" units={prettyUnits(curve.delta_g_units)} color="#FF8000" points={curve.points} tmC={curve.tm_c} read={(point) => point.delta_g} />
                <CurveChart title="ΔH(T)" units={prettyUnits(curve.delta_h_units)} color="var(--studio-foreground)" points={curve.points} tmC={curve.tm_c} read={(point) => point.delta_h} />
                <CurveChart title="ΔS(T)" units={prettyUnits(curve.delta_s_units)} color="#266FB1" points={curve.points} tmC={curve.tm_c} read={(point) => point.delta_s} />
                <p className="text-sm leading-relaxed text-studio-muted">{curve.result_label || CURVE_LABEL}</p>
                <p className="text-sm text-studio-foreground">These curves use the enthalpy and heat capacity you typed. They are calculations, not a measurement on our protein.</p>
                {pending ? <p className="text-sm text-studio-label">Updating the curves…</p> : null}
                {curve.warnings.length > 0 ? (
                  <ul className="list-disc space-y-1 pl-5 text-sm leading-relaxed text-studio-muted">
                    {curve.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : (
              <p className="text-sm leading-relaxed text-studio-muted">{curveNote}</p>
            )}
          </ResultBlock>
        </section>
      </div>
    </div>
  );
}
