"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { StudioNav } from "@/components/studio-nav";
import { PHILLIPS_PRINTED_DELTA_G_T_C } from "@/lib/thermo";
import {
  CANONICAL_SERIES_ID,
  TEAM_LENGTHS,
  citedTm,
  fetchStabilityPanel,
  formatMeasure,
  panelHasTeamRows,
  seriesCopy,
  teamLengthSlots,
  type LengthSlot,
  type SeriesCurveFit,
  type StabilityPanel,
  type StabilityRow,
} from "@/lib/stability";

/** Phillips DSC columns whose unfolding ΔG is the 10 °C table value. */
const PHILLIPS_DSC = new Set<string>(["phillips2012_ctpra_dsc", "phillips2012_ctpr_dsc"]);

const COMPARISON_C = 37;

type LengthKind = "pass" | "fail" | "not_fit" | "other" | "conflict";

type LengthView = {
  nRepeats: number;
  kind: LengthKind;
  stateWord: string;
  stateSpeech: string;
  lengthNote: string | null;
  tmText: string;
  paperTmText: string | null;
  bandText: string;
  bandSpeech: string | null;
  deltaGText: string;
  deltaGSpeech: string;
  paperDeltaGText: string | null;
  deltaGBandText: string | null;
  rowCount?: number;
};

function prettyUnits(text: string): string {
  return text.replaceAll("mol-1", "mol⁻¹").replaceAll("K-1", "K⁻¹");
}

function formatFit(value: number): string {
  if (!Number.isFinite(value)) {
    throw new Error("formatFit requires a finite number.");
  }
  const abs = Math.abs(value);
  if (abs !== 0 && (abs >= 1000 || abs < 0.001)) {
    return value.toExponential(3);
  }
  return formatMeasure(value);
}

function bandSpan(low: number | null, high: number | null, units: string): string | null {
  if (low === null || high === null) return null;
  if (!Number.isFinite(low) || !Number.isFinite(high)) return null;
  const unitText = units.trim();
  const span = `${formatFit(low)}–${formatFit(high)}`;
  return unitText ? `${span} ${unitText}` : span;
}

function paperLine(value: number | null | undefined, units: string): string | null {
  if (value === undefined) return null;
  if (value === null || !Number.isFinite(value)) return "Paper row: not in this series";
  const unitText = units.trim();
  return unitText ? `Paper row: ${formatMeasure(value)} ${unitText}` : `Paper row: ${formatMeasure(value)}`;
}

/** 95% half-width is (high − low) / 2. It has to be finite and smaller than |value|. */
function halfWidthSmallerThanAbs(value: number, low: number | null, high: number | null): boolean {
  if (!Number.isFinite(value) || low === null || high === null) return false;
  if (!Number.isFinite(low) || !Number.isFinite(high)) return false;
  const half = (high - low) / 2;
  return Number.isFinite(half) && half < Math.abs(value);
}

function saturatingDeltaGUnusable(row: StabilityRow): boolean {
  if (row.delta_g_fit_form !== "saturating") return false;
  if (typeof row.delta_g !== "number" || !Number.isFinite(row.delta_g)) return true;
  return !halfWidthSmallerThanAbs(row.delta_g, row.delta_g_band_95_low, row.delta_g_band_95_high);
}

function rowsDoNotDetermineDeltaG(fit: SeriesCurveFit | null): boolean {
  return fit?.warnings.some((warning) => warning.includes("do not determine ΔG(n)")) ?? false;
}

