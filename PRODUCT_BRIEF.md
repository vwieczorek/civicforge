# CivicForge · Product Brief (v0.4)

*Tone — concise humility · clear practicality · positive intent*

---

## 1 · Problem Statement

Millions feel **disengaged**: layoffs, displacement, shrinking social trust. CivicForge turns passive scrolling into **actionable, real‑world impact** — even a single trash pickup or neighbor visit counts as a win.

---

## 2 · Mission

> **Turn community ideas into work done—rewarded and recorded on a public log, federation-ready and purposefully customizable.**

---

## 3 · Core Entities

| Layer     | Purpose                                      | Minimum Viable Scope                       |
| --------- | ----------------------------------------------------------- | ------------------------------------------ |
| **Forge** | Global governance layer, board themes, etc.  | Registry; arbitration; cross‑Board routing |
| **Board** | Themed local quest board                     | Quest CRUD; experience ledger; theming     |
| **Quest** | Atomic task with dual‑attestation flow       | PENDING → DONE / EXCEPTIONAL / DISPUTED    |

---

## 4 · External Outreach & Partnerships
TBD


---

## 5 · Naming & Customization Guidelines

* Base theme schema is defined and standardized to make participation easy. Updates are coordinated and timely.
* Board owners and communities are encouraged to tailor and theme almost everything; Civic(Forge) name and interactions stay universal.

---

## 6 · User Personas

| Persona         | Goal                              | Example Themes                      |
| --------------- | --------------------------------- | ----------------------------------- |
| **Organizer**   | Spin up & curate a Board          | School admin, Scout leader, pastor  |
| **Participant** | Complete quests & earn experience | Student, neighbor, club member      |
| **Verifier**    | Confirm completion, give feedback | Elderly homeowner, AI photo checker |

---

## 7 · Incentive & Economy Framework

* **Default earn rule: DONE +10 · EXCEPTIONAL +15; 2% weekly decay.**
* Experience funds new quests or boosts others; direct cash‑out discouraged (high‑friction fee).
* Boards may swap in bespoke policies via config.

---

## 8 · Quest Lifecycle

1. **Create** (requester) → 2. **Claim** (performer) → 3. **Verify** (verifier) → 4. **Log** (hash, sigs, timestamp).
   Exceptional = optional higher bar (e.g., recycle‑sorted trash).

---

## 9 · Identity & Trust

* Real‑name KYC at Forge level; Boards may mask names, but real names can always be revealed with one click.
* Anti‑Sybil: device-plus-biometric-hash & reputation heuristics.

---

## 10 · Moderation & Disputes

* Individual-level: Arbitrated at the **Board‑level first**; if stale ⇒ escalates to Primary Forge council (human + AI)
* Board-level: Failing Boards as determined by the Forge enter **probation**; new moderators elected or Board archived.
* External: Disputes follow hierarchy; Boards and their communities take ownership; Forge to support.

---

## 11 · Initial GenAI Strategy

* Model: **Claude‑family** via AWS Bedrock (MVP Consideration).
* Local fallback for privacy‑sensitive Boards.

---

## 12 · Privacy & Compliance

* Store **minimal PII**; US‑first launch.
* GDPR/CCPA hooks abstracted but disabled until needed.

---

## 13 · Security & Threat Model

* Continuous AI red‑team scans.
* Abuse scenarios: spam quests, collusion farms, hostile forks.

---

## 14 · Architecture Preferences

* Start **monolith wit feature flags**; extract micro‑services as scale dictates.
* (MVP Consideration) AWS stack exploration: Lambda, Bedrock, Q Business.
* Everything via public **REST & Webhook API**.

---

## 15 · Integrations

* GitHub, Slack/Discord, MCP, civic open‑data APIs.
* Webhooks for IFTTT / Zapier style flows.

---

## 16 · Governance Evolution

* Forge RFCs → elected council vote → versioned standards.
* Boards free to experiment; popular tweaks bubble up via RFC/vote/correction/learning.
* Succession Clause encoded in Forge smart‑contract for tamper‑proof enforcement.

---

## 17 · Funding Model

* Open‑source core (MIT/Apache).
* Optional SaaS hosting & "pro" analytics, access, features, incentives, participation options to explore.
* Marketplace fee on premium Board themes.

---

## 18 · KPIs

* **North‑Star:** Positive community impacts via number of tasks completed per user.
* Backup: Quest creation rate, quest quality, median claim time, dispute statistics, bad actor analysis, WAU/MAU.

---

## 19 · 12‑Month Success Criteria

* ≥ 2 live communities (e.g., neighborhood HOA & school).
* Primary Forge operational, Board stats dashboard live, hierarchy test scenario simulated.
* Open‑source repo with ≥ 20 external contributors.

---

**Parking Lot**

* Finish External Outreach & Partnerships section
* Add Change Management concepts for protocol or framework updates--look for good examples
* Finalize experience presets & exceptional‑task rubric.
* Flesh out Quest taxonomies (trash‑clean, elder‑aid, fundraiser…).
* POC Forge hierarchy voting contract.
