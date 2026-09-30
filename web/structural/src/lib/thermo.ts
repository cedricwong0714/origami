/**
 * Client for the two-state Gibbs–Helmholtz calculator.
 *
 * Temperatures are sent in °C. The chassis converts with T_K = t_C + 273.15.
 * ΔH and ΔCp are filled only when the prefill payload actually contains them.
 * The stability snapshot is used for Tm alone.
 */

import { SERIES_COPY, type KnownSeriesId } from "@/lib/stability";

const KNOWN_SERIES_IDS = SERIES_COPY.map((item) => item.id);

const LIVE = process.env.NEXT_PUBLIC_SA_API ?? "";

export const THERMO_EQUATION = [
  "For a two-state unfold, temperatures are in kelvin (T_K = t_C + 273.15).",
  "ΔG at the melting temperature is 0. You do not need ΔH or ΔS for that value.",
  "The identity holds only for a two-state melt. It is not a wet-lab fit.",
  "",
  "A temperature curve away from Tm still needs ΔHcal and ΔCp.",
  "ΔHcal is ΔH at Tm. ΔCp is constant.",
  "",
  "ΔH(T) = ΔHcal + ΔCp (T − Tm)",
  "ΔS(T) = ΔHcal/Tm + ΔCp ln(T/Tm)",
  "ΔG(T) = ΔH(T) − T ΔS(T)",
].join("\n");

/**
 * Temperature stated for the Phillips et al. 2012 Table I unfolding ΔG column.
 * Source: data/stability/README.md, "Unfolding ΔG at 10°C".
 * Used only to label a looked-up table value when the payload omits the
 * temperature. It is not calculated from Tm.
 */
export const PHILLIPS_PRINTED_DELTA_G_T_C = 10;

/** Display window sent with a curve request. Not a DSC setpoint. */
export const CURVE_T_MIN_C = 0;
export const CURVE_T_MAX_C = 100;
export const CURVE_POINTS = 101;

export const CALORIMETRY_MISSING =
  "ΔHcal or ΔCp is blank, so no temperature curve is drawn. You do not need ΔH or ΔS to get ΔG at the melting temperature.";

export const EFFECTIVE_CAPTION =
  "ΔCp = 0 assumption, not the Phillips calorimetric ΔH.";

export const EFFECTIVE_EQUATION = [
  "When Tm and an anchor ΔG at a known temperature are both finite, ΔHcal and ΔCp are still two unknowns.",
  "The curve below closes that only by assuming ΔCp = 0. Temperatures are kelvin (T_K = t_C + 273.15).",
  "",
  "ΔH_eff = ΔG(T_ref) / (1 − T_ref/Tm)",
  "ΔG(T) = ΔH_eff (1 − T/Tm)",
  "ΔS_eff = ΔH_eff / Tm",
  "",
  "ΔH_eff is an effective enthalpy under that assumption. It is not the Phillips calorimetric ΔH.",
  "confidence tier is hypothesis_only. is_extrapolation is true. calibrated stays false.",
  "",
  "When the anchor ΔG and Tm both have a printed uncertainty, the ΔG(T) curve carries a 95% band.",
  "That band is value ± 1.96 σ from a first-order delta method. It is a linear approximation, not a wet-lab confidence interval.",
  "If the table printed no uncertainty, the point value is shown and the band is omitted. A blank sigma is not zero.",
].join("\n");

export const CURVE_LABEL =
  "Calculation from the ΔHcal, ΔCp, and Tm entered here. calibrated = false. This is not a measurement of the Hong Kong team fusion.";

export type EnergyUnits = "kcal" | "kJ";

export type ThermoReport = {
  calibrated: boolean;
  delta_g: number;
  delta_h: number;
  delta_s: number;
  delta_g_units: string;
  delta_h_units: string;
  delta_s_units: string;
  t_c: number;
  t_k: number;
  tm_c: number;
  tm_k: number;
  unit_conversion_applied: boolean;
  uncertainty_defined: boolean;
  uncertainty_note: string;
  delta_g_sigma: number | null;
  delta_g_95_lower: number | null;
  delta_g_95_upper: number | null;
  delta_h_sigma: number | null;
  delta_h_95_lower: number | null;
  delta_h_95_upper: number | null;
  delta_s_sigma: number | null;
  delta_s_95_lower: number | null;
  delta_s_95_upper: number | null;
  assumptions: string[];
  warnings: string[];
};

