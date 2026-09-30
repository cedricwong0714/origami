/**
 * Thermal lookup for the stability confirmation screen.
 *
 * The chassis keeps four literature series separate. This module does not
 * average them, does not fit Tm(n), and does not fill a missing melting
 * temperature with 0.
 *
 * Citation strings below are copied from
 * data/stability/ctpr_thermal_literature.json. Buffer, pH, method, and
 * construct family are the series keys in origami/stability/series.py.
 * 37 °C is the screen's comparison temperature: an E. coli operating
 * assumption, not a DSC setpoint from those papers.
 */

export const TEAM_LENGTHS = [3, 8, 14] as const;

export const SERIES_IDS = [
  "phillips2012_ctpra_dsc",
  "cortajarena2011_ctpra_dsc",
  "phillips2012_ctpra_cd",
  "phillips2012_ctpr_dsc",
] as const;

export type KnownSeriesId = (typeof SERIES_IDS)[number];

export type StabilityRow = {
  series_id: string;
  n_repeats: number;
  t_assay_C: number;
  thermal_state: string;
  tm_C: number | null;
  tm_interval_low: number | null;
  tm_interval_high: number | null;
  delta_g: number | null;
  delta_g_units: string | null;
  delta_g_uncertainty: number | null;
  calibrated: boolean;
  thermal_reason: string | null;
};

export type StabilityPanel = {
  calibrated: boolean;
  t_assay_C: number;
  rows: StabilityRow[];
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
    detail: "Default series. CTPRa, DSC, 50 mM phosphate, pH 7.0, Table I.",
  },
  {
    id: "cortajarena2011_ctpra_dsc",
    title: "Cortajarena and Regan 2011, CTPRa, DSC",
    isDefault: false,
    citation:
      "Cortajarena AL, Regan L. Calorimetric study of a series of designed repeat proteins: modular structure and modular folding. Protein Sci. 2011;20(2):336-340.",
    doi: "10.1002/pro.564",
    detail: "CTPRa, DSC, 150 mM NaCl, 50 mM phosphate, pH 6.8, Table I.",
  },
  {
    id: "phillips2012_ctpra_cd",
    title: "Phillips et al. 2012, CTPRa, CD",
    isDefault: false,
    citation:
      "Phillips JJ, Javadi Y, Millership C, Main ERG. Modulation of the multistate folding of designed TPR proteins through intrinsic and extrinsic factors. Protein Sci. 2012;21(3):327-338.",
    doi: "10.1002/pro.2018",
    detail: "CTPRa, CD, 50 mM phosphate, pH 7.0, Table I.",
  },
  {
    id: "phillips2012_ctpr_dsc",
    title: "Phillips et al. 2012, CTPR, DSC",
    isDefault: false,
    citation:
      "Phillips JJ, Javadi Y, Millership C, Main ERG. Modulation of the multistate folding of designed TPR proteins through intrinsic and extrinsic factors. Protein Sci. 2012;21(3):327-338.",
    doi: "10.1002/pro.2018",
    detail: "CTPR, DSC, 50 mM phosphate, pH 7.0, Table I.",
  },
];

/** Word shown wherever a melting temperature is missing. Never a zero. */
export const MISSING_TM_LABEL = "extrapolated";

/** Printed ΔG column when that table has no value at this length. */
export const MISSING_DELTA_G_LABEL = "not printed";

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
  return {
    series_id: row.series_id,
    n_repeats: row.n_repeats,
    t_assay_C: row.t_assay_C,
    thermal_state: row.thermal_state,
    tm_C: finiteNumber(row.tm_C, `row ${index} tm_C`),
    tm_interval_low: finiteNumber(row.tm_interval_low, `row ${index} tm_interval_low`),
    tm_interval_high: finiteNumber(row.tm_interval_high, `row ${index} tm_interval_high`),
    delta_g: finiteNumber(row.delta_g, `row ${index} delta_g`),
    delta_g_units: textOrNull(row.delta_g_units, `row ${index} delta_g_units`),
    delta_g_uncertainty: finiteNumber(
      row.delta_g_uncertainty,
      `row ${index} delta_g_uncertainty`,
    ),
    calibrated: row.calibrated,
    thermal_reason: textOrNull(row.thermal_reason, `row ${index} thermal_reason`),
  };
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
  const rows = record.rows.map((row, index) => parseRow(row, index));
  const wanted = new Set<number>(TEAM_LENGTHS);
  return {
    calibrated: record.calibrated,
    t_assay_C: record.t_assay_C,
    rows: rows.filter((row) => wanted.has(row.n_repeats)),
    note: typeof record.note === "string" ? record.note : undefined,
  };
}

export async function fetchStabilityPanel(): Promise<StabilityPanel> {
  try {
    const response = await fetch(`${LIVE}/api/stability/panel?t_assay_C=37`, {
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`API ${response.status}`);
    }
    const body: unknown = await response.json();
    return { ...parseStabilityPanel(body), source: "live" };
  } catch {
    const snapshot = await fetch("/stability-snapshot.json", { cache: "no-store" });
    if (!snapshot.ok) {
      throw new Error(
        "Stability API is unreachable and no wiki snapshot is available.",
      );
    }
    const body: unknown = await snapshot.json();
    return { ...parseStabilityPanel(body), source: "snapshot" };
  }
}

/**
 * Cited Tm that may be drawn. Extrapolated and omitted rows have no point.
 * A numeric 0 is not plotted: a missing Tm is the word "extrapolated".
 */
export function citedTm(row: StabilityRow | null): number | null {
  if (!row) return null;
  if (row.thermal_state === "extrapolated" || row.thermal_state === "omitted") {
    return null;
  }
  if (row.thermal_state !== "pass" && row.thermal_state !== "fail") return null;
  if (typeof row.tm_C !== "number" || !Number.isFinite(row.tm_C)) return null;
  if (row.tm_C === 0) return null;
  return row.tm_C;
}

export function citedInterval(
  row: StabilityRow | null,
): { low: number; high: number } | null {
  if (citedTm(row) === null || !row) return null;
  const low = row.tm_interval_low;
  const high = row.tm_interval_high;
  if (typeof low !== "number" || typeof high !== "number") return null;
  if (!Number.isFinite(low) || !Number.isFinite(high) || low > high) return null;
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

export function intervalLabel(row: StabilityRow | null): string {
  const interval = citedInterval(row);
  if (!interval) return "—";
  return `${formatMeasure(interval.low)}–${formatMeasure(interval.high)} °C`;
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

/** Four named series, in citation order, plus any unexpected id kept alone. */
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
