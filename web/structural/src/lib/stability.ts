/**
 * Stability confirmation screen.
 *
 * The live confirm payload is a per-series length fit. The number at
 * n = 3, n = 8, and n = 14 is that model evaluated at n. The panel
 * route and the wiki snapshot remain the literature lookup.
 *
 * The confirmation screen uses Phillips 2012 CTPRa DSC only. This module
 * does not average series and does not fill a missing melting temperature with 0.
 *
 * Citation strings below are copied from
 * data/stability/ctpr_thermal_literature.json. Buffer, pH, method, and
 * construct family are the series keys in origami/stability/series.py.
 * 37 °C is the screen's comparison temperature: an E. coli operating
 * assumption, not a DSC setpoint from those papers.
 */

export const TEAM_LENGTHS = [3, 8, 14] as const;

/** Canonical literature series for team-facing stability confirmation. */
export const CANONICAL_SERIES_ID = "phillips2012_ctpra_dsc" as const;

export const SERIES_IDS = [
  "phillips2012_ctpra_dsc",
  "cortajarena2011_ctpra_dsc",
  "phillips2012_ctpra_cd",
  "phillips2012_ctpr_dsc",
] as const;

export type KnownSeriesId = (typeof SERIES_IDS)[number];

export type FittedParameter = {
  name: string;
  value: number;
  units: string;
  standard_error: number | null;
  identifiable: boolean;
};

export type SeriesCurveFit = {
  form: string;
  equation: string;
  n_points: number;
  n_repeats: number[];
  units: string;
  longest_cited_n: number | null;
  warnings: string[];
  parameters: FittedParameter[];
};

export type SeriesFitBlock = {
  series_id: string;
  tm: SeriesCurveFit;
  delta_g: SeriesCurveFit;
};

export type StabilityRow = {
  series_id: string;
  n_repeats: number;
  t_assay_C: number;
  thermal_state: string;
  tm_C: number | null;
  /** Fit sigma in °C when the payload is a length fit. Lookup rows still carry the printed sigma. */
  tm_uncertainty_C: number | null;
  tm_interval_low: number | null;
  tm_interval_high: number | null;
  tm_band_label: string | null;
  tm_fit_form: string | null;
  delta_g: number | null;
  delta_g_units: string | null;
  delta_g_uncertainty: number | null;
  delta_g_band_95_low: number | null;
  delta_g_band_95_high: number | null;
  delta_g_band_label: string | null;
  delta_g_fit_form: string | null;
  /** Present on the fit payload. Undefined on the raw lookup. */
  paper_tm_C?: number | null;
  paper_delta_g?: number | null;
  paper_delta_g_units?: string | null;
  comparison_uses_fit: boolean;
  length_note: string | null;
  past_longest_cited_length: boolean;
  calibrated: boolean;
  thermal_reason: string | null;
};

export type StabilityPanel = {
  calibrated: boolean;
  t_assay_C: number;
  rows: StabilityRow[];
  series_fits?: SeriesFitBlock[];
  literature_series_id?: string;
  doi?: string;
  method?: string;
  construct_family?: string;
  comparison?: string;
  equation_saturating?: string;
  equation_line?: string;
  note?: string;
  source?: "live" | "snapshot";
};

export type SeriesCopy = {
  id: KnownSeriesId;
  title: string;
  isDefault: boolean;
  citation: string;
  doi: string;
  detail: string;
};

export const SERIES_COPY: readonly SeriesCopy[] = [
  {
    id: "phillips2012_ctpra_dsc",
    title: "Phillips et al. 2012, CTPRa, DSC",
    isDefault: true,
    citation:
      "Phillips JJ, Javadi Y, Millership C, Main ERG. Modulation of the multistate folding of designed TPR proteins through intrinsic and extrinsic factors. Protein Sci. 2012;21(3):327-338.",
    doi: "10.1002/pro.2018",
    detail: "Default numbers. CTPRa proteins measured by DSC in 50 mM phosphate, pH 7.0, Table I.",
  },
  {
    id: "cortajarena2011_ctpra_dsc",
    title: "Cortajarena and Regan 2011, CTPRa, DSC",
    isDefault: false,
    citation:
      "Cortajarena AL, Regan L. Calorimetric study of a series of designed repeat proteins: modular structure and modular folding. Protein Sci. 2011;20(2):336-340.",
    doi: "10.1002/pro.564",
    detail: "CTPRa proteins measured by DSC in 150 mM NaCl, 50 mM phosphate, pH 6.8, Table I.",
  },
  {
    id: "phillips2012_ctpra_cd",
    title: "Phillips et al. 2012, CTPRa, CD",
    isDefault: false,
    citation:
      "Phillips JJ, Javadi Y, Millership C, Main ERG. Modulation of the multistate folding of designed TPR proteins through intrinsic and extrinsic factors. Protein Sci. 2012;21(3):327-338.",
    doi: "10.1002/pro.2018",
    detail: "CTPRa proteins measured by circular dichroism in 50 mM phosphate, pH 7.0, Table I.",
  },
  {
    id: "phillips2012_ctpr_dsc",
    title: "Phillips et al. 2012, CTPR, DSC",
    isDefault: false,
    citation:
      "Phillips JJ, Javadi Y, Millership C, Main ERG. Modulation of the multistate folding of designed TPR proteins through intrinsic and extrinsic factors. Protein Sci. 2012;21(3):327-338.",
    doi: "10.1002/pro.2018",
    detail: "CTPR proteins measured by DSC in 50 mM phosphate, pH 7.0, Table I.",
  },
];