export type TmStatus = "cited" | "extrapolated" | "omitted" | null;

export type ThermoPrefill = {
  origin: "api" | "snapshot" | "none";
  tmStatus: TmStatus;
  tmC: number | null;
  tmUncertainty: number | null;
  deltaH: number | null;
  deltaCp: number | null;
  deltaG: number | null;
  deltaGUnits: string | null;
  deltaGUncertainty: number | null;
  deltaGOrigin: "looked_up" | null;
  deltaGTemperatureC: number | null;
  doi: string | null;
  method: string | null;
  message: string;
};

export type ThermoCurvePoint = {
  t_c: number;
  t_k: number;
  delta_h: number;
  delta_s: number;
  delta_g: number;
};

export type ThermoCurve = {
  calibrated: boolean;
  has_curve: boolean;
  message: string;
  result_label: string;
  delta_g_units: string;
  delta_h_units: string;
  delta_s_units: string;
  delta_g_at_tm: number;
  delta_h_at_tm: number;
  delta_s_at_tm: number;
  tm_c: number;
  tm_k: number;
  points: ThermoCurvePoint[];
  unit_conversion_applied: boolean;
  warnings: string[];
};

export type ThermoInputs = {
  tC: number;
  tmC: number;
  deltaH: number;
  deltaCp: number;
  units: EnergyUnits;
  deltaHSigma?: number;
  deltaCpSigma?: number;
  tmSigmaC?: number;
};

type SnapshotIndex = {
  seriesIds: string[];
  nBySeries: Map<string, number[]>;
  rows: Map<string, Record<string, unknown>[]>;
};

function finiteOrNull(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return value;
}

function textOrNull(value: unknown): string | null {
  if (typeof value !== "string" || value.trim() === "") return null;
  return value;
}

function requireFinite(value: unknown, field: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`Calculator response is missing a finite ${field}.`);
  }
  return value;
}

