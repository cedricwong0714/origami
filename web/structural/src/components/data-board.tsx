"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Copy, Download, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StudioNav } from "@/components/studio-nav";
import { fetchPrediction, fmt, type PredictResponse } from "@/lib/sa";

const N_LIST = [3, 8, 14];

function csvEscape(value: string | number): string {
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
      ]
        .map(csvEscape)
        .join(",")
    );
  }
  return lines.join("\n");
}

function captionFor(data: PredictResponse): string {
  const bits = data.constructs.map((row) => {
    return `n=${row.n_repeats}: end chord ${fmt(row.end_junction.chord_A, 1)} Å (95% ${fmt(row.end_junction.chord_95_low_A, 1)}–${fmt(row.end_junction.chord_95_high_A, 1)} Å), facing cosine ${fmt(row.end_junction.facing_cosine, 2)}`;
  });
  return [
    "Figure. Computational CTPR backbone for the Hong Kong team fusion drawing.",
    "Measured block is the CTPR screw only (SpyCatcher–CTPR–flx×3–LgBiT lengths are not included).",
    "Geometry is a Kabsch screw fit to deposited Cα of PDB 2AVP, 2HYZ, and 2FO7 (Kajander et al. 2007, DOI 10.1107/S0907444907024353).",
    bits.join(". ") + ".",
    "95% bands are deposited sample scatter, not a wet-lab interval. calibrated = false. This is not a crystal structure of the fusion.",
  ].join(" ");
}

function ChordChart({ data }: { data: PredictResponse }) {
  const width = 640;
  const height = 280;
  const pad = { l: 48, r: 16, t: 24, b: 36 };
  const max = Math.max(
    ...data.constructs.map((row) => row.end_junction.chord_95_high_A),
    1
  );
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const slot = innerW / data.constructs.length;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" role="img" aria-label="End chord comparison">
      <text x={pad.l} y={16} fill="#8A8175" fontSize="11">
        End chord (Å), 95% band
      </text>
      {[0, 0.5, 1].map((frac) => {
        const y = pad.t + innerH * (1 - frac);
        return (
          <g key={frac}>
            <line x1={pad.l} x2={width - pad.r} y1={y} y2={y} stroke="#E3D9CC" />
            <text x={8} y={y + 4} fill="#8A8175" fontSize="11">
              {Math.round(max * frac)}
            </text>
          </g>
        );
      })}
      {data.constructs.map((row, index) => {
        const end = row.end_junction;
        const x = pad.l + slot * index + slot / 2;
        const yChord = pad.t + innerH * (1 - end.chord_A / max);
        const yLow = pad.t + innerH * (1 - end.chord_95_low_A / max);
        const yHigh = pad.t + innerH * (1 - end.chord_95_high_A / max);
        const yAxial = pad.t + innerH * (1 - row.axial_span_A / max);
        return (
          <g key={row.n_repeats}>
            <line x1={x} x2={x} y1={yHigh} y2={yLow} stroke="#266FB1" strokeWidth="2" />
            <line x1={x - 8} x2={x + 8} y1={yHigh} y2={yHigh} stroke="#266FB1" strokeWidth="2" />
            <line x1={x - 8} x2={x + 8} y1={yLow} y2={yLow} stroke="#266FB1" strokeWidth="2" />
            <circle cx={x} cy={yChord} r="6" fill="#FF8000" />
            <circle cx={x + 16} cy={yAxial} r="4" fill="#242220" />
            <text x={x} y={height - 12} textAnchor="middle" fill="#242220" fontSize="13">
              n={row.n_repeats}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function DataBoard() {
  const [data, setData] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let alive = true;
    fetchPrediction(N_LIST)
      .then((payload) => {
        if (alive) setData(payload);
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
  }, []);

  const caption = useMemo(() => (data ? captionFor(data) : ""), [data]);

  function download() {
    if (!data) return;
    const blob = new Blob([comparisonCsv(data)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "origami-backbone-n3-8-14.csv";
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
          <p className="text-[11px] font-semibold tracking-[0.22em] text-[#C45C12] uppercase">
            Data presentation · backbone only
          </p>
          <h1 className="mt-2 font-heading text-4xl text-[#242220] md:text-5xl">
            n = 3, 8, 14
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-[#5C564E]">
            The numbers the chassis already computed. Orange points are end chords.
            Black points are axial span. Blue whiskers are the 95% chord band.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge className="rounded-full bg-[#242220] text-white">calibrated = false</Badge>
          {data?.source === "live" ? <Badge variant="outline">live chassis</Badge> : null}
          {data?.source === "snapshot" ? <Badge variant="outline">wiki snapshot</Badge> : null}
        </div>
      </header>

      {loading ? (
        <p className="mt-10 flex items-center gap-2 text-sm text-[#8A8175]">
          <Loader2 className="animate-spin" /> Loading measurements…
        </p>
      ) : null}
      {error ? (
        <p className="mt-10 flex items-start gap-2 text-sm text-[#9B2C2C]">
          <AlertCircle className="mt-0.5 size-4" /> {error}
        </p>
      ) : null}

      {data ? (
        <div className="mt-8 space-y-6">
          <Card className="border-[#E3D9CC] bg-white shadow-none">
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="font-heading text-2xl">End separation</CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" onClick={download}>
                  <Download /> CSV
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <ChordChart data={data} />
              <p className="mt-2 text-xs text-[#8A8175]">
                Orange: straight-line junction chord. Black: axial span. The gap between them is the helical bow.
              </p>
            </CardContent>
          </Card>

          <div className="overflow-x-auto rounded-xl border border-[#E3D9CC] bg-white">
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
                <Card key={row.n_repeats} className="border-[#E3D9CC] bg-[#FFF7EF] shadow-none">
                  <CardHeader>
                    <CardTitle className="font-heading text-2xl">n = {row.n_repeats}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm leading-relaxed text-[#3F3A34]">
                    {(reading?.reading ?? []).slice(0, 3).map((line) => (
                      <p key={line}>{line}</p>
                    ))}
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <Card className="border-[#E3D9CC] bg-white shadow-none">
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="font-heading text-2xl">Wiki caption</CardTitle>
              <Button variant="outline" onClick={copyCaption}>
                <Copy /> {copied ? "Copied" : "Copy"}
              </Button>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed text-[#5C564E]">{caption}</p>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
