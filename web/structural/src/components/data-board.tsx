"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Copy, Download, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StudioNav } from "@/components/studio-nav";
import { PageGuide } from "@/components/page-guide";
import { fetchPrediction, fmt, type PredictResponse } from "@/lib/sa";

const DEFAULT_LENGTHS = [3, 8, 14];

function csvEscape(value: string | number | boolean): string {
  const text = String(value);
  return text.includes(",") ? `"${text}"` : text;
}

function comparisonCsv(data: PredictResponse): string {
  const header = [
    "n",
    "rigid",
    "contour_nm",
    "wlc_rms_nm",
    "axial_A",
    "end_chord_A",
    "chord_95_low_A",
    "chord_95_high_A",
    "end_phase_deg",
    "facing_cosine",
    "bow_A",
    "near_both",
    "m13_repeat_1based",
    "m13_index",
    "graft_to_n_A",
    "graft_to_c_A",
  ];
  const lines = [header.join(",")];
  for (const row of data.constructs) {
    const reading = data.readings.find((item) => item.n_repeats === row.n_repeats);
    const bow = row.end_junction.chord_A - row.axial_span_A;
    lines.push(
      [
        row.n_repeats,
        row.rigid_screw,
        row.contour_nm,
        row.wlc_end_to_end_rms_nm,
        row.axial_span_A,
        row.end_junction.chord_A,
        row.end_junction.chord_95_low_A,
        row.end_junction.chord_95_high_A,
        row.end_junction.phase_deg,
        row.end_junction.facing_cosine,
        bow,
        reading?.reach.repeats_near_both_ends.join(" ") || "",
        row.m13_graft?.repeat_1based ?? "",
        row.m13_graft?.repeat_index ?? "",
        row.m13_graft?.to_n_end.chord_A ?? "",
        row.m13_graft?.to_c_end.chord_A ?? "",
      ]
        .map(csvEscape)
        .join(",")
    );
  }
  return lines.join("\n");
}

function captionFor(data: PredictResponse): string {
  const bits = data.constructs.map((row) => {
    return `n=${row.n_repeats}: straight-line end distance ${fmt(row.end_junction.chord_A, 1)} Å (95% ${fmt(row.end_junction.chord_95_low_A, 1)}–${fmt(row.end_junction.chord_95_high_A, 1)} Å), facing ${fmt(row.end_junction.facing_cosine, 2)} (1 = same way, −1 = opposite)`;
  });
  return [
    "Figure. End-to-end distances on the CTPR screw for the lengths you selected. SpyCatcher, linkers, and LgBiT are outside these chord numbers.",
    "Fit to published Cα coordinates in PDB 2AVP, 2HYZ, and 2FO7 (Kajander et al. 2007, DOI 10.1107/S0907444907024353).",
    bits.join(". ") + ".",
    "The shaded band is the spread among those crystal structures. It is not a fold of our fusion construct and not wet-lab data.",
  ].join(" ");
}

const CHART_FONT = "var(--font-inter), Inter, sans-serif";

/** Nice axis whose tick labels are the gridline values, and whose ceiling covers the data. */
function axisScale(maxValue: number): { ceiling: number; step: number } {
  const padded = Math.max(maxValue, 1) * 1.06;
  const rough = padded / 4;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const fraction = rough / magnitude;
  const nice = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10;
  const step = nice * magnitude;
  const ceiling = Math.ceil((padded - 1e-9) / step) * step;
  return { ceiling, step };
}

function tickLabel(value: number): string {
  if (Math.abs(value - Math.round(value)) < 1e-6) return String(Math.round(value));
  return value.toFixed(1);
}

