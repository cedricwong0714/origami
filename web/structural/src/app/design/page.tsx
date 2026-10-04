import type { Metadata } from "next";
import { DesignBoard } from "@/components/design-board";

export const metadata: Metadata = {
  title: "Choose a length · ORIGAMI",
  description:
    "Score every scaffold length from 3 to 24 for melt, association, LgBiT–SmBiT occupancy, SpyCatcher–SpyTag half-life, and clash.",
};

export default function DesignPage() {
  return <DesignBoard />;
}
