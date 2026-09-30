"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { StudioNav } from "@/components/studio-nav";
import { PHILLIPS_PRINTED_DELTA_G_T_C } from "@/lib/thermo";
import {
  SERIES_IDS,
  TEAM_LENGTHS,
  citedTm,
  deltaGLabel,
  fetchStabilityPanel,
  formatMeasure,
  panelHasTeamRows,
  printedTmUncertainty,
  seriesBlocks,
  seriesCopy,
  type LengthSlot,
  type SeriesBlock,
  type StabilityPanel,
  type StabilityRow,
} from "@/lib/stability";

/** Phillips DSC columns whose unfolding ΔG is the 10 °C table value. */
const PHILLIPS_DSC = new Set<string>(["phillips2012_ctpra_dsc", "phillips2012_ctpr_dsc"]);

const COMPARISON_C = 37;

type LengthKind = "pass" | "fail" | "extrapolated" | "other" | "conflict";

type LengthView = {
  nRepeats: number;
  kind: LengthKind;
  stateWord: string;
  stateSpeech: string;
  tmText: string;
  uncertaintyText: string;
  uncertaintySpeech: string | null;
  deltaGText: string;
  deltaGSpeech: string;
  rowCount?: number;
};

function prettyUnits(text: string): string {
  return text.replaceAll("mol-1", "mol⁻¹").replaceAll("K-1", "K⁻¹");
}

function aboveComparison(assayC: number): string {
  return `The cited melt is above ${formatMeasure(assayC)} °C.`;
}

function deltaGCopy(
  row: StabilityRow | null,
  seriesId: string,
  seriesHasDeltaG: boolean,
  panelHasRows: boolean,
): { text: string; speech: string } {
  if (row && typeof row.delta_g === "number" && Number.isFinite(row.delta_g)) {
    const where = PHILLIPS_DSC.has(seriesId)
      ? `${PHILLIPS_PRINTED_DELTA_G_T_C} °C`
      : "the temperature the table states";
    return {
      text: prettyUnits(deltaGLabel(row)),
      speech: `Unfolding free energy copied from the table, at ${where}. It does not decide pass or fail, and editing a temperature elsewhere does not change it.`,
    };
  }
  if (!panelHasRows) {
    return {
      text: "Not printed",
      speech: "No unfolding free energy was copied. The lookup has no rows for these lengths.",
    };
  }
  if (!seriesHasDeltaG) {
    return { text: "Not printed", speech: "This series has no ΔG column." };
  }
  return {
    text: "Not printed",
    speech: "This paper has no row for this length, so no unfolding free energy was copied.",
  };
}

function extrapolatedView(
  nRepeats: number,
  seriesId: string,
  seriesHasDeltaG: boolean,
  panelHasRows: boolean,
): LengthView {
  const deltaG = deltaGCopy(null, seriesId, seriesHasDeltaG, panelHasRows);
  return {
    nRepeats,
    kind: "extrapolated",
    stateWord: "Extrapolated",
    stateSpeech: "This paper has no row for this length, so no melting temperature was fit.",
    tmText: "Not fit",
    uncertaintyText: "Not printed",
    uncertaintySpeech: null,
    deltaGText: deltaG.text,
    deltaGSpeech: deltaG.speech,
  };
}

