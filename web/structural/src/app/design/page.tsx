import type { Metadata } from "next";
import { DesignBoard } from "@/components/design-board";

export const metadata: Metadata = {
  title: "Choose a length · ORIGAMI",
  description:
    "Score every scaffold length from 3 to 24 for folding, end-to-end binding, the light reporter, the Spy lock, and overlap.",
};

export default function DesignPage() {
  return <DesignBoard />;
}