function requireText(value: unknown, field: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Calculator response is missing ${field}.`);
  }
  return value;
}

function optionalSigma(value: unknown, field: string): number | null {
  if (value === null || value === undefined) return null;
  return requireFinite(value, field);
}

export function parseThermoReport(body: unknown): ThermoReport {
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    throw new Error("Calculator response is not an object.");
  }
  const row = body as Record<string, unknown>;
  if (typeof row.calibrated !== "boolean") {
    throw new Error("Calculator response is missing calibrated.");
  }
  if (typeof row.uncertainty_defined !== "boolean") {
    throw new Error("Calculator response is missing uncertainty_defined.");
  }
  if (typeof row.unit_conversion_applied !== "boolean") {
    throw new Error("Calculator response is missing unit_conversion_applied.");
  }
  const assumptions = row.assumptions;
  const warnings = row.warnings;
  if (!Array.isArray(assumptions) || assumptions.some((item) => typeof item !== "string")) {
    throw new Error("Calculator response is missing assumptions.");
  }
  if (!Array.isArray(warnings) || warnings.some((item) => typeof item !== "string")) {
    throw new Error("Calculator response is missing warnings.");
  }
  return {
    calibrated: row.calibrated,
    delta_g: requireFinite(row.delta_g, "delta_g"),
    delta_h: requireFinite(row.delta_h, "delta_h"),
    delta_s: requireFinite(row.delta_s, "delta_s"),
    delta_g_units: requireText(row.delta_g_units, "delta_g_units"),
    delta_h_units: requireText(row.delta_h_units, "delta_h_units"),
    delta_s_units: requireText(row.delta_s_units, "delta_s_units"),
    t_c: requireFinite(row.t_c, "t_c"),
    t_k: requireFinite(row.t_k, "t_k"),
    tm_c: requireFinite(row.tm_c, "tm_c"),
    tm_k: requireFinite(row.tm_k, "tm_k"),
    unit_conversion_applied: row.unit_conversion_applied,
    uncertainty_defined: row.uncertainty_defined,
    uncertainty_note: requireText(row.uncertainty_note, "uncertainty_note"),
    delta_g_sigma: optionalSigma(row.delta_g_sigma, "delta_g_sigma"),
    delta_g_95_lower: optionalSigma(row.delta_g_95_lower, "delta_g_95_lower"),
    delta_g_95_upper: optionalSigma(row.delta_g_95_upper, "delta_g_95_upper"),
    delta_h_sigma: optionalSigma(row.delta_h_sigma, "delta_h_sigma"),
    delta_h_95_lower: optionalSigma(row.delta_h_95_lower, "delta_h_95_lower"),
    delta_h_95_upper: optionalSigma(row.delta_h_95_upper, "delta_h_95_upper"),
    delta_s_sigma: optionalSigma(row.delta_s_sigma, "delta_s_sigma"),
    delta_s_95_lower: optionalSigma(row.delta_s_95_lower, "delta_s_95_lower"),
    delta_s_95_upper: optionalSigma(row.delta_s_95_upper, "delta_s_95_upper"),
    assumptions: assumptions as string[],
    warnings: warnings as string[],
  };
}

export function formatQuantity(value: number): string {
  if (!Number.isFinite(value)) return "not finite";
  const abs = Math.abs(value);
  if (abs !== 0 && (abs < 1e-4 || abs >= 1e6)) return value.toExponential(4);
  const digits = abs >= 100 ? 4 : 6;
  return value.toLocaleString("en-US", { maximumFractionDigits: digits });
}

export function energyUnitLabel(units: EnergyUnits, kind: "energy" | "entropy"): string {
  if (units === "kJ") {
    return kind === "energy" ? "kJ mol⁻¹" : "kJ mol⁻¹ K⁻¹";
  }
  return kind === "energy" ? "kcal mol⁻¹" : "kcal mol⁻¹ K⁻¹";
}

async function errorDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string" && detail.trim() !== "") return detail;
    }
  } catch {
    // The body was not JSON.
  }
  return `The calculator returned HTTP ${response.status}.`;
}

export async function postThermo(inputs: ThermoInputs): Promise<ThermoReport> {
  const payload: Record<string, number | string> = {
    t_c: inputs.tC,
    tm_c: inputs.tmC,
    delta_h: inputs.deltaH,
    delta_cp: inputs.deltaCp,
    units: inputs.units,
  };
  if (inputs.deltaHSigma !== undefined) payload.delta_h_sigma = inputs.deltaHSigma;
  if (inputs.deltaCpSigma !== undefined) payload.delta_cp_sigma = inputs.deltaCpSigma;
  if (inputs.tmSigmaC !== undefined) payload.tm_sigma_c = inputs.tmSigmaC;
  let response: Response;
  try {
    response = await fetch(`${LIVE}/api/stability/thermo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error("The calculator API did not answer. No ΔG was filled in.");
  }
  if (!response.ok) {
    throw new Error(await errorDetail(response));
  }
  return parseThermoReport(await response.json());
}

function tmStatusOf(value: unknown, tmC: number | null): TmStatus {
  if (value === "cited" || value === "extrapolated" || value === "omitted") return value;
  if (tmC === null) return null;
  return "cited";
}

function prefillMessage(prefill: Omit<ThermoPrefill, "message">): string {
  const parts: string[] = [];
  if (prefill.origin === "api") {
    parts.push("Prefill from the literature API.");
  } else if (prefill.origin === "snapshot") {
    parts.push("Prefill from stability-snapshot.json. Only Tm and the printed ΔG are copied from the snapshot.");
  }
  if (prefill.tmStatus === "extrapolated" || (prefill.tmC === null && prefill.tmStatus !== "omitted")) {
    parts.push(
      "No cited Tm at this repeat count. It stays extrapolated. The Tm field is empty. A temperature you type is a user-entered Tm, not a cited one.",
    );
  } else if (prefill.tmC === null) {
    parts.push(
      "No cited Tm at this repeat count. Interpolation is not applied. The Tm field is empty. A temperature you type is a user-entered Tm, not a cited one.",
    );
  } else {
    const uncertainty =
      prefill.tmUncertainty === null ? "" : ` (printed uncertainty ${formatQuantity(prefill.tmUncertainty)} °C)`;
    parts.push(`Cited Tm ${formatQuantity(prefill.tmC)} °C${uncertainty}.`);
  }
  if (prefill.deltaH === null || prefill.deltaCp === null) {
    parts.push(
      "ΔHcal and ΔCp stay blank. They are not the DSC values, and they are not filled from the printed ΔG.",
    );
  }
  if (prefill.deltaG !== null) {
    const units = prefill.deltaGUnits ?? "reported units";
    const at =
      prefill.deltaGTemperatureC === null
        ? ""
        : ` at ${formatQuantity(prefill.deltaGTemperatureC)} °C`;
    parts.push(
      `Looked up, not calculated from Tm: printed unfolding ΔG is ${formatQuantity(prefill.deltaG)} ${units}${at}.`,
    );
  }
  if (prefill.method || prefill.doi) {
    const source = [prefill.method, prefill.doi ? `DOI ${prefill.doi}` : null].filter(Boolean).join(", ");
    parts.push(`Source: ${source}.`);
  }
  return parts.join(" ");
}

