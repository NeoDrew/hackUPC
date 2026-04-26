import type { ReactNode } from "react";

/**
 * Single source of truth for ad-tech acronyms used in this UI. Add new
 * entries here and they'll auto-tooltip everywhere ``<Acronym>`` /
 * ``<AcronymText>`` is rendered.
 *
 * Definitions are short — they show in a native browser tooltip on hover,
 * which the OS truncates aggressively. ≤ ~80 chars.
 */
export const ACRONYM_DEFINITIONS: Record<string, string> = {
  CTR: "Click-through rate · clicks ÷ impressions",
  CVR: "Conversion rate · conversions ÷ clicks",
  ROAS: "Return on ad spend · revenue ÷ spend",
  IPM: "Installs per mille · conversions per 1,000 impressions",
  CPA: "Cost per acquisition · spend ÷ conversions",
  CPI: "Cost per install · spend ÷ installs",
  CPM: "Cost per mille · spend per 1,000 impressions",
  KPI: "Key performance indicator",
  CTA: "Call to action · the button copy on the creative",
  ATT: "App Tracking Transparency · Apple's iOS opt-in tracking framework",
  DSP: "Demand-side platform · the ad-buying platform (Smadex here)",
  OS: "Operating system · Android or iOS",
  UGC: "User-generated content · creator-style ad layout",
  MMP: "Mobile measurement partner · attribution provider (e.g. AppsFlyer)",
  MMM: "Marketing mix modelling · regression-based attribution method",
  LTV: "Lifetime value · cumulative revenue per acquired user",
  RPM: "Revenue per mille · revenue per 1,000 impressions",
  // Country / cluster shorthand we surface in the advisor:
  LATAM: "Latin America cluster — BR, MX, AR, CO",
  SEA: "Southeast Asia cluster — ID, PH, TH, VN",
};

/**
 * Wrap a known acronym to render as a hover-tooltipped ``<abbr>``. Falls
 * back to the literal string if the acronym isn't in the dictionary.
 *
 * Usage:
 *   <Acronym>CTR</Acronym>            → tooltipped
 *   <Acronym>FOO</Acronym>            → renders "FOO" plain
 */
export function Acronym({ children }: { children: string }) {
  const def = ACRONYM_DEFINITIONS[children.toUpperCase()];
  if (!def) return <>{children}</>;
  return (
    <abbr title={def} className="acronym-hint">
      {children}
    </abbr>
  );
}

/**
 * Auto-wrap acronyms inside a free-text string. Splits on word boundaries
 * and only wraps tokens whose all-uppercase form is in the dictionary —
 * so country codes ("MX", "BR") and OS names ("iOS", "Android") pass
 * through untouched.
 *
 * Usage:
 *   <AcronymText text="Pause in BR · CTR -78%" />
 *      → "Pause in BR · " + tooltipped "CTR" + " -78%"
 */
export function AcronymText({ text }: { text: string }): ReactNode {
  // Split on standalone runs of A-Z (≥ 2 chars). Lower-case mixes (iOS)
  // don't match because of the case-sensitive class.
  const parts = text.split(/(\b[A-Z]{2,6}\b)/);
  return (
    <>
      {parts.map((part, i) =>
        ACRONYM_DEFINITIONS[part] ? (
          <Acronym key={i}>{part}</Acronym>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}
