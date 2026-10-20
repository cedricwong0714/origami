export type Junction = {
  i: number;
  j: number;
  delta_i: number;
  phase_deg: number;
  facing_cosine: number;
  chord_A: number;
  axial_A: number;
  chord_sigma_A: number;
  chord_95_low_A: number;
  chord_95_high_A: number;
};

export type RepeatSite = {
  repeat_index: number;
  phase_deg: number;
  phase_mod_360_deg: number;
  facing_cosine_vs_repeat_0: number;
  x_A: number;
  y_A: number;
  z_A: number;
  position_rms_A: number;
  m13_graft: boolean;
};

export type GraftStation = {
  repeat_1based: number;
  repeat_index: number;
  counting: string;
  to_n_end: Junction;
  to_c_end: Junction;
};

export type ConstructRow = {
  n_repeats: number;
  m13_graft: GraftStation | null;
  axial_span_A: number;
  contour_nm: number;
  wlc_end_to_end_rms_nm: number;
  rigid_screw: boolean;
  ca_count: number;
  ca_z_min_A: number;
  ca_z_max_A: number;
  ca_radial_min_A: number;
  ca_radial_mean_A: number;
  ca_radial_max_A: number;
  end_junction: Junction;
  repeats: RepeatSite[];
  pairs: Junction[];
};

export type HelixScene = {
  n_repeats: number;
  sites: { index: number; x_A: number; y_A: number; z_A: number; m13_graft?: boolean }[];
  ca_stride: number;
  ca_A: number[][];
};

export type Reading = {
  n_repeats: number;
  reach: {
    linker_rms_A: number;
    comparison_window_A: number;
    repeats_near_n_end: number[];
    repeats_near_c_end: number[];
    repeats_near_both_ends: number[];
    end_bow_A: number;
    end_bow_fraction_of_chord: number;
  };
  reading: string[];
};

export type PredictResponse = {
  calibrated: boolean;
  payloads: boolean;
  n_to_c: string[];
  measured_block: string;
  constructs: ConstructRow[];
  screw: Record<string, number | boolean | string>;
  deposited: Record<string, unknown>;
  deposited_steps: Record<string, unknown>[];
  library_rows: Record<string, unknown>[];
  scenes: HelixScene[];
  readings: Reading[];
  notes: string[];
  source?: "live" | "snapshot";
};

const LIVE = process.env.NEXT_PUBLIC_SA_API ?? "";

export async function fetchPrediction(nList: number[]): Promise<PredictResponse> {
  const query = nList.join(",");
  try {
    const response = await fetch(`${LIVE}/api/sa/predict?n=${query}`, {
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`API ${response.status}`);
    }
    const text = await response.text();
    const trimmed = text.trim();
    if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) {
      throw new Error("Structural API returned a page instead of model data.");
    }
    const body = JSON.parse(trimmed) as PredictResponse;
    return { ...body, source: "live" };
  } catch {
    const snapshot = await fetch("/sa-snapshot.json");
    if (!snapshot.ok) {
      throw new Error(
        "Structural API is unreachable and no wiki snapshot is available."
      );
    }
    const body = (await snapshot.json()) as PredictResponse;
    const wanted = new Set(nList);
    return {
      ...body,
      constructs: body.constructs.filter((row) => wanted.has(row.n_repeats)),
      scenes: body.scenes.filter((row) => wanted.has(row.n_repeats)),
      readings: body.readings.filter((row) => wanted.has(row.n_repeats)),
      source: "snapshot",
    };
  }
}

export function fmt(value: number, digits = 2): string {
  return Number(value).toFixed(digits);
}
