import type { Metadata } from "next";
import { GuideBoard } from "@/components/guide-board";

export const metadata: Metadata = {
  title: "Data dependencies · ORIGAMI",
  description: "What needs lab data vs literature vs team dry-lab inputs.",
};

export default function GuidePage() {
  return <GuideBoard />;
}
