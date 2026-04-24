# HackUPC 2026 — Sponsor Challenges

Source: https://live.hackupc.com/talks (authoritative) at the time of the event. Original sponsor PDFs and the opening-ceremony transcript have since been removed from the repo; recover from git history if needed.

## Sponsor challenges (all opt-in via Devpost)

### 1. Mecalux — Warehouse Optimizer
Design an intelligent system that places storage bays in the most cost-effective way. Given a provided warehouse layout + bay catalogue, decide which bays to install and how to position them while minimising cost. Encouraged approaches: heuristics, optimisation, creative visualisations.
Adjacent Mecalux talk: "Free-threaded Python: unlocking true parallelism" — CPU-parallelism deep-dive using the new no-GIL Python.

### 2. Qualcomm (with Arduino + Edge Impulse) — EdgeAI for a Resilient and Greener Barcelona
Hardware challenge. Build an on-device Edge AI system using the provided kit:
- Brain: Arduino UNO Q (with Qualcomm processor).
- Vision: USB webcam.
- Sensors/Actuators: Arduino Modulino nodes (Movement, Distance, Thermo, Vibro, Light, Knob, Button, Buzzer, Pixels) + QWIIC cables.
- Software: Arduino App Lab IDE + Edge Impulse Studio.

System must collect local sensor/camera data, run inference locally (classification, object/anomaly/audio detection, small LLMs/VLMs), make autonomous decisions and trigger actions, under real-world constraints.

Application areas: surviving heatwaves, water conservation, urban & coastal cleanliness, biodiversity monitoring.

Mandatory 3-step submission or disqualified:
1. Devpost project summary with team + links.
2. Public GitHub repo with `main.py`, `sketch.ino`, YAML configs, `README.md`, and `LICENSE.txt` (Mozilla Public License 2.0).
3. Arduino Project Hub page named exactly `[HackUPC2026] - Your Project Name` containing description, hardware list, AI-model info, software architecture, visuals/video, GitHub link.

Judging criteria: Creativity & Relevance · Technical Execution (latency, accuracy) · Impact & Scalability.
Workshops: "Arduino UNO Q: Getting Started" and "Arduino UNO Q & Edge Impulse: Edge AI Getting Started".

### 3. PEARS (by Tether) — Build a P2P App
"No backend. No cloud bill. No single point of failure. Build an unstoppable app — and win a prize money can't usually buy." Build with Tether's open-source Peers peer-to-peer platform. Workshop: "How to build a P2P app? From zero to unstoppable — deploy an app that keeps running through outages, censorship, and network disruptions."

### 4. Smadex — Creative Intelligence for Mobile Advertising
Given an anonymised dataset of ad creatives + simplified performance metrics, build a web app that helps a marketer answer: (1) Which creatives are working best? (2) Which look repetitive or tired? (3) What should we test next? Ad-tech data-app challenge.

### 5. JetBrains — Help the Developer
Create an innovative application or IntelliJ-based plugin that simplifies a developer's life. Examples: routine test creator, refactor suggester, or any idea (even META-level). Ideally AI-powered. Integration with JetBrains tools (IntelliJ / Koog) is nice-to-have, not required. Acceptable form factors: plugin, web app, desktop app, mobile app. Prizes announced Saturday. Booth + Slack channel `#jetbrains`.

### 6. Skyscanner — The Future of Travel
Design a next-generation AI-powered travel experience tackling two problems: (a) help travellers discover the right destinations; (b) use natural language search to truly understand their intent. Smart, relevant recommendations that cut complexity while preserving user control. Open use of any AI tooling.

### 7. HP — Intelligent Digital Replica for an Industrial 3D Printer
Build a digital twin for the HP Metal Jet S100 metal 3D printer. Three progressive phases, pick your depth:
- **Model** — digitally replicate the printer and the vectors that affect it (humidity, temperature, number of jobs, human operator roughness, maintenance cadence).
- **Simulate** — connect the vectors, run it over time, predict when/how the printer fails.
- **Interact** (bonus) — natural-language interface. "Ask the printer: how are you doing? When are you going to break?"

Open to physics-modelling, ML, data-engineering, or UX strengths. Free tech stack. No historical data required. HP volunteers coaching on-site all weekend.

### 8. INDITEXTECH — Hack the Flow: Algorithms for Greater Logistics Agility
Design the intelligence that governs box movement through Zara/Inditex automated silos (hundreds of thousands of boxes per silo; twice-weekly shipping to thousands of stores worldwide + e-commerce). The challenge is not just space — it's the choreography of inputs and outputs to minimise response times and maximise silo agility. Algorithms / scheduling / simulation focus.
Adjacent INDITEXTECH talk: "Redefining Visual Creation with Pixia" — their AI creative-production tool (image/video/3D/product recontextualisation).

### 9. Bending Spoons — Efficiency Multiplier
(Announced at opening; their on-site talks are "Engineering for Security Efficiency" and "Sync or Swim: Rebuilding Evernote's Backbone".) Build tools that make engineers/people more efficient: automation, AI assistants, productivity tooling. Their in-house products include Evernote, WeTransfer, Remini, Komoot — they want systems that multiply engineer output.

### 10. Airbus — No challenge this year
Airbus sponsors the hackathon and provides mentors; no prize track. Company talk: "Airbus GeoTech — Center of Excellence for Earth Observation" (satellites, HAPS, stratospheric imagery, disaster/forest monitoring, geospatial analytics).

## MLH side-prizes (stack these on top of your main challenge)

- **Best use of Gemma 4** — Google's new open-weights model, exclusive this weekend. Win Google swag kits. Workshop at 10:00 AM Saturday in A5002 ("Intro to Google AI Studio"). Also: "Intro to Agent Mode with GitHub Copilot".
- **Best use of Solana** — pay-per-use APIs, shared leaderboards, fast backend.
- **Best use of ElevenLabs** — conversational AI / voice agents ("Give your vision a voice").
- **Best use of MongoDB Atlas** — managed DB, no credit card required.
- **Best domain name from GoDaddy Registry** — free domain code + prize for best name.

## HackUPC general prizes
Mandatory HackUPC demo (A3 building) — required to be eligible for these AND for travel reimbursement. No slides allowed, 3 minutes, code demo, one project per team (same project can be submitted to multiple tracks).

- **1st:** DJI Neo drone + trophy
- **2nd:** Asus portable screen + trophy
- **3rd:** Lego set + trophy

Sponsor-specific demos happen in A4 after HackUPC judging.

## Key deadlines
- Hacking starts: Fri Apr 24, 21:00 (after Opening Ceremony). Qualcomm PDF says 20:30.
- Hacking ends: Sun Apr 26, 09:00.
- **Mandatory submission deadline: Sun Apr 26, 09:15 on Devpost.**
- Judging: Sun Apr 26, 10:15–13:15.
- Closing ceremony / awards: Sun Apr 26, 15:00–17:00.
- Total hacking window: 36 hours.