function deltaGCopy(
  row: StabilityRow | null,
  seriesId: string,
  dgFit: SeriesCurveFit | null,
): { text: string; speech: string; paper: string | null; band: string | null } {
  const phillips = PHILLIPS_DSC.has(seriesId)
    ? ` The printed column is the table value at ${PHILLIPS_PRINTED_DELTA_G_T_C} °C.`
    : "";
  const paperUnits = prettyUnits(row?.delta_g_units ?? row?.paper_delta_g_units ?? "");
  const omitted = rowsDoNotDetermineDeltaG(dgFit) || (row ? saturatingDeltaGUnusable(row) : false);
  if (omitted) {
    return {
      text: "Not determined",
      speech: "The rows do not determine ΔG(n).",
      paper: row?.comparison_uses_fit ? paperLine(row.paper_delta_g, paperUnits) : null,
      band: null,
    };
  }
  if (row && typeof row.delta_g === "number" && Number.isFinite(row.delta_g)) {
    const units = prettyUnits(row.delta_g_units ?? "");
    const band = bandSpan(row.delta_g_band_95_low, row.delta_g_band_95_high, units);
    const lineFallback =
      row.delta_g_fit_form === "line" &&
      (dgFit?.warnings.some((warning) => warning.includes("saturating form is non-identifiable")) ?? false);
    const calculated = lineFallback
      ? `Calculated from this series' printed unfolding ΔG values versus repeat count. The saturating form is non-identifiable, so this number is the straight line y = a + b n and its linearized 95% band. It is not a temperature correction, and it does not decide pass or fail.${phillips}`
      : `Calculated from this series' printed unfolding ΔG values versus repeat count. It is not a temperature correction, and it does not decide pass or fail.${phillips}`;
    return {
      text: `${formatFit(row.delta_g)}${units ? ` ${units}` : ""}`,
      speech: row.comparison_uses_fit
        ? calculated
        : `Unfolding free energy from the lookup.${phillips} It does not decide pass or fail.`,
      paper: row.comparison_uses_fit ? paperLine(row.paper_delta_g, units) : null,
      band: row.comparison_uses_fit ? band : null,
    };
  }
  if (row?.comparison_uses_fit) {
    return {
      text: "Not printed",
      speech: "This series has no unfolding ΔG rows. Nothing was borrowed from another paper.",
      paper: null,
      band: null,
    };
  }
  return {
    text: "Not printed",
    speech: "This series has no unfolding ΔG value at this length.",
    paper: null,
    band: null,
  };
}

function emptyMelt(
  nRepeats: number,
  seriesId: string,
  reason: string,
  dgFit: SeriesCurveFit | null,
): LengthView {
  const deltaG = deltaGCopy(null, seriesId, dgFit);
  return {
    nRepeats,
    kind: "not_fit",
    stateWord: "Not fit",
    stateSpeech: reason,
    lengthNote: null,
    tmText: "Not fit",
    paperTmText: null,
    bandText: "Not reported",
    bandSpeech: null,
    deltaGText: deltaG.text,
    deltaGSpeech: deltaG.speech,
    paperDeltaGText: deltaG.paper,
    deltaGBandText: deltaG.band,
  };
}

