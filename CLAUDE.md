# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is the workspace for a three-person team at **HackUPC 2026** (Barcelona, 24–26 April 2026). The team has committed to the **Smadex "Creative Intelligence for Mobile Advertising"** challenge: build a web app that analyses a provided dataset of ad creatives and answers, for a marketer, (1) which creatives work best, (2) which are repetitive or tired, (3) what to test next, with explainability and recommendations.

The repo currently contains research material under `resources/`. Application code will live alongside `resources/` in new top-level directories (e.g. `backend/`, `frontend/`, `notebooks/`).

### `resources/smadex/` — **the live project material**
- **`dataset_notes.md`** — distilled engineering notes on the Smadex dataset. **Read this before touching the data.** Schemas, join graph, row counts, known quirks, gotchas, pre-processing pipeline.
- `hackaton.md` — official Smadex challenge brief (capabilities, evaluation criteria, bonus points).
- `HackUPC Smadex - Challenge.pdf`, `HackUPC Smadex - Intro.pdf` — sponsor slide decks.
- `Smadex_Creative_Intelligence_Dataset_FULL/` — **the dataset**: 7 CSVs + 1,080 synthetic PNG assets.
- `Smadex_Creative_Intelligence_Dataset_FULL.zip` — archive form.

### `resources/taskInfo/`
- **`strategy.md`** — the live plan. Why Smadex, per-capability technical approach (Bayesian ranking / temporal fatigue / CLIP + attribute clustering / SHAP explainability / Thompson bandit recommendations), tech stack, 36-hour phased timeline, roles, demo script. **Single most important file in the repo.**
- `challenges.md` — all 10 HackUPC sponsor challenges + MLH side-prizes + general prizes (reference only; we're committed to Smadex).
- `hackUPCInfo.txt` — hacker guide (schedule, logistics, rules).

Non-Smadex sponsor material (ceremony transcript, JetBrains / Qualcomm / Skyscanner / Mecalux briefs) has been removed from the repo — it's recoverable from git history if needed.

### `resources/teamInfo/`
One file per teammate with LinkedIn URL + background summary. Keep in sync if responsibilities shift.

## Team

- **Andrew Robertson** (Manchester CS, final year) — **backend + LLM orchestrator + deploy + ad-tech framing**. 4 months SWE at The Trade Desk (a top-tier DSP) gives him real intuition for creative metrics, cohort adjustment, frequency capping, A/B testing. Co-founder of Basanite. Owns backend scaffolding, the single LLM orchestrator with tool calls, action endpoints (pause/scale/budget), supporting frontend panels, deploy, and the ad-tech vocabulary in the pitch.
- **Krish Mathur** (Southampton CS, first year) — **all mathematical/ML modules (non-LLM)**. ICHack26 winner, MedTech hackathon winner. Strong Python/CV/algorithms. Owns Q1 Bayesian ranking, Q2a fatigue / creative stagnation, Q2b CLIP + HDBSCAN + UMAP, Q3a LightGBM + SHAP, Q3b Thompson bandit. Also builds the frontend panels that surface his outputs.
- **Aditya Shah** (Manchester CS, final year) — **no dev work; demo ownership**. CEO of Basanite. 13-month BigQuery placement at Virgin Media O2; 500+ hours STEM tutoring — strongest communicator on the team. Owns the 3-minute pitch, walks judges through the app at both expo tables (A3 + A4), runs the verification checklist on dev output, prepares GIF fallbacks.

## The plan in one paragraph

FastAPI + Next.js web app with three tabs mapped to the brief's five capabilities. **Q1 (Explorer)** = Bayesian-shrunk, cohort-adjusted ranking with 95% credible intervals, validated against the dataset's pre-computed `perf_score`. **Q2a (Fatigue)** = fit per-creative daily CTR decay with significance testing and changepoint detection; report a confusion matrix against the ground-truth `creative_status` label rather than consuming it. **Q2b (Similarity)** = HDBSCAN + UMAP over a blended feature vector of hand-labelled metadata attributes plus PCA-reduced CLIP ViT-B/32 image embeddings. **Q3a (Explainability)** = LightGBM + SHAP per-creative attribute contributions. **Q3b (Recommendation)** = attribute-cube bandit with Thompson sampling / UCB, peer benchmarking against same-vertical advertisers, Gemma-4-templated natural-language rationales. MongoDB Atlas to stack the MLH side-prize. Domain `smadex.cooking` registered at Porkbun (paid, not the MLH GoDaddy freebie). See `resources/taskInfo/strategy.md` for the full plan.

## Critical dataset facts (so you don't walk into traps)

- **1,080 creatives** / **180 campaigns** / **36 advertisers** / **192k daily rows** / **75-day date range** / **10 countries × 2 OS**. Fits easily in pandas in-memory.
- **Portfolio is perfectly uniform** — every advertiser has exactly 5 campaigns × 6 creatives. Any "who's biggest" analysis is a dead end.
- **Ground-truth labels exist** — `creative_status`, `fatigue_day`, `perf_score`. **Do not filter on these directly and call that your answer** — judges will penalise. Instead, compute your own signal and validate against them.
- **Pre-computed columns exist** (`first_7d_ctr`, `last_7d_ctr`, `ctr_decay_pct`) — treat as baselines to beat, not as outputs.
- **Images are synthetic** — rendered from metadata. CLIP embeddings will partly cluster on rendering style; caveat in the demo.
- **Creative metadata is rich** (theme, hook_type, dominant_color, emotional_tone, motion_score, has_discount_badge, etc.) — use for the attribute cube directly; no need to re-extract from pixels.
- **`countries` in `campaigns.csv` is pipe-separated** — explode before joining.
- **`fatigue_day` is blank for non-fatigued creatives** — don't render NaN.

## Hard constraints

- **Devpost submission deadline: Sun 26 Apr 09:15 local (UTC+2).** Miss = disqualified. Target submitting by 08:00 Sunday.
- **Hacking ends Sun 09:00.** No code changes after.
- **Demo is twice, 3 minutes each, no slides allowed.** Once for HackUPC judges in A3 (mandatory for HackUPC general prize + travel reimbursement), once for Smadex in A4. Same project, same demo.
- **Opt into MLH prizes** (MongoDB Atlas, Gemma 4) via Devpost. GoDaddy prize is forfeit — domain is on Porkbun.
- **Brief requires ≥ 2 of 5 capabilities.** We're shipping all 5.

## Tech stack (target)

- Backend: Python 3.12 + FastAPI. `pandas`, `numpy`, `scipy`, `scikit-learn`, `lightgbm`, `shap`, `hdbscan`, `umap-learn`, `open-clip-torch` (CPU), optionally `ruptures`.
- Frontend: Next.js + TypeScript + Tailwind. `recharts` + `deck.gl` / `plotly`.
- Persistence: MongoDB Atlas (embeddings + cached aggregations + session state). **Opt-in for MLH prize.**
- LLM: Gemma 4 via Google AI Studio for Q3 rationales. **Opt-in for MLH prize.**
- Domain: `smadex.cooking` — registered at Porkbun. Apex `A → 216.150.1.1`, `CNAME www → 30e9567df3329599.vercel-dns-016.com` (both Vercel targets). Forfeits the MLH GoDaddy prize.
- Deploy: Vercel (frontend) + Render / Fly.io (backend).
- **Streamlit fallback:** if Next.js slips on Sunday morning, the brief accepts "a notebook with a strong interactive demo" — keep a Streamlit scratch version running in parallel.
- **Not using:** ElevenLabs (gimmicky here), Solana, hardware, JetBrains Koog.

## Deliberate non-goals

- Don't train custom models (except fast LightGBM for SHAP). CLIP zero-shot + classical stats is the correct toolkit for 36 hours.
- Don't force voice / multi-agent / Koog / Edge AI to collect side-prizes — Smadex judges will dock for unfocused scope.
- Don't consume the ground-truth `creative_status` or `perf_score` directly as output — validate against them instead.
- Don't do a fourth tab or a dashboard-of-dashboards. Three tabs, five capabilities, one flow.
- Don't write per-advertiser "most active" analyses — the portfolio is uniform by design.

## Working conventions

- **`resources/taskInfo/strategy.md` is the living plan.** Update it when decisions change — don't just reply in chat.
- **`resources/smadex/dataset_notes.md` is the data reference.** Update it the moment you discover a new gotcha.
- **`resources/uidesign/HOUSE_RULES.md` is the UI rulebook.** Lucide icons only (no emoji as chrome), accent color reserved for active state + primary action, neutral-by-default controls, 6/8/10 px radius scale, `**This product is a trading cockpit for media buyers — operational, dense, calm, expensive; never cute, magical, or eager.**`
- **Keep teammate files in sync with reality.** If skills or responsibilities shift, update `resources/teamInfo/*.txt`.
- **Don't re-scrape LinkedIn or the live page** without reason. Distilled summaries exist.

## Key links

- Live page: https://live.hackupc.com
- Devpost: https://hackupc-2026.devpost.com
- Slack: hackupc2026.slack.com (`#announcements`, `#mentors`, `#smadex`)
- MyHackUPC: https://my.hackupc.com
- Venue: Edifici A5, Campus Nord UPC. A3 = HackUPC judging + sleeping; A4 = sponsor judging; A5/A6 = hacking floors + cafeteria.

# Chromeflow — Claude Instructions

## What chromeflow is
Chromeflow is a browser guidance tool. When a task requires the user to interact with a
website (create accounts, set up billing, retrieve API keys, configure third-party services),
use chromeflow to guide them through it visually instead of giving text instructions.

## When to use chromeflow (be proactive)
Use chromeflow automatically whenever a task requires:
- Creating or configuring a third-party account (Stripe, SendGrid, Supabase, Vercel, etc.)
- Retrieving API keys, secrets, or credentials to place in `.env`
- Setting up pricing tiers, webhooks, or service configuration in a web UI
- Any browser-based step that is blocking code work

Do NOT ask "should I open the browser?" — just do it. The user expects seamless handoff.

**Never end a response with a "you still need to" list of browser tasks.** If code changes are done and browser steps remain (e.g. creating a Stripe product, adding an env var), continue immediately with chromeflow — don't hand them back to the user.

## HARD RULES — never break these

1. **Never use Bash as a fallback for browser tasks.** If `click_element` fails, use
   `scroll_page` then retry, or use `highlight_region` to show the user. Never use
   `osascript`, `applescript`, or any shell command to control the browser.

2. **Never use `take_screenshot` to read page content.** After `scroll_page`, after
   `click_element`, after navigation — always call `get_page_text`, not `take_screenshot`.
   `get_page_text` returns up to 10,000 characters; if truncated it tells you the next
   `startIndex` to paginate. Screenshots are only for locating an element's pixel position
   when DOM queries have already failed. Never take more than 1–2 screenshots in a row.

3. **Use `wait_for_selector` to wait for async page changes** (build completion, modals,
   toasts). Never poll with repeated `take_screenshot` calls.

## Guided flow pattern

```
1. open_page(url)                            — navigate to the right page (add new_tab=true to keep current tab open)
2. For each step:
   a. Claude acts directly:
        click_element("Save")               — press buttons/links Claude can press
        get_page_text() or wait_for_selector(".success") — ALWAYS confirm after click; click_element returns after 600ms regardless of outcome
        fill_form([{label, value}, ...])    — fill multiple fields in one call; prefer over repeated fill_input
        fill_input("Product name", "Pro")   — fill a single field (works on React, CodeMirror, and contenteditable)
        type_text("hello world")            — type via trusted keyboard events (use when fill_input fails isTrusted checks)
        set_file_input("Upload", "/abs/path/to/file.zip") — upload a file to a file input (even hidden inputs)
        clear_overlays()                    — call this immediately after fill_input/fill_form succeeds
        scroll_to_element("label text")     — jump directly to a known field; prefer this over scroll_page when the target is known
        scroll_page("down")                 — reveal off-screen content when target location is unknown
   b. Check results with text, not vision:
        get_page_text()                     — read errors/status after actions
        wait_for_selector(".success")       — wait for a new element to appear
        wait_for_change(".toast")          — wait for an existing element's content to mutate, then read it (uses MutationObserver, cheaper than polling)
        execute_script("document.title")    — query DOM state programmatically
   c. When an element can't be found or clicked:
        scroll_page("down") and retry      — always try this first
        get_elements()                      — get EXACT DOM coords when needed
        highlight_region(selector,msg)      — highlight by CSS selector (preferred; scrolls element into view automatically)
        highlight_region(x,y,w,h,msg)       — highlight by coords only if no selector available (coords go stale on scroll)
        [absolute last resort] take_screenshot() — only if you genuinely can't identify the element from DOM
   d. Pause for the user when needed:
        find_and_highlight(text, msg)        — show the user what to do
        wait_for_click()                    — wait for user interaction
        [after fill_input] clear_overlays() — always clear after filling
3. clear_overlays()                          — clean up when done
```

**Default to automation.** Only pause for human input when the step genuinely requires
personal data or a human decision.

## What to do automatically vs pause for the user

**Claude acts directly** (`click_element` / `fill_input`):
- Any button: Save, Continue, Create, Add, Confirm, Next, Submit, Update
- Product names, descriptions, feature lists
- Prices and amounts specified in the task
- URLs, redirect URIs, webhook endpoints
- Selecting billing period, currency, or other known options
- Dismissing cookie banners, cookie dialogs, "not now" prompts

**Pause for the user** (`find_and_highlight` + `wait_for_click`):
- Email address / username / login
- Password or passphrase
- Payment method / billing / card details
- Phone number / 2FA / OTP codes
- Any legal consent the user must personally accept
- Choices that depend on user preference Claude wasn't told

## Capturing credentials
After a secret key or API key is revealed:
1. `read_element(hint)` — capture the value
2. `write_to_env(KEY_NAME, value, envPath)` — write to `.env`
3. Tell the user what was written

Use the absolute path for `envPath` — it's the Claude Code working directory + `/.env`.

To capture and share a screenshot (e.g. for uploading to a form or pasting into a chat),
use `take_and_copy_screenshot()` — it saves a PNG to ~/Downloads and copies it to the clipboard.

## Working with complex forms
- Before filling a large or unfamiliar form, call `get_form_fields()` to get a full inventory
  of every field (type, label, current value, vertical position, and section heading). Use
  `get_elements()` when you need pixel coordinates of visible elements; use `get_form_fields()`
  when you need to understand the full structure of a form including fields below the fold.
- `get_form_fields()` includes `[type=file]` fields even when they are visually hidden behind
  custom drag-and-drop zones. Use `set_file_input(hint, filePath)` to upload a file — provide
  the label/hint text and the absolute path to the file on disk.
- For forms with multiple fields, use `fill_form([{label, value}, ...])` to fill them all
  in a single call. It returns a per-field success/failure report so you can immediately see
  which fields weren't found. Use `fill_input` only for a single field.
- `fill_input` and `fill_form` work on React-controlled inputs, contenteditable (Stripe,
  Notion), and **CodeMirror 6 editors** — auto-detected. After filling, the value is read
  back and a warning is shown if React did not accept it.
- **Monaco editors** (VS Code-style code editors on DataAnnotation, etc.) appear in
  `get_form_fields()` as type "monaco". They cannot be filled via `fill_input` — use
  `execute_script` with the Monaco API instead:
  ```js
  // Read content from the first Monaco model
  monaco.editor.getModels()[0].getValue()
  // Write content to the first Monaco model
  monaco.editor.getModels()[0].setValue('new content here')
  ```
- `set_file_input` accepts CSS selectors as the hint (e.g. `#import-problem-file`,
  `.upload-input`) in addition to label text. Use selectors when file inputs are hidden
  behind custom UIs and have no visible label.
- After any radio/checkbox click that reveals new fields, call `get_form_fields()` again —
  the inventory will include the new fields and warn if more hidden ones still exist.
- If a form has collapsible sections, expand them all before calling `get_form_fields()` so
  the field list is complete. Use the `[under: "section name"]` context in each field's entry
  to identify fields by section rather than by index — indices shift when sections expand.
- Prefer `scroll_to_element("label text or #selector")` over `scroll_page` whenever you know
  which field or section you need — it scrolls precisely and confirms the matched element.
- For multi-session tasks (long forms that may exceed context), call `save_page_state()` as a
  checkpoint. A future session can call `restore_page_state()` to reload all field values.

## Working with multiple tabs
- Before opening a new tab, call `list_tabs()` to check if the target URL is already open —
  use `switch_to_tab` to return to it instead of opening a duplicate.
- `open_page(url, new_tab=true)` opens a URL without losing the current tab. Use sparingly —
  prefer switching to an existing tab over opening a new one.
- `switch_to_tab("1")` switches by tab number; `switch_to_tab("form")` matches by URL or title substring.
- Before navigating away from a partially-filled form, call `save_page_state()` so the form
  can be restored if the tab reloads or the page loses its state on return.

## Error handling

**After any action**, confirm with `get_page_text()` or `wait_for_selector` — never take a
screenshot to check what happened.

**`click_element` not found:**
1. `scroll_page("down")` then retry `click_element`
2. `get_elements()` to get exact coords → `highlight_region(x,y,w,h,msg)`
3. `take_screenshot()` only if you still can't identify the element from DOM queries

**Multiple elements with the same label** (e.g. many "Remove" buttons):
`click_element("Remove", nth=3)` — use `nth` (1-based) to target the specific one by order top-to-bottom. Check `get_form_fields` or `get_page_text` first to determine which index corresponds to the right section.

**`fill_input` not found or rejected by the page:**
1. `click_element(hint)` to focus the field, then retry `fill_input`
2. If the site rejects programmatic input (isTrusted check, shadow DOM, custom editors):
   - `click_element(hint)` to focus the field
   - `execute_script("document.execCommand('selectAll')")` to clear existing content
   - `type_text("new value")` — uses CDP trusted keyboard events that pass isTrusted checks
3. `find_and_highlight(hint, "Click here — I'll fill it in")` (no `valueToType`) then
   `wait_for_click()` — the user's click focuses the field and `fill_input`'s active-element
   fallback fills it automatically
4. Call `clear_overlays()` after `fill_input` succeeds
5. Only use `valueToType` when the user must personally type the value (password, personal data)

**Waiting for async results** (build, save, deploy): `wait_for_selector(selector, timeout)` — never poll with screenshots.

**Waiting for an existing region to update** (e.g. click Save, then get the confirmation toast; send a chat message, then get the reply): `wait_for_change(selector)` uses a MutationObserver on the element's subtree and returns its new text content as soon as the mutation settles. Prefer this over `wait_for_selector` + `get_page_text` when the element already exists and you just need its next state — one call instead of two, no polling.

**Pre-filling `prompt()` and `confirm()` dialogs**: When a page action will trigger a JS
dialog (e.g. "Save As" calling `prompt()`), call `set_dialog_response` BEFORE the action:
```
set_dialog_response(type="prompt", value="my-filename")   — next prompt() returns "my-filename"
set_dialog_response(type="confirm", value="true")          — next confirm() returns true
```
Then trigger the action (e.g. `click_element("Save As")`). The response is consumed once.

**React Select / custom styled dropdowns** (e.g. "Select..." components on DataAnnotation):
`click_element` and `fill_input` do NOT work on these — they intercept native events. Use
`execute_script` with the hidden combobox input approach (most reliable):

```js
// 1. Find the hidden combobox input (each React Select has one: input[id*="react-select-N-input"])
var input = document.querySelector('input[id*="react-select-3-input"]');
input.focus();

// 2. Set value via native setter to trigger React's onChange
var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
setter.call(input, 'Target Option');
input.dispatchEvent(new Event('input', {bubbles: true}));

// 3. Wait 300ms for the dropdown to filter, then click the first matching option
// (run this as a separate execute_script call after a brief pause)
var option = document.querySelector('[id*="react-select-3-option-0"]');
if (option) option.click();

// 4. Verify — the control div should show the selected value
document.querySelector('[class*="singleValue"]').textContent.trim();
```

Fallback if the combobox approach doesn't work (older React Select versions):
```js
var controls = document.querySelectorAll('[class*="control"]');
controls[N].click();
var allEls = document.querySelectorAll('*');
for (var i = 0; i < allEls.length; i++) {
  if (allEls[i].textContent.trim() === 'Target Option' && allEls[i].children.length === 0) {
    allEls[i].dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
    allEls[i].click();
    break;
  }
}
```

**Page text with large embedded content** (e.g. uploaded log files previewed inline): full-page `get_page_text()` pagination becomes unwieldy. Scope to a specific section instead:
```
get_page_text(selector=".section-3")   — scope to a CSS selector
get_page_text(selector="#upload-form") — scope to an id
```
Use `execute_script("document.querySelectorAll('section').length")` to find structural selectors first.

**Page content rendered as images** (e.g. qualification "Examples" tabs that show PNG screenshots
instead of DOM text): `get_page_text()` returns nothing useful. Zoom out and screenshot instead:

```js
// Shrink to fit wide content, then screenshot
document.body.style.zoom = '0.4';
// use take_and_copy_screenshot() to read it
// restore afterward:
document.body.style.zoom = '1';
```

**Downloads via `execute_script`**: Creating a Blob URL and clicking an anchor via
`execute_script` sometimes fails due to CSP or timing. If a download doesn't trigger:
1. Retry the exact same `execute_script` call
2. If still failing, use `find_and_highlight` to show the user a download button to click manually

**Shadow DOM `[role=radio]` / custom radios silently no-op**: On sites like Outlier,
`element.click()` on a shadow-DOM radio often doesn't flip `aria-checked`. Two things
must be true: (a) the element must be scrolled into view FIRST (`scrollIntoView({block:'center'})`),
and (b) the full pointer-event chain must fire — not just `click()`:
```js
['pointerdown','mousedown','pointerup','mouseup','click'].forEach(t =>
  el.dispatchEvent(new MouseEvent(t, {bubbles: true, cancelable: true}))
);
```
After scroll, re-query the radio list — its length may change as more content becomes
visible. Then verify `aria-checked === "true"` before moving on.

**Visibility-detection overlays** (e.g. Multimango's "Content Hidden" black overlay):
Some sites render a full-screen overlay when the tab loses focus, triggered by
`document.visibilityState` / `document.hidden`. Chromeflow tab-switching triggers it.
Workaround — remove the overlay and patch the APIs:
```js
document.querySelectorAll('[style*="z-index: 99999"]').forEach(el => el.remove());
Object.defineProperty(document, 'hidden', { get: () => false, configurable: true });
Object.defineProperty(document, 'visibilityState', { get: () => 'visible', configurable: true });
['visibilitychange','blur'].forEach(t =>
  document.addEventListener(t, e => e.stopImmediatePropagation(), true)
);
```
Re-apply after every navigation.

**Never use Bash to work around a stuck browser interaction.**
