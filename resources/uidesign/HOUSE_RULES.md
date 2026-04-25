# B2B Creative Intelligence Dashboard UI House Rules

Build this product like infrastructure for media buyers, not like an AI demo. The target standard is Linear, Vercel Dashboard, Stripe Dashboard, and the denser parts of enterprise ad-tech tools: calm, precise, compact, and clearly designed by humans.

## Core rule

**Make the AI feel like infrastructure, not decoration.** Linear's redesign language emphasizes reducing visual noise while improving hierarchy and alignment, and that is the correct bar for this product.

## 1. Icons

- Ban emoji as icons everywhere. No `🎙`, `✦`, `▾`, `■`, or any text glyph used as UI chrome.
- Use **Lucide** only. Do not mix Lucide with Heroicons, Phosphor, Tabler, or custom random SVG packs.
- Lucide is the default because it is restrained, geometric, readable at small sizes, and visually closer to serious SaaS product UI than more expressive icon sets.
- Use icon sizes intentionally: 14px for dense tables/chips, 16px for inputs and standard buttons, 18px for toolbar/header actions, 20px only for larger navigation affordances.
- Use consistent stroke logic: 1.5px at 14px, 1.75px at 16–18px. Do not let icons look heavier in one surface and thinner in another.
- Align icons optically to text, not mathematically to the box. Nudge by 0.5px to 1px when needed so they sit correctly next to 14px or 15px labels.
- Icon color is muted foreground by default. Only use accent color when the entire control is active or selected.
- Never place icons in decorative colored circles or tinted rounded squares. That reads like SaaS template UI, not product design.
- Microphone button: use a plain `mic` icon only if voice input is genuinely useful. It is a secondary input mode, never a hero action.
- Stop recording: use `square`. Cancel or dismiss: use `x`. Do not overload one icon with two meanings.
- AI launcher: never use sparkles, stars, magic wands, or "AI" glyph theater. Prefer a text label, or use a quiet icon like `panel-right` only if needed.
- Expand/collapse: use `chevron-down`, `chevron-right`, `chevron-up`. Never use text triangles or ASCII symbols.
- Search: use a small low-contrast `search` icon inside the field as an affordance, not as a branded element.
- Tool-call chips: keep them text-first. If an icon is necessary, use a tiny neutral symbol like `command`, `terminal-square`, or `workflow`.
- If a repeated product action is central to the workflow and stock icons feel sloppy at your target sizes, replace that one icon with a hand-tuned SVG.

## 2. AI and copilot visual language

- Do not brand the assistant like a toy. No `✨ Copilot`, no "AI assistant" hero treatments, no rainbow gradients, no sparkles, no "magic" framing.
- Signal AI the way Linear and Vercel signal advanced functionality: through placement, speed, and utility, not decorative branding.
- Name features by role or noun, not by capability theater.
- Approved labels: `Assistant`, `Creative assistant`, `Analysis`, `Compare`, `Explain change`, `Fatigue summary`, `Twin comparison`.
- Rejected labels: `Ask Copilot`, `Smart suggestions`, `Ask AI`, `Powered by AI`, `Anything else?`, `How can I help?`.
- The assistant should live in the same visual system as the rest of the product: same panel chrome, same border treatment, same typography, same density.
- AI surfaces are mostly neutral. The assistant is not allowed a separate visual identity.
- Use one subtle signal that the feature is active: selected tab, open panel state, focused action. Do not invent a special AI palette.
- Suggestions must look like prebuilt operations, not inspirational prompts. Example labels: `Summarize fatigue`, `Find outliers`, `Compare selected creatives`, `Explain CTR decline`.
- Remove anything that looks like a shadcn landing-page demo: tinted icon circles, gradient borders, oversized empty-state illustrations, or a "featured" look on every panel.

## 3. Color

- Accent color gets exactly two jobs: active state and primary action.
- Do not paint every interactive element with the accent. Links, icons, tabs, pills, borders, helper text, charts, and empty states should not all be purple.
- Default state for controls is neutral: neutral text, neutral border, subtle hover fill.
- Accent color is allowed for: active nav item, selected tab, selected filter when state matters, focused chart series, primary button, and selected row.
- Secondary buttons are neutral. Ghost buttons are neutral. Inputs are neutral until focused.
- Search, sort, pagination, table affordances, and metadata stay neutral unless active.
- Status colors are semantic, not decorative.
- Success is only for positive delivery or strong performance.
- Warning is only for fatigue risk, pacing risk, anomaly, or low confidence.
- Danger is only for broken states, severe drop, rejection, or tracking failure.
- Keep all status colors muted and slightly dusty. No pure green, pure yellow, or pure red.
- Charts should start neutral: gray grid, gray axes, muted series. Use saturation only to direct attention to the one important series or state.
- Delete the gradient brand brick in the top-left. Logos in product UI should be flat, quiet, and reducible.

