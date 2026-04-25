"use client";

import { useEffect, useRef, useState } from "react";

import { healthColor } from "@/lib/health";

export function HealthRing({
  value,
  ghostValue,
  size = 72,
  showLabel = true,
}: {
  value: number;
  ghostValue?: number;
  size?: 20 | 72 | 120;
  showLabel?: boolean;
}) {
  const stroke = Math.max(2, Math.round(size * 0.08));
  const radius = (size - stroke) / 2;
  const circ = 2 * Math.PI * radius;
  const target = Math.max(0, Math.min(100, value));
  const ghostTarget = ghostValue !== undefined ? Math.max(0, Math.min(100, ghostValue)) : null;

  const [progress, setProgress] = useState(0);
  const ref = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    // Trigger animation on mount.
    const id = requestAnimationFrame(() => setProgress(target));
    return () => cancelAnimationFrame(id);
  }, [target]);

  const dashOffset = circ * (1 - progress / 100);
  const ghostOffset = ghostTarget !== null ? circ * (1 - ghostTarget / 100) : null;
  const color = healthColor(target);

  return (
    <span className="health-ring" style={{ width: size, height: size }}>
      <svg
        ref={ref}
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        aria-label={`Health ${target}`}
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="var(--ring-track)"
          strokeWidth={stroke}
          fill="none"
        />
        {ghostOffset !== null && (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="var(--line-strong)"
            strokeWidth={stroke}
            strokeLinecap="round"
            fill="none"
            strokeDasharray={circ}
            strokeDashoffset={ghostOffset}
            opacity={0.45}
          />
        )}
        <circle
          className="fill"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={circ}
          strokeDashoffset={dashOffset}
        />
      </svg>
      {showLabel && size >= 72 && (
        <span className="val">
          <span className="n" style={{ fontSize: size === 120 ? 28 : 18 }}>
            {target}
          </span>
          <span className="l">Health</span>
        </span>
      )}
      {showLabel && size === 20 && (
        <span className="val">
          <span className="n" style={{ fontSize: 9 }}>
            {target}
          </span>
        </span>
      )}
    </span>
  );
}
