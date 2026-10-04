"use client";

import { Moon, Sun } from "lucide-react";
import { useStudioTheme } from "@/components/theme-provider";

/** Switch between light studio and #242220 dark studio. */
export function ThemeToggle() {
  const { theme, toggleTheme, ready } = useStudioTheme();
  const dark = theme === "dark";
  return (
    <button
      type="button"
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      aria-pressed={dark}
      disabled={!ready}
      onClick={toggleTheme}
      className="inline-flex items-center gap-2 rounded-full border border-studio-border bg-studio-card px-3 py-1.5 text-sm text-studio-muted transition hover:text-studio-foreground disabled:opacity-50"
    >
      {dark ? <Sun className="size-4 text-studio-accent" aria-hidden /> : <Moon className="size-4" aria-hidden />}
      <span className="hidden sm:inline">{dark ? "Light" : "Dark"}</span>
    </button>
  );
}
