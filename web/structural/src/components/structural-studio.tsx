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
import { PageGuide } from "@/components/page-guide";

const ScrewView = dynamic(() => import("@/components/screw-view").then((mod) => mod.ScrewView), {
  ssr: false,
  loading: () => (
    <div className="flex h-[560px] items-center justify-center rounded-xl bg-studio-viewport text-sm text-studio-viewport-text">
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
                : "rounded-full bg-studio-secondary px-3 py-1 text-xs font-medium text-studio-foreground"
            }
          >
            {label === "CTPR" ? "CTPR(n)" : label}
          </span>
          {index < labels.length - 1 ? (
            <span className="text-studio-label" aria-hidden>
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
    <div className="rounded-xl border border-studio-border bg-studio-card/70 px-4 py-3">
      <p className="text-[11px] tracking-[0.14em] text-studio-label uppercase">
        {label}
      </p>
      <p className="mt-1 font-heading text-xl text-studio-foreground">{value}</p>
      {hint ? <p className="mt-1 text-xs text-studio-muted">{hint}</p> : null}
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
          <p className="text-[11px] font-semibold tracking-[0.22em] text-studio-accent uppercase">
            Hong Kong team · ISEF 2026 · ORIGAMI
          </p>
          <h1 className="mt-2 font-heading text-4xl leading-[1.1] text-studio-foreground md:text-5xl">
            Where do the two ends sit?
          </h1>
          <PageGuide
            intro="The scaffold is a protein chain made of repeating units. This page draws that chain in 3D so you can see how far the two ends are, and where we attach the M13 peptide. n is the number of repeats: n = 8 means eight units."
            steps={[
              "Start with n = 3, 8, or 14 (the lengths we plan to build), or type another count from 3 to 24.",
              "Drag the model to spin it. Scroll to zoom.",
              "Blue is the SpyCatcher end. Orange is the M13 peptide. Brown is the other end.",
            ]}
            read={[
              "The pale tube is the protein backbone from published crystal structures. It is a drawing of the scaffold, not a photo of our fusion.",
              "Read distances in the numbers under the model. Those are in ångströms (Å). The 3D view is only for looking around.",
              "SpyCatcher, the flexible linker, and LgBiT are listed on the side. They are not built into the 3D tube.",
            ]}
            rules={[
              "We attach M13 on repeat 2 when n = 3, repeat 4 when n = 8, and repeat 7 when n = 14.",
              "The shape comes from published CTPR crystals. It is a template, not a predicted structure of our full fusion.",
            ]}
            next={[
              "Compare lengths if you want those end-to-end distances as a chart.",
              "Choose a length if you also want folding, binding, and the light reporter on one page.",
            ]}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant="secondary"
            className="rounded-full bg-studio-button text-studio-button-text"
            title="Distances come from published CTPR crystals, not from a measurement of this fusion."
          >
            Calculated, not measured
          </Badge>
          {data?.source === "snapshot" ? (
            <Badge variant="outline">Using a saved file. The live calculator is down. The n = 8 peptide site may be an older position.</Badge>
          ) : null}
          {data?.source === "live" ? (
            <Badge variant="outline" className="border-studio-blue text-studio-blue">
              live calculator
            </Badge>
          ) : null}
        </div>
      </header>

      <section className="mt-6" id="screw-model">
        {!data && !loading ? (
          <div className="flex h-[520px] items-center justify-center rounded-2xl border border-dashed border-studio-border bg-studio-viewport text-center text-sm text-studio-viewport-text">
            Run the 3D model to place the scaffold.
          </div>
        ) : null}
        {loading && !data ? (
          <div className="flex h-[520px] items-center justify-center rounded-2xl bg-studio-viewport text-sm text-studio-viewport-text">
            Drawing the published scaffold…
          </div>
        ) : null}
        {data && construct ? (
          <Card className="border-studio-border bg-studio-card shadow-none">
            <CardHeader className="flex-row items-center justify-between gap-3">
              <CardTitle className="font-heading text-2xl">
                CTPR{construct.n_repeats} scaffold
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
                    className="rounded-full data-[state=on]:bg-studio-button data-[state=on]:text-studio-button-text"
                  >
                    n={row.n_repeats}
                  </Toggle>
                ))}
                <span className="text-xs text-studio-label">{construct.ca_count} backbone atoms · drag to spin</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <ScrewView scene={scene} selected={site} />
              <p className="text-xs text-studio-muted">
                Drag to spin. Scroll to zoom. Distances on the screen are not the ångström numbers in the table.
              </p>
            </CardContent>
          </Card>
        ) : null}
      </section>

      <Card className="mt-8 border-studio-border bg-studio-surface/80 shadow-none">
        <CardContent className="space-y-4 pt-6">
          <p className="text-[11px] tracking-[0.16em] text-studio-label uppercase">
            Full construct, N-end to C-end
          </p>
          <ConstructStrip labels={data?.n_to_c ?? ["FL", "rigid_spacer", "rigid_spacer", "FL", "SpyCatcher", "CTPR", "flx", "flx", "flx", "LgBiT"]} />
          <p className="text-sm text-studio-muted">
            Only the orange CTPR block is drawn in 3D. The M13 peptide sits on repeat 2 (n = 3), repeat 4 (n = 8), or repeat 7 (n = 14).
          </p>
        </CardContent>
      </Card>

      <section className="mt-6 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-studio-border bg-studio-card/80 shadow-none">
          <CardHeader>
            <CardTitle className="font-heading text-2xl">Draw a length</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-studio-muted">
              Choose how many repeats to draw. n = 3, 8, and 14 are the lengths we plan to build.
              You can add any other count from 3 to 24.
            </p>
            <div className="flex flex-wrap gap-2">
              {PRESET.map((n) => (
                <Toggle
                  key={n}
                  pressed={selectedN.includes(n)}
                  onPressedChange={() => toggleN(n)}
                  className="h-11 min-w-14 rounded-full border border-studio-border data-[state=on]:border-primary data-[state=on]:bg-primary data-[state=on]:text-white"
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
                className="w-24 bg-studio-card"
              />
              <Button variant="outline" type="button" onClick={addCustom}>
                Add repeat count
              </Button>
              <span className="text-sm text-studio-label">
                drawing {nOptions.length ? nOptions.join(", ") : "nothing"}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button type="button" onClick={run} disabled={loading || nOptions.length === 0} size="lg">
                {loading ? <Loader2 className="animate-spin" /> : <Check />}
                Draw the scaffold
              </Button>
              <Button variant="outline" type="button" onClick={downloadJson} disabled={!data}>
                <Download /> Download numbers
              </Button>
              <Button variant="ghost" type="button" onClick={() => setWiki((value) => !value)} aria-pressed={wiki}>
                <Printer /> {wiki ? "Back to the usual layout" : "Wiki-figure layout"}
              </Button>
            </div>
            {error ? (
              <p className="flex items-start gap-2 text-sm text-destructive">
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                {error}
              </p>
            ) : null}
          </CardContent>
        </Card>
        <Card className="border-studio-border bg-studio-card/80 shadow-none">
          <CardHeader>
            <CardTitle className="font-heading text-2xl">What you get here</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-relaxed text-studio-muted">
            <p>How long the chain is, the straight-line distance between the two ends, how much the helix bends, and whether the two ends point the same way.</p>
            <p>Whether the ends bump into each other, how crowded they are, and whether the reporter lights up are on other pages. Those need sizes or concentrations this page does not use.</p>
            <p>The 95% band is how much the published crystal structures disagree. It is not a lab error bar.</p>
          </CardContent>
        </Card>
      </section>

      {data && construct ? (
        <div className="mt-8 space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Metric label="Straight-line end distance" value={`${fmt(construct.end_junction.chord_A)} Å`} hint={`${fmt(construct.end_junction.chord_95_low_A, 1)}–${fmt(construct.end_junction.chord_95_high_A, 1)} Å range among crystals`} />
              <Metric label="Distance along the helix axis" value={`${fmt(construct.axial_span_A)} Å`} hint={`${fmt(construct.end_junction.phase_deg, 1)}° of turn from repeat 0 to ${construct.n_repeats - 1}`} />
              <Metric label="Path length along the chain" value={`${fmt(construct.contour_nm, 3)} nm`} hint="Walking along the repeats. Not the straight-line jump." />
              <Metric label="Do the ends point the same way?" value={fmt(construct.end_junction.facing_cosine, 3)} hint="1 = same direction. −1 = opposite." />
              {construct.m13_graft ? (
                <Metric
                  label={`M13 on repeat ${construct.m13_graft.repeat_1based}`}
                  value={`${fmt(construct.m13_graft.to_n_end.chord_A)} Å to N-end`}
                  hint={`${fmt(construct.m13_graft.to_c_end.chord_A)} Å to C-end · site index ${construct.m13_graft.repeat_index}`}
                />
              ) : null}
            </div>

          <div className="grid gap-3 md:grid-cols-4">
            <Metric label="Rise per repeat" value={`${fmt(Number(data.screw.rise_A), 3)} Å`} />
            <Metric label="Twist per repeat" value={`${fmt(Number(data.screw.twist_deg), 1)}°`} />
            <Metric label="Pitch of the helix" value={`${fmt(Number(data.screw.pitch_A), 3)} Å`} />
            <Metric label="Helix radius" value={`${fmt(Number(data.screw.junction_radius_A), 3)} Å`} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="border-studio-border bg-studio-card shadow-none">
              <CardHeader>
                <CardTitle className="font-heading text-2xl">Inputs for n = {construct.n_repeats}</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-3 text-sm leading-relaxed text-studio-foreground">
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-studio-label uppercase">How many repeats</dt>
                    <dd>{construct.n_repeats}</dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-studio-label uppercase">Sites along the chain</dt>
                    <dd>Repeats 0 through {construct.n_repeats - 1}. Index 0 is the SpyCatcher end.</dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-studio-label uppercase">How the helix turns</dt>
                    <dd>
                      {fmt(Number(data.screw.twist_deg), 1)}° of twist per repeat. Total turn from end to end {fmt(construct.end_junction.phase_deg, 1)}°. Facing score {fmt(construct.end_junction.facing_cosine, 3)} (1 = same direction, −1 = opposite).
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-studio-label uppercase">What sits at each end</dt>
                    <dd>{data.n_to_c.join(" — ")}. SpyCatcher is on the N-side of the CTPR. LgBiT sits after three flexible linkers on the C-side.</dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-studio-label uppercase">Flexible linker</dt>
                    <dd>
                      (GGGGS)₃. Typical reach {reading ? fmt(reading.reach.linker_rms_A, 2) : "—"} Å. Comparison window {reading ? fmt(reading.reach.comparison_window_A, 2) : "—"} Å (twice that reach). This is a size check, not a lab measurement of the linker.
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-studio-label uppercase">Where the M13 peptide sits</dt>
                    <dd>
                      {construct.m13_graft
                        ? `Repeat ${construct.m13_graft.repeat_1based} of ${construct.n_repeats} (index ${construct.m13_graft.repeat_index}, counting from 0 at the SpyCatcher end).`
                        : "No peptide site is named for this length."}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-studio-label uppercase">Sensor and reporter</dt>
                    <dd>
                      SpyCatcher sits on the N-side of the scaffold. LgBiT sits after (GGGGS)₃ on the C-side. Those fusion pieces are listed here but are not built into the published CTPR drawing.
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-studio-label uppercase">Protein sizes for bumping</dt>
                    <dd>Not used on this page. Sizes are an input on the binding pages, not a measurement from this drawing.</dd>
                  </div>
                </dl>
              </CardContent>
            </Card>
            <Card className="border-studio-border bg-studio-card shadow-none">
              <CardHeader>
                <CardTitle className="font-heading text-2xl">Outputs for n = {construct.n_repeats}</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-3 text-sm leading-relaxed text-studio-foreground">
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-studio-label uppercase">3D coordinates</dt>
                    <dd>{construct.ca_count} backbone atoms and {construct.n_repeats} sites, in ångströms. The spinning view above uses these coordinates.</dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-studio-label uppercase">Distance between the two ends</dt>
                    <dd>
                      Straight-line {fmt(construct.end_junction.chord_A)} Å. Along the helix axis {fmt(construct.axial_span_A)} Å. Extra length from the curve {fmt(construct.end_junction.chord_A - construct.axial_span_A)} Å.
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-studio-label uppercase">Distance from the peptide to each end</dt>
                    <dd>
                      {construct.m13_graft
                        ? `To the N-end ${fmt(construct.m13_graft.to_n_end.chord_A)} Å. To the C-end ${fmt(construct.m13_graft.to_c_end.chord_A)} Å. These are CTPR-to-CTPR distances, not SpyCatcher-to-LgBiT.`
                        : "Unset until a peptide site is named for this length."}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-studio-label uppercase">How sure the distances are</dt>
                    <dd>
                      Straight-line end distance range {fmt(construct.end_junction.chord_95_low_A, 1)}–{fmt(construct.end_junction.chord_95_high_A, 1)} Å.
                      {construct.m13_graft
                        ? ` Peptide to N-end ${fmt(construct.m13_graft.to_n_end.chord_95_low_A, 1)}–${fmt(construct.m13_graft.to_n_end.chord_95_high_A, 1)} Å. Peptide to C-end ${fmt(construct.m13_graft.to_c_end.chord_95_low_A, 1)}–${fmt(construct.m13_graft.to_c_end.chord_95_high_A, 1)} Å.`
                        : ""}
                      {" "}That range is how much the published crystals disagree, not a wet-lab interval.
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] tracking-[0.14em] text-studio-label uppercase">The 3D view</dt>
                    <dd>A drawing of the backbone and the docking spheres. Trust the tables for distances in ångströms. PDB files live in data/exports/ctpr_3d.</dd>
                  </div>
                </dl>
              </CardContent>
            </Card>
          </div>

          {reading ? (
            <Card className="border-studio-border bg-studio-accent-soft shadow-none">
              <CardHeader>
                <CardTitle className="font-heading text-2xl">How to read n = {construct.n_repeats}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {reading.reading.map((line) => (
                  <p key={line} className="text-sm leading-relaxed text-studio-foreground">
                    {line}
                  </p>
                ))}
                <Separator />
                <p className="text-sm text-studio-muted">
                  Repeats close to the N-end: {reading.reach.repeats_near_n_end.join(", ") || "none"}.
                  Close to the C-end: {reading.reach.repeats_near_c_end.join(", ") || "none"}.
                  Close to both: {reading.reach.repeats_near_both_ends.join(", ") || "none"}.
                </p>
              </CardContent>
            </Card>
          ) : null}

          <Tabs defaultValue="junctions">
            <TabsList className="bg-studio-secondary">
              <TabsTrigger value="junctions">Each repeat</TabsTrigger>
              <TabsTrigger value="pairs">Distances from the N-end</TabsTrigger>
              <TabsTrigger value="deposited">Published crystals</TabsTrigger>
              <TabsTrigger value="notes">Caption</TabsTrigger>
            </TabsList>
            <TabsContent value="junctions">
              <div className="overflow-x-auto rounded-xl border border-studio-border bg-studio-card">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>repeat</TableHead>
                      <TableHead>turn (°)</TableHead>
                      <TableHead>same direction as 0?</TableHead>
                      <TableHead>x, y, z (Å)</TableHead>
                      <TableHead>scatter (Å)</TableHead>
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
                          {row.m13_graft ? " · M13" : ""}
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
              <div className="overflow-x-auto rounded-xl border border-studio-border bg-studio-card">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>repeats apart</TableHead>
                      <TableHead>turn (°)</TableHead>
                      <TableHead>same direction?</TableHead>
                      <TableHead>straight-line (Å)</TableHead>
                      <TableHead>range (Å)</TableHead>
                      <TableHead>along axis (Å)</TableHead>
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
              <div className="overflow-x-auto rounded-xl border border-studio-border bg-studio-card">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>PDB</TableHead>
                      <TableHead>step</TableHead>
                      <TableHead>rise (Å)</TableHead>
                      <TableHead>twist (°)</TableHead>
                      <TableHead>helix radius (Å)</TableHead>
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
              <Card className="border-studio-border bg-studio-card shadow-none">
                <CardContent className="space-y-3 pt-6 text-sm leading-relaxed text-studio-muted">
                  <p>
                    <strong>Wiki caption.</strong> CTPR scaffold for n = {construct.n_repeats},
                    fit to published backbone coordinates in PDB 2AVP, 2HYZ, and 2FO7
                    (Kajander et al. 2007, DOI 10.1107/S0907444907024353).
                    Straight-line distance between the ends: {fmt(construct.end_junction.chord_A)} Å.
                    This is a template from published crystals, not a structure of our fusion and not a lab measurement.
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

      <footer className="mt-12 border-t border-studio-border pt-6 text-xs leading-relaxed text-studio-label">
        Hong Kong team · ORIGAMI ·{" "}
        <a
          className="underline decoration-studio-border underline-offset-2 hover:decoration-studio-accent"
          href="https://gitlab.ISEF.org/2026/software/hong-kong-team/origami"
          rel="noopener noreferrer"
          target="_blank"
        >
          GitLab repository
        </a>
        . A passing software test is not a lab result.
      </footer>
    </div>
  );
}