function lookedUpDeltaG(row: Record<string, unknown>): {
  deltaG: number | null;
  deltaGUnits: string | null;
  deltaGUncertainty: number | null;
  deltaGOrigin: "looked_up" | null;
  deltaGTemperatureC: number | null;
} {
  const deltaG = finiteOrNull(row.delta_g);
  if (deltaG === null) {
    return {
      deltaG: null,
      deltaGUnits: null,
      deltaGUncertainty: null,
      deltaGOrigin: null,
      deltaGTemperatureC: null,
    };
  }
  const stated = finiteOrNull(row.delta_g_t_c);
  return {
    deltaG,
    deltaGUnits: textOrNull(row.delta_g_units),
    deltaGUncertainty: finiteOrNull(row.delta_g_uncertainty),
    deltaGOrigin: "looked_up",
    deltaGTemperatureC: stated === null ? PHILLIPS_PRINTED_DELTA_G_T_C : stated,
  };
}

function fromApiBody(body: unknown): ThermoPrefill | null {
  if (!body || typeof body !== "object" || Array.isArray(body)) return null;
  const row = body as Record<string, unknown>;
  const tmC = finiteOrNull(row.tm_c);
  const printed = lookedUpDeltaG(row);
  const prefill: Omit<ThermoPrefill, "message"> = {
    origin: "api",
    tmStatus: tmStatusOf(row.tm_status, tmC),
    tmC,
    tmUncertainty: finiteOrNull(row.tm_uncertainty),
    deltaH: finiteOrNull(row.delta_h),
    deltaCp: finiteOrNull(row.delta_cp),
    ...printed,
    doi: textOrNull(row.doi),
    method: textOrNull(row.method),
  };
  return { ...prefill, message: prefillMessage(prefill) };
}

export async function loadSnapshotIndex(): Promise<SnapshotIndex> {
  const empty: SnapshotIndex = {
    seriesIds: [...KNOWN_SERIES_IDS],
    nBySeries: new Map(),
    rows: new Map(),
  };
  try {
    const response = await fetch("/stability-snapshot.json", { cache: "no-store" });
    if (!response.ok) return empty;
    const body: unknown = await response.json();
    if (!body || typeof body !== "object" || !Array.isArray((body as { rows?: unknown }).rows)) {
      return empty;
    }
    const rows = (body as { rows: unknown[] }).rows;
    const nBySeries = new Map<string, number[]>();
    const grouped = new Map<string, Record<string, unknown>[]>();
    for (const item of rows) {
      if (!item || typeof item !== "object") continue;
      const row = item as Record<string, unknown>;
      if (typeof row.series_id !== "string" || !Number.isInteger(row.n_repeats)) continue;
      const seriesId = row.series_id;
      const nRepeats = row.n_repeats as number;
      const ns = nBySeries.get(seriesId) ?? [];
      if (!ns.includes(nRepeats)) ns.push(nRepeats);
      nBySeries.set(seriesId, ns);
      const bucket = grouped.get(seriesId) ?? [];
      bucket.push(row);
      grouped.set(seriesId, bucket);
    }
    for (const ns of nBySeries.values()) ns.sort((a, b) => a - b);
    const known = new Set<string>(KNOWN_SERIES_IDS);
    const seriesIds = [
      ...KNOWN_SERIES_IDS,
      ...[...nBySeries.keys()].filter((id) => !known.has(id)),
    ];
    return { seriesIds, nBySeries, rows: grouped };
  } catch {
    return empty;
  }
}