function lengthView(
  slot: LengthSlot,
  seriesId: string,
  seriesHasDeltaG: boolean,
  panelHasRows: boolean,
  assayC: number,
): LengthView {
  if (slot.rows.length > 1) {
    const deltaG = deltaGCopy(null, seriesId, seriesHasDeltaG, panelHasRows);
    return {
      nRepeats: slot.nRepeats,
      kind: "conflict",
      stateWord: "Not shown",
      stateSpeech: `This length has ${slot.rows.length} rows in this paper. They were not averaged, and no melting temperature was chosen.`,
      tmText: "Not shown",
      uncertaintyText: "Not shown",
      uncertaintySpeech: null,
      deltaGText: deltaG.text,
      deltaGSpeech: deltaG.speech,
      rowCount: slot.rows.length,
    };
  }
  const row = slot.rows[0] ?? null;
  if (!row) {
    return extrapolatedView(slot.nRepeats, seriesId, seriesHasDeltaG, panelHasRows);
  }
  const tm = citedTm(row);
  const deltaG = deltaGCopy(row, seriesId, seriesHasDeltaG, panelHasRows);
  const noCitedMelt =
    row.thermal_state === "extrapolated" ||
    (tm === null && row.thermal_state !== "pass" && row.thermal_state !== "fail");
  if (noCitedMelt) {
    const empty = extrapolatedView(slot.nRepeats, seriesId, seriesHasDeltaG, panelHasRows);
    return { ...empty, deltaGText: deltaG.text, deltaGSpeech: deltaG.speech };
  }
  if (tm === null) {
    return {
      nRepeats: slot.nRepeats,
      kind: "other",
      stateWord: row.thermal_state === "fail" ? "Fail" : row.thermal_state === "pass" ? "Pass" : "Not shown",
      stateSpeech:
        row.thermal_reason ??
        "The lookup marked this length, and no melting temperature is available to show.",
      tmText: "Not fit",
      uncertaintyText: "Not printed",
      uncertaintySpeech: null,
      deltaGText: deltaG.text,
      deltaGSpeech: deltaG.speech,
    };
  }
  const sigma = printedTmUncertainty(row);
  const passed = row.thermal_state === "pass";
  const failed = row.thermal_state === "fail";
  return {
    nRepeats: slot.nRepeats,
    kind: passed ? "pass" : failed ? "fail" : "other",
    stateWord: passed ? "Pass" : failed ? "Fail" : row.thermal_state,
    stateSpeech: passed
      ? aboveComparison(assayC)
      : failed
        ? `The cited melt is not above ${formatMeasure(assayC)} °C.`
        : (row.thermal_reason ?? "This length is listed as the lookup returned it."),
    tmText: `${formatMeasure(tm)} °C`,
    uncertaintyText: sigma === null ? "Omitted" : `± ${formatMeasure(sigma)} °C`,
    uncertaintySpeech:
      sigma === null ? "The paper did not print an uncertainty, not zero." : null,
    deltaGText: deltaG.text,
    deltaGSpeech: deltaG.speech,
  };
}

function seriesHasPrintedDeltaG(block: SeriesBlock): boolean {
  return block.slots.some((slot) =>
    slot.rows.some((row) => typeof row.delta_g === "number" && Number.isFinite(row.delta_g)),
  );
}

function ChoiceButton({
  pressed,
  onClick,
  children,
}: {
  pressed: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={
        pressed
          ? "rounded-full bg-[#242220] px-4 py-2.5 text-left text-sm text-white"
          : "rounded-full border border-[#E3D9CC] bg-white px-4 py-2.5 text-left text-sm text-[#3F3A34] hover:border-[#C45C12]"
      }
    >
      {children}
    </button>
  );
}

