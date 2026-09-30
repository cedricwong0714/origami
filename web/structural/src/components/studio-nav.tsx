"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Run" },
  { href: "/present", label: "Present" },
  { href: "/stability", label: "Stability" },
  { href: "/stability/calculator", label: "Estimate ΔG" },
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
