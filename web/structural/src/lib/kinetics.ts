/**
 * Stage-1 scaffold kinetics (vacant SpyTag rates until lab ingestion).
 */

export type RateSlot = {
  name: string;
  status: "literature" | "vacant" | "user_supplied";
  value: number | null;
  units: string;
  source: string | null;
  system: string | null;
  method: string | null;
  notes: string;
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
