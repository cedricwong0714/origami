import type { Metadata } from "next";
import { StabilityBoard } from "@/components/stability-board";

export const metadata: Metadata = {
  title: "Stability confirmation · ORIGAMI",
  description:
    "Calculated melting temperature and unfolding ΔG at n = 3, 8, and 14. The comparison at 37 °C uses the fit. calibrated stays false.",
};

export default function StabilityPage() {
  return <StabilityBoard />;
}