function LengthCard({ view }: { view: LengthView }) {
  const stateClass =
    view.kind === "extrapolated"
      ? "text-[#C45C12]"
      : view.kind === "fail" || view.kind === "conflict"
        ? "text-[#9B2C2C]"
        : "text-[#242220]";
  const shell =
    view.kind === "extrapolated"
      ? "flex h-full flex-col rounded-2xl border border-dashed border-[#C45C12]/40 bg-white p-5 md:p-6"
      : "flex h-full flex-col rounded-2xl border border-[#E3D9CC] bg-white p-5 md:p-6";
  return (
    <article className={shell}>
      <p className="text-xs font-semibold tracking-[0.16em] text-[#8A8175] uppercase">n = {view.nRepeats}</p>
      <p className="mt-5 text-xs font-medium tracking-[0.14em] text-[#8A8175] uppercase">State</p>
      <h3 className={`mt-1 font-heading text-3xl font-semibold tracking-tight ${stateClass}`}>{view.stateWord}</h3>
      <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">{view.stateSpeech}</p>
      <dl className="mt-6 space-y-5 border-t border-[#E3D9CC] pt-5">
        <div>
          <dt className="text-xs font-medium tracking-[0.14em] text-[#8A8175] uppercase">Melting temperature</dt>
          <dd className="mt-1 font-heading text-2xl font-semibold tabular-nums text-[#242220]">{view.tmText}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium tracking-[0.14em] text-[#8A8175] uppercase">Uncertainty</dt>
          <dd
            className={
              view.uncertaintySpeech
                ? "mt-1 text-base font-medium text-[#C45C12]"
                : "mt-1 text-base font-medium tabular-nums text-[#242220]"
            }
          >
            {view.uncertaintyText}
          </dd>
          {view.uncertaintySpeech ? (
            <p className="mt-1 text-sm leading-relaxed text-[#5C564E]">{view.uncertaintySpeech}</p>
          ) : null}
        </div>
        <div>
          <dt className="text-xs font-medium tracking-[0.14em] text-[#8A8175] uppercase">Unfolding ΔG</dt>
          <dd className="mt-1 text-base font-medium text-[#242220]">{view.deltaGText}</dd>
          <p className="mt-1 text-sm leading-relaxed text-[#5C564E]">{view.deltaGSpeech}</p>
        </div>
      </dl>
    </article>
  );
}

function SeriesResult({
  block,
  assayC,
  panelHasRows,
}: {
  block: SeriesBlock;
  assayC: number;
  panelHasRows: boolean;
}) {
  const copy = seriesCopy(block.seriesId);
  const hasDeltaG = seriesHasPrintedDeltaG(block);
  const views = block.slots.map((slot) =>
    lengthView(slot, block.seriesId, hasDeltaG, panelHasRows, assayC),
  );
  return (
    <section className="rounded-2xl border border-[#E3D9CC] bg-[#FBF8F3] p-5 md:p-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 max-w-3xl">
          <h2 className="font-heading text-2xl font-semibold tracking-tight text-[#242220] md:text-3xl">
            {copy?.title ?? block.seriesId}
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">
            {copy?.detail ??
              "This series was in the lookup. It is shown on its own and is not merged into the four named papers."}
          </p>
          {copy ? (
            <p className="mt-2 text-sm leading-relaxed text-[#6F675C]">
              {copy.citation}{" "}
              <a
                className="underline decoration-[#E3D9CC] underline-offset-4 hover:decoration-[#C45C12]"
                href={`https://doi.org/${copy.doi}`}
              >
                DOI {copy.doi}
              </a>
              .
            </p>
          ) : null}
        </div>
        {copy?.isDefault ? (
          <Badge variant="outline" className="w-fit rounded-full">
            Default series
          </Badge>
        ) : null}
      </div>
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {views.map((view) => (
          <LengthCard key={view.nRepeats} view={view} />
        ))}
      </div>
    </section>
  );
}

function seriesChoices(blocks: SeriesBlock[]): { id: string; title: string; isDefault: boolean }[] {
  const known = new Set<string>(SERIES_IDS);
  const extras = blocks.map((block) => block.seriesId).filter((id) => !known.has(id));
  const uniqueExtras = [...new Set(extras)].sort();
  const ids = [...SERIES_IDS, ...uniqueExtras];
  return [
    { id: "all", title: uniqueExtras.length > 0 ? "All series" : "All four", isDefault: false },
    ...ids.map((id) => {
      const copy = seriesCopy(id);
      return { id, title: copy?.title ?? id, isDefault: Boolean(copy?.isDefault) };
    }),
  ];
}

export function StabilityBoard() {
  const [data, setData] = useState<StabilityPanel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [seriesFilter, setSeriesFilter] = useState("all");

  useEffect(() => {
    let alive = true;
    fetchStabilityPanel()
      .then((payload) => {
        if (alive) setData(payload);
      })
      .catch((err: unknown) => {
        if (alive) {
          setError(err instanceof Error ? err.message : "Could not load the cited melting temperatures.");
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const blocks = data ? seriesBlocks(data.rows) : [];
  const hasRows = data ? panelHasTeamRows(data.rows) : false;
  const choices = seriesChoices(blocks);
  const visible = blocks.filter((block) => seriesFilter === "all" || block.seriesId === seriesFilter);
  const selectedTitle =
    seriesFilter === "all"
      ? choices.some((choice) => choice.id === "all" && choice.title === "All series")
        ? "every series in the lookup"
        : "all four papers"
      : (seriesCopy(seriesFilter)?.title ?? seriesFilter);
  const assayC = data?.t_assay_C ?? COMPARISON_C;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 md:px-8 md:py-12">
      <StudioNav />
      <header className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold tracking-[0.22em] text-[#C45C12] uppercase">Stability</p>
          <h1 className="mt-2 font-heading text-4xl leading-[1.1] font-semibold tracking-tight text-[#242220] md:text-5xl">
            Stability confirmation
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-[#5C564E]">
            Cited melting temperatures for n = 3, n = 8, and n = 14. Each paper stays in its own block. Nothing here is averaged, and a missing melt is not filled in.
          </p>
          <Link
            href="/stability/calculator"
            className="mt-4 inline-block text-sm font-medium text-[#C45C12] underline decoration-[#E3D9CC] underline-offset-4 hover:decoration-[#C45C12]"
          >
            Estimate ΔG at other temperatures
          </Link>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge className="rounded-full bg-[#242220] text-white">
            calibrated = {data ? String(data.calibrated) : "false"}
          </Badge>
          {data?.source === "live" ? (
            <Badge variant="outline" className="border-[#266FB1] text-[#266FB1]">
              live chassis
            </Badge>
          ) : null}
          {data?.source === "snapshot" ? <Badge variant="outline">wiki snapshot</Badge> : null}
        </div>
      </header>

      <section className="mt-10 rounded-2xl border border-[#E3D9CC] bg-white p-5 md:p-8" aria-label="Inputs">
        <h2 className="font-heading text-2xl font-semibold tracking-tight text-[#242220]">Inputs</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
          Choose which paper to read. The lengths and the comparison temperature stay fixed.
        </p>

        <div className="mt-8">
          <h3 className="text-sm font-semibold text-[#242220]">Series</h3>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
            All four papers, or one at a time. Phillips CTPRa DSC is the default series.
          </p>
          <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Series to show">
            {choices.map((choice) => (
              <ChoiceButton
                key={choice.id}
                pressed={seriesFilter === choice.id}
                onClick={() => setSeriesFilter(choice.id)}
              >
                <span className="block">{choice.title}</span>
                {choice.isDefault ? <span className="mt-0.5 block text-[11px] opacity-80">Default series</span> : null}
              </ChoiceButton>
            ))}
          </div>
        </div>

        <div className="mt-8 grid gap-8 border-t border-[#E3D9CC] pt-8 md:grid-cols-2">
          <div>
            <h3 className="text-sm font-semibold text-[#242220]">Repeat counts</h3>
            <ul className="mt-3 flex flex-wrap gap-2" aria-label="Lengths being confirmed">
              {TEAM_LENGTHS.map((n) => (
                <li key={n} className="rounded-full bg-[#242220] px-4 py-2.5 text-sm font-medium text-white">
                  n = {n}
                </li>
              ))}
            </ul>
            <p className="mt-3 text-sm leading-relaxed text-[#5C564E]">
              These repeat counts are fixed. They are the lengths being confirmed.
            </p>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[#242220]">Comparison temperature</h3>
            <p className="mt-3 font-heading text-4xl font-semibold tabular-nums tracking-tight text-[#242220]">37 °C</p>
            <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">
              This is an E. coli operating assumption, not a temperature from the papers.
            </p>
            {data && data.t_assay_C !== COMPARISON_C ? (
              <p className="mt-3 text-sm leading-relaxed text-[#9B2C2C]">
                The loaded lookup reports {formatMeasure(data.t_assay_C)} °C, which is not the 37 °C comparison on this page.
              </p>
            ) : null}
          </div>
        </div>
      </section>

      <section className="mt-12" aria-label="Results">
        <h2 className="font-heading text-2xl font-semibold tracking-tight text-[#242220]">Results</h2>
        {data ? (
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
            Showing {selectedTitle}. Each block lists n = 3, n = 8, and n = 14.
          </p>
        ) : (
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
            Each paper is listed on its own, with n = 3, n = 8, and n = 14.
          </p>
        )}
        {data?.note ? <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#6F675C]">{data.note}</p> : null}

        {loading ? (
          <p className="mt-8 flex items-center gap-2 text-sm text-[#8A8175]">
            <Loader2 className="animate-spin" /> Loading the cited melting temperatures…
          </p>
        ) : null}

        {error ? (
          <div className="mt-8 rounded-2xl border border-[#E3D9CC] bg-white px-5 py-6">
            <p className="flex items-start gap-2 text-sm text-[#9B2C2C]">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <span>{error}</span>
            </p>
            <p className="mt-3 text-sm leading-relaxed text-[#5C564E]">
              No melting temperatures are shown. This screen does not fill in example values when the papers cannot be loaded.
            </p>
          </div>
        ) : null}

        {data && !hasRows ? (
          <p className="mt-8 rounded-2xl border border-dashed border-[#E3D9CC] bg-white px-5 py-6 text-sm leading-relaxed text-[#5C564E]">
            The lookup loaded, and it has no rows for n = 3, n = 8, or n = 14. The lengths below stay empty.
          </p>
        ) : null}

        {data ? (
          <div className="mt-6 space-y-6">
            {visible.map((block) => (
              <SeriesResult key={block.seriesId} block={block} assayC={assayC} panelHasRows={hasRows} />
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