function ChordChart({ data }: { data: PredictResponse }) {
  const width = 640;
  const height = 320;
  const pad = { l: 52, r: 16, t: 36, b: 56 };
  const maxValue = Math.max(
    ...data.constructs.flatMap((row) => [
      row.end_junction.chord_95_high_A,
      row.end_junction.chord_A,
      row.axial_span_A,
    ]),
    1
  );
  const { ceiling, step } = axisScale(maxValue);
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const slot = innerW / data.constructs.length;
  const yOf = (value: number) => pad.t + innerH * (1 - value / ceiling);
  const baseline = yOf(0);
  const ticks: number[] = [];
  for (let value = 0; value <= ceiling + 1e-9; value += step) ticks.push(value);
  const summary = data.constructs
    .map(
      (row) =>
        `n=${row.n_repeats}: axial ${row.axial_span_A.toFixed(2)} Å, chord ${row.end_junction.chord_A.toFixed(2)} Å, 95% ${row.end_junction.chord_95_low_A.toFixed(2)}–${row.end_junction.chord_95_high_A.toFixed(2)} Å`
    )
    .join("; ");
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-auto w-full"
      role="img"
      aria-label={`End separation in angstroms. ${summary}`}
      style={{ fontFamily: CHART_FONT }}
    >
      <text x={pad.l} y={16} fill="var(--studio-chart-label)" fontSize="11" fontFamily={CHART_FONT}>
        Å, same scale for axial span and end chord
      </text>
      {ticks.map((value) => {
        const y = yOf(value);
        return (
          <g key={value}>
            <line x1={pad.l} x2={width - pad.r} y1={y} y2={y} stroke="var(--studio-chart-grid)" />
            <text x={8} y={y + 4} fill="var(--studio-chart-label)" fontSize="11" fontFamily={CHART_FONT}>
              {tickLabel(value)}
            </text>
          </g>
        );
      })}
      {data.constructs.map((row, index) => {
        const end = row.end_junction;
        const center = pad.l + slot * index + slot / 2;
        const barW = Math.min(slot * 0.28, 36);
        const gap = 8;
        const axialX = center - gap / 2 - barW;
        const chordX = center + gap / 2;
        const yAxial = yOf(row.axial_span_A);
        const yChord = yOf(end.chord_A);
        const yLow = yOf(end.chord_95_low_A);
        const yHigh = yOf(end.chord_95_high_A);
        const whiskerX = chordX + barW / 2;
        return (
          <g key={row.n_repeats}>
            <rect x={axialX} y={yAxial} width={barW} height={baseline - yAxial} fill="var(--studio-foreground)" />
            <rect x={chordX} y={yChord} width={barW} height={baseline - yChord} fill="#FF8000" />
            <line x1={whiskerX} x2={whiskerX} y1={yHigh} y2={yLow} stroke="#266FB1" strokeWidth="2" />
            <line x1={whiskerX - 7} x2={whiskerX + 7} y1={yHigh} y2={yHigh} stroke="#266FB1" strokeWidth="2" />
            <line x1={whiskerX - 7} x2={whiskerX + 7} y1={yLow} y2={yLow} stroke="#266FB1" strokeWidth="2" />
            <text x={center} y={height - 28} textAnchor="middle" fill="var(--studio-foreground)" fontSize="13" fontFamily={CHART_FONT}>
              n={row.n_repeats}
            </text>
          </g>
        );
      })}
      <g fontFamily={CHART_FONT} fontSize="11" fill="var(--studio-muted)">
        <rect x={pad.l} y={height - 16} width={10} height={10} fill="var(--studio-foreground)" />
        <text x={pad.l + 14} y={height - 7}>
          axial span
        </text>
        <rect x={pad.l + 96} y={height - 16} width={10} height={10} fill="#FF8000" />
        <text x={pad.l + 110} y={height - 7}>
          end chord
        </text>
        <line x1={pad.l + 188} x2={pad.l + 188} y1={height - 16} y2={height - 6} stroke="#266FB1" strokeWidth="2" />
        <text x={pad.l + 196} y={height - 7}>
          95% chord band
        </text>
      </g>
    </svg>
  );
}

