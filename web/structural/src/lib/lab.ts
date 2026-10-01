export type LabSlot = {
  name: string;
  units: string;
  section: string;
  description: string;
  origin: string;
  value: null;
  sigma: null;
};

export type LabSchema = {
  calibrated: false;
  confidence_tier: string;
  slots: LabSlot[];
  not_collected: string[];
  sections: Record<string, string>;
  residual_gp: { fitted: boolean; reason: string };
};

export type Ratio = {
  value: number;
  sigma: number | null;
  interval_95_lower: number | null;
  interval_95_upper: number | null;
};

export type SectionResult = {
  computable: boolean;
  calibrated?: boolean;
  missing?: string[];
  warnings?: string[];
  model_name?: string;
  equation?: string;
  [key: string]: unknown;
};

export type LabRun = {
  calibrated: false;
  confidence_tier: string;
  prep: SectionResult & {
    structure_context: {
      n_repeats: number;
      contour_nm: number;
      rigid_screw: boolean;
      calibrated: boolean;
      source: string;
    } | null;
    updates_screw: boolean;
  };
  assay_window: {
    standard_curve: SectionResult;
    furimazine: SectionResult;
    cv: SectionResult;
    linear_range: SectionResult;
  };
  calcium: {
    dose_response: SectionResult;
    specificity: SectionResult;
    temperature: SectionResult;
    replaces_cam_m13_kd: boolean;
  };
  lock: SectionResult;
  bridging: SectionResult & {
    signal_over_background?: Ratio;
    competition_over_bridge?: Ratio;
    hook_over_bridge?: Ratio;
    pattern_holds?: boolean;
  };
  residual_gp: { fitted: boolean; n_rows: number; reason: string };
};

export async function fetchLabSchema(): Promise<LabSchema> {
  const response = await fetch("/api/lab/schema");
  if (!response.ok) {
    throw new Error(`Schema request failed (${response.status}).`);
  }
  return response.json() as Promise<LabSchema>;
}

export async function runLab(body: Record<string, unknown>): Promise<LabRun> {
  const response = await fetch("/api/lab/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = `Run failed (${response.status}).`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) detail = payload.detail;
    } catch {
      /* keep the status line */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<LabRun>;
}
