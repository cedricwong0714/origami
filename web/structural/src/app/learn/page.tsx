import type { Metadata } from "next";
import { LearnBoard } from "@/components/learn-board";

export const metadata: Metadata = {
  title: "Surrogate active learning · ORIGAMI",
  description:
    "Residual Gaussian process on surrogate readouts across CTPR lengths. calibrated = false.",
};

export default function LearnPage() {
  return <LearnBoard />;
}