export function DataBoard() {
  const [lengths, setLengths] = useState<number[]>(DEFAULT_LENGTHS);
  const [draft, setDraft] = useState("10");
  const [data, setData] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const lengthKey = lengths.join(",");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    const requested = lengthKey.split(",").map((item) => Number(item));
    fetchPrediction(requested)
      .then((payload) => {
        if (!alive) return;
        if (payload.constructs.length === 0) {
          setData(null);
          setError("No screw was returned for those repeat counts.");
          return;
        }
        setData(payload);
      })
      .catch((err: unknown) => {
        if (alive) setError(err instanceof Error ? err.message : "Could not load measurements.");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [lengthKey]);

  function addLength() {
    const n = Number(draft);
    if (!Number.isInteger(n) || n < 3 || n > 24) {
      setError("Repeat count must be an integer from 3 to 24.");
      return;
    }
    setError(null);
    setLengths((current) => (current.includes(n) ? current : [...current, n].sort((a, b) => a - b)));
  }

  function removeLength(n: number) {
    setLengths((current) => (current.length === 1 ? current : current.filter((item) => item !== n)));
  }

  const caption = useMemo(() => (data ? captionFor(data) : ""), [data]);

  function download() {
    if (!data) return;
    const blob = new Blob([comparisonCsv(data)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "origami-backbone.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function copyCaption() {
    await navigator.clipboard.writeText(caption);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 md:px-8">
      <StudioNav />
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-[11px] font-semibold tracking-[0.22em] text-studio-accent uppercase">
            Structural analysis · compare lengths
          </p>
          <h1 className="mt-2 font-heading text-4xl text-studio-foreground md:text-5xl">
            How far apart are the ends?
          </h1>
          <PageGuide
            intro="This page compares end-to-end distance across scaffold lengths. Use it when you want the geometry, without the binding scores."
            steps={[
              "The chart starts with n = 3, 8, and 14.",
              "Add another count from 3 to 24, or click a chip to remove it.",
              "Read the dark bar and the orange bar for each length.",
            ]}
            read={[
              "Dark bar: distance along the screw axis.",
              "Orange bar: straight-line distance between the ends. Docking uses this as the chord.",
              "Blue whisker: the spread among the three crystal structures.",
              "A longer scaffold usually increases both bars. Check the chart instead of assuming that.",
            ]}
            rules={[
              "These distances come from published CTPR crystals.",
              "They are not a measurement of our fusion.",
            ]}
            next={[
              "If the orange bar looks short, open Docking and check clash.",
              "If you also care about folding and the reporter, open Choose a length.",
            ]}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge
            className="rounded-full bg-studio-button text-studio-button-text"
            title="Distances come from published CTPR crystals, not from a measurement of this fusion."
          >
            Not a lab measurement
          </Badge>
          {data?.source === "live" ? <Badge variant="outline">live model</Badge> : null}
          {data?.source === "snapshot" ? <Badge variant="outline">Saved file. API is down.</Badge> : null}
        </div>
      </header>

      <div className="mt-6 flex flex-wrap items-end gap-2">
        {lengths.map((n) => (
          <button
            key={n}
            type="button"
            className="rounded-full border border-studio-border bg-studio-card px-3 py-1 text-sm"
            onClick={() => removeLength(n)}
          >
            n = {n} ×
          </button>
        ))}
        <label className="text-sm">
          Add repeat count
          <input
            className="ml-2 h-9 w-20 rounded-lg border border-studio-border px-2"
            type="number"
            min={3}
            max={24}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
        </label>
        <Button type="button" onClick={addLength}>
          Add to chart
        </Button>
      </div>

      {loading ? (
        <p className="mt-10 flex items-center gap-2 text-sm text-studio-label">
          <Loader2 className="animate-spin" /> Loading measurements…
        </p>
      ) : null}
      {error ? (
        <p className="mt-10 flex items-start gap-2 text-sm text-destructive">
          <AlertCircle className="mt-0.5 size-4" /> {error}
        </p>
      ) : null}

      {data ? (
        <div className="mt-8 space-y-6">
          <Card className="border-studio-border bg-studio-card shadow-none">
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="font-heading text-2xl">End separation</CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" type="button" onClick={download}>
                  <Download /> Download CSV
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <ChordChart data={data} />
              <p className="mt-2 text-xs text-studio-label">
                Heights are in Å. Orange minus dark is the bow: how far the helix leaves a straight axis. The whisker is only on the straight-line distance.
              </p>
            </CardContent>
          </Card>

          <div className="overflow-x-auto rounded-xl border border-studio-border bg-studio-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>n</TableHead>
                  <TableHead>regime</TableHead>
                  <TableHead>contour</TableHead>
                  <TableHead>end chord</TableHead>
                  <TableHead>95% band</TableHead>
                  <TableHead>bow</TableHead>
                  <TableHead>facing</TableHead>
                  <TableHead>m13</TableHead>
                  <TableHead>graft to N / C</TableHead>
                  <TableHead>near both ends</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.constructs.map((row) => {
                  const reading = data.readings.find((item) => item.n_repeats === row.n_repeats);
                  const bow = row.end_junction.chord_A - row.axial_span_A;
                  const both = reading?.reach.repeats_near_both_ends ?? [];
                  return (
                    <TableRow key={row.n_repeats}>
                      <TableCell className="font-medium">{row.n_repeats}</TableCell>
                      <TableCell>{row.rigid_screw ? "rigid screw" : "past 15 nm cutoff"}</TableCell>
                      <TableCell>{fmt(row.contour_nm, 3)} nm</TableCell>
                      <TableCell>{fmt(row.end_junction.chord_A, 2)} Å</TableCell>
                      <TableCell>
                        {fmt(row.end_junction.chord_95_low_A, 1)}–{fmt(row.end_junction.chord_95_high_A, 1)}
                      </TableCell>
                      <TableCell>{fmt(bow, 2)} Å</TableCell>
                      <TableCell>{fmt(row.end_junction.facing_cosine, 3)}</TableCell>
                      <TableCell>
                        {row.m13_graft
                          ? `repeat ${row.m13_graft.repeat_1based} (index ${row.m13_graft.repeat_index})`
                          : "unset"}
                      </TableCell>
                      <TableCell>
                        {row.m13_graft
                          ? `${fmt(row.m13_graft.to_n_end.chord_A, 2)} / ${fmt(row.m13_graft.to_c_end.chord_A, 2)} Å`
                          : "unset"}
                      </TableCell>
                      <TableCell>{both.length ? both.join(", ") : "none"}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {data.constructs.map((row) => {
              const reading = data.readings.find((item) => item.n_repeats === row.n_repeats);
              return (
                <Card key={row.n_repeats} className="border-studio-border bg-studio-accent-soft shadow-none">
                  <CardHeader>
                    <CardTitle className="font-heading text-2xl">n = {row.n_repeats}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm leading-relaxed text-studio-foreground">
                    {(reading?.reading ?? []).slice(0, 4).map((line) => (
                      <p key={line}>{line}</p>
                    ))}
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <Card className="border-studio-border bg-studio-card shadow-none">
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="font-heading text-2xl">Wiki caption</CardTitle>
              <Button variant="outline" type="button" onClick={copyCaption}>
                <Copy /> {copied ? "Caption copied" : "Copy caption"}
              </Button>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed text-studio-muted">{caption}</p>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
