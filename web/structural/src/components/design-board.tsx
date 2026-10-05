"use client";

import { useEffect, useState } from "react";
import { SeriesChart } from "@/components/model-chart";
import { StudioNav } from "@/components/studio-nav";
import { PageGuide } from "@/components/page-guide";

type SweepPoint = {
  n_repeats: number;
  tm_C: number | null;
  tm_interval_low: number | null;
  tm_interval_high: number | null;
  delta_g: number | null;
  thermal_state: string;
  past_longest_cited_length: boolean;
  docking_computed: boolean;
  docking_skip_reason: string | null;
  indices: number[] | null;
  chord_A: number | null;
  c_eff_M: number | null;
  p_clash: number | null;
  association_theta: number | null;
  association_holds: boolean | null;
  nanobit_theta: number | null;
  drives_lgbit_smbit: boolean;
  spy_half_life_s: number | null;
  drives_spycatcher_spytag: boolean;
  call: string;
};

type SweepReport = {
  calibrated: boolean;
  t_assay_C: number;
  kd_M: number | null;
  graft_index: number | null;
  graft_rule: string;
  ranking_rule: string;
  marked_n: number | null;
  reporter_lengths: number[];
  any_length_drives_reporter: boolean;
  points: SweepPoint[];
  note: string;
};

const CALL_COLOR: Record<string, string> = {
  reporter: "#2F6B4F",
  held_reporter_dark: "#C45C12",
  folded_not_held: "#266FB1",
  below_assay: "#9B2C2C",
  docking_skipped: "#C8BDB0",
  not_fit: "#8A8175",
};

const CALL_LABEL: Record<string, string> = {
  reporter: "Stays folded, ends stay together, reporter at least half on",
  held_reporter_dark: "Stays folded and ends stay together, but the reporter stays mostly off",
  folded_not_held: "Stays folded, but the two ends do not stay together",
  below_assay: "Predicted to unfold at 37 °C",
  docking_skipped: "Folding was scored; end-to-end binding was skipped because the peptide site does not fit",
  not_fit: "No folding prediction for this length",
};

const PLANNED = new Set([3, 8, 14]);

function sci(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return value.toExponential(3);
}

function plain(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  if (abs !== 0 && (abs >= 1000 || abs < 0.01)) return value.toExponential(3);
  return value.toFixed(digits);
}

function finitePoints(points: SweepPoint[], read: (point: SweepPoint) => number | null) {
  return points.flatMap((point) => {
    const y = read(point);
    return y === null || !Number.isFinite(y) ? [] : [{ x: point.n_repeats, y }];
  });
}

