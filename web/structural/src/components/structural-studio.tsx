"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Check,
  Download,
  Loader2,
  Printer,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Toggle } from "@/components/ui/toggle";
import { StudioNav } from "@/components/studio-nav";

const ScrewView = dynamic(() => import("@/components/screw-view").then((mod) => mod.ScrewView), {
  ssr: false,
  loading: () => (
    <div className="flex h-[560px] items-center justify-center rounded-xl bg-[#1c1a18] text-sm text-[#E7E0D6]">
      Placing the screw…
    </div>
  ),
});
import {
  fetchPrediction,
  fmt,
  type ConstructRow,
  type PredictResponse,
} from "@/lib/sa";

const PRESET = [3, 8, 14];

function ConstructStrip({ labels }: { labels: string[] }) {
  return (
    <ol className="flex flex-wrap items-center gap-1.5">
      {labels.map((label, index) => (
        <li key={`${label}-${index}`} className="flex items-center gap-1.5">
          <span
            className={
              label === "CTPR"
                ? "rounded-full bg-[#FF8000] px-3 py-1 text-xs font-semibold text-white"
                : "rounded-full bg-[#EBE4D9] px-3 py-1 text-xs font-medium text-[#242220]"
            }
          >
            {label === "CTPR" ? "CTPR(n)" : label}
          </span>
          {index < labels.length - 1 ? (
            <span className="text-[#C4B8A8]" aria-hidden>
              —
            </span>
          ) : null}
        </li>
      ))}
    </ol>
  );
}