function lengthView(
  slot: LengthSlot,
  seriesId: string,
  assayC: number,
  dgFit: SeriesCurveFit | null,
): LengthView {
  if (slot.rows.length > 1) {
    const deltaG = deltaGCopy(null, seriesId, dgFit);
    return {
      nRepeats: slot.nRepeats,
      kind: "conflict",
      stateWord: "Not shown",
      stateSpeech: `This length has ${slot.rows.length} rows in this paper. They were not averaged, and no melting temperature was chosen.`,
      lengthNote: null,
      tmText: "Not shown",
      paperTmText: null,
      bandText: "Not shown",
      bandSpeech: null,
      deltaGText: deltaG.text,
      deltaGSpeech: deltaG.speech,
      paperDeltaGText: deltaG.paper,
      deltaGBandText: deltaG.band,
      rowCount: slot.rows.length,
    };
  }
  const row = slot.rows[0] ?? null;
  if (!row) {
    return emptyMelt(
      slot.nRepeats,
      seriesId,
      "This length has no calculated melting temperature.",
      dgFit,
    );
  }
  const tm = citedTm(row);
  const deltaG = deltaGCopy(row, seriesId, dgFit);
  if (tm === null) {
    const empty = emptyMelt(
      slot.nRepeats,
      seriesId,
      row.thermal_reason ?? "No melting-temperature curve was fit for this series.",
      dgFit,
    );
    return {
      ...empty,
      deltaGText: deltaG.text,
      deltaGSpeech: deltaG.speech,
      paperDeltaGText: deltaG.paper,
      deltaGBandText: deltaG.band,
    };
  }
  const passed = row.thermal_state === "pass";
  const failed = row.thermal_state === "fail";
  const usesFit = row.comparison_uses_fit;
  const band = usesFit ? bandSpan(row.tm_interval_low, row.tm_interval_high, "°C") : null;
  return {
    nRepeats: slot.nRepeats,
    kind: passed ? "pass" : failed ? "fail" : "other",
    stateWord: passed ? "Pass" : failed ? "Fail" : row.thermal_state,
    stateSpeech: usesFit
      ? passed
        ? `The comparison uses the fit. The calculated melt is above ${formatMeasure(assayC)} °C.`
        : failed
          ? `The comparison uses the fit. The calculated melt is not above ${formatMeasure(assayC)} °C.`
          : (row.thermal_reason ?? "The comparison uses the fit.")
      : passed
        ? `The cited melt is above ${formatMeasure(assayC)} °C.`
        : failed
          ? `The cited melt is not above ${formatMeasure(assayC)} °C.`
          : (row.thermal_reason ?? "This length is listed as the lookup returned it."),
    lengthNote: row.length_note,
    tmText: `${formatFit(tm)} °C`,
    paperTmText: usesFit ? paperLine(row.paper_tm_C, "°C") : null,
    bandText: usesFit ? (band ?? "Not reported") : "Lookup",
    bandSpeech: usesFit
      ? band
        ? "Linear approximation of the fit covariance, value ± 1.96 σ. Not a wet-lab confidence interval."
        : "The fit covariance is not finite, so the 95% band is non-identifiable. The calculated value is still shown."
      : null,
    deltaGText: deltaG.text,
    deltaGSpeech: deltaG.speech,
    paperDeltaGText: deltaG.paper,
    deltaGBandText: deltaG.band,
  };
}

function LengthCard({ view }: { view: LengthView }) {
  const stateClass =
    view.kind === "not_fit"
      ? "text-[#C45C12]"
      : view.kind === "fail" || view.kind === "conflict"
        ? "text-[#9B2C2C]"
        : "text-[#242220]";
  const shell =
    view.kind === "not_fit"
      ? "flex h-full flex-col rounded-2xl border border-dashed border-[#C45C12]/40 bg-white p-5 md:p-6"
      : "flex h-full flex-col rounded-2xl border border-[#E3D9CC] bg-white p-5 md:p-6";
  return (
    <article className={shell}>
      <p className="text-xs font-semibold tracking-[0.16em] text-[#8A8175] uppercase">n = {view.nRepeats}</p>
      <p className="mt-5 text-xs font-medium tracking-[0.14em] text-[#8A8175] uppercase">State</p>
      <h3 className={`mt-1 font-heading text-3xl font-semibold tracking-tight ${stateClass}`}>{view.stateWord}</h3>
      <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">{view.stateSpeech}</p>
      {view.lengthNote ? (
        <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">{view.lengthNote}</p>
      ) : null}
      <dl className="mt-6 space-y-5 border-t border-[#E3D9CC] pt-5">
        <div>
          <dt className="text-xs font-medium tracking-[0.14em] text-[#8A8175] uppercase">Calculated melt</dt>
          <dd className="mt-1 font-heading text-2xl font-semibold tabular-nums text-[#242220]">{view.tmText}</dd>
          {view.paperTmText ? (
            <p className="mt-1 text-sm text-[#8A8175]">{view.paperTmText}</p>
          ) : null}
        </div>
        <div>
          <dt className="text-xs font-medium tracking-[0.14em] text-[#8A8175] uppercase">95% band</dt>
          <dd className="mt-1 text-base font-medium tabular-nums text-[#242220]">{view.bandText}</dd>
          {view.bandSpeech ? (
            <p className="mt-1 text-sm leading-relaxed text-[#5C564E]">{view.bandSpeech}</p>
          ) : null}
        </div>
        <div>
          <dt className="text-xs font-medium tracking-[0.14em] text-[#8A8175] uppercase">Calculated ΔG</dt>
          <dd
            className={
              view.deltaGText === "Not determined" || view.deltaGText === "Not printed"
                ? "mt-1 text-base font-medium text-[#5C564E]"
                : "mt-1 text-base font-medium tabular-nums text-[#242220]"
            }
          >
            {view.deltaGText}
          </dd>
          {view.deltaGBandText ? (
            <p className="mt-1 text-sm tabular-nums text-[#242220]">95% band: {view.deltaGBandText}</p>
          ) : null}
          {view.paperDeltaGText ? (
            <p className="mt-1 text-sm text-[#8A8175]">{view.paperDeltaGText}</p>
          ) : null}
          <p className="mt-1 text-sm leading-relaxed text-[#5C564E]">{view.deltaGSpeech}</p>
        </div>
      </dl>
    </article>
  );
}

