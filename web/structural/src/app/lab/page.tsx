import type { Metadata } from "next";
import { LabBoard } from "@/components/lab-board";

export const metadata: Metadata = {
  title: "Lab numbers · ORIGAMI",
  description:
    "Paste measured concentration, calcium curve, Spy lock, and four-tube bridge numbers. Empty boxes stay empty.",
};

export default function LabPage() {
  return <LabBoard />;
}
