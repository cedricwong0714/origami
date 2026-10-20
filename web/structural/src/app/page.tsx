import type { Metadata } from "next";
import { EnterScreen } from "@/components/enter-screen";

export const metadata: Metadata = {
  title: "ORIGAMI",
  description: "Enter the ORIGAMI studio.",
};

export default function Home() {
  return <EnterScreen />;
}