export function seriesTitle(seriesId: string): string {
  const known = SERIES_COPY.find((item) => item.id === (seriesId as KnownSeriesId));
  return known?.title ?? seriesId;
}

export function repeatCounts(index: SnapshotIndex, seriesId: string): number[] {
  return index.nBySeries.get(seriesId) ?? [];
}

function fromSnapshot(index: SnapshotIndex, seriesId: string, n: number): ThermoPrefill {
  const matches = (index.rows.get(seriesId) ?? []).filter((row) => row.n_repeats === n);
  if (matches.length !== 1) {
    const prefill: Omit<ThermoPrefill, "message"> = {
      origin: "snapshot",
      tmStatus: matches.length === 0 ? "extrapolated" : null,
      tmC: null,
      tmUncertainty: null,
      deltaH: null,
      deltaCp: null,
      deltaG: null,
      deltaGUnits: null,
      deltaGUncertainty: null,
      deltaGOrigin: null,
      deltaGTemperatureC: null,
      doi: null,
      method: null,
    };
    const reason =
      matches.length === 0
        ? "The snapshot has no row for this series and repeat count. Tm was not interpolated."
        : "More than one snapshot row matches this series and repeat count. They were not averaged, and Tm was left empty.";
    return { ...prefill, message: `${reason} ΔH and ΔCp were left blank.` };
  }
  const row = matches[0] ?? {};
  const tmC = finiteOrNull(row.tm_C);
  const printed = lookedUpDeltaG(row);
  const prefill: Omit<ThermoPrefill, "message"> = {
    origin: "snapshot",
    tmStatus: tmStatusOf(row.thermal_state, tmC),
    tmC,
    tmUncertainty: finiteOrNull(row.tm_uncertainty_C),
    deltaH: null,
    deltaCp: null,
    ...printed,
    doi: null,
    method: null,
  };
  return { ...prefill, message: prefillMessage(prefill) };
}

function parseCurvePoint(value: unknown, index: number): ThermoCurvePoint {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`Curve point ${index} is not an object.`);
  }
  const row = value as Record<string, unknown>;
  return {
    t_c: requireFinite(row.t_c, `points[${index}].t_c`),
    t_k: requireFinite(row.t_k, `points[${index}].t_k`),
    delta_h: requireFinite(row.delta_h, `points[${index}].delta_h`),
    delta_s: requireFinite(row.delta_s, `points[${index}].delta_s`),
    delta_g: requireFinite(row.delta_g, `points[${index}].delta_g`),
  };
}

export function parseThermoCurve(body: unknown): ThermoCurve {
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    throw new Error("Curve response is not an object.");
  }
  const row = body as Record<string, unknown>;
  if (row.has_curve !== true) {
    throw new Error(CALORIMETRY_MISSING);
  }
  if (row.calibrated !== false) {
    throw new Error("Curve response must keep calibrated false.");
  }
  if (!Array.isArray(row.points) || row.points.length === 0) {
    throw new Error("The calculator returned no curve. Nothing was plotted.");
  }
  const warnings = row.warnings;
  if (!Array.isArray(warnings) || warnings.some((item) => typeof item !== "string")) {
    throw new Error("Curve response is missing warnings.");
  }
  return {
    calibrated: false,
    has_curve: true,
    message: requireText(row.message, "message"),
    result_label: requireText(row.result_label, "result_label"),
    delta_g_units: requireText(row.delta_g_units, "delta_g_units"),
    delta_h_units: requireText(row.delta_h_units, "delta_h_units"),
    delta_s_units: requireText(row.delta_s_units, "delta_s_units"),
    delta_g_at_tm: requireFinite(row.delta_g_at_tm, "delta_g_at_tm"),
    delta_h_at_tm: requireFinite(row.delta_h_at_tm, "delta_h_at_tm"),
    delta_s_at_tm: requireFinite(row.delta_s_at_tm, "delta_s_at_tm"),
    tm_c: requireFinite(row.tm_c, "tm_c"),
    tm_k: requireFinite(row.tm_k, "tm_k"),
    points: row.points.map((point, index) => parseCurvePoint(point, index)),
    unit_conversion_applied: row.unit_conversion_applied === true,
    warnings: warnings as string[],
  };
}

