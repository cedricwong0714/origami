"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/theme-toggle";

const SECTIONS = [
  {
    label: "All models",
    tabs: [{ href: "/models", label: "Choose a model" }],
  },
  {
    label: "Structural analysis",
    tabs: [
      { href: "/scaffold", label: "3D scaffold" },
      { href: "/present", label: "Compare lengths" },
      { href: "/design", label: "Choose a length" },
      { href: "/learn", label: "Next length" },
    ],
  },
  {
    label: "Stability confirmation",
    tabs: [
      { href: "/stability", label: "Stay folded?" },
      { href: "/stability/calculator", label: "Energy vs temperature" },
    ],
  },
  {
    label: "Docking verification",
    tabs: [
      { href: "/docking", label: "Will it bind?" },
      { href: "/docking/geometry", label: "Distance and clash" },
    ],
  },
  {
    label: "Kinetic modelling",
    tabs: [
      { href: "/kinetics", label: "How much is bound?" },
      { href: "/kinetics/spy", label: "Spy lock" },
      { href: "/kinetics/nanobit", label: "Light reporter" },
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
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link href="/models" className="inline-flex items-center" aria-label="Choose a model">
          <Image
            src="/origami-wordmark.png"
            alt="ORIGAMI"
            width={440}
            height={128}
            className="h-10 w-auto sm:h-12"
            priority
          />
        </Link>
        <ThemeToggle />
      </div>
      <nav className="flex flex-wrap gap-2" aria-label="SSDK">
        {SECTIONS.map((section) => {
          const on = section === active;
          return (
            <Link
              key={section.label}
              href={section.tabs[0].href}
              className={
                on
                  ? "rounded-full bg-studio-nav-active px-4 py-1.5 text-sm text-studio-nav-active-text"
                  : "rounded-full border border-studio-border bg-studio-card px-4 py-1.5 text-sm text-studio-muted"
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
                  ? "rounded-full border border-studio-accent bg-studio-accent-soft px-3 py-1 text-sm text-studio-accent"
                  : "rounded-full px-3 py-1 text-sm text-studio-muted underline decoration-studio-border underline-offset-4"
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
