# CivicForge Project Compass: Foundation Document

## I. Vision & Purpose

**Mission:** Launch an open, verifiable quest tracker that turns real tasks into *dual-attested "Done" events* on an append-only public log.

**Purpose:** Provide elite engineers the minimal context to ship a **minimal-loveable, AI-first** quest network—fast—while guaranteeing dignity, privacy, free expression, and antifascist resilience.

**North-Star Metric v1:** **Weekly Verified Actions per Active User (WAU)**—actor **and** recipient confirm. Stretch target: **≥ 1.5 WAU** by week 12.

**Tone:** Concise humility · Clear practicality · Positive intent

**Guiding Philosophy:** State goals + constraints, define the threat model in one paragraph, lock success targets, then **get out of the way** so better ideas surface.

**Key Reference - Platinum Rule++:** "Treat others **as they *want* to be treated**, provided doing so doesn't disproportionately cause harm or create significant negative externalities for communities or environments without just cause."

**Structural Terminology:**
- **World:** An independently customizable implementation of CivicForge for a specific community or purpose.
- **The Forge:** The meta-framework that coordinates between all Worlds, providing core infrastructure, standards, and governance mechanisms.

**Initial Implementation Focus:** Local neighborhood enhancement through beautification projects, elderly assistance, lawn care, community space improvements, and other community-building initiatives, with room for organic evolution as the first World in The Forge ecosystem.

## II. Foundational Principles

### A. Non-Negotiable Values

1. **Action over form** – Shortest path from "I'll do it" → "We both confirmed it's done."
   * Establish clear qualitative distinction between "done" (meeting basic requirements) and "exceptional" (extra-credit) for each quest.
   * Example: Done = trash cleaned from roadside and properly disposed of; Exceptional = trash cleaned, sorted for recycling, and properly disposed of (earning bonus credit/points/rewards).

2. **Visibility beats complexity** – Transparency first; cryptography where responsible (public plaintext log first; E2EE for private content).  

3. **Iterate in daylight** – Code/specs/decisions open (MIT / Apache-2.0; CC-BY-4.0 docs).  

4. **Bias for deletion** – After a genuine experiment, kill any feature that fails to advance the mission; document lessons, then move on.

5. **Integrity Guard-Rail:**  
   * Advertising is allowed but discouraged and must align with positive intent.
   * Nepotism, insider capture, monopolies, and similar "malicious compliance" are not permitted without renewed **and just** cause.
   * Coordination to subvert positive intent is blocked (exceptions made for well-meaning feedback; self-correction mandate requires fair arbitration with mutually agreeable conditions).
   * Repeated violations are blocked at protocol level, **with appeals possible (defined by each World, with oversight from The Forge)**.

6. **Free Speech with Safeguards** – Robust expression *unless* content incites violence, spreads fascism, or targets protected groups. Hate ≠ debate; harassment triggers moderation with appeal route.

7. **Anti-Surveillance Protection** – System design explicitly prevents evolving into a surveillance or social control mechanism:
   * Reputation metrics strictly limited to completed actions, never personal attributes.
   * No algorithmic scoring of "social worth" or character.
   * No mandatory participation requirements.
   * Transparent, community-governed standards with protection against scope creep.
   * No data correlation with external behavior tracking systems.

8. **Externality Awareness** – All quests and actions must consider broader impacts:
   * Environmental consequences must be assessed and minimized.
   * Community disruption potential must be evaluated.
   * Long-term sustainability should be prioritized over short-term gains.
   * Unintended consequences require monitoring and mitigation plans.

### B. Privacy & Security Commitments

1. **Privacy & Data Rights:**
   * **Right to be Forgotten** – Self-delete personal data + quests; irreversible purge within 24h, leaving anonymized aggregates.
   * **Least PII by Design** – Store only auth hash + display name; everything else optional.
   * **No Kafka Bureaucracy** – In-app toggle, no hard copies.

2. **Encryption & Lawful Safeguards:**
   * Aim for end-to-end encryption of private content **without** weakening cryptography.
   * Explore AI-side scanning or privacy-preserving hash-matching for abuse detection at client endpoints or zero-knowledge server workflows.
   * Cooperate with law enforcement **only** under due process, restricted to abuse investigation—never for political suppression.
   * Collaborate with independent experts (privacy, accessibility, ethics) for quarterly bias/security reviews; publish findings. 
   * All interception or scanning methods—if/when deemed possible—must be publicly documented, independently auditable, and revocable via community vote within each World and at The Forge level.

## III. User Experience Framework

### A. UX Mandate — "**Positivity** From Click One"

