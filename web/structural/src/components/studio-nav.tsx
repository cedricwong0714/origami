"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Screw" },
  { href: "/present", label: "Compare 3, 8, 14" },
  { href: "/stability", label: "Melting temperature" },
  { href: "/stability/calculator", label: "ΔG vs temperature" },
  { href: "/kinetics", label: "Binding" },
  { href: "/ssdk", label: "One length" },
  { href: "/lab", label: "Lab numbers" },
  { href: "/intake", label: "Plate file" },
  { href: "/learn", label: "Next length" },
  { href: "/wizard", label: "Step by step" },
  { href: "/guide", label: "What you can run" },
];

export function StudioNav() {
  const path = usePathname();
  return (
    <nav className="mb-6 flex flex-wrap gap-2" aria-label="Studio screens">
      {LINKS.map((link) => {
        const active = path === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={
              active
                ? "rounded-full bg-[#242220] px-4 py-1.5 text-sm text-white"
                : "rounded-full border border-[#E3D9CC] bg-white px-4 py-1.5 text-sm text-[#5C564E]"
            }
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
