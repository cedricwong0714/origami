import type { Metadata } from "next";
import { StabilityBoard } from "@/components/stability-board";

export const metadata: Metadata = {
  title: "Stability confirmation · ORIGAMI",
  description:
    "Melting temperature and unfolding energy at n = 3, 8, and 14 from the Phillips 2012 length fit. Pass at 37 °C means that calculated melt is above 37 °C.",
};

export default function StabilityPage() {
  return <StabilityBoard />;
}
