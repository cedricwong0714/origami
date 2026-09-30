import type { Metadata } from "next";
import { StabilityBoard } from "@/components/stability-board";

export const metadata: Metadata = {
  title: "Stability confirmation · ORIGAMI",
  description:
    "Confirm cited melting temperatures at n = 3, 8, and 14. Pass means the cited melt is above 37 °C. A length with no paper row stays extrapolated. calibrated stays false.",
};

export default function StabilityPage() {
  return <StabilityBoard />;
}
