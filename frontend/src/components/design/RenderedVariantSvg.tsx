export interface VariantBrief {
  headline: string;
  subhead: string;
  cta: string;
  dominantColor: string;
  discountBadge: boolean;
}

const COLOR_MAP: Record<string, { bg: string; fg: string }> = {
  purple: { bg: "#5B2B8A", fg: "#FCE8FF" },
  blue: { bg: "#1F3A93", fg: "#DCE9FF" },
  green: { bg: "#137A5A", fg: "#DCFCE8" },
  orange: { bg: "#B06018", fg: "#FFE8CC" },
  red: { bg: "#9B2A3A", fg: "#FFE0E6" },
  yellow: { bg: "#C09000", fg: "#FFF4C2" },
  black: { bg: "#1C1B22", fg: "#F4F0FA" },
  white: { bg: "#E7E5EC", fg: "#15131A" },
};

export function RenderedVariantSvg({ brief }: { brief: VariantBrief }) {
  const palette = COLOR_MAP[brief.dominantColor.toLowerCase()] ?? COLOR_MAP.purple;
  return (
    <svg
      viewBox="0 0 360 360"
      width="100%"
      height="auto"
      role="img"
      aria-label="Generated variant mock"
      style={{ borderRadius: 10, display: "block" }}
    >
      <rect x="0" y="0" width="360" height="360" fill={palette.bg} />
      {/* decorative blob */}
      <circle cx="280" cy="80" r="90" fill={palette.fg} opacity={0.18} />
      <circle cx="60" cy="280" r="70" fill={palette.fg} opacity={0.12} />
      {/* hero shape stand-in */}
      <rect x="110" y="100" width="140" height="100" rx="12" fill={palette.fg} opacity={0.95} />
      <text
        x="180"
        y="158"
        textAnchor="middle"
        fontFamily="Inter, system-ui"
        fontSize="18"
        fontWeight="700"
        fill={palette.bg}
      >
        HERO
      </text>
      {/* headline */}
      <text
        x="180"
        y="230"
        textAnchor="middle"
        fontFamily="Inter, system-ui"
        fontSize="18"
        fontWeight="700"
        fill={palette.fg}
      >
        {truncate(brief.headline, 28)}
      </text>
      <text
        x="180"
        y="252"
        textAnchor="middle"
        fontFamily="Inter, system-ui"
        fontSize="12"
        fontWeight="500"
        fill={palette.fg}
        opacity={0.85}
      >
        {truncate(brief.subhead, 42)}
      </text>
      {/* CTA */}
      <rect
        x="130"
        y="280"
        width="100"
        height="36"
        rx="18"
        fill={palette.fg}
        stroke={palette.fg}
      />
      <text
        x="180"
        y="303"
        textAnchor="middle"
        fontFamily="Inter, system-ui"
        fontSize="13"
        fontWeight="600"
        fill={palette.bg}
      >
        {truncate(brief.cta, 18)}
      </text>
      {brief.discountBadge && (
        <g transform="translate(290 40)">
          <circle r="28" fill="#FFD166" stroke={palette.bg} strokeWidth="2" />
          <text
            textAnchor="middle"
            fontFamily="Inter, system-ui"
            fontSize="12"
            fontWeight="700"
            fill={palette.bg}
            dy="5"
          >
            -20%
          </text>
        </g>
      )}
    </svg>
  );
}

function truncate(value: string, max: number): string {
  if (value.length <= max) return value;
  return `${value.slice(0, max - 1)}…`;
}