/** Word shown when a melting temperature was not calculated. Never a zero. */
export const MISSING_TM_LABEL = "Not fit";

/** Printed ΔG column when that table has no value at this length. */
export const MISSING_DELTA_G_LABEL = "not printed";

/**
 * Shown when the table printed no Tm uncertainty.
 * A gate envelope of low = high = Tm is not a measured ±0.
 */
export const OMITTED_UNCERTAINTY_LABEL = "omitted";

/** Shown beside a calculated length that is past the longest cited n in that series. */
export const PAST_LONGEST_CITED = "past the longest cited length";

const LIVE = process.env.NEXT_PUBLIC_SA_API ?? "";

const COPY_BY_ID = new Map<string, SeriesCopy>(SERIES_COPY.map((item) => [item.id, item]));

export function seriesCopy(seriesId: string): SeriesCopy | null {
  return COPY_BY_ID.get(seriesId) ?? null;
}

function finiteNumber(value: unknown, field: string): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  throw new Error(`Stability field ${field} is not a finite number.`);
}

function textOrNull(value: unknown, field: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value;
  throw new Error(`Stability field ${field} is not text.`);
}

function parseRow(value: unknown, index: number): StabilityRow {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`Stability row ${index} is not an object.`);
  }
  const row = value as Record<string, unknown>;
  if (typeof row.series_id !== "string" || row.series_id.trim() === "") {
    throw new Error(`Stability row ${index} is missing series_id.`);
  }
  if (typeof row.n_repeats !== "number" || !Number.isInteger(row.n_repeats)) {
    throw new Error(`Stability row ${index} is missing n_repeats.`);
  }
  if (typeof row.t_assay_C !== "number" || !Number.isFinite(row.t_assay_C)) {
    throw new Error(`Stability row ${index} is missing t_assay_C.`);
  }
  if (typeof row.thermal_state !== "string" || row.thermal_state.trim() === "") {
    throw new Error(`Stability row ${index} is missing thermal_state.`);
  }
  if (typeof row.calibrated !== "boolean") {
    throw new Error(`Stability row ${index} is missing calibrated.`);
  }
  const parsed: StabilityRow = {
    series_id: row.series_id,
    n_repeats: row.n_repeats,
    t_assay_C: row.t_assay_C,
    thermal_state: row.thermal_state,
    tm_C: finiteNumber(row.tm_C, `row ${index} tm_C`),
    tm_uncertainty_C: finiteNumber(
      "tm_uncertainty_C" in row ? row.tm_uncertainty_C : null,
      `row ${index} tm_uncertainty_C`,
    ),
    tm_interval_low: finiteNumber(row.tm_interval_low, `row ${index} tm_interval_low`),
    tm_interval_high: finiteNumber(row.tm_interval_high, `row ${index} tm_interval_high`),
    tm_band_label: textOrNull(
      "tm_band_label" in row ? row.tm_band_label : null,
      `row ${index} tm_band_label`,
    ),
    tm_fit_form: textOrNull(
      "tm_fit_form" in row ? row.tm_fit_form : null,
      `row ${index} tm_fit_form`,
    ),
    delta_g: finiteNumber(row.delta_g, `row ${index} delta_g`),
    delta_g_units: textOrNull(row.delta_g_units, `row ${index} delta_g_units`),
    delta_g_uncertainty: finiteNumber(
      row.delta_g_uncertainty,
      `row ${index} delta_g_uncertainty`,
    ),
    delta_g_band_95_low: finiteNumber(
      "delta_g_band_95_low" in row ? row.delta_g_band_95_low : null,
      `row ${index} delta_g_band_95_low`,
    ),
    delta_g_band_95_high: finiteNumber(
      "delta_g_band_95_high" in row ? row.delta_g_band_95_high : null,
      `row ${index} delta_g_band_95_high`,
    ),
    delta_g_band_label: textOrNull(
      "delta_g_band_label" in row ? row.delta_g_band_label : null,
      `row ${index} delta_g_band_label`,
    ),
    delta_g_fit_form: textOrNull(
      "delta_g_fit_form" in row ? row.delta_g_fit_form : null,
      `row ${index} delta_g_fit_form`,
    ),
    comparison_uses_fit: row.comparison_uses_fit === true,
    length_note: textOrNull(
      "length_note" in row ? row.length_note : null,
      `row ${index} length_note`,
    ),
    past_longest_cited_length: row.past_longest_cited_length === true,
    calibrated: row.calibrated,
    thermal_reason: textOrNull(row.thermal_reason, `row ${index} thermal_reason`),
  };
  if ("paper_tm_C" in row) {
    parsed.paper_tm_C = finiteNumber(row.paper_tm_C, `row ${index} paper_tm_C`);
  }
  if ("paper_delta_g" in row) {
    parsed.paper_delta_g = finiteNumber(row.paper_delta_g, `row ${index} paper_delta_g`);
  }
  if ("paper_delta_g_units" in row) {
    parsed.paper_delta_g_units = textOrNull(
      row.paper_delta_g_units,
      `row ${index} paper_delta_g_units`,
    );
  }
  return parsed;
}