function downloadJson(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function DesignBoard() {
  const [kind, setKind] = useState<"kd" | "ka">("kd");
  const [value, setValue] = useState("0.19");
  const [unit, setUnit] = useState("nM");
  const [graft, setGraft] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<SweepReport | null>(null);
  const [selected, setSelected] = useState<number>(8);

  async function run(next?: { kind: "kd" | "ka"; value: string; unit: string; graft: string }) {
    const request = next ?? { kind, value, unit, graft };
    const parsed = Number(request.value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setError("Affinity value must be a number greater than zero.");
      return;
    }
    const body: {
      affinity: string;
      value: number;
      unit: string;
      graft_index?: number;
    } = { affinity: request.kind, value: parsed, unit: request.unit };
    if (request.graft.trim() !== "") {
      const index = Number(request.graft);
      if (!Number.isInteger(index)) {
        setError("Peptide site must be a whole number, or left blank.");
        return;
      }
      body.graft_index = index;
    }
    setRunning(true);
    setError(null);
    try {
      const res = await fetch("/api/docking/sweep", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "Length sweep failed.");
      }
      const sweep = data as SweepReport;
      setReport(sweep);
      setSelected(sweep.marked_n ?? 8);
    } catch (err: unknown) {
      setReport(null);
      setError(err instanceof Error ? err.message : "Length sweep failed.");
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    void run({ kind: "kd", value: "0.19", unit: "nM", graft: "" });
    // The first paint asks the peptide Kd already used by the bound-fraction model.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const focus = report?.points.find((point) => point.n_repeats === selected) ?? null;
  const assay = report?.t_assay_C ?? 37;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 text-studio-foreground">
      <StudioNav />
      <p className="text-[11px] font-semibold tracking-[0.22em] text-studio-accent uppercase">
        Structural analysis
      </p>
      <h1 className="mt-2 text-3xl font-semibold">Which length should the scaffold be?</h1>
      <PageGuide
        intro="The scaffold is a chain of repeating protein units. This page scores every length from 3 to 24 repeats. It asks three questions: does it stay folded at 37 °C, do the two ends stay together, and does the light reporter turn on?"
        steps={[
          "Leave Kd at 0.19 nM unless you want to test a tighter or looser sensor. Smaller Kd means tighter sticking.",
          "Leave the peptide site blank to use the usual M13 position. Type a number only if you want a fixed second site.",
          "Click Score every length.",
          "Click a colored square to read that length.",
        ]}
        read={[
          "Melting temperature is where half the protein unfolds. Above 37 °C, the model still calls it folded in a typical E. coli assay.",
          "Bound fraction is how often the two ends stay together. At 0.5 they are together half the time. We call that holding.",
          "Reporter on-fraction is how often LgBiT and SmBiT assemble at that same crowding. 0.5 is half on. Higher is brighter.",
          "Spy half-life is how long the covalent lock takes. Shorter is faster. Clash near 0 means the two proteins are unlikely to overlap.",
        ]}
        rules={[
          "Green: stays folded, ends stay together, reporter at least half on.",
          "Orange: stays folded and ends stay together, but the reporter stays mostly off.",
          "Blue: stays folded, but the two ends do not stay together.",
          "The marked length is the green square, or the orange square with the brightest reporter if none are green.",
        ]}
        next={[
          "If only n = 3 is green, longer planned constructs will not turn the reporter on at this tightness.",
          "Open Will it bind? for one length in more detail.",
          "Open Stay folded? for the melting curve on its own.",
        ]}
      />

      <section className="mt-8 rounded-2xl border border-studio-border bg-studio-card p-6">
        <p className="text-sm text-studio-muted">
          Start with the peptide Kd, 0.19 nM. Kd is how tightly CaM and M13 stick: smaller is tighter.
          Change it if you want to test a looser or tighter sensor.
          Leave the peptide site blank to use each length’s usual M13 position. Lengths without a named site use the last repeat.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          <label className="block text-sm font-medium">
            Constant
            <select
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2"
              value={kind}
              onChange={(event) => setKind(event.target.value === "ka" ? "ka" : "kd")}
            >
              <option value="kd">Kd (smaller = tighter)</option>
              <option value="ka">Ka (larger = tighter)</option>
            </select>
          </label>
          <label className="block text-sm font-medium">
            Value
            <input
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2 font-mono"
              value={value}
              onChange={(event) => setValue(event.target.value)}
            />
          </label>
          <label className="block text-sm font-medium">
            Unit
            <select
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2"
              value={unit}
              onChange={(event) => setUnit(event.target.value)}
            >
              {["M", "mM", "uM", "nM", "pM"].map((item) => (
                <option key={item} value={item}>
                  {kind === "ka" ? `per ${item}` : item}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-medium">
            Peptide site
            <input
              className="mt-1 w-full rounded-lg border border-studio-border px-3 py-2 font-mono"
              value={graft}
              placeholder="blank = usual site"
              onChange={(event) => setGraft(event.target.value)}
            />
          </label>
        </div>
        <button
          type="button"
          className="mt-5 rounded-full bg-studio-button px-5 py-2 text-sm text-studio-button-text disabled:opacity-50"
          onClick={() => void run()}
          disabled={running}
        >
          {running ? "Scoring lengths…" : "Score every length"}
        </button>
        {error ? <p className="mt-4 text-sm text-destructive">{error}</p> : null}
      </section>

      {report ? (
        <>
          <section className="mt-6 rounded-2xl border border-studio-border bg-studio-card p-6">
            <h2 className="text-lg font-medium">
              {report.marked_n === null
                ? "No length both stays folded and keeps the ends together"
                : `Best length on this page: n = ${report.marked_n}`}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-studio-muted">{report.ranking_rule}</p>
            <p className="mt-2 text-sm leading-relaxed text-studio-muted">
              {report.any_length_drives_reporter
                ? `The light reporter is at least half on at n = ${report.reporter_lengths.join(", ")}.`
                : "No length in this sweep puts the light reporter at or above half on. The mark, when present, is only the highest reporter score among lengths that fold and hold."}
            </p>
            <p className="mt-2 text-sm text-studio-muted">{report.graft_rule}</p>
            <div className="mt-5 flex flex-wrap gap-1" aria-label="Length calls">
              {report.points.map((point) => {
                const on = point.n_repeats === selected;
                return (
                  <button
                    key={point.n_repeats}
                    type="button"
                    aria-pressed={on}
                    aria-label={`n = ${point.n_repeats}. ${CALL_LABEL[point.call] ?? point.call}`}
                    className="h-10 w-10 rounded-md text-xs text-white"
                    style={{
                      background: CALL_COLOR[point.call] ?? "#8A8175",
                      outline: on ? "2px solid var(--studio-foreground)" : "none",
                      outlineOffset: 2,
                    }}
                    onClick={() => setSelected(point.n_repeats)}
                  >
                    {point.n_repeats}
                  </button>
                );
              })}
            </div>
            <ul className="mt-4 grid gap-1 text-xs text-studio-muted sm:grid-cols-2">
              {Object.entries(CALL_LABEL).map(([key, label]) => (
                <li key={key} className="flex items-center gap-2">
                  <span
                    className="inline-block h-3 w-3 rounded-sm"
                    style={{ background: CALL_COLOR[key] }}
                  />
                  {label}
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-studio-label">
              Planned build lengths are 3, 8, and 14. Click a square to read that length.
            </p>
          </section>

          {focus ? (
            <section className="mt-6 rounded-2xl border border-studio-border bg-studio-card p-6">
              <h2 className="text-lg font-medium">
                n = {focus.n_repeats}
                {PLANNED.has(focus.n_repeats) ? " · planned build" : ""}
                {report.marked_n === focus.n_repeats ? " · marked as best on this page" : ""}
              </h2>
              <p className="mt-2 text-sm text-studio-muted">{CALL_LABEL[focus.call] ?? focus.call}</p>
              {focus.past_longest_cited_length ? (
                <p className="mt-2 text-sm text-studio-muted">
                  This length is longer than the longest melt in the paper. The melting temperature is the same fit, read outside that range.
                </p>
              ) : null}
              {focus.docking_skip_reason ? (
                <p className="mt-2 text-sm text-studio-muted">{focus.docking_skip_reason}</p>
              ) : null}
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-studio-label">Melting temperature</dt>
                  <dd className="font-mono">{plain(focus.tm_C)} °C</dd>
                </div>
                <div>
                  <dt className="text-studio-label">Unfolding energy at 10 °C</dt>
                  <dd className="font-mono">{plain(focus.delta_g)} kcal/mol</dd>
                </div>
                <div>
                  <dt className="text-studio-label">How often the ends stay together</dt>
                  <dd className="font-mono">
                    {plain(focus.association_theta, 3)}{" "}
                    {focus.association_holds === null
                      ? ""
                      : focus.association_holds
                        ? "holds"
                        : "does not hold"}
                  </dd>
                </div>
                <div>
                  <dt className="text-studio-label">How crowded the two ends are</dt>
                  <dd className="font-mono">{sci(focus.c_eff_M)} M</dd>
                </div>
                <div>
                  <dt className="text-studio-label">Light reporter on-fraction</dt>
                  <dd className="font-mono">
                    {sci(focus.nanobit_theta)}{" "}
                    {focus.drives_lgbit_smbit ? "at or above half on" : "below half on"}
                  </dd>
                </div>
                <div>
                  <dt className="text-studio-label">Spy lock half-life</dt>
                  <dd className="font-mono">{sci(focus.spy_half_life_s)} s</dd>
                </div>
                <div>
                  <dt className="text-studio-label">Chance the two proteins overlap</dt>
                  <dd className="font-mono">{plain(focus.p_clash, 3)}</dd>
                </div>
                <div>
                  <dt className="text-studio-label">Straight-line end distance</dt>
                  <dd className="font-mono">{focus.chord_A === null ? "—" : `${focus.chord_A.toFixed(2)} Å`}</dd>
                </div>
              </dl>
            </section>
          ) : null}

          <section className="mt-6 space-y-6 rounded-2xl border border-studio-border bg-studio-card p-6">
            <div>
              <h2 className="text-lg font-medium">Melting temperature</h2>
              <p className="mt-1 text-sm text-studio-muted">
                Dashed line: 37 °C. Above it, the model still calls the protein folded.
              </p>
              <SeriesChart
                label="Melting temperature versus repeat count"
                xLabel="Repeat count"
                yLabel="Tm (°C)"
                guideY={{ y: assay, label: `${assay} °C` }}
                markerX={selected}
                series={[
                  {
                    color: "#C8BDB0",
                    points: finitePoints(report.points, (point) => point.tm_interval_low),
                  },
                  {
                    color: "#C8BDB0",
                    points: finitePoints(report.points, (point) => point.tm_interval_high),
                  },
                  {
                    color: "#C45C12",
                    width: 2.5,
                    points: finitePoints(report.points, (point) => point.tm_C),
                  },
                ]}
              />
            </div>
            <div>
              <h2 className="text-lg font-medium">Do the two ends stay together?</h2>
              <p className="mt-1 text-sm text-studio-muted">
                Dashed line: half bound. At or above it, your Kd holds the two ends together.
              </p>
              <SeriesChart
                label="Association bound fraction versus repeat count"
                xLabel="Repeat count"
                yLabel="Bound fraction"
                guideY={{ y: 0.5, label: "1/2" }}
                markerX={selected}
                series={[
                  {
                    color: "var(--studio-foreground)",
                    points: finitePoints(report.points, (point) => point.association_theta),
                  },
                ]}
              />
            </div>
            <div>
              <h2 className="text-lg font-medium">Does the light reporter turn on?</h2>
              <p className="mt-1 text-sm text-studio-muted">
                Dashed line: half on. A line along the bottom means the reporter stays dark.
              </p>
              <SeriesChart
                label="Light reporter on-fraction versus repeat count"
                xLabel="Repeat count"
                yLabel="Occupancy"
                guideY={{ y: 0.5, label: "1/2" }}
                markerX={selected}
                series={[
                  {
                    color: "#266FB1",
                    points: finitePoints(report.points, (point) => point.nanobit_theta),
                  },
                ]}
              />
            </div>
            <div>
              <h2 className="text-lg font-medium">Spy lock half-life</h2>
              <p className="mt-1 text-sm text-studio-muted">
                Time for half of the Spy pairs to lock. The axis is log scale. Shorter means faster.
              </p>
              <SeriesChart
                label="SpyCatcher–SpyTag half-life versus repeat count"
                xLabel="Repeat count"
                yLabel="Half-life (s)"
                yLog
                markerX={selected}
                series={[
                  {
                    color: "#2F6B4F",
                    points: finitePoints(report.points, (point) => point.spy_half_life_s),
                  },
                ]}
              />
            </div>
            <div>
              <h2 className="text-lg font-medium">Do the two proteins overlap?</h2>
              <p className="mt-1 text-sm text-studio-muted">
                Chance the SpyCatcher and LgBiT sizes overlap in space. Near zero is what you want.
              </p>
              <SeriesChart
                label="Clash probability versus repeat count"
                xLabel="Repeat count"
                yLabel="Clash probability"
                markerX={selected}
                series={[
                  {
                    color: "#9B2C2C",
                    points: finitePoints(report.points, (point) => point.p_clash),
                  },
                ]}
              />
            </div>
          </section>

          <p className="mt-4 text-sm text-studio-muted">{report.note}</p>
          <p className="mt-2 text-sm text-studio-muted">
            Kd used: {sci(report.kd_M)} M. These scores are calculations, not a measurement of the fusion.
          </p>
          <button
            type="button"
            className="mt-4 rounded-full border border-studio-border bg-studio-card px-4 py-2 text-sm"
            onClick={() => downloadJson("origami-length-sweep.json", report)}
          >
            Download sweep file
          </button>
        </>
      ) : null}
    </main>
  );
}
