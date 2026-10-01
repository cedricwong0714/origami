/**
 * Stage-1 scaffold kinetics. Literature priors emulate a fusion path.
 * Lab overrides stay empty until assay data.
 */

export type RateSlot = {
  name: string;
  status: "literature" | "vacant" | "user_supplied";
  origin: "literature_prior" | "lab_measurement";
  value: number | null;
  lab_value: number | null;
  units: string;
  source: string | null;
  system: string | null;
  method: string | null;
  notes: string;
  sigma: number | null;
};

export type KineticsSchema = {
  workflow_id: string;
  model_name: string;
  model_version: string;
  calibrated: boolean;
  confidence_tier: string;
  human_review_required: boolean;
  rate_slots: RateSlot[];
  note: string;
};

export type RecruitmentSim = {
  mode: "recruitment_steady";
  calibrated: boolean;
  confidence_tier: string;
  recruitment: {
    theta_ss: number;
    theta_95_lower: number;
    theta_95_upper: number;
    kd_M: number;
    c_free_M: number;
    kon_per_M_s: number | null;
    warnings: string[];
  };
  derived: { k_off_per_s: number | null };
};

export type CovalentSim = {
  mode: "covalent_timecourse";
  calibrated: boolean;
  confidence_tier: string;
  series: {
    tag_M: number[];
    catcher_M: number[];
    complex_M: number[];
    adduct_M: number[];
  };
  time_s: number[];
  rates_used: {
    spy_k_on_per_M_s: number;
    spy_k_rev_per_s: number | null;
    spy_k_bond_per_s: number | null;
    path: string;
  };
};

export async function fetchKineticsSchema(): Promise<KineticsSchema> {
  const res = await fetch("/api/kinetics/schema", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`schema ${res.status}`);
  }
  return res.json() as Promise<KineticsSchema>;
}

export async function simulateRecruitment(cFreeM: number): Promise<RecruitmentSim> {
  const res = await fetch("/api/kinetics/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "recruitment_steady", c_free_M: cFreeM }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `simulate ${res.status}`);
  }
  return res.json() as Promise<RecruitmentSim>;
}

export type NanoBitSim = {
  mode: "nanobit_complementation";
  calibrated: boolean;
  confidence_tier: string;
  equilibrium_complex_M: number;
  equilibrium_uses: string;
  warnings: string[];
  rates_used: {
    nanobit_k_on_per_M_s: number;
    nanobit_k_off_per_s: number;
    printed_kd_M: number;
    kinetic_kd_M: number;
  };
  series: { complex_M: number[] };
};

export async function simulateNanoBit(lg0M: number, sm0M: number): Promise<NanoBitSim> {
  const res = await fetch("/api/kinetics/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mode: "nanobit_complementation",
      lg0_M: lg0M,
      sm0_M: sm0M,
      num_points: 40,
    }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `simulate ${res.status}`);
  }
  return res.json() as Promise<NanoBitSim>;
}

export async function simulateCovalent(body: {
  tag0_M: number;
  catcher0_M: number;
  spy_k_on_per_M_s?: number;
  spy_k_rev_per_s?: number;
  spy_k_bond_per_s?: number;
}): Promise<CovalentSim> {
  const payload: Record<string, number | string> = {
    mode: "covalent_timecourse",
    tag0_M: body.tag0_M,
    catcher0_M: body.catcher0_M,
    num_points: 40,
  };
  if (body.spy_k_on_per_M_s !== undefined) {
    payload.spy_k_on_per_M_s = body.spy_k_on_per_M_s;
  }
  if (body.spy_k_rev_per_s !== undefined && body.spy_k_bond_per_s !== undefined) {
    payload.spy_k_rev_per_s = body.spy_k_rev_per_s;
    payload.spy_k_bond_per_s = body.spy_k_bond_per_s;
  }
  const res = await fetch("/api/kinetics/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `simulate ${res.status}`);
  }
  return res.json() as Promise<CovalentSim>;
}
