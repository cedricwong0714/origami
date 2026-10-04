"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const SECTIONS = [
  {
    label: "Structural analysis",
    tabs: [
      { href: "/", label: "Screw" },
      { href: "/present", label: "Compare lengths" },
    ],
  },
  {
    label: "Stability confirmation",
    tabs: [
      { href: "/stability", label: "Melting temperature" },
      { href: "/stability/calculator", label: "ΔG vs temperature" },
    ],
  },
  {
    label: "Docking verification",
    tabs: [
      { href: "/docking", label: "Affinity check" },
      { href: "/docking/geometry", label: "Distance and clash" },
    ],
  },
  {
    label: "Kinetic modelling",
    tabs: [
      { href: "/kinetics", label: "Bound fraction" },
      { href: "/kinetics/spy", label: "SpyCatcher–SpyTag" },
      { href: "/kinetics/nanobit", label: "LgBiT–SmBiT" },
    ],
  },
];

function sectionFor(path: string) {
  return (
    SECTIONS.find((section) => section.tabs.some((tab) => tab.href === path)) ??
    SECTIONS[0]
  );
}

export function StudioNav() {
  const path = usePathname();
  const active = sectionFor(path);
  return (
    <div className="mb-6 space-y-3">
      <nav className="flex flex-wrap gap-2" aria-label="SSDK">
        {SECTIONS.map((section) => {
          const on = section === active;
          return (
            <Link
              key={section.label}
              href={section.tabs[0].href}
              className={
                on
                  ? "rounded-full bg-[#242220] px-4 py-1.5 text-sm text-white"
                  : "rounded-full border border-[#E3D9CC] bg-white px-4 py-1.5 text-sm text-[#5C564E]"
              }
            >
              {section.label}
            </Link>
          );
        })}
      </nav>
      <nav className="flex flex-wrap gap-2" aria-label={active.label}>
        {active.tabs.map((tab) => {
          const on = path === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={
                on
                  ? "rounded-full border border-[#C45C12] bg-[#FFF7EF] px-3 py-1 text-sm text-[#C45C12]"
                  : "rounded-full px-3 py-1 text-sm text-[#5C564E] underline decoration-[#E3D9CC] underline-offset-4"
              }
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