export async function postThermoCurve(inputs: {
  tmC: number;
  deltaH: number;
  deltaCp: number;
  units: EnergyUnits;
  tMinC: number;
  tMaxC: number;
}): Promise<ThermoCurve> {
  let response: Response;
  try {
    response = await fetch(`${LIVE}/api/stability/thermo/curves`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tm_c: inputs.tmC,
        delta_h: inputs.deltaH,
        delta_cp: inputs.deltaCp,
        units: inputs.units,
        t_min_c: inputs.tMinC,
        t_max_c: inputs.tMaxC,
        n_points: CURVE_POINTS,
      }),
    });
  } catch {
    throw new Error("The calculator API did not answer. No curve was filled in.");
  }
  if (!response.ok) {
    throw new Error(await errorDetail(response));
  }
  return parseThermoCurve(await response.json());
}

export async function loadThermoPrefill(
  seriesId: string,
  n: number,
  index: SnapshotIndex,
): Promise<ThermoPrefill> {
  try {
    const response = await fetch(
      `${LIVE}/api/stability/thermo/prefill?series_id=${encodeURIComponent(seriesId)}&n=${n}`,
      { cache: "no-store" },
    );
    if (response.ok) {
      const parsed = fromApiBody(await response.json());
      if (parsed) return parsed;
    }
  } catch {
    // Fall through to the snapshot for Tm only.
  }
  if (index.rows.has(seriesId)) return fromSnapshot(index, seriesId, n);
  const prefill: Omit<ThermoPrefill, "message"> = {
    origin: "none",
    tmStatus: null,
    tmC: null,
    tmUncertainty: null,
    deltaH: null,
    deltaCp: null,
    deltaG: null,
    deltaGUnits: null,
    deltaGUncertainty: null,
    deltaGOrigin: null,
    deltaGTemperatureC: null,
    doi: null,
    method: null,
  };
  return {
    ...prefill,
    message: "The literature lookup did not answer. Tm, ΔH, and ΔCp were not filled.",
  };
}

export type EffectivePoint = {
  t_c: number;
  t_k: number;
  delta_h: number;
  delta_s: number;
  delta_g: number;
  delta_g_sigma: number | null;
  delta_g_95_lower: number | null;
  delta_g_95_upper: number | null;
};

export type EffectiveEnthalpy = {
  calibrated: false;
  confidence_tier: "hypothesis_only" | null;
  is_extrapolation: boolean | null;
  human_review_required: boolean;
  has_effective_enthalpy: boolean;
  has_curve: boolean;
  message: string;
  result_label: string;
  assumption_delta_cp: number | null;
  delta_h_eff: number | null;
  delta_h_eff_sigma: number | null;
  delta_h_eff_95_lower: number | null;
  delta_h_eff_95_upper: number | null;
  delta_s_eff: number | null;
  delta_g_at_tm: number | null;
  delta_g_at_t_ref: number | null;
  delta_g_at_t_ref_sigma: number | null;
  delta_g_at_t_ref_95_lower: number | null;
  delta_g_at_t_ref_95_upper: number | null;
  anchor_delta_g: number | null;
  uncertainty_defined: boolean;
  uncertainty_note: string;
  delta_g_units: string | null;
  delta_h_units: string | null;
  delta_s_units: string | null;
  t_ref_c: number | null;
  t_ref_k: number | null;
  tm_c: number | null;
  tm_k: number | null;
  points: EffectivePoint[];
  unit_conversion_applied: boolean;
  warnings: string[];
  assumptions: string[];
};

function optionalFinite(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  return finiteOrNull(value);
}

