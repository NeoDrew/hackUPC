# Which challenge should we pick? — Strategy note

## Team's unfair advantages (from the LinkedIns)

- **Andrew + Krish already won Best ElevenLabs + runner-up JetBrains at ICHack26** with Guardian, a multi-agent voice system using ElevenLabs + RAG + JetBrains Koog. They have shipped this exact genre of project 3 months ago.
- **Andrew (AI Engineer at Outlier + DataAnnotation) and Aditya (CEO of Basanite — AI interviewer for technical roles)** are literally building a developer-evaluation product as their startup. The JetBrains brief ("make developers' lives easier, ideally AI") maps to Basanite-adjacent territory.
- **Andrew did 4 months at The Trade Desk as a SWE intern** — one of the world's largest DSPs. He has first-hand exposure to programmatic ad-tech: creative auctioning, bidders, campaign performance metrics, ad serving at scale. This is exactly Smadex's domain.
- **Krish** has hackathon range: computer vision (MedTech winner), Flask/web, mobile, Azure AI, algorithms (A*, priority queues). He's the fastest builder.
- **Aditya** is the strongest communicator (500+ tutoring hours, CEO role, stakeholder comms from Virgin Media O2). He also brings BigQuery / data-analytics chops — a good fit for any dataset-heavy challenge. He will carry the two 3-minute demos.
- **Combined hackathon W/L is excellent** — Bloomberg BPuzzled 1st, ICHack26 (2 prizes), Southampton MedTech 1st, AI Tinkerers top 15. They are a known-winning unit.

## Team's gaps

- **Zero embedded / Arduino / Edge Impulse experience on file.** Nobody has posted sensor/firmware work. Hardware debugging in a 36-hour window with unfamiliar hardware is a trap.
- **No 3D-printing / physics-modelling experience.** HP's Metal Jet digital twin wants physics modelling, ML, or data engineering from operator telemetry — nothing the team has demonstrated.
- **No P2P / BitTorrent / distributed-systems experience.** Tether's Peers challenge is niche and the platform is new to them.

## Recommendation: **JetBrains "Help the Developer"** as the primary track

Reasons:

1. **Highest skill match.** Their ICHack winning stack (ElevenLabs voice + JetBrains Koog multi-agent backend + RAG) maps almost 1:1 to a dev-productivity AI tool.
2. **They know the judging taste.** They already won runner-up JetBrains — they understand what the Ernest/JetBrains crew rewards.
3. **Lowest setup cost.** Pure software, no hardware, no unfamiliar platform. Every hour counts.
4. **High prize-stacking potential.** A dev-productivity AI tool can naturally win:
   - JetBrains (primary).
   - MLH Best use of ElevenLabs (voice interface to the tool — "debug by conversation").
   - MLH Best use of MongoDB Atlas (store sessions / traces / embeddings).
   - MLH Best use of Gemma 4 (open-weights agent component — novel and Google is judging).
   - MLH Best GoDaddy domain.
   - HackUPC main prize (DJI Neo) if the demo is polished — judges are expo-style non-specialists.
5. **Aditya's Basanite experience is directly relevant** — they understand the "evaluate a developer" problem space, which is close to "help a developer".

### Concrete project ideas that fit the stack

- **"Pair-review agent"** — an IntelliJ plugin where you talk to a voice agent that reviews your diff, asks clarifying questions about intent, and writes/refines the PR description. ElevenLabs voice + Koog multi-agent (reviewer / style / test-coverage agents) + Gemma 4 for the local-weights path.
- **"Test-intent creator"** — instead of auto-generating tests from code, the plugin elicits the test *intent* conversationally (edge cases, invariants) and only then writes tests. Solves the real pain: auto-tests are shallow because they pattern-match code not intent.
- **"Refactor diary"** — plugin that watches your changes, clusters them into a narrative of why you refactored, and learns your style so future suggestions match.

Any of these can be built in 36 hours by this team and demoed crisply.

## Strong backup: Smadex "Creative Intelligence for Mobile Advertising"

Andrew's 4 months at The Trade Desk is a genuine edge here — he understands the creative-auction / performance-metrics mental model Smadex judges will probe on. Aditya's BigQuery background suits the data-app shape (dataset → charts → recommendation). The brief is tightly scoped (three specific questions for a marketer), which is ideal for a 36-hour build — you can't easily over-scope it.

Why it's the backup rather than the pick:

- Prize-stacking is weaker — it's a web app consuming a static dataset, so ElevenLabs / Koog / Gemma don't graft onto it as cleanly as they do to a dev-productivity tool.
- Smadex engineers are ex-FIB / UPC — home-turf judges who will see through shallow work.
- Even so: if the JetBrains room looks crowded Saturday morning, pivoting to Smadex is a sensible hedge because the brief is self-contained (no platform to learn).

## Second backup: Skyscanner "Future of Travel"

Natural-language travel agent is a voice-agent problem → replays ICHack playbook. Stacks ElevenLabs / Gemma / MongoDB / GoDaddy prizes well. Skyscanner engineering is in Barcelona — home crowd. Slightly weaker than JetBrains only because the team has no specific prior traction with Skyscanner judges.

## Avoid

- **Qualcomm Edge AI** — hardware learning curve too steep for this team in 36 hrs. The 3-step submission (Devpost + GitHub + Arduino Project Hub) is also more admin overhead than a student team should absorb.
- **HP digital twin** — niche domain, no data provided, requires physics or serious telemetry-modelling experience.
- **Mecalux / INDITEXTECH logistics** — these reward OR / scheduling research chops. Doable, but glamour is lower and the demo won't pop against a voice-agent competitor.
- **Tether Peers** — new platform, niche, 36 hours is thin for learning distributed P2P plus shipping.
- **Bending Spoons Efficiency Multiplier** — overlaps with JetBrains but with vaguer judging criteria and no branded ecosystem to leverage.

## Tactical notes

- Opt in to **every** MLH side-prize on Devpost — they are free upside.
- Present the SAME project at HackUPC judging (A3) and at the sponsor booth (A4). Demo twice.
- No slides. 3-minute code demo. Aditya leads the pitch; Krish/Andrew handle the live demo + questions.
- Register the GoDaddy domain early Saturday morning; it takes DNS time to propagate.
- Start Devpost submission by Sunday 08:00 to avoid the 09:15 deadline crunch.
