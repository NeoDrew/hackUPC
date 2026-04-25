export function Sparkline({
  series,
  fatigueDay,
  width = 80,
  height = 24,
  stroke = "var(--accent)",
  fill = "var(--accent-soft)",
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

  // Right-align short series in a 30-slot logical window (table sparklines
  // assume daily-ish density). For longer series (KPI tile spans the whole
  // active window), distribute points evenly across the full width.
  const max = Math.max(...series);
  const min = Math.min(...series);
  const range = Math.max(1e-9, max - min);
  const n = series.length;
  const slots = 30;
  const useFullWidth = n >= slots;
  const stepX = useFullWidth ? width / Math.max(1, n - 1) : width / (slots - 1);

  const points = series.map((v, i) => {
    const x = useFullWidth ? i * stepX : (slots - n + i) * stepX;
    const y = height - ((v - min) / range) * (height - 2) - 1;
    return { x, y, slot: i };
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
    <svg
      className="sparkline"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      aria-hidden
    >
      <path d={areaPath} fill={fill} stroke="none" />
      <path
        d={linePath}
        fill="none"
        stroke={stroke}
        strokeWidth={1.5}
        vectorEffect="non-scaling-stroke"
      />
      {fatigueDot && (
        <circle cx={fatigueDot.x} cy={fatigueDot.y} r={2.2} fill="var(--status-cut)" />
      )}
    </svg>
  );
}