export function parseEffectiveEnthalpy(body: unknown): EffectiveEnthalpy {
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    throw new Error("Effective-enthalpy response is not an object.");
  }
  const row = body as Record<string, unknown>;
  if (row.calibrated !== false) {
    throw new Error("Effective-enthalpy response must keep calibrated false.");
  }
  if (typeof row.has_effective_enthalpy !== "boolean") {
    throw new Error("Effective-enthalpy response is missing has_effective_enthalpy.");
  }
  const warnings = row.warnings;
  const assumptions = row.assumptions;
  if (!Array.isArray(warnings) || warnings.some((item) => typeof item !== "string")) {
    throw new Error("Effective-enthalpy response is missing warnings.");
  }
  if (!Array.isArray(assumptions) || assumptions.some((item) => typeof item !== "string")) {
    throw new Error("Effective-enthalpy response is missing assumptions.");
  }
  if (typeof row.uncertainty_defined !== "boolean") {
    throw new Error("Effective-enthalpy response is missing uncertainty_defined.");
  }
  const uncertaintyDefined = row.uncertainty_defined;
  const uncertaintyNote = requireText(row.uncertainty_note, "uncertainty_note");
  const points = Array.isArray(row.points)
    ? row.points.map((point, index) => parseEffectivePoint(point, index, uncertaintyDefined))
    : [];
  if (row.has_effective_enthalpy) {
    if (row.confidence_tier !== "hypothesis_only" || row.is_extrapolation !== true) {
      throw new Error("ΔCp = 0 output must be hypothesis_only and an extrapolation.");
    }
    if (row.assumption_delta_cp !== 0) {
      throw new Error("ΔCp = 0 output is missing the explicit zero heat capacity.");
    }
    if (points.length === 0) {
      throw new Error("ΔCp = 0 output did not include a ΔG(T) curve.");
    }
    return {
      calibrated: false,
      confidence_tier: "hypothesis_only",
      is_extrapolation: true,
      human_review_required: row.human_review_required === true,
      has_effective_enthalpy: true,
      has_curve: true,
      message: requireText(row.message, "message"),
      result_label: requireText(row.result_label, "result_label"),
      assumption_delta_cp: 0,
      delta_h_eff: requireFinite(row.delta_h_eff, "delta_h_eff"),
      delta_h_eff_sigma: uncertaintyDefined
        ? requireFinite(row.delta_h_eff_sigma, "delta_h_eff_sigma")
        : optionalSigma(row.delta_h_eff_sigma, "delta_h_eff_sigma"),
      delta_h_eff_95_lower: uncertaintyDefined
        ? requireFinite(row.delta_h_eff_95_lower, "delta_h_eff_95_lower")
        : optionalSigma(row.delta_h_eff_95_lower, "delta_h_eff_95_lower"),
      delta_h_eff_95_upper: uncertaintyDefined
        ? requireFinite(row.delta_h_eff_95_upper, "delta_h_eff_95_upper")
        : optionalSigma(row.delta_h_eff_95_upper, "delta_h_eff_95_upper"),
      delta_s_eff: requireFinite(row.delta_s_eff, "delta_s_eff"),
      delta_g_at_tm: requireFinite(row.delta_g_at_tm, "delta_g_at_tm"),
      delta_g_at_t_ref: requireFinite(row.delta_g_at_t_ref, "delta_g_at_t_ref"),
      delta_g_at_t_ref_sigma: uncertaintyDefined
        ? requireFinite(row.delta_g_at_t_ref_sigma, "delta_g_at_t_ref_sigma")
        : optionalSigma(row.delta_g_at_t_ref_sigma, "delta_g_at_t_ref_sigma"),
      delta_g_at_t_ref_95_lower: uncertaintyDefined
        ? requireFinite(row.delta_g_at_t_ref_95_lower, "delta_g_at_t_ref_95_lower")
        : optionalSigma(row.delta_g_at_t_ref_95_lower, "delta_g_at_t_ref_95_lower"),
      delta_g_at_t_ref_95_upper: uncertaintyDefined
        ? requireFinite(row.delta_g_at_t_ref_95_upper, "delta_g_at_t_ref_95_upper")
        : optionalSigma(row.delta_g_at_t_ref_95_upper, "delta_g_at_t_ref_95_upper"),
      anchor_delta_g: requireFinite(row.anchor_delta_g, "anchor_delta_g"),
      uncertainty_defined: uncertaintyDefined,
      uncertainty_note: uncertaintyNote,
      delta_g_units: requireText(row.delta_g_units, "delta_g_units"),
      delta_h_units: requireText(row.delta_h_units, "delta_h_units"),
      delta_s_units: requireText(row.delta_s_units, "delta_s_units"),
      t_ref_c: requireFinite(row.t_ref_c, "t_ref_c"),
      t_ref_k: requireFinite(row.t_ref_k, "t_ref_k"),
      tm_c: requireFinite(row.tm_c, "tm_c"),
      tm_k: requireFinite(row.tm_k, "tm_k"),
      points,
      unit_conversion_applied: row.unit_conversion_applied === true,
      warnings: warnings as string[],
      assumptions: assumptions as string[],
    };
  }
  return {
    calibrated: false,
    confidence_tier: null,
    is_extrapolation: null,
    human_review_required: false,
    has_effective_enthalpy: false,
    has_curve: false,
    message: requireText(row.message, "message"),
    result_label: requireText(row.result_label, "result_label"),
    assumption_delta_cp: null,
    delta_h_eff: null,
    delta_h_eff_sigma: null,
    delta_h_eff_95_lower: null,
    delta_h_eff_95_upper: null,
    delta_s_eff: null,
    delta_g_at_tm: optionalFinite(row.delta_g_at_tm),
    delta_g_at_t_ref: null,
    delta_g_at_t_ref_sigma: null,
    delta_g_at_t_ref_95_lower: null,
    delta_g_at_t_ref_95_upper: null,
    anchor_delta_g: null,
    uncertainty_defined: false,
    uncertainty_note: uncertaintyNote,
    delta_g_units: textOrNull(row.delta_g_units),
    delta_h_units: null,
    delta_s_units: null,
    t_ref_c: null,
    t_ref_k: null,
    tm_c: optionalFinite(row.tm_c),
    tm_k: optionalFinite(row.tm_k),
    points: [],
    unit_conversion_applied: false,
    warnings: warnings as string[],
    assumptions: assumptions as string[],
  };
}

