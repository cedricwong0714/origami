"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StudioNav } from "@/components/studio-nav";
import {
  MISSING_TM_LABEL,
  N14_NO_FIT_NOTE,
  OMITTED_UNCERTAINTY_LABEL,
  citedInterval,
  citedTm,
  deltaGLabel,
  fetchStabilityPanel,
  formatMeasure,
  panelHasTeamRows,
  seriesBlocks,
  seriesCopy,
  tmAxis,
  tmLabel,
  uncertaintyLabel,
  type SeriesBlock,
  type StabilityPanel,
  type StabilityRow,
} from "@/lib/stability";

function yPercent(value: number, low: number, high: number): number {
  const span = high - low || 1;
  return (1 - (value - low) / span) * 100;
}

function TmPlot({
  block,
  assayC,
}: {
  block: SeriesBlock;
  assayC: number;
}) {
  const samples: number[] = [];
  for (const slot of block.slots) {
    const row = slot.rows.length === 1 ? (slot.rows[0] ?? null) : null;
    const tm = citedTm(row);
    const interval = citedInterval(row);
    if (tm !== null) samples.push(tm);
    if (interval) samples.push(interval.low, interval.high);
  }
  const axis = tmAxis(samples, assayC);
  const title = seriesCopy(block.seriesId)?.title ?? block.seriesId;
  const summary = block.slots
    .map((slot) => {
      if (slot.rows.length === 0) return `n=${slot.nRepeats}: not in this lookup`;
      if (slot.rows.length > 1) return `n=${slot.nRepeats}: multiple rows, not plotted`;
      return `n=${slot.nRepeats}: ${tmLabel(slot.rows[0] ?? null)}`;
    })
    .join(". ");

  return (
    <figure>
      <div
        className="flex gap-2"
        role="img"
        aria-label={`${title}. ${summary}. Missing melting temperatures are labeled ${MISSING_TM_LABEL}. No zero is drawn.`}
      >
        <div className="relative h-52 w-11 shrink-0 sm:h-64">
          <div className="absolute inset-x-0 top-3 bottom-6">
            {axis.ticks.map((tick) => (
              <span
                key={tick}
                className="absolute right-0 -translate-y-1/2 text-[11px] text-[#8A8175]"
                style={{ top: `${yPercent(tick, axis.low, axis.high)}%` }}
              >
                {formatMeasure(tick)}
              </span>
            ))}
          </div>
        </div>
        <div className="relative h-52 min-w-0 flex-1 sm:h-64">
          <div className="absolute inset-x-0 top-3 bottom-6">
            {axis.ticks.map((tick) => (
              <div
                key={tick}
                className="absolute right-0 left-0 border-t border-[#E3D9CC]"
                style={{ top: `${yPercent(tick, axis.low, axis.high)}%` }}
              />
            ))}
            <div
              className="absolute right-0 left-0 z-[1] border-t border-dashed border-[#C45C12]"
              style={{ top: `${yPercent(assayC, axis.low, axis.high)}%` }}
            />
            <div className="absolute inset-0 z-[2] grid grid-cols-3">
              {block.slots.map((slot) => {
                const row = slot.rows.length === 1 ? (slot.rows[0] ?? null) : null;
                const tm = citedTm(row);
                const interval = citedInterval(row);
                const whisker =
                  interval && interval.high > interval.low
                    ? {
                        top: yPercent(interval.high, axis.low, axis.high),
                        bottom: yPercent(interval.low, axis.low, axis.high),
                      }
                    : null;
                return (
                  <div key={slot.nRepeats} className="relative h-full">
                    {whisker ? (
                      <>
                        <div
                          className="absolute w-0.5 -translate-x-1/2 bg-[#266FB1]"
                          style={{
                            left: "50%",
                            top: `${whisker.top}%`,
                            height: `${whisker.bottom - whisker.top}%`,
                          }}
                        />
                        <div
                          className="absolute h-0.5 w-3 -translate-x-1/2 bg-[#266FB1]"
                          style={{ left: "50%", top: `${whisker.top}%` }}
                        />
                        <div
                          className="absolute h-0.5 w-3 -translate-x-1/2 bg-[#266FB1]"
                          style={{ left: "50%", top: `${whisker.bottom}%` }}
                        />
                      </>
                    ) : null}
                    {tm !== null ? (
                      <div
                        className="absolute size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#FF8000] ring-2 ring-white"
                        style={{
                          left: "50%",
                          top: `${yPercent(tm, axis.low, axis.high)}%`,
                        }}
                      />
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
      <div className="mt-1 grid grid-cols-3 pl-12 text-center text-sm text-[#242220]">
        {block.slots.map((slot) => {
          const row = slot.rows.length === 1 ? (slot.rows[0] ?? null) : null;
          const missing =
            slot.rows.length > 1
              ? "not averaged"
              : slot.rows.length === 0
                ? "not in lookup"
                : citedTm(row) === null
                  ? MISSING_TM_LABEL
                  : "";
          return (
            <div key={slot.nRepeats}>
              <p>n={slot.nRepeats}</p>
              <p className="min-h-8 text-[11px] leading-tight font-medium text-[#C45C12]">{missing || "\u00a0"}</p>
            </div>
          );
        })}
      </div>
      <figcaption className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[#5C564E]">
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-[#FF8000]" /> Cited Tm
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3 w-0.5 bg-[#266FB1]" /> Cited interval
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-4 border-t border-dashed border-[#C45C12]" />
          {formatMeasure(assayC)} °C comparison
        </span>
        <span>A missing printed uncertainty is omitted. It is not drawn as ±0.</span>
      </figcaption>
    </figure>
  );
}

function SeriesSection({
  block,
  assayC,
}: {
  block: SeriesBlock;
  assayC: number;
}) {
  const copy = seriesCopy(block.seriesId);
  const present = block.slots.some((slot) => slot.rows.length > 0);
  return (
    <Card className="border-[#E3D9CC] bg-white shadow-none">
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold tracking-[0.16em] text-[#C45C12] uppercase break-all">
              {block.seriesId}
            </p>
            <CardTitle className="mt-1 font-heading text-2xl text-[#242220]">
              {copy?.title ?? block.seriesId}
            </CardTitle>
            <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">
              {copy?.detail ??
                "This series id was in the lookup. It is shown alone and is not merged into the four named series."}
            </p>
          </div>
          {copy?.isDefault ? (
            <Badge variant="outline" className="w-fit rounded-full">
              default series
            </Badge>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {copy ? (
          <p className="text-xs leading-relaxed text-[#6F675C]">
            {copy.citation}{" "}
            <a
              className="underline decoration-[#E3D9CC] underline-offset-2"
              href={`https://doi.org/${copy.doi}`}
            >
              DOI {copy.doi}
            </a>
            .
          </p>
        ) : null}
        {present ? <TmPlot block={block} assayC={assayC} /> : null}
        {!present ? (
          <p className="rounded-xl border border-dashed border-[#E3D9CC] bg-[#FBF8F3] px-4 py-6 text-sm text-[#5C564E]">
            No row for n = 3, 8, or 14 in this series. Nothing is filled in.
          </p>
        ) : (
          <>
            <div className="grid gap-3 md:hidden">
              {block.slots.map((slot) => (
                <LengthCard key={slot.nRepeats} nRepeats={slot.nRepeats} rows={slot.rows} />
              ))}
            </div>
            <div className="hidden overflow-x-auto rounded-xl border border-[#E3D9CC] md:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>n</TableHead>
                    <TableHead>thermal state</TableHead>
                    <TableHead>Tm</TableHead>
                    <TableHead>printed uncertainty</TableHead>
                    <TableHead>printed unfolding ΔG</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {block.slots.map((slot) => (
                    <LengthRow key={slot.nRepeats} nRepeats={slot.nRepeats} rows={slot.rows} />
                  ))}
                </TableBody>
              </Table>
            </div>
          </>
        )}
        <p className="text-xs leading-relaxed text-[#6F675C]">
          Printed unfolding ΔG is the value in the source table when that column exists. It does not set the gate and it does not decide pass or fail.
        </p>
      </CardContent>
    </Card>
  );
}

function LengthCard({ nRepeats, rows }: { nRepeats: number; rows: StabilityRow[] }) {
  if (rows.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-[#E3D9CC] px-3 py-3 text-sm text-[#5C564E]">
        n = {nRepeats} is not in this lookup.
      </p>
    );
  }
  if (rows.length > 1) {
    return (
      <p className="rounded-xl border border-[#E3D9CC] px-3 py-3 text-sm text-[#9B2C2C]">
        n = {nRepeats} has {rows.length} rows. They were not averaged and are not plotted.
      </p>
    );
  }
  const row = rows[0];
  if (!row) return null;
  const tm = citedTm(row);
  const facts = [
    ["thermal state", row.thermal_state, false],
    ["Tm", tmLabel(row), tm === null],
    ["printed uncertainty", uncertaintyLabel(row), uncertaintyLabel(row) === OMITTED_UNCERTAINTY_LABEL],
    ["printed unfolding ΔG", deltaGLabel(row), deltaGLabel(row) === "not printed"],
  ] as const;
  return (
    <div className="rounded-xl border border-[#E3D9CC] px-3 py-3">
      <p className="font-medium text-[#242220]">n = {nRepeats}</p>
      <dl className="mt-2 space-y-1.5">
        {facts.map(([label, value, missing]) => (
          <div key={label} className="flex items-baseline justify-between gap-3 text-sm">
            <dt className="text-[#8A8175]">{label}</dt>
            <dd className={missing ? "text-right font-medium text-[#C45C12]" : "text-right text-[#242220]"}>
              {value}
            </dd>
          </div>
        ))}
      </dl>
      {nRepeats === 14 && row.thermal_state === "extrapolated" ? (
        <p className="mt-2 text-xs leading-relaxed text-[#C45C12]">{N14_NO_FIT_NOTE}</p>
      ) : null}
      {row.thermal_reason ? (
        <p className="mt-2 text-xs leading-relaxed text-[#8A8175]">{row.thermal_reason}</p>
      ) : null}
    </div>
  );
}

function LengthRow({ nRepeats, rows }: { nRepeats: number; rows: StabilityRow[] }) {
  if (rows.length === 0) {
    return (
      <TableRow>
        <TableCell className="font-medium">{nRepeats}</TableCell>
        <TableCell colSpan={4} className="whitespace-normal text-[#5C564E]">
          Not in this lookup.
        </TableCell>
      </TableRow>
    );
  }
  if (rows.length > 1) {
    return (
      <TableRow>
        <TableCell className="font-medium">{nRepeats}</TableCell>
        <TableCell colSpan={4} className="whitespace-normal text-[#9B2C2C]">
          {rows.length} rows share this series and length. They were not averaged and are not plotted.
        </TableCell>
      </TableRow>
    );
  }
  const row = rows[0];
  if (!row) return null;
  const tm = citedTm(row);
  return (
    <TableRow>
      <TableCell className="font-medium">{nRepeats}</TableCell>
      <TableCell>{row.thermal_state}</TableCell>
      <TableCell className={tm === null ? "font-medium text-[#C45C12]" : undefined}>
        {tmLabel(row)}
      </TableCell>
      <TableCell className={uncertaintyLabel(row) === OMITTED_UNCERTAINTY_LABEL ? "font-medium text-[#C45C12]" : undefined}>
        {uncertaintyLabel(row)}
      </TableCell>
      <TableCell className="whitespace-normal">
        {deltaGLabel(row)}
        {nRepeats === 14 && row.thermal_state === "extrapolated" ? (
          <span className="mt-1 block text-xs font-normal text-[#C45C12]">{N14_NO_FIT_NOTE}</span>
        ) : null}
        {row.thermal_reason ? (
          <span className="mt-1 block text-xs font-normal text-[#8A8175]">{row.thermal_reason}</span>
        ) : null}
      </TableCell>
    </TableRow>
  );
}

export function StabilityBoard() {
  const [data, setData] = useState<StabilityPanel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    fetchStabilityPanel()
      .then((payload) => {
        if (alive) setData(payload);
      })
      .catch((err: unknown) => {
        if (alive) {
          setError(err instanceof Error ? err.message : "Could not load the thermal lookup.");
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

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 md:px-8">
      <StudioNav />
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold tracking-[0.22em] text-[#C45C12] uppercase">
            Literature lookup · four series
          </p>
          <h1 className="mt-2 font-heading text-4xl text-[#242220] md:text-5xl">
            Thermal confirmation
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-[#5C564E] md:text-[15px]">
            Cited melting temperatures for team lengths n = 3, 8, and 14. Each series stays in its own block. This page does not average them, does not fit a Tm(n) curve, and does not claim a wet-lab validation of the fusion.
          </p>
          <Link href="/stability/calculator" className="mt-3 inline-block text-sm font-medium text-[#FF8000]">
            ΔG, ΔH, ΔS calculator
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

      <Card className="mt-6 border-[#E3D9CC] bg-[#FFF7EF] shadow-none">
        <CardContent className="space-y-2 pt-6 text-sm leading-relaxed text-[#3F3A34]">
          <p>
            The comparison temperature is 37 °C. That figure is an E. coli operating assumption for this screen. It is not a DSC setpoint from Phillips et al. 2012 or Cortajarena and Regan 2011.
          </p>
          {data && data.t_assay_C !== 37 ? (
            <p>
              The loaded lookup reports t_assay_C = {formatMeasure(data.t_assay_C)} °C, which is not the 37 °C comparison requested for this page.
            </p>
          ) : null}
          <p>
            The gate is pass only when a cited Tm is strictly above that comparison temperature. A missing Tm stays the word extrapolated. No point is drawn for it, and it is never replaced with 0. A printed Tm uncertainty is shown as printed. When the table printed none, the cell says omitted. A zero-width gate envelope is not shown as ±0.
          </p>
          <p>
            {N14_NO_FIT_NOTE} Phillips 2012 CTPRa CD and Phillips 2012 CTPR DSC have no cited Tm at n = 8, so those cells stay extrapolated. Each series stays in its own block.
          </p>
          {data?.note ? <p>{data.note}</p> : null}
        </CardContent>
      </Card>

      {loading ? (
        <p className="mt-10 flex items-center gap-2 text-sm text-[#8A8175]">
          <Loader2 className="animate-spin" /> Loading the thermal lookup…
        </p>
      ) : null}
      {error ? (
        <div className="mt-10 rounded-xl border border-[#E3D9CC] bg-white px-4 py-6">
          <p className="flex items-start gap-2 text-sm text-[#9B2C2C]">
            <AlertCircle className="mt-0.5 size-4 shrink-0" />
            <span>{error}</span>
          </p>
          <p className="mt-3 text-sm leading-relaxed text-[#5C564E]">
            No melting temperatures are shown. This screen does not substitute example values when the lookup is missing.
          </p>
        </div>
      ) : null}

      {data && !hasRows ? (
        <div className="mt-8 rounded-xl border border-dashed border-[#E3D9CC] bg-white px-4 py-8">
          <p className="text-sm leading-relaxed text-[#5C564E]">
            The lookup loaded, and it has no rows for n = 3, 8, or 14. The four series are listed below with those lengths empty.
          </p>
        </div>
      ) : null}

      {data ? (
        <div className="mt-8 space-y-6">
          {blocks.map((block) => (
            <SeriesSection key={block.seriesId} block={block} assayC={data.t_assay_C} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