function Metric({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-[#E3D9CC] bg-white/70 px-4 py-3">
      <p className="text-[11px] tracking-[0.14em] text-[#8A8175] uppercase">
        {label}
      </p>
      <p className="mt-1 font-heading text-xl text-[#242220]">{value}</p>
      {hint ? <p className="mt-1 text-xs text-[#6F675C]">{hint}</p> : null}
    </div>
  );
}

function from0(row: ConstructRow) {
  return row.pairs.filter((pair) => pair.i === 0);
}

export function StructuralStudio() {
  const [selectedN, setSelectedN] = useState<number[]>(PRESET);
  const [custom, setCustom] = useState("20");
  const [wiki, setWiki] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PredictResponse | null>(null);
  const [focus, setFocus] = useState<number>(8);
  const [site, setSite] = useState<number | null>(0);

  const construct = data?.constructs.find((row) => row.n_repeats === focus) ?? data?.constructs[0];
  const scene = data?.scenes.find((row) => row.n_repeats === (construct?.n_repeats ?? -1)) ?? null;
  const reading = data?.readings.find((row) => row.n_repeats === (construct?.n_repeats ?? -1));

  const nOptions = useMemo(() => {
    const set = new Set(selectedN);
    return Array.from(set).sort((a, b) => a - b);
  }, [selectedN]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    fetchPrediction(PRESET)
      .then((payload) => {
        if (!alive) return;
        setData(payload);
        setFocus(8);
        const row = payload.constructs.find((item) => item.n_repeats === 8);
        setSite(row?.m13_graft?.repeat_index ?? 0);
      })
      .catch((err: unknown) => {
        if (!alive) return;
        setError(err instanceof Error ? err.message : "Prediction failed.");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchPrediction(nOptions.length ? nOptions : PRESET);
      setData(payload);
      const nextFocus = payload.constructs.some((row) => row.n_repeats === focus)
        ? focus
        : payload.constructs[0].n_repeats;
      setFocus(nextFocus);
      const focused = payload.constructs.find((row) => row.n_repeats === nextFocus);
      setSite(focused?.m13_graft?.repeat_index ?? 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed.");
    } finally {
      setLoading(false);
    }
  }

  function toggleN(n: number) {
    setSelectedN((current) =>
      current.includes(n) ? current.filter((item) => item !== n) : [...current, n].sort((a, b) => a - b)
    );
  }

  function addCustom() {
    const n = Number.parseInt(custom, 10);
    if (!Number.isInteger(n) || n < 3 || n > 24) {
      setError("Custom n must be an integer from 3 to 24.");
      return;
    }
    setError(null);
    setSelectedN((current) => (current.includes(n) ? current : [...current, n].sort((a, b) => a - b)));
  }

  function downloadJson() {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `origami-sa-${nOptions.join("-")}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className={wiki ? "wiki-figure mx-auto max-w-6xl px-4 py-8" : "mx-auto max-w-6xl px-4 py-8 md:px-8"}>
      <StudioNav />
      <header className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold tracking-[0.22em] text-[#C45C12] uppercase">
            Hong Kong team · ISEF 2026 · ORIGAMI
          </p>
          <h1 className="mt-2 font-heading text-4xl leading-[1.1] text-[#242220] md:text-5xl">
            CTPR screw
          </h1>
          <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-[#5C564E]">
            Run a repeat count from 3 to 24. You get the backbone shape and the
            distances on it. Source: published CTPR crystals PDB 2AVP, 2HYZ, and
            2FO7. This is not a structure of the full fusion, and not a lab measurement.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant="secondary"
            className="rounded-full bg-[#242220] text-white"
            title="Distances come from published CTPR crystals, not from a measurement of this fusion."
          >
            Not a lab measurement
          </Badge>
          {data?.source === "snapshot" ? (
            <Badge variant="outline">Saved file. API is down. n = 8 graft may be the old repeat.</Badge>
          ) : null}
          {data?.source === "live" ? (
            <Badge variant="outline" className="border-[#266FB1] text-[#266FB1]">
              live model
            </Badge>
          ) : null}
        </div>
      </header>

      <section className="mt-6" id="screw-model">
        {!data && !loading ? (
          <div className="flex h-[520px] items-center justify-center rounded-2xl border border-dashed border-[#D9CFC2] bg-[#1c1a18] text-center text-sm text-[#E7E0D6]">
            Run the backbone model to place the CTPR screw.
          </div>
        ) : null}
        {loading && !data ? (
          <div className="flex h-[520px] items-center justify-center rounded-2xl bg-[#1c1a18] text-sm text-[#E7E0D6]">
            Placing the deposited screw…
          </div>
        ) : null}
        {data && construct ? (
          <Card className="border-[#E3D9CC] bg-white shadow-none">
            <CardHeader className="flex-row items-center justify-between gap-3">
              <CardTitle className="font-heading text-2xl">
                CTPR{construct.n_repeats} screw
              </CardTitle>
              <div className="flex flex-wrap items-center gap-2">
                {data.constructs.map((row) => (
                  <Toggle
                    key={row.n_repeats}
                    pressed={focus === row.n_repeats}
                    onPressedChange={() => {
                      setFocus(row.n_repeats);
                      setSite(row.m13_graft?.repeat_index ?? 0);
                    }}
                    className="rounded-full data-[state=on]:bg-[#242220] data-[state=on]:text-white"
                  >
                    n={row.n_repeats}
                  </Toggle>
                ))}
                <span className="text-xs text-[#8A8175]">{construct.ca_count} Cα · drag to orbit</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <ScrewView scene={scene} selected={site} />
              <p className="text-xs text-[#6F675C]">
                Pale tube: Cα trace. Blue sphere: SpyCatcher-side end. Orange sphere: m13 graft. Brown sphere: C-end. The model rotates on its own. Drag to orbit, scroll to zoom.
              </p>
            </CardContent>
          </Card>
        ) : null}
      </section>

      <Card className="mt-8 border-[#E3D9CC] bg-[#FBF8F3]/80 shadow-none">
        <CardContent className="space-y-4 pt-6">
          <p className="text-[11px] tracking-[0.16em] text-[#8A8175] uppercase">
            Architecture, N to C
          </p>
          <ConstructStrip labels={data?.n_to_c ?? ["FL", "rigid_spacer", "rigid_spacer", "FL", "SpyCatcher", "CTPR", "flx", "flx", "flx", "LgBiT"]} />
          <p className="text-sm text-[#6F675C]">
            Only the orange CTPR block is in this model. SpyCatcher, the three
            flexible linkers, and LgBiT are labels. The M13 peptide sits on
            repeat 2 of n = 3, repeat 4 of n = 8, and repeat 7 of n = 14.
          </p>
        </CardContent>
      </Card>

      <section className="mt-6 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-[#E3D9CC] bg-white/80 shadow-none">
          <CardHeader>
            <CardTitle className="font-heading text-2xl">Run a backbone prediction</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-[#6F675C]">
              Choose the repeat counts to measure. Team lengths 3, 8, and 14 are
              selected. Add any other n in 3–24 if you need it for a figure.
            </p>
            <div className="flex flex-wrap gap-2">
              {PRESET.map((n) => (
                <Toggle
                  key={n}
                  pressed={selectedN.includes(n)}
                  onPressedChange={() => toggleN(n)}
                  className="h-11 min-w-14 rounded-full border border-[#E3D9CC] data-[state=on]:border-[#FF8000] data-[state=on]:bg-[#FF8000] data-[state=on]:text-white"
                >
                  n={n}
                </Toggle>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Input
                value={custom}
                onChange={(event) => setCustom(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    addCustom();
                  }
                }}
                aria-label="Custom repeat count"
                className="w-24 bg-white"
              />
              <Button variant="outline" type="button" onClick={addCustom}>
                Add repeat count
              </Button>
              <span className="text-sm text-[#8A8175]">
                measuring {nOptions.length ? nOptions.join(", ") : "nothing"}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button type="button" onClick={run} disabled={loading || nOptions.length === 0} size="lg">
                {loading ? <Loader2 className="animate-spin" /> : <Check />}
                Run structural analysis
              </Button>
              <Button variant="outline" type="button" onClick={downloadJson} disabled={!data}>
                <Download /> Download JSON
              </Button>
              <Button variant="ghost" type="button" onClick={() => setWiki((value) => !value)} aria-pressed={wiki}>
                <Printer /> {wiki ? "Switch to edit layout" : "Switch to wiki figure layout"}
              </Button>
            </div>
            {error ? (
              <p className="flex items-start gap-2 text-sm text-[#9B2C2C]">
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                {error}
              </p>
            ) : null}
          </CardContent>
        </Card>
        <Card className="border-[#E3D9CC] bg-white/80 shadow-none">
          <CardHeader>
            <CardTitle className="font-heading text-2xl">What this predicts</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-relaxed text-[#5C564E]">
            <p>Length along the repeats, straight-line distance between two repeats, how far the helix bows off the axis, and whether the ends face the same way.</p>
            <p>Clash, local concentration, and luminescence are on other pages. They need radii or concentrations this page does not use.</p>
            <p>The 95% band is the spread among the published crystal structures. It is not a lab error bar.</p>
          </CardContent>
        </Card>
      </section>

      {data && construct ? (
        <div className="mt-8 space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Metric label="End chord" value={`${fmt(construct.end_junction.chord_A)} Å`} hint={`${fmt(construct.end_junction.chord_95_low_A, 1)}–${fmt(construct.end_junction.chord_95_high_A, 1)} Å 95% band`} />
              <Metric label="Axial span" value={`${fmt(construct.axial_span_A)} Å`} hint={`${fmt(construct.end_junction.phase_deg, 1)}° screw phase, repeat 0 to ${construct.n_repeats - 1}`} />
              <Metric label="Length along repeats" value={`${fmt(construct.contour_nm, 3)} nm`} hint="Sum of the repeat steps. Not the straight-line end distance." />
              <Metric label="Facing" value={fmt(construct.end_junction.facing_cosine, 3)} hint="1 = ends face the same way. −1 = opposite." />
              {construct.m13_graft ? (
                <Metric
                  label={`m13 repeat ${construct.m13_graft.repeat_1based}`}
                  value={`${fmt(construct.m13_graft.to_n_end.chord_A)} Å to N`}
                  hint={`${fmt(construct.m13_graft.to_c_end.chord_A)} Å to C · index ${construct.m13_graft.repeat_index}`}
                />
              ) : null}
            </div>

          <div className="grid gap-3 md:grid-cols-4">
            <Metric label="Rise" value={`${fmt(Number(data.screw.rise_A), 3)} Å`} />
            <Metric label="Twist" value={`${fmt(Number(data.screw.twist_deg), 1)}°`} />
            <Metric label="Pitch" value={`${fmt(Number(data.screw.pitch_A), 3)} Å`} />
            <Metric label="Junction radius" value={`${fmt(Number(data.screw.junction_radius_A), 3)} Å`} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="border-[#E3D9CC] bg-white shadow-none">
              <CardHeader>
                <CardTitle className="font-heading text-2xl">Inputs for n = {construct.n_repeats}</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-3 text-sm leading-relaxed text-[#3F3A34]">
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-[#8A8175] uppercase">CTPR repeat number</dt>
                    <dd>{construct.n_repeats}</dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-[#8A8175] uppercase">Docking-site positions</dt>
                    <dd>Repeats 0 through {construct.n_repeats - 1}. Index 0 is the SpyCatcher side.</dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-[#8A8175] uppercase">Scaffold orientation</dt>
                    <dd>
                      {fmt(Number(data.screw.twist_deg), 1)}° per repeat. End screw phase {fmt(construct.end_junction.phase_deg, 1)}°. Facing cosine {fmt(construct.end_junction.facing_cosine, 3)}.
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-[#8A8175] uppercase">Fusion termini</dt>
                    <dd>{data.n_to_c.join(" — ")}. SpyCatcher is on the N-side of the CTPR. LgBiT follows flx ×3 on the C-side.</dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-[#8A8175] uppercase">Linker length and type</dt>
                    <dd>
                      (GGGGS)₃. RMS {reading ? fmt(reading.reach.linker_rms_A, 2) : "—"} Å. Comparison window {reading ? fmt(reading.reach.comparison_window_A, 2) : "—"} Å, twice that RMS.
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-[#8A8175] uppercase">Functional-site location</dt>
                    <dd>
                      {construct.m13_graft
                        ? `m13 graft on repeat ${construct.m13_graft.repeat_1based} of ${construct.n_repeats} (index ${construct.m13_graft.repeat_index}).`
                        : "No graft was named for this n."}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-[#8A8175] uppercase">Sensor and reporter arrangement</dt>
                    <dd>SpyCatcher abuts the N-end junction. LgBiT is after three flexible linkers off the C-end. Those parts have no lengths in this screw.</dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-[#8A8175] uppercase">Payload dimensions</dt>
                    <dd>Omitted. A radius is a docking input, not a structural measurement.</dd>
                  </div>
                </dl>
              </CardContent>
            </Card>
            <Card className="border-[#E3D9CC] bg-white shadow-none">
              <CardHeader>
                <CardTitle className="font-heading text-2xl">Outputs for n = {construct.n_repeats}</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-3 text-sm leading-relaxed text-[#3F3A34]">
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-[#8A8175] uppercase">3D scaffold coordinates</dt>
                    <dd>{construct.ca_count} Cα atoms and {construct.n_repeats} docking sites, in ångströms. The orbit view above is those coordinates.</dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-[#8A8175] uppercase">Distance between docking sites</dt>
                    <dd>
                      End chord {fmt(construct.end_junction.chord_A)} Å. Axial span {fmt(construct.axial_span_A)} Å. Bow {fmt(construct.end_junction.chord_A - construct.axial_span_A)} Å.
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-[#8A8175] uppercase">Distance between functional site and the ends</dt>
                    <dd>
                      {construct.m13_graft
                        ? `Graft to N-end ${fmt(construct.m13_graft.to_n_end.chord_A)} Å. Graft to C-end ${fmt(construct.m13_graft.to_c_end.chord_A)} Å. Junction to junction, not SpyCatcher to LgBiT.`
                        : "Unset until a graft repeat is named."}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-[#8A8175] uppercase">Structural uncertainty</dt>
                    <dd>
                      End chord 95% {fmt(construct.end_junction.chord_95_low_A, 1)}–{fmt(construct.end_junction.chord_95_high_A, 1)} Å.
                      {construct.m13_graft
                        ? ` Graft to N ${fmt(construct.m13_graft.to_n_end.chord_95_low_A, 1)}–${fmt(construct.m13_graft.to_n_end.chord_95_high_A, 1)} Å. Graft to C ${fmt(construct.m13_graft.to_c_end.chord_95_low_A, 1)}–${fmt(construct.m13_graft.to_c_end.chord_95_high_A, 1)} Å.`
                        : ""}
                      {" "}Deposited screw scatter, not a wet-lab interval.
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-[#8A8175] uppercase">3D visualization</dt>
                    <dd>Shaded orbit view of the Cα trace and docking spheres. Distances in the tables are the measurements, in ångströms. PDB files are in data/exports/ctpr_3d.</dd>
                  </div>
                </dl>
              </CardContent>
            </Card>
          </div>

          {reading ? (
            <Card className="border-[#E3D9CC] bg-[#FFF7EF] shadow-none">
              <CardHeader>
                <CardTitle className="font-heading text-2xl">How to read n = {construct.n_repeats}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {reading.reading.map((line) => (
                  <p key={line} className="text-sm leading-relaxed text-[#3F3A34]">
                    {line}
                  </p>
                ))}
                <Separator />
                <p className="text-sm text-[#5C564E]">
                  Repeats near the N-end comparison window: {reading.reach.repeats_near_n_end.join(", ") || "none"}.
                  Near the C-end: {reading.reach.repeats_near_c_end.join(", ") || "none"}.
                  Near both: {reading.reach.repeats_near_both_ends.join(", ") || "none"}.
                </p>
              </CardContent>
            </Card>
          ) : null}

          <Tabs defaultValue="junctions">
            <TabsList className="bg-[#EBE4D9]">
              <TabsTrigger value="junctions">Junctions</TabsTrigger>
              <TabsTrigger value="pairs">Pairs from 0</TabsTrigger>
              <TabsTrigger value="deposited">Deposited steps</TabsTrigger>
              <TabsTrigger value="notes">Caption</TabsTrigger>
            </TabsList>
            <TabsContent value="junctions">
              <div className="overflow-x-auto rounded-xl border border-[#E3D9CC] bg-white">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>i</TableHead>
                      <TableHead>phase</TableHead>
                      <TableHead>face vs 0</TableHead>
                      <TableHead>x, y, z (Å)</TableHead>
                      <TableHead>RMS (Å)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {construct.repeats.map((row) => (
                      <TableRow
                        key={row.repeat_index}
                        className="cursor-pointer"
                        role="button"
                        tabIndex={0}
                        onClick={() => setSite(row.repeat_index)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            setSite(row.repeat_index);
                          }
                        }}
                        aria-label={`Highlight repeat ${row.repeat_index} in the 3D view`}
                        data-state={site === row.repeat_index ? "selected" : undefined}
                      >
                        <TableCell className="font-medium">
                          {row.repeat_index}
                          {row.m13_graft ? " · m13" : ""}
                        </TableCell>
                        <TableCell>{fmt(row.phase_mod_360_deg, 1)}°</TableCell>
                        <TableCell>{fmt(row.facing_cosine_vs_repeat_0, 3)}</TableCell>
                        <TableCell>
                          {fmt(row.x_A, 2)}, {fmt(row.y_A, 2)}, {fmt(row.z_A, 2)}
                        </TableCell>
                        <TableCell>{fmt(row.position_rms_A, 2)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>
            <TabsContent value="pairs">
              <div className="overflow-x-auto rounded-xl border border-[#E3D9CC] bg-white">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Δi</TableHead>
                      <TableHead>phase</TableHead>
                      <TableHead>facing</TableHead>
                      <TableHead>chord (Å)</TableHead>
                      <TableHead>95% (Å)</TableHead>
                      <TableHead>axial (Å)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {from0(construct).map((pair) => (
                      <TableRow key={pair.delta_i}>
                        <TableCell>{pair.delta_i}</TableCell>
                        <TableCell>{fmt(pair.phase_deg, 1)}°</TableCell>
                        <TableCell>{fmt(pair.facing_cosine, 3)}</TableCell>
                        <TableCell>{fmt(pair.chord_A, 3)}</TableCell>
                        <TableCell>
                          {fmt(pair.chord_95_low_A, 2)}–{fmt(pair.chord_95_high_A, 2)}
                        </TableCell>
                        <TableCell>{fmt(pair.axial_A, 3)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>
            <TabsContent value="deposited">
              <div className="overflow-x-auto rounded-xl border border-[#E3D9CC] bg-white">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>PDB</TableHead>
                      <TableHead>step</TableHead>
                      <TableHead>rise (Å)</TableHead>
                      <TableHead>twist (°)</TableHead>
                      <TableHead>junction R (Å)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.deposited_steps.map((step, index) => (
                      <TableRow key={`${step.pdb_id}-${index}`}>
                        <TableCell>{String(step.pdb_id)}</TableCell>
                        <TableCell>{String(step.step_index)}</TableCell>
                        <TableCell>{fmt(Number(step.rise_A), 3)}</TableCell>
                        <TableCell>{fmt(Number(step.twist_deg), 2)}</TableCell>
                        <TableCell>{fmt(Number(step.junction_radius_A), 3)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>
            <TabsContent value="notes">
              <Card className="border-[#E3D9CC] bg-white shadow-none">
                <CardContent className="space-y-3 pt-6 text-sm leading-relaxed text-[#5C564E]">
                  <p>
                    <strong>Wiki caption.</strong> CTPR screw for n = {construct.n_repeats},
                    fit to published Cα coordinates in PDB 2AVP, 2HYZ, and 2FO7
                    (Kajander et al. 2007, DOI 10.1107/S0907444907024353).
                    Straight-line distance between the ends: {fmt(construct.end_junction.chord_A)} Å.
                    Not a structure of this fusion. Not a lab measurement.
                  </p>
                  {data.notes.map((note) => (
                    <p key={note}>{note}</p>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      ) : null}

      <footer className="mt-12 border-t border-[#E3D9CC] pt-6 text-xs leading-relaxed text-[#8A8175]">
        Hong Kong team · ORIGAMI ·{" "}
        <a
          className="underline decoration-[#E3D9CC] underline-offset-2 hover:decoration-[#C45C12]"
          href="https://gitlab.ISEF.org/2026/software/hong-kong-team/origami"
          rel="noopener noreferrer"
          target="_blank"
        >
          GitLab repository
        </a>
        . A green software test is not a lab result.
      </footer>
    </div>
  );
}
