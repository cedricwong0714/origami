export type PlateObservation = {
  n_repeats: number;
  y: number;
  sigma: number | null;
  source: string;
  construct: string;
  batch: string;
  n_wells: number;
  blank_mean_rlu: number;
  units: string;
};

export type PlateImport = {
  observations: PlateObservation[];
  normalization_method: string;
  input_sha256: string | null;
  source: string;
  calibrated: false;
};

export type AblationMetrics = {
  rmse: number;
  mae: number;
  spearman: number | null;
  coverage_95: number | null;
  mean_half_width: number | null;
};

export type Ablation = {
  n_rows: number;
  groups: string[];
  xgb_active_folds: number;
  results: Record<string, AblationMetrics>;
  xgb_gain_rmse: number | null;
  xgb_justified: boolean;
  calibrated: false;
  note: string;
};

async function post<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      typeof payload.detail === "string" ? payload.detail : `Request failed (${response.status})`,
    );
  }
  return payload as T;
}

export const importPlate = (csv_text: string, source: string) =>
  post<PlateImport>("/api/lab/plate", { csv_text, source });

export const runAblation = (body: Record<string, unknown>) =>
  post<Ablation>("/api/lab/ablation", body);
