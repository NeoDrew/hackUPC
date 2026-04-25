# Smadex Creative Twin Copilot — Streamlit handoff

Persona: Maya Tanaka, creative strategist. ROAS-first hierarchy. Every screen should answer
"which creatives deserve more money / less money / a replacement".

Stack assumption: Streamlit + custom CSS injected via `st.markdown("<style>…</style>")` and
`components.html` for the few bits Streamlit can't render natively (animated rings,
sparklines, twin diff lines).

---

## Screen 1 — Cockpit (Portfolio)

URL-equivalent: default landing view.

### Component tree
- TopBar
  - product mark · workspace breadcrumb · search · Period chip · demo button · avatar
- CockpitHeader
  - Greeting ("Good morning, Maya — it's Wednesday")
  - 5 KPI tiles (ROAS-first order): ROAS · Spend · CTR · CVR · Attention count
- TabBar
  - 5 tabs: Scale · Watch · Rescue · Cut · Explore (utility)
  - urgent dot on Rescue + Cut, count badge on all four action tabs
- CreativeTable  (renders for action tabs; ExploreView for Explore)
  - Heading block ("N creatives recommended to …") + contextual subcopy
  - Density toggle · Sort chip · bulk action button (Rescue only)
  - Table: 9 columns, 80px regular rows
    `thumb | headline + meta | CTR | CVR | ROAS | Spend | Days | 7d trend | Health`

### Data dictionary — columns read
| Component | data fields |
|---|---|
| KPI tiles | `PORTFOLIO_KPIS.{total_spend,total_revenue,roas,ctr,cvr,attention_count}` |
| Tab counts | count of `CREATIVES` per `status` |
| Row thumb | `creative.asset` (from labelled PNG) |
| Row headline | `headline`, `creative_id`, `advertiser_name`, `vertical`, `format`, `duration_sec`, `days_active` |
| Row metrics | `ctr`, `cvr`, `roas`, `spend`, `days_active` |
| Row sparkline | `series` (30-day CTR array), `fatigue_day` (optional red dot) |
| Row health ring | `health` (0–100) |

### Layout
- 1440 design width, page padding 32px horizontal
- Table is a single `<div>` with `display:grid`, `grid-template-columns: 88px 2fr 76px 76px 76px 76px 80px 92px 110px`
- Row hover: `background: var(--bg-2)`
- Numeric cells: `font-variant-numeric: tabular-nums`, right-aligned

### Streamlit approach
- KPI tiles: 5-column `st.columns`, each a `<div>` of HTML (the `.kpi-tile` CSS below)
- Tabs: `st.radio` styled as pills OR `streamlit_option_menu`
- Table: `st.dataframe` is too rigid. Build rows manually via `st.container` + HTML; on click fire a `st.session_state.open_creative = id` and rerun
- Health ring + sparkline: render as inline SVG in the HTML cell. Do NOT use `st.components.v1.html` for each row (slow). Build the SVG string in Python and pass as part of the row HTML

---

## Screen 2 — Detail Drawer

Triggered by clicking any creative row. Slides in from right over a scrim.

### Component tree
- DrawerHeader:   `#id` · StatusPill · advertiser · campaign · close
- DrawerHero:     120px creative image + meta · animated HealthRing w/ optional ghost arc (health_at_launch) + 4 score bars (CTR pct, CVR pct, Volume, Fatigue resistance)
- FatigueChart:   (fatigued only) 672×180 SVG — 30-day CTR line with PEAK and FATIGUE annotations
- PerformanceGrid: 6-cell stat block (ROAS, Spend, Revenue, Impressions, Clicks, Conversions)
- CreativeMetadata: 10 pill tags (theme, hook, tone, CTA text, text_density, clutter, novelty, product_count, has_ugc_style, has_discount_badge)
- TwinPreviewCard: (fatigued only) purple-bordered hero card → opens Twin view

### Data fields
All fields on the `creative` object. Fatigue chart adds: `series`, `fatigue_day`,
`first_7d_ctr`, `last_7d_ctr`, `ctr_decay`.

### Streamlit approach
- Drawer: fake via full-width modal (`st.dialog` in recent Streamlit) OR a right-hand `st.sidebar` emulation. Cleanest: put the drawer content into a `st.container` and conditionally render at the top of the page with a scrim overlay (HTML + high z-index)
- Animated ring: inline SVG; animate stroke-dashoffset via CSS keyframe on mount — NOT React state
- Fatigue chart: matplotlib with custom style OR hand-rolled inline SVG (recommended — more control)

---

## Screen 3 — Twin Comparison

Full-screen overlay. The core "wow" moment.

### Component tree
- Sticky header: back · segment pill (`81% similar · travel × rewarded_video`) · Save · **Generate next variant**
- Page heading ("Why is your fatigued creative losing to its twin? · 3 high-impact")
- TwinCanvas: two CreativePanels + CenterConnector (diff icon in circle)
  - CreativePanel: image thumb · HealthRing · StatusPill · headline · 3-cell MiniStat (ROAS/CTR/CVR) · 5 Tag chips with highlight rules
