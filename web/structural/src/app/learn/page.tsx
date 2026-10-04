import type { Metadata } from "next";
import { LearnBoard } from "@/components/learn-board";

export const metadata: Metadata = {
  title: "Next length · ORIGAMI",
  description:
    "Suggest the next repeat count from the docking score, or from luminescence readings you type.",
};

export default function LearnPage() {
  return <LearnBoard />;
}