## 4. Copy

- Write copy like a product control surface, not like a chatbot.
- Name the noun, not the capability.
- Buttons describe the outcome, not the underlying intelligence.
- Approved button labels: `Generate summary`, `Compare variants`, `Export CSV`, `Open assistant`, `Review changes`, `Apply filters`, `Create report`.
- Rejected button labels: `Ask Copilot`, `Use AI`, `Try asking`, `Get smart insights`, `Anything else?`, `Powered by AI`.
- Placeholder text describes the object or lookup key, not a conversation.
- Approved placeholders: `Search creatives by name, tag, or ID`, `Filter by campaign`, `Enter creative ID`, `Search by ad set or network`, `Add internal note`.
- Rejected placeholders: `Ask about creatives, cohorts, fatigue…`, `Try asking about performance`, `What do you want to know?`.
- Empty states must say what object is missing and what action resolves it.
- Approved empty states: `No creatives match these filters.`, `No comparison selected. Choose two creatives to compare.`, `No fatigue signals yet. Increase the date range or lower the threshold.`
- Tooltips explain system behavior, not product personality.
- Approved tooltips: `Includes spend from paused variants.`, `Confidence updates every 4 hours.`, `Voice input transcribes directly to the query field.`
- Every label must still work if all icons are removed. If the meaning disappears without the icon, rewrite the copy.

## 5. Shape and density

- Reduce radius everywhere. Over-rounded UI is one of the strongest "made by an LLM" tells for serious software.
- Use this radius scale consistently:
  - Inputs, chips, segmented controls: 6px
  - Buttons: 6px
  - Cards and panels: 8px
  - Modals and drawers: 10px
- Never use pill shapes except for chips, tiny badges, or true segmented controls.
- Control heights:
  - Dense table toolbar controls: 32px
  - Standard buttons and inputs: 36px
  - Prominent header actions: 40px
  - Do not exceed 40px anywhere in the authenticated app
- Table row heights:
  - Default: 40px
  - Dense mode: 36px
  - Expanded analytical rows: 48px only when actually needed
- KPI tiles must be compact. Tight label, strong value, small delta, optional sparkline. No giant padding or giant corners.
- Use 4px spacing increments. Most component padding should land between 8px and 16px.
- Use cards only when content needs containment or separation. Do not wrap every section in a card if a flat surface with dividers is cleaner.
- Flat with dividers is the default for tables, filter bars, assistant transcripts, settings panels, and comparison metadata.
- Shadows must be minimal. Prefer border plus surface shift over floating-card shadows.
- Dense interfaces earn trust in power-user tools because they show more signal per viewport and reduce scroll tax.

## 6. Microcopy-free giveaways to remove

Delete these on sight:

1. Gradient logo bricks or gradient brand tiles.
2. Glassmorphism, frosted panels, blurry translucent overlays.
3. Sparkle icons, wand icons, stars, aurora borders, glow effects.
4. `Powered by AI` chips or any badge whose only job is to announce AI.
5. One accent color painted across every clickable element.
6. Three-feature suggestion grids with identical icon circles and two-line blurbs.
7. Vague placeholders like `Ask about creatives, cohorts, fatigue…`.
8. Emoji or typographic symbols used as controls.
9. Oversized radius combined with oversized padding and oversized shadows.
10. Generic assistant theater: `Try asking`, `Suggested prompts`, `Anything else?`, `Smart insights`, `Your AI copilot for mobile ads`.

## Competitor translation

Use competitor screenshots as a filter, not as a design source.

- Copy from AppsFlyer and Smartly: density, clear filter bars, chart-and-table hierarchy, operational labeling, and neutral enterprise chrome.
- Reject from Replai-style screens: playful assistant energy, mascot-like framing, and soft AI-demo polish.
- The right direction is **AppsFlyer meets Linear**, not "AI dashboard with charts."

## Non-negotiables

- One screen gets one visual boss: the data, the workflow, or the currently selected analysis. Not the branding.
- Every component must be classifiable in one second as navigation, filter, action, status, or data.
- If a design choice exists mainly to signal "this is AI," remove it.
- If a design choice would look embarrassing in Linear, Vercel, or Stripe Dashboard, remove it.
- Every surface must justify itself with information density, hierarchy, or workflow clarity.

## Final line to enforce

**This product is a trading cockpit for media buyers. It must look operational, dense, calm, and expensive — never cute, magical, or eager.**