- VisionInsight: purple left-border card with Claude Vision badge, typing-animation body, Regenerate button
- DiffTable: 5-col grid — field · yours · twin · direction · impact (with mini bar gauge)
- WinningPatternsCard: 3×2 grid of PatternCard (lift, prevalence, trait, what)

### Data fields
- `TWIN_DIFF.fatigued_id`, `winner_id` → look up in CREATIVES
- `TWIN_DIFF.similarity`, `segment.{vertical,format}`, `diffs[]`, `vision_insight.{headline,body,confidence}`
- `WINNING_PATTERNS.{segment, sample_size, top_rate, patterns[]}`

### Streamlit approach
- Render the whole view inside `components.html` iframe — too much interlinked motion for native widgets
- OR: break into st-columns + HTML cards; skip the typing animation (keep static body copy)
- The "Generate next variant" button: use `st.button` at the top of the fragment; on click set `st.session_state.view = "variant"`

---

## Screen 4 — AI-Generated Variant

Opens from Twin's primary CTA.

### Component tree
- Sticky header: back-to-twin · variant id mono · Save / Send to designer / **Push to test campaign**
- Lineage (wow moment 2): 3 thumbs + 2 arrows
  - Fatigued → (twin found) → Winner → (variant generated) → Variant mock
- Hero grid (380 | 1fr):
  - RenderedVariant: SVG mock matching dataset flat-shape style (purple bg, single hero shape, white pill CTA)
  - BriefPanel: 10 BriefField k/v grid + "Why these choices" rationale list with check icons
- PredictedLift: green-tinted card with 3 stat comparisons (fatigued → variant, with % lift pill)
- Closing line: "From diagnosis to draft creative in 92 seconds"

### Data fields
- `NEXT_VARIANT.brief.{headline, subhead, cta, duration_sec, dominant_color, emotional_tone, text_density, product_count, has_ugc_style, has_discount_badge, rationale[], predicted_ctr, predicted_cvr, predicted_roas, confidence}`
- `NEXT_VARIANT.source_fatigued`, `twin_winner` → CREATIVES lookup for lineage
- `fatigued.{last_7d_ctr, last_7d_cvr, roas}` for lift comparison

### Streamlit approach
- The rendered mock is a single hand-authored SVG; pass brief values in as f-string substitutions. Don't try to generate real pixels
- Rationale staggered reveal: skip the animation; render list as-is
- Push-to-test button: tie to `st.toast` for confirmation

---

## Screen 5 — Explore (utility)

Flat filtered table. Lower visual density — quiet cousin to the action tabs.

### Component tree
- Title + subtitle ("Cross-slice all N active creatives")
- Filter chip rows (vertical stack): Vertical · Format · Country · OS · Status (with status colors)
- Aggregates strip: 7 cells — Creatives · Avg health · Impressions · CTR · CVR · Spend · ROAS (colorized by threshold)
- Sortable table: 9 columns, 56px rows
  `thumb | id + headline | status | health | CTR | CVR | ROAS | Spend | Days`

### Data fields
- Filter universes derived from `CREATIVES` (unique values of each column)
- Aggregates computed over filtered set
- Same row fields as cockpit table

### Streamlit approach
- Filters: `st.multiselect` with `format_func` to show capitalized labels; or chip-styled `st.button` per option
- Aggregates: 7-column `st.columns`
- Table: `st.dataframe` with column_config is acceptable here (utility context tolerates less custom chrome). Use `column_config.ProgressColumn` for Health, `NumberColumn(format="%.2fx")` for ROAS

---

## Shared patterns

### Status → verb mapping (used everywhere)
top_performer → "Scale"
stable → "Watch"
fatigued → "Rescue"
underperformer → "Cut"

Never show the raw status string to users.

### HealthRing contract
- Input: `value` 0–100, optional `ghostValue` (health_at_launch)
- Animates 0 → value on mount over 800ms cubic ease-out
- Color by value: `healthColor(v)` function (see CSS)
- Sizes: 20 (inline in table rows), 72 (detail/twin), 120 (empty states)
- Stroke: `size * 0.08` rounded, minimum 2

### Sparkline contract
- Input: `series[]` (CTR per day), optional `fatigueDay`
- 80×24 default; renders filled area + line. Red dot at fatigueDay.

### Typography
Use Inter 400/500/600/700 + Roboto Mono for all numeric cells. `font-variant-numeric: tabular-nums` on every number so columns don't jiggle.

### Motion
- All transitions use `cubic-bezier(.2,.8,.2,1)` (token: `--ease-out`)
- Fast hover/focus: 120ms. Tab underline glide: 180ms. Drawer slide: 260ms.
- Rings animate 800ms on mount. Score bars animate width 700ms.

### Key CSS classes (Streamlit-ready — see smadex.css)
`.t-page` `.t-section` `.t-body` `.t-td` `.t-micro` `.t-overline` `.label-xs` `.num` `.mono` `.tnum` `.row` `.col` `.row.center` `.row.between` `.gap-1` `.gap-2` `.gap-3` `.gap-4` `.kpi-tile` `.chip` `.filter-chip` `.status-pill` `.creative-row` (with hover state) `.drawer-scrim` `.drawer-panel` `.chip-pos` `.chip-neg` (diff green/red chips) `.skeleton` (shimmer loading)