function parseParameter(value: unknown, index: number): FittedParameter {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`Fit parameter ${index} is not an object.`);
  }
  const row = value as Record<string, unknown>;
  if (typeof row.name !== "string" || row.name.trim() === "") {
    throw new Error(`Fit parameter ${index} is missing name.`);
  }
  if (typeof row.units !== "string") {
    throw new Error(`Fit parameter ${index} is missing units.`);
  }
  if (typeof row.identifiable !== "boolean") {
    throw new Error(`Fit parameter ${index} is missing identifiable.`);
  }
  const parameterValue = finiteNumber(row.value, `parameter ${index} value`);
  if (parameterValue === null) {
    throw new Error(`Fit parameter ${index} is missing value.`);
  }
  return {
    name: row.name,
    value: parameterValue,
    units: row.units,
    standard_error: finiteNumber(row.standard_error, `parameter ${index} standard_error`),
    identifiable: row.identifiable,
  };
}

function parseCurve(value: unknown, label: string): SeriesCurveFit {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} fit is not an object.`);
  }
  const row = value as Record<string, unknown>;
  if (typeof row.form !== "string" || typeof row.equation !== "string") {
    throw new Error(`${label} fit is missing form or equation.`);
  }
  if (typeof row.n_points !== "number" || !Number.isInteger(row.n_points)) {
    throw new Error(`${label} fit is missing n_points.`);
  }
  if (!Array.isArray(row.n_repeats) || !Array.isArray(row.parameters) || !Array.isArray(row.warnings)) {
    throw new Error(`${label} fit is missing points or parameters.`);
  }
  if (typeof row.units !== "string") {
    throw new Error(`${label} fit is missing units.`);
  }
  return {
    form: row.form,
    equation: row.equation,
    n_points: row.n_points,
    n_repeats: row.n_repeats.map((item, index) => {
      if (typeof item !== "number" || !Number.isInteger(item)) {
        throw new Error(`${label} fit n_repeats ${index} is not an integer.`);
      }
      return item;
    }),
    units: row.units,
    longest_cited_n:
      row.longest_cited_n === null
        ? null
        : (() => {
            const longest = finiteNumber(row.longest_cited_n, `${label} longest_cited_n`);
            if (longest === null || !Number.isInteger(longest)) {
              throw new Error(`${label} fit longest_cited_n is not an integer.`);
            }
            return longest;
          })(),
    warnings: row.warnings.map((item, index) => {
      if (typeof item !== "string") {
        throw new Error(`${label} fit warning ${index} is not text.`);
      }
      return item;
    }),
    parameters: row.parameters.map((item, index) => parseParameter(item, index)),
  };
}

function parseSeriesFits(value: unknown): SeriesFitBlock[] | undefined {
  if (value === undefined || value === null) return undefined;
  if (!Array.isArray(value)) {
    throw new Error("series_fits is not a list.");
  }
  return value.map((item, index) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) {
      throw new Error(`series_fits ${index} is not an object.`);
    }
    const row = item as Record<string, unknown>;
    if (typeof row.series_id !== "string" || row.series_id.trim() === "") {
      throw new Error(`series_fits ${index} is missing series_id.`);
    }
    return {
      series_id: row.series_id,
      tm: parseCurve(row.tm, `series_fits ${index} tm`),
      delta_g: parseCurve(row.delta_g, `series_fits ${index} delta_g`),
    };
  });
}

export function parseStabilityPanel(body: unknown): StabilityPanel {
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    throw new Error("Stability payload is not an object.");
  }
  const record = body as Record<string, unknown>;
  if (typeof record.calibrated !== "boolean") {
    throw new Error("Stability payload is missing calibrated.");
  }
  if (typeof record.t_assay_C !== "number" || !Number.isFinite(record.t_assay_C)) {
    throw new Error("Stability payload is missing t_assay_C.");
  }
  if (!Array.isArray(record.rows)) {
    throw new Error("Stability payload is missing rows.");
  }
  const parsed = record.rows.map((row, index) => parseRow(row, index));
  const wantedLengths = new Set<number>(TEAM_LENGTHS);
  const canonical = parsed.filter(
    (row) =>
      row.series_id === CANONICAL_SERIES_ID && wantedLengths.has(row.n_repeats),
  );
  const rows =
    canonical.length > 0
      ? canonical
      : parsed.filter((row) => wantedLengths.has(row.n_repeats));
  const fits = parseSeriesFits(record.series_fits);
  const canonicalFits = fits?.filter((fit) => fit.series_id === CANONICAL_SERIES_ID);
  return {
    calibrated: record.calibrated,
    t_assay_C: record.t_assay_C,
    rows,
    series_fits:
      canonicalFits && canonicalFits.length > 0 ? canonicalFits : fits,
    literature_series_id:
      typeof record.literature_series_id === "string"
        ? record.literature_series_id
        : undefined,
    doi: typeof record.doi === "string" ? record.doi : undefined,
    method: typeof record.method === "string" ? record.method : undefined,
    construct_family:
      typeof record.construct_family === "string" ? record.construct_family : undefined,
    comparison: typeof record.comparison === "string" ? record.comparison : undefined,
    equation_saturating:
      typeof record.equation_saturating === "string" ? record.equation_saturating : undefined,
    equation_line: typeof record.equation_line === "string" ? record.equation_line : undefined,
    note: typeof record.note === "string" ? record.note : undefined,
  };
}

async function fetchLivePanel(path: string): Promise<StabilityPanel> {
  const response = await fetch(`${LIVE}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API ${response.status}`);
  }
  const text = await response.text();
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) {
    throw new Error("Stability API returned a page instead of model data.");
  }
  const body: unknown = JSON.parse(trimmed);
  return { ...parseStabilityPanel(body), source: "live" };
}

export async function fetchStabilityPanel(): Promise<StabilityPanel> {
  let lastError: unknown = null;
  try {
    return await fetchLivePanel("/api/stability/confirm?t_assay_C=37");
  } catch (err: unknown) {
    lastError = err;
  }
  try {
    const snapshot = await fetch("/stability-snapshot.json", { cache: "no-store" });
    if (!snapshot.ok) {
      throw new Error(
        "Stability API is unreachable and no wiki snapshot is available.",
      );
    }
    const body: unknown = await snapshot.json();
    return { ...parseStabilityPanel(body), source: "snapshot" };
  } catch (err: unknown) {
    const reason = err instanceof Error ? err.message : String(lastError ?? err);
    throw new Error(reason);
  }
}

/**
 * Melting temperature to show. A finite tm_C is the number, whether it
 * came from the length fit or from a lookup row that has a table cell.
 * A missing temperature stays missing. It is not replaced with 0.
 */
export function citedTm(row: StabilityRow | null): number | null {
  if (!row) return null;
  if (typeof row.tm_C !== "number" || !Number.isFinite(row.tm_C)) return null;
  return row.tm_C;
}

/**
 * Printed Tm uncertainty in °C.
 * Null, missing, or non-finite means the table printed none.
 * The gate envelope is not consulted: a missing sigma is not zero.
 */
export function printedTmUncertainty(row: StabilityRow | null): number | null {
  if (citedTm(row) === null || !row) return null;
  const sigma = row.tm_uncertainty_C;
  if (typeof sigma !== "number" || !Number.isFinite(sigma)) return null;
  return sigma;
}

/**
 * Whisker for a printed Tm uncertainty.
 * Built from Tm ± the printed sigma. A null sigma returns null, even
 * when the payload still carries a zero-width gate envelope.
 */
export function citedInterval(
  row: StabilityRow | null,
): { low: number; high: number } | null {
  const tm = citedTm(row);
  const sigma = printedTmUncertainty(row);
  if (tm === null || sigma === null) return null;
  const low = tm - sigma;
  const high = tm + sigma;
  if (!Number.isFinite(low) || !Number.isFinite(high) || !(high > low)) return null;
  return { low, high };
}

export function formatMeasure(value: number): string {
  if (!Number.isFinite(value)) {
    throw new Error("formatMeasure requires a finite number.");
  }
  const rounded = value.toFixed(4);
  if (!rounded.includes(".")) return rounded;
  return rounded.replace(/0+$/, "").replace(/\.$/, "");
}

export function tmLabel(row: StabilityRow | null): string {
  const tm = citedTm(row);
  if (tm === null) return MISSING_TM_LABEL;
  return `${formatMeasure(tm)} °C`;
}

/** Printed Tm uncertainty, or the word omitted. Never a zero-width interval. */
export function uncertaintyLabel(row: StabilityRow | null): string {
  const sigma = printedTmUncertainty(row);
  if (sigma === null) return OMITTED_UNCERTAINTY_LABEL;
  return `± ${formatMeasure(sigma)} °C`;
}

export function intervalLabel(row: StabilityRow | null): string {
  return uncertaintyLabel(row);
}

export function deltaGLabel(row: StabilityRow | null): string {
  if (!row || typeof row.delta_g !== "number" || !Number.isFinite(row.delta_g)) {
    return MISSING_DELTA_G_LABEL;
  }
  const units = row.delta_g_units ?? "";
  const value = formatMeasure(row.delta_g);
  if (
    typeof row.delta_g_uncertainty === "number" &&
    Number.isFinite(row.delta_g_uncertainty)
  ) {
    return `${value} ± ${formatMeasure(row.delta_g_uncertainty)} ${units}`.trim();
  }
  return `${value} ${units}`.trim();
}

export type LengthSlot = {
  nRepeats: number;
  rows: StabilityRow[];
};

export type SeriesBlock = {
  seriesId: string;
  slots: LengthSlot[];
};

/** Team lengths as slots for the canonical confirmation model. */
export function teamLengthSlots(rows: StabilityRow[]): LengthSlot[] {
  return TEAM_LENGTHS.map((nRepeats) => ({
    nRepeats,
    rows: rows.filter((row) => row.n_repeats === nRepeats),
  }));
}

/** Named series blocks; retained for tests and legacy snapshots. */
export function seriesBlocks(rows: StabilityRow[]): SeriesBlock[] {
  const known = new Set<string>(SERIES_IDS);
  const extras = [...new Set(rows.map((row) => row.series_id))]
    .filter((seriesId) => !known.has(seriesId))
    .sort();
  const order = [...SERIES_IDS, ...extras];
  return order.map((seriesId) => ({
    seriesId,
    slots: TEAM_LENGTHS.map((nRepeats) => ({
      nRepeats,
      rows: rows.filter(
        (row) => row.series_id === seriesId && row.n_repeats === nRepeats,
      ),
    })),
  }));
}

export function panelHasTeamRows(rows: StabilityRow[]): boolean {
  return rows.some((row) =>
    (TEAM_LENGTHS as readonly number[]).includes(row.n_repeats),
  );
}

export type TmAxis = {
  low: number;
  high: number;
  step: number;
  ticks: number[];
};

/** Axis around cited temperatures and the comparison temperature. Zero is not a tick unless the data reach it. */
export function tmAxis(samples: number[], assayC: number): TmAxis {
  const finite = samples.filter((value) => Number.isFinite(value));
  const anchor = finite.length > 0 ? finite : [assayC];
  let min = Math.min(...anchor, assayC);
  let max = Math.max(...anchor, assayC);
  const span = Math.max(max - min, 8);
  min -= span * 0.2;
  max += span * 0.25;
  const rough = (max - min) / 4;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const fraction = rough / magnitude;
  const nice = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10;
  const step = nice * magnitude;
  const low = Math.floor(min / step) * step;
  const high = Math.ceil((max - 1e-9) / step) * step;
  const ticks: number[] = [];
  const count = Math.round((high - low) / step);
  for (let index = 0; index <= count; index += 1) {
    ticks.push(Math.round((low + index * step) * 1000) / 1000);
  }
  return { low, high: Math.max(high, low + step), step, ticks };
}
