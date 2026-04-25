"use client";

import { useEffect, useState } from "react";

import { api, type CreativeTimeseries } from "@/lib/api";

interface Props {
  creativeId: number;
  fatigueDay?: number | null;
}

export function FatigueChart({ creativeId, fatigueDay }: Props) {
  const [data, setData] = useState<CreativeTimeseries | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getCreativeTimeseries(creativeId)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [creativeId]);

  if (error) return <p className="t-body muted">Failed to load: {error}</p>;
  if (!data) return <p className="t-body muted">Loading daily series…</p>;
  if (data.points.length === 0) return <p className="t-body muted">No daily data.</p>;

  const points = data.points.map((p) => ({
    date: p.date,
    ctr: p.impressions > 0 ? p.clicks / p.impressions : 0,
  }));
  const width = 672;
  const height = 180;
  const padL = 40;
  const padR = 16;
  const padT = 16;
  const padB = 28;

  const xStep = (width - padL - padR) / Math.max(1, points.length - 1);
  const max = Math.max(...points.map((p) => p.ctr));
  const min = 0;
  const range = Math.max(1e-9, max - min);
  const peakIdx = points.findIndex((p) => p.ctr === max);

  const scaleX = (i: number) => padL + i * xStep;
  const scaleY = (v: number) =>
    padT + (height - padT - padB) * (1 - (v - min) / range);

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${scaleX(i).toFixed(1)} ${scaleY(p.ctr).toFixed(1)}`)
    .join(" ");

  const areaPath = `${linePath} L ${scaleX(points.length - 1).toFixed(1)} ${height - padB} L ${scaleX(0).toFixed(1)} ${height - padB} Z`;

  const fatigueIdx =
    fatigueDay !== null && fatigueDay !== undefined && fatigueDay < points.length
      ? fatigueDay
      : null;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="auto" role="img" aria-label="Daily CTR">
      {/* gridline */}
      <line
        x1={padL}
        x2={width - padR}
        y1={height - padB}
        y2={height - padB}
        stroke="var(--line)"
        strokeWidth={1}
      />
      <path d={areaPath} fill="var(--accent-soft)" stroke="none" />
      <path d={linePath} fill="none" stroke="var(--accent)" strokeWidth={2} />

      {/* peak marker */}
      {peakIdx >= 0 && (
        <g>
          <circle cx={scaleX(peakIdx)} cy={scaleY(max)} r={3.5} fill="var(--status-top)" />
          <text
            x={scaleX(peakIdx)}
            y={scaleY(max) - 8}
            fontSize={10}
            fontWeight={600}
            fill="var(--status-top)"
            textAnchor="middle"
          >
            PEAK
          </text>
        </g>
      )}

      {/* fatigue marker */}
      {fatigueIdx !== null && (
        <g>
          <line
            x1={scaleX(fatigueIdx)}
            x2={scaleX(fatigueIdx)}
            y1={padT}
            y2={height - padB}
            stroke="var(--status-cut)"
            strokeWidth={1}
            strokeDasharray="3 3"
          />
          <circle cx={scaleX(fatigueIdx)} cy={scaleY(points[fatigueIdx].ctr)} r={3.5} fill="var(--status-cut)" />
          <text
            x={scaleX(fatigueIdx)}
            y={padT + 10}
            fontSize={10}
            fontWeight={600}
            fill="var(--status-cut)"
            textAnchor="middle"
          >
            FATIGUE
          </text>
        </g>
      )}

      {/* x-axis labels */}
      <text x={padL} y={height - 8} fontSize={10} fill="var(--t-3)">
        {points[0].date}
      </text>
      <text x={width - padR} y={height - 8} fontSize={10} fill="var(--t-3)" textAnchor="end">
        {points[points.length - 1].date}
      </text>
    </svg>
  );
}
