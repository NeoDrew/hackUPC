export function Sparkline({
  series,
  fatigueDay,
  width = 80,
  height = 24,
  stroke = "var(--t-3)",
  fill = "transparent",
}: {
  series: number[];
  fatigueDay?: number | null;
  width?: number;
  height?: number;
  stroke?: string;
  fill?: string;
}) {
  if (!series || series.length === 0) {
    return <svg className="sparkline" width={width} height={height} aria-hidden />;
  }

  // Right-align: series shorter than the design's 30 sits at the right.
  const max = Math.max(...series);
  const min = Math.min(...series);
  const range = Math.max(1e-9, max - min);
  const n = series.length;
  // We assume a logical width of 30 slots; if the series is shorter, plot it
  // starting at slot (30 - n).
  const slots = 30;
  const stepX = width / (slots - 1);

  const points = series.map((v, i) => {
    const slot = slots - n + i;
    const x = slot * stepX;
    const y = height - ((v - min) / range) * (height - 2) - 1;
    return { x, y, slot };
  });

  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${height} L ${points[0].x.toFixed(1)} ${height} Z`;

  let fatigueDot: { x: number; y: number } | null = null;
  if (fatigueDay !== null && fatigueDay !== undefined) {
    // Map fatigueDay (days since launch) to the rightmost matching slot in our
    // 30-slot window. We don't know the absolute day index per point, so use a
    // proportional mapping into the visible window.
    const idx = Math.min(n - 1, Math.max(0, Math.round((fatigueDay / Math.max(1, n)) * (n - 1))));
    fatigueDot = { x: points[idx].x, y: points[idx].y };
  }

  return (
    <svg className="sparkline" width={width} height={height} aria-hidden>
      <path d={areaPath} fill={fill} stroke="none" />
      <path d={linePath} fill="none" stroke={stroke} strokeWidth={1.5} />
      {fatigueDot && (
        <circle cx={fatigueDot.x} cy={fatigueDot.y} r={2.2} fill="var(--status-cut)" />
      )}
    </svg>
  );
}
