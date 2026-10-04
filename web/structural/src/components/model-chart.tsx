"use client";

type Point = { x: number; y: number };

type Series = {
  color: string;
  width?: number;
  points: Point[];
};

/** Line chart for a model output. yLog uses log10 and drops non-positive y. */
export function SeriesChart({
  label,
  xLabel,
  yLabel,
  series,
  yLog = false,
  xLog = false,
  guideY,
  markerX,
}: {
  label: string;
  xLabel: string;
  yLabel: string;
  series: Series[];
  yLog?: boolean;
  xLog?: boolean;
  guideY?: { y: number; label: string };
  markerX?: number;
}) {
  const width = 640;
  const height = 280;
  const pad = { l: 56, r: 16, t: 16, b: 40 };
  const prepared = series
    .map((item) => ({
      ...item,
      points: item.points.filter(
        (point) =>
          Number.isFinite(point.x) &&
          Number.isFinite(point.y) &&
          (!yLog || point.y > 0) &&
          (!xLog || point.x > 0),
      ),
    }))
    .filter((item) => item.points.length > 0);
  const ys = prepared.flatMap((item) => item.points.map((point) => (yLog ? Math.log10(point.y) : point.y)));
  const xs = prepared.flatMap((item) => item.points.map((point) => (xLog ? Math.log10(point.x) : point.x)));
  if (guideY && Number.isFinite(guideY.y) && (!yLog || guideY.y > 0)) {
    ys.push(yLog ? Math.log10(guideY.y) : guideY.y);
  }
  if (xs.length === 0 || ys.length === 0) return null;
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const yMin = Math.min(...ys);
  const yMax = Math.max(...ys);
  const xSpan = xMax - xMin || 1;
  const ySpan = yMax - yMin || 1;
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const xOf = (x: number) => pad.l + (((xLog ? Math.log10(x) : x) - xMin) / xSpan) * innerW;
  const yOfRaw = (y: number) => pad.t + innerH * (1 - (y - yMin) / ySpan);
  const yOf = (y: number) => yOfRaw(yLog ? Math.log10(y) : y);
  const yTicks = [yMin, yMin + ySpan / 2, yMax];
  const pathOf = (points: Point[]) =>
    points
      .map((point, index) => `${index === 0 ? "M" : "L"} ${xOf(point.x).toFixed(2)} ${yOf(point.y).toFixed(2)}`)
      .join(" ");
  const tickText = (raw: number) => {
    const value = yLog ? 10 ** raw : raw;
    if (yLog) return value.toExponential(0);
    if (Math.abs(value) >= 100 || (Math.abs(value) > 0 && Math.abs(value) < 0.01)) return value.toExponential(1);
    return Math.abs(value - Math.round(value)) < 1e-6 ? String(Math.round(value)) : value.toFixed(1);
  };

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" role="img" aria-label={label}>
      <text x={pad.l} y={12} fill="var(--studio-chart-label)" fontSize="11">
        {yLabel}
      </text>
      {yTicks.map((tick) => (
        <g key={tick}>
          <line x1={pad.l} x2={width - pad.r} y1={yOfRaw(tick)} y2={yOfRaw(tick)} stroke="var(--studio-chart-grid)" />
          <text x={4} y={yOfRaw(tick) + 4} fill="var(--studio-chart-label)" fontSize="11">
            {tickText(tick)}
          </text>
        </g>
      ))}
      {guideY && (!yLog || guideY.y > 0) ? (
        <g>
          <line
            x1={pad.l}
            x2={width - pad.r}
            y1={yOf(guideY.y)}
            y2={yOf(guideY.y)}
            stroke="var(--studio-blue)"
            strokeDasharray="4 4"
          />
          <text x={width - pad.r - 4} y={yOf(guideY.y) - 6} fill="var(--studio-blue)" fontSize="11" textAnchor="end">
            {guideY.label}
          </text>
        </g>
      ) : null}
      {prepared.map((item, index) => (
        <path
          key={`${item.color}-${index}`}
          d={pathOf(item.points)}
          fill="none"
          stroke={item.color}
          strokeWidth={item.width ?? 2}
        />
      ))}
      {markerX !== undefined && Number.isFinite(markerX) ? (
        <line x1={xOf(markerX)} x2={xOf(markerX)} y1={pad.t} y2={height - pad.b} stroke="var(--studio-chart-marker)" strokeDasharray="2 3" />
      ) : null}
      <text x={width / 2} y={height - 8} fill="var(--studio-chart-label)" fontSize="11" textAnchor="middle">
        {xLabel}
      </text>
    </svg>
  );
}
