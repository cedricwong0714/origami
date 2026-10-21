"use client";

import Link from "next/link";
import { StudioNav } from "@/components/studio-nav";
import { MODEL_GROUPS } from "@/lib/model-catalog";

export function ModelIndex() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-10 font-[family-name:var(--font-inter)] text-studio-foreground">
      <StudioNav />
      <header className="mb-8">
        <h1 className="text-3xl font-semibold">Choose a mode</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-studio-muted">
          Open a card to run that calculation. The last group combines the models or records a measurement.
        </p>
      </header>
      <div className="space-y-10">
        {MODEL_GROUPS.map((group) => (
          <section key={group.title}>
            <h2 className="text-lg font-semibold">{group.title}</h2>
            <p className="mt-1 text-sm text-studio-muted">{group.blurb}</p>
            <ul className="mt-4 grid gap-3 sm:grid-cols-2">
              {group.models.map((model) => (
                <li key={model.href}>
                  <Link
                    href={model.href}
                    className="block h-full rounded-xl border border-studio-border bg-studio-card p-4 transition hover:border-studio-accent"
                  >
                    <span className="text-base font-medium">{model.title}</span>
                    <span className="mt-1 block text-sm leading-relaxed text-studio-muted">
                      {model.summary}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </main>
  );
}
