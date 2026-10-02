"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Structural run" },
  { href: "/present", label: "Present data" },
  { href: "/stability", label: "Stability check" },
  { href: "/stability/calculator", label: "Estimate ΔG" },
  { href: "/kinetics", label: "Kinetics" },
  { href: "/ssdk", label: "SSDK" },
  { href: "/lab", label: "Lab chassis" },
  { href: "/intake", label: "Data intake" },
  { href: "/learn", label: "Active learning" },
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
