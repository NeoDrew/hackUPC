"use client";

import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api, type TimeseriesPoint } from "@/lib/api";

type EnrichedPoint = TimeseriesPoint & {
  ctr: number | null;
  cvr: number | null;
};

export function TimeseriesChart({ creativeId }: { creativeId: number }) {
  const [data, setData] = useState<EnrichedPoint[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getCreativeTimeseries(creativeId)
      .then((res) => {
        if (cancelled) return;
        const enriched: EnrichedPoint[] = res.points.map((p) => ({
          ...p,
          ctr: p.impressions > 0 ? p.clicks / p.impressions : null,
          cvr: p.clicks > 0 ? p.conversions / p.clicks : null,
        }));
        setData(enriched);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [creativeId]);

  if (error) return <p>Failed to load time series: {error}</p>;
  if (!data) return <p>Loading time series…</p>;
  if (data.length === 0) return <p>No daily data.</p>;

  return (
    <div data-chart="timeseries">
      <section data-chart-section>
        <h4>Rates — CTR (left axis) &amp; CVR (right axis)</h4>
        <div style={{ width: "100%", height: 220 }}>
          <ResponsiveContainer>
            <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis
                yAxisId="ctr"
                tickFormatter={formatPct}
                tick={{ fontSize: 11, fill: "#0f766e" }}
                width={56}
                domain={[0, "auto"]}
              />
              <YAxis
                yAxisId="cvr"
                orientation="right"
                tickFormatter={formatPct}
                tick={{ fontSize: 11, fill: "#9333ea" }}
                width={56}
                domain={[0, "auto"]}
              />
              <Tooltip
                formatter={(value) =>
                  typeof value === "number" ? formatPct(value) : String(value)
                }
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line
                yAxisId="ctr"
                type="monotone"
                dataKey="ctr"
                name="CTR"
                stroke="#0f766e"
                strokeWidth={2}
                dot={false}
                connectNulls
              />
              <Line
                yAxisId="cvr"
                type="monotone"
                dataKey="cvr"
                name="CVR"
                stroke="#9333ea"
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section data-chart-section>
        <h4>Volume — impressions (left axis) · clicks &amp; conversions (right axis)</h4>
        <div style={{ width: "100%", height: 220 }}>
          <ResponsiveContainer>
            <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis
                yAxisId="impr"
                tickFormatter={formatShort}
                tick={{ fontSize: 11 }}
                width={56}
              />
              <YAxis
                yAxisId="acts"
                orientation="right"
                tickFormatter={formatShort}
                tick={{ fontSize: 11 }}
                width={56}
              />
              <Tooltip formatter={(value) => formatFull(value)} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line
                yAxisId="impr"
                type="monotone"
                dataKey="impressions"
                name="Impressions"
                stroke="#0284c7"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="acts"
                type="monotone"
                dataKey="clicks"
                name="Clicks"
                stroke="#ca8a04"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="acts"
                type="monotone"
                dataKey="conversions"
                name="Conversions"
                stroke="#dc2626"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}

function formatPct(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function formatShort(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return String(value);
}

function formatFull(value: unknown): string {
  if (typeof value !== "number") return String(value);
  return value.toLocaleString();
}
