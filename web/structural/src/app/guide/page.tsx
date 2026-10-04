import type { Metadata } from "next";
import { GuideBoard } from "@/components/guide-board";

export const metadata: Metadata = {
  title: "What you can run · ORIGAMI",
  description: "Which calculations run with no plate, and which numbers still need a measurement.",
};

export default function GuidePage() {
  return <GuideBoard />;
}