function parameterLine(fit: SeriesCurveFit): string[] {
  return fit.parameters.map((parameter) => {
    const value = formatFit(parameter.value);
    if (!parameter.identifiable || parameter.standard_error === null) {
      return `${parameter.name} = ${value} ${parameter.units} (non-identifiable)`;
    }
    return `${parameter.name} = ${value} ± ${formatFit(parameter.standard_error)} ${parameter.units}`;
  });
}

function FitSummary({
  fit,
  title,
  omitCoefficients = false,
}: {
  fit: SeriesCurveFit;
  title: string;
  omitCoefficients?: boolean;
}) {
  const points = fit.n_repeats.length > 0 ? `Fit on n = ${fit.n_repeats.join(", ")}.` : "No points were fit.";
  return (
    <div className="mt-4">
      <h3 className="text-sm font-semibold text-[#242220]">{title}</h3>
      {omitCoefficients ? null : fit.equation ? (
        <p className="mt-1 font-heading text-sm text-[#242220]">{fit.equation}</p>
      ) : null}
      <p className="mt-1 text-sm leading-relaxed text-[#5C564E]">{points}</p>
      {omitCoefficients ? (
        <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">
          The saturating coefficients are non-identifiable and are not shown as fitted values.
        </p>
      ) : parameterLine(fit).length > 0 ? (
        <ul className="mt-2 space-y-1 text-sm tabular-nums text-[#3F3A34]">
          {parameterLine(fit).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
      {fit.warnings.map((warning) => (
        <p key={warning} className="mt-2 text-sm leading-relaxed text-[#5C564E]">
          {warning}
        </p>
      ))}
    </div>
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

  const canonicalCopy = seriesCopy(CANONICAL_SERIES_ID);
  const slots = data ? teamLengthSlots(data.rows) : [];
  const hasRows = data ? panelHasTeamRows(data.rows) : false;
  const fit = data?.series_fits?.[0] ?? null;
  const dgFit = fit?.delta_g ?? null;
  const hideSaturatingDeltaG = slots.some((slot) =>
    slot.rows.some((row) => saturatingDeltaGUnusable(row)),
  );
  const views = slots.map((slot) =>
    lengthView(slot, CANONICAL_SERIES_ID, data?.t_assay_C ?? COMPARISON_C, dgFit),
  );

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 md:px-8 md:py-12">
      <StudioNav />
      <header className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold tracking-[0.22em] text-[#C45C12] uppercase">Stability</p>
          <h1 className="mt-2 font-heading text-4xl leading-[1.1] font-semibold tracking-tight text-[#242220] md:text-5xl">
            Melting temperature
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-[#5C564E]">
            Run n = 3, 8, and 14. Melting temperature and unfolding energy (ΔG)
            come from a fit to Phillips et al. 2012 CTPRa data (DOI 10.1002/pro.2018).
            “Passes at 37 °C” means that calculated melt is above 37 °C. This is
            not a measurement on our protein.
          </p>
          <Link
            href="/stability/calculator"
            className="mt-4 inline-block text-sm font-medium text-[#C45C12] underline decoration-[#E3D9CC] underline-offset-4 hover:decoration-[#C45C12]"
          >
            Estimate ΔG at other temperatures
          </Link>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge
            className="rounded-full bg-[#242220] text-white"
            title="Calculated from a published length fit. Not measured on this fusion."
          >
            Not a lab measurement
          </Badge>
          {data?.source === "live" ? (
            <Badge variant="outline" className="border-[#266FB1] text-[#266FB1]">
              live model
            </Badge>
          ) : null}
          {data?.source === "snapshot" ? <Badge variant="outline">Saved file. API is down.</Badge> : null}
        </div>
      </header>

      <section className="mt-10 rounded-2xl border border-[#E3D9CC] bg-white p-5 md:p-8" aria-label="Inputs">
        <h2 className="font-heading text-2xl font-semibold tracking-tight text-[#242220]">Inputs</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
          Lengths are fixed at the three planned constructs. 37 °C is the comparison temperature, not a temperature from the paper.
        </p>

        {canonicalCopy ? (
          <div className="mt-8 rounded-xl border border-[#E3D9CC] bg-[#FBF8F3] p-4">
            <h3 className="text-sm font-semibold text-[#242220]">{canonicalCopy.title}</h3>
            <p className="mt-1 text-sm leading-relaxed text-[#5C564E]">{canonicalCopy.detail}</p>
            <p className="mt-2 text-sm leading-relaxed text-[#6F675C]">
              {canonicalCopy.citation}{" "}
              <a
                className="underline decoration-[#E3D9CC] underline-offset-4 hover:decoration-[#C45C12]"
                href={`https://doi.org/${canonicalCopy.doi}`}
              >
                DOI {canonicalCopy.doi}
              </a>
              .
            </p>
          </div>
        ) : null}

        <div className="mt-8 grid gap-8 border-t border-[#E3D9CC] pt-8 md:grid-cols-2">
          <div>
            <h3 className="text-sm font-semibold text-[#242220]">Repeat counts</h3>
            <ul className="mt-3 flex flex-wrap gap-2" aria-label="Lengths being confirmed (fixed, not selectable)">
              {TEAM_LENGTHS.map((n) => (
                <li
                  key={n}
                  className="rounded-full border border-[#E3D9CC] bg-[#FBF8F3] px-4 py-2.5 text-sm font-medium text-[#242220]"
                >
                  n = {n}
                </li>
              ))}
            </ul>
            <p className="mt-3 text-sm leading-relaxed text-[#5C564E]">
              These three repeat counts are fixed on this screen. They match the team&apos;s CTPR lengths and cannot be changed here.
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
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
          One row per team length: n = 3, n = 8, and n = 14.
        </p>
        {data?.note ? <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#6F675C]">{data.note}</p> : null}

        {loading ? (
          <p className="mt-8 flex items-center gap-2 text-sm text-[#8A8175]">
            <Loader2 className="animate-spin" /> Loading the calculated melting temperatures…
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

        {data && hasRows ? (
          <div className="mt-6 space-y-6">
            {fit ? (
              <div className="rounded-2xl border border-[#E3D9CC] bg-[#FBF8F3] p-5 md:p-8">
                <div className="grid gap-4 md:grid-cols-2">
                  <FitSummary fit={fit.tm} title="Calculated melt" />
                  <FitSummary
                    fit={fit.delta_g}
                    title="Calculated ΔG"
                    omitCoefficients={hideSaturatingDeltaG}
                  />
                </div>
              </div>
            ) : null}
            <div className="grid gap-4 md:grid-cols-3">
              {views.map((view) => (
                <LengthCard key={view.nRepeats} view={view} />
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
