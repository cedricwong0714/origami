import type { Metadata } from "next";
import { SsdkBoard } from "@/components/ssdk-board";

export const metadata: Metadata = {
  title: "One length · ORIGAMI",
  description:
    "Screw, melting temperature, docking distance, and optional binding for one repeat count.",
};

export default function SsdkPage() {
  return <SsdkBoard />;
}