function parseEffectivePoint(value: unknown, index: number, requireBand: boolean): EffectivePoint {
  const point = parseCurvePoint(value, index);
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`Curve point ${index} is not an object.`);
  }
  const row = value as Record<string, unknown>;
  const sigma = requireBand
    ? requireFinite(row.delta_g_sigma, `points[${index}].delta_g_sigma`)
    : optionalSigma(row.delta_g_sigma, `points[${index}].delta_g_sigma`);
  const low = requireBand
    ? requireFinite(row.delta_g_95_lower, `points[${index}].delta_g_95_lower`)
    : optionalSigma(row.delta_g_95_lower, `points[${index}].delta_g_95_lower`);
  const high = requireBand
    ? requireFinite(row.delta_g_95_upper, `points[${index}].delta_g_95_upper`)
    : optionalSigma(row.delta_g_95_upper, `points[${index}].delta_g_95_upper`);
  return {
    ...point,
    delta_g_sigma: sigma,
    delta_g_95_lower: low,
    delta_g_95_upper: high,
  };
}

export async function postEffectiveEnthalpy(inputs: {
  tmC: number;
  deltaGRef: number | null;
  tRefC: number | null;
  units: EnergyUnits;
  deltaGSigma?: number | null;
  tmSigmaC?: number | null;
}): Promise<EffectiveEnthalpy> {
  let response: Response;
  try {
    response = await fetch(`${LIVE}/api/stability/thermo/effective`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tm_c: inputs.tmC,
        delta_g_ref: inputs.deltaGRef,
        t_ref_c: inputs.tRefC,
        units: inputs.units,
        delta_g_sigma: inputs.deltaGSigma ?? null,
        tm_sigma_c: inputs.tmSigmaC ?? null,
        t_min_c: CURVE_T_MIN_C,
        t_max_c: CURVE_T_MAX_C,
        n_points: CURVE_POINTS,
      }),
    });
  } catch {
    throw new Error("The calculator API did not answer. No ΔG(T) was filled in.");
  }
  if (!response.ok) {
    throw new Error(await errorDetail(response));
  }
  return parseEffectiveEnthalpy(await response.json());
}
