import type { Metadata } from "next";
import { ModelIndex } from "@/components/model-index";

export const metadata: Metadata = {
  title: "Choose a model · ORIGAMI",
  description: "Every ORIGAMI calculation, grouped so you can open the one you need.",
};

export default function ModelsPage() {
  return <ModelIndex />;
}
