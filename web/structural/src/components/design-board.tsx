"use client";

import { useEffect, useState } from "react";
import { SeriesChart } from "@/components/model-chart";
import { StudioNav } from "@/components/studio-nav";

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
  reporter: "Folded, held, and reporter occupancy at or above one half",
  held_reporter_dark: "Folded and held; reporter occupancy below one half",
  folded_not_held: "Folded; association does not hold",
  below_assay: "Calculated melting temperature at or below the assay temperature",
  docking_skipped: "Melt kept; docking skipped because the graft does not fit",
  not_fit: "No melting-temperature fit",
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
        setError("Graft index must be a whole number, or left blank.");
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
    <main className="mx-auto max-w-4xl px-6 py-10 text-[#242220]">
      <StudioNav />
      <p className="text-[11px] font-semibold tracking-[0.22em] text-[#C45C12] uppercase">
        Structural analysis
      </p>
      <h1 className="mt-2 text-3xl font-semibold">Which length should the scaffold be?</h1>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#5C564E]">
        Every repeat count from 3 to 24 is scored with the same melt model and the same
        affinity check. A length stays in the running when its calculated melting temperature
        is above the assay temperature and the typed Kd or Ka holds the two docking sites
        together. Among those lengths, the highest LgBiT–SmBiT occupancy is marked. SpyCatcher–SpyTag
        half-life and clash are drawn on the same sweep so a short distance is not chosen
        blindly. The mark is that ranking rule. It is not a validated optimum.
      </p>

      <section className="mt-8 rounded-2xl border border-[#E3D9CC] bg-white p-6">
        <p className="text-sm text-[#5C564E]">
          The box starts at the peptide Kd used by the bound-fraction model, 0.19 nM. Type
          another Kd or Ka to ask a different affinity. Leave the graft blank to use each
          length’s named M13 position, or the C-terminal repeat when that length has none.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          <label className="block text-sm font-medium">
            Constant
            <select
              className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2"
              value={kind}
              onChange={(event) => setKind(event.target.value === "ka" ? "ka" : "kd")}
            >
              <option value="kd">Dissociation, Kd</option>
              <option value="ka">Association, Ka</option>
            </select>
          </label>
          <label className="block text-sm font-medium">
            Value
            <input
              className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2 font-mono"
              value={value}
              onChange={(event) => setValue(event.target.value)}
            />
          </label>
          <label className="block text-sm font-medium">
            Unit
            <select
              className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2"
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
            Graft index
            <input
              className="mt-1 w-full rounded-lg border border-[#E3D9CC] px-3 py-2 font-mono"
              value={graft}
              placeholder="blank = named"
              onChange={(event) => setGraft(event.target.value)}
            />
          </label>
        </div>
        <button
          type="button"
          className="mt-5 rounded-full bg-[#242220] px-5 py-2 text-sm text-white disabled:opacity-50"
          onClick={() => void run()}
          disabled={running}
        >
          {running ? "Scoring lengths…" : "Score every length"}
        </button>
        {error ? <p className="mt-4 text-sm text-[#9B2C2C]">{error}</p> : null}
      </section>

      {report ? (
        <>
          <section className="mt-6 rounded-2xl border border-[#E3D9CC] bg-white p-6">
            <h2 className="text-lg font-medium">
              {report.marked_n === null
                ? "No length both stays folded and holds together"
                : `Marked length: n = ${report.marked_n}`}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">{report.ranking_rule}</p>
            <p className="mt-2 text-sm leading-relaxed text-[#5C564E]">
              {report.any_length_drives_reporter
                ? `LgBiT–SmBiT occupancy reaches one half at n = ${report.reporter_lengths.join(", ")}.`
                : "No length in this sweep puts LgBiT–SmBiT occupancy at or above one half. The mark, when present, is only the highest occupancy among lengths that fold and hold."}
            </p>
            <p className="mt-2 text-sm text-[#5C564E]">{report.graft_rule}</p>
            <div className="mt-5 flex flex-wrap gap-1" role="list" aria-label="Length calls">
              {report.points.map((point) => {
                const on = point.n_repeats === selected;
                return (
                  <button
                    key={point.n_repeats}
                    type="button"
                    role="listitem"
                    aria-pressed={on}
                    aria-label={`n = ${point.n_repeats}. ${CALL_LABEL[point.call] ?? point.call}`}
                    className="h-10 w-10 rounded-md text-xs text-white"
                    style={{
                      background: CALL_COLOR[point.call] ?? "#8A8175",
                      outline: on ? "2px solid #242220" : "none",
                      outlineOffset: 2,
                    }}
                    onClick={() => setSelected(point.n_repeats)}
                  >
                    {point.n_repeats}
                  </button>
                );
              })}
            </div>
            <ul className="mt-4 grid gap-1 text-xs text-[#5C564E] sm:grid-cols-2">
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
            <p className="mt-3 text-xs text-[#8A8175]">
              Planned construct lengths are 3, 8, and 14. Click a cell to read that length.
            </p>
          </section>

          {focus ? (
            <section className="mt-6 rounded-2xl border border-[#E3D9CC] bg-white p-6">
              <h2 className="text-lg font-medium">
                n = {focus.n_repeats}
                {PLANNED.has(focus.n_repeats) ? " · planned construct" : ""}
                {report.marked_n === focus.n_repeats ? " · marked by the ranking rule" : ""}
              </h2>
              <p className="mt-2 text-sm text-[#5C564E]">{CALL_LABEL[focus.call] ?? focus.call}</p>
              {focus.past_longest_cited_length ? (
                <p className="mt-2 text-sm text-[#5C564E]">
                  This length is past the longest cited melt. The melting temperature is an
                  extrapolation of the length fit.
                </p>
              ) : null}
              {focus.docking_skip_reason ? (
                <p className="mt-2 text-sm text-[#5C564E]">{focus.docking_skip_reason}</p>
              ) : null}
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-[#8A8278]">Melting temperature</dt>
                  <dd className="font-mono">{plain(focus.tm_C)} °C</dd>
                </div>
                <div>
                  <dt className="text-[#8A8278]">Unfolding ΔG at the anchor temperature</dt>
                  <dd className="font-mono">{plain(focus.delta_g)} kcal/mol</dd>
                </div>
                <div>
                  <dt className="text-[#8A8278]">Bound fraction</dt>
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
                  <dt className="text-[#8A8278]">Local concentration</dt>
                  <dd className="font-mono">{sci(focus.c_eff_M)} M</dd>
                </div>
                <div>
                  <dt className="text-[#8A8278]">LgBiT–SmBiT occupancy</dt>
                  <dd className="font-mono">
                    {sci(focus.nanobit_theta)}{" "}
                    {focus.drives_lgbit_smbit ? "at or above one half" : "below one half"}
                  </dd>
                </div>
                <div>
                  <dt className="text-[#8A8278]">SpyCatcher–SpyTag half-life</dt>
                  <dd className="font-mono">{sci(focus.spy_half_life_s)} s</dd>
                </div>
                <div>
                  <dt className="text-[#8A8278]">Clash probability</dt>
                  <dd className="font-mono">{plain(focus.p_clash, 3)}</dd>
                </div>
                <div>
                  <dt className="text-[#8A8278]">Chord</dt>
                  <dd className="font-mono">{focus.chord_A === null ? "—" : `${focus.chord_A.toFixed(2)} Å`}</dd>
                </div>
              </dl>
            </section>
          ) : null}

          <section className="mt-6 space-y-6 rounded-2xl border border-[#E3D9CC] bg-white p-6">
            <div>
              <h2 className="text-lg font-medium">Melting temperature</h2>
              <p className="mt-1 text-sm text-[#5C564E]">
                The dashed line is the assay temperature, {assay} °C. A point above it passes
                the fold comparison used everywhere else in the studio.
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
              <h2 className="text-lg font-medium">Does the association hold?</h2>
              <p className="mt-1 text-sm text-[#5C564E]">
                Bound fraction at the local concentration. The dashed line is one half, the
                Langmuir midpoint. At or above that line, the typed affinity holds the two
                sites together.
              </p>
              <SeriesChart
                label="Association bound fraction versus repeat count"
                xLabel="Repeat count"
                yLabel="Bound fraction"
                guideY={{ y: 0.5, label: "1/2" }}
                markerX={selected}
                series={[
                  {
                    color: "#242220",
                    points: finitePoints(report.points, (point) => point.association_theta),
                  },
                ]}
              />
            </div>
            <div>
              <h2 className="text-lg font-medium">Does that proximity drive LgBiT–SmBiT?</h2>
              <p className="mt-1 text-sm text-[#5C564E]">
                Occupancy uses the printed LgBiT–SmBiT Kd at the same local concentration,
                and only when the association holds. The dashed line is one half. A curve
                along the bottom is far below the reporter.
              </p>
              <SeriesChart
                label="LgBiT–SmBiT occupancy versus repeat count"
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
              <h2 className="text-lg font-medium">SpyCatcher–SpyTag half-life</h2>
              <p className="mt-1 text-sm text-[#5C564E]">
                Point half-life is ln(2) divided by the on-rate times the local concentration.
                The axis is logarithmic. A higher local concentration shortens this half-life.
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
              <h2 className="text-lg font-medium">Clash</h2>
              <p className="mt-1 text-sm text-[#5C564E]">
                Probability that the SpyCatcher and LgBiT spheres overlap at this chord.
                A length that holds the sites together can still clash.
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

          <p className="mt-4 text-sm text-[#5C564E]">{report.note}</p>
          <p className="mt-2 text-sm text-[#5C564E]">
            Kd used: {sci(report.kd_M)} M. This sweep is not calibrated to a measurement of
            the fusion.
          </p>
          <button
            type="button"
            className="mt-4 rounded-full border border-[#E3D9CC] bg-white px-4 py-2 text-sm"
            onClick={() => downloadJson("origami-length-sweep.json", report)}
          >
            Download sweep file
          </button>
        </>
      ) : null}
    </main>
  );
}