| Core Directive | Implementation Guard-rail |
|-----------|-----------|
| **AI-First Copilot** converts natural text into quests, suggests recipients & deadlines, summarizes progress in plain English. | Users can override/bypass AI in very few taps—no hostage flows. |
| **90-Second WOW**: land → create quest → invite recipient **in < 90s**. | Time every test; shave steps until it hurts. |
| **Fun Where We Can**—feedback/results celebrated, meaningful encouragement, purposeful acknowledgment on customizable milestones. | Sensitive quests auto-switch to calm palette & respectful copy (Platinum Rule++). |
| **Respect Where We Must**—quests tagged *personal/health* default private. | Privacy status always visible; one-click toggle. |
| **Zero-Instruction UI**—icons + labels pass the "grandparent test." | No wall-of-text tutorials; inline hints or 30-sec video. |
| **Mobile- & Accessibility-First**—works one-handed, screen-reader-friendly, low-bandwidth tolerant. | Consult lived-experience testers; fix WCAG AA issues before launch. |
| **Instant Feedback**—every tap responds visually/haptically in < 100ms. | Errors state *what next* in one sentence with responsive (triaged) support or self-help options. |
| **Human-Tone Copy**—verbs, not jargon.| Copy review is part of code review—no "AI/Human-slop" survives commit—own the work. |
| **World Identity**—each World can customize appearance within Forge guidelines. | Core functionality remains consistent across all Worlds. Customization within Rails—Worlds theme; users tweak cosmetics. Transparent review/appeal flow; safety rails set by Forge, refined by Worlds. |

**Benchmark:** ≥ 80 *PMF-UX* on a 5-min UserMaze test (25 external testers) by week 8.

## IV. Implementation Roadmap

### A. MVP Scope (12 weeks, single-tenant)

| **Must Exist** | **Must *Not* Exist (yet)** |
|----------------|----------------------------|
| Email / OAuth 2 or Passkeys | Federation protocol between Worlds |
| Conversational AI Copilot | Tokenized "Action Credits" |
| Quest CRUD + dual attestation | DAO governance / on-chain votes |
| Public JSON log (read-only) | AI incentive-audit engine |
| Reputation points leaderboard | ZK / MPC cheat detection |
| Moderator + Data-use dashboard | Incentive / micro-reward features |
| Content policy hooks & logging | Complex KYC / GDPR bureaucracy |
| Encryption roadmap & abuse-detection TODO | Premature backdoors |
| Basic World/Forge structure definitions | Full World customization framework |

If it's not in the left column, assume Phase 2+—*until WAU ≥ 5*.

### B. Development Phases & Milestones

| Week | Outcome | Success Signal |
|------|---------|----------------|
| 1–2 | **Spec Freeze v1.0** | Dummy client passes CI tests. |
| 3–6 | **World-Alpha** live (AI Copilot + 90-sec WOW) | 100 users, ≥ 300 quests closed, churn < 40%. |
| 7–8 | **Reputation Points** live | ≥ 70% quests rated; top users report motivation. |
| 9–10 | **Mod + Delete-Me Tools** | Abuse < 3%, delete flow < 24h. |
| 11–12 | **Public Docs & SDK stub** | ≥ 3 external PRs merged. |

CI/CD day 1; lint, test, preview deploy every push.

### C. Repository Structure `civicforge-spec`

```
/specs/        quest-schema-v1.yaml, api.md, rationale/
/server/       reference implementation (Go or Rust suggested)
/web/          thin client (React, Svelte, etc.)
/docs/         vision.md, roadmap.md, moderation.md, charter.md, privacy.md, encryption.md
/forge/        world-definitions.yaml, forge-governance.md, standards/
```

Every commit must contain a one-line **WHY**.

## V. Execution Plan

### A. Immediate Backlog (next 7 days)

1. **Lock Quest Schema v1** – GitHub for comment.  
2. **UX Proto-Sprint** – Figma + 5 usability tests pre-backend.  
3. **Plain-English FAQ** – cover Habitica/XPFarm etc.  
4. **One-Page Diagram** – only MVP; dotted boxes = Phase 2+.  
5. **Dev-Chat** – Discord/Slack; recruit 3-5 partner engineers.  
6. **Real-time WAU Counter** – dashboard day 1 (Grafana etc.).  
7. **Delete-Me API Spec** – purge rules + SLA.  
8. **Content Policy Hooks** – stub flag/appeal endpoints.  
9. **Encryption & Abuse-Detection RFC** – outline candidate approaches (client-side AI, perceptual hashing, zero-knowledge proofs) + open questions.
10. **Neighborhood-Specific Quest Templates** – Create initial templates for beautification, elderly assistance, and community enhancement projects.
11. **World/Forge Relationship Spec** – Define core infrastructure vs. World-level customizations.
12. **Threat Model Document** – Define specific security, privacy, and governance threats to be mitigated.

### B. Open Challenges (Phase 2+ parking lot)

* Federation & cross-world arbitration through The Forge  
* Token economy & regulatory compliance  
* AI incentive audit & sentiment scaffolding  
* ZK proofs for cheat detection  
* Employment / wage-hour exposure for micro-tasks  
* Quantum-safe encryption & post-quantum key rotation  
* Expansion beyond neighborhood-level implementation
* Safeguards against mission creep toward surveillance or control
* Multi-World governance models within The Forge framework
* Externality monitoring and mitigation systems

Capture ideas—**build later**. Better paths may appear.

## VI. Success Metrics & Adaptation

If WAU ≥ 1.5 and abuse ≤ 3% by week 12, **freeze feature creep** and draft scaling RFCs. If not, **slice scope again**—no sacred cows.

**Ship small. Ship loud. Delete what doesn't advance the North-Star.**
