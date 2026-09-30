import type { Metadata } from "next";
import { StabilityBoard } from "@/components/stability-board";

export const metadata: Metadata = {
  title: "Thermal confirmation · ORIGAMI",
  description:
    "Cited CTPR melting temperatures for n = 3, 8, and 14. Four literature series stay separate. calibrated stays false.",
};

export default function StabilityPage() {
  return <StabilityBoard />;
}
