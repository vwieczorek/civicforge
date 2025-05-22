# First Board MVP Plan (Based on `math_model_guideance.md`)
This plan distills the guidance in `math_model_guideance.md` into a concise task list for building the initial Board. Defaults that should remain configurable are omitted. Modules are outlined so later Boards can interoperate with the wider CivicForge ecosystem.

## 1. Core Goals
- Deliver a working Board where users can create, claim, verify, and log Quests.
- Introduce Experience points and a simple reputation system.
- Provide stubs for Forge‑level interactions (identity, governance, feature registry).
- Move CivicForge development tracking and improvement discussions to this Board as soon as possible to validate its usefulness.

## 2. Features for the First Board

### 2.1 User Identity and Accounts
- **KYC stub**: follow the requirement that real names can be revealed on demand. The Forge will later handle global identity (`Uglobal`). For MVP we collect minimal info and store a `verified` flag.
- **User roles**: Organizer, Participant, Verifier. 

### 2.2 Quest Lifecycle
Implement the S0–S12 quest state machine described in `math_model_guideance.md`:
1. **Create** → 2. **Claim** → 3. **Verify** → 4. **Log**
- Include optional `EXCEPTIONAL` completion.
- Both performer and verifier attest as described in the dual‑attestation notes.

### 2.3 Verification & Reputation
- Use a simple Bayesian or agreement model for dual attestation as recommended.
- Each user accrues reputation for successful quest completions and accurate verifications.
- Reputation feeds back into verifier selection and dispute resolution.

### 2.4 Experience Point Economy
- Define Experience rewards and decay rates in the Board configuration. math_model_guideance.md notes that rewards should scale with impact and can decay over time.
- Users spend Experience to post new Quests and optionally boost visibility.
- Track balances per user; implement decay via a scheduled job.

### 2.5 Moderation & Disputes
- Board‑level moderators handle disputes first.
- Build an escalation hook for the Forge council but leave the logic stubbed.

### 2.6 Stats and Impact
- Record metrics for quests completed, reputation changes, and Experience earned/spent.
- Expose an endpoint to export stats for the planned Composite Community Impact Index.

## 3. Forge Stubs
- Placeholder service for verifying global identity (`Uglobal`). Returns a mock verification response.
- Minimal API endpoints for registering Boards and for submitting feature proposals to the Forge registry (`Fregistry`). These just log the request.
- Hooks for cross‑Board collaboration (`Xglobal`) left unimplemented but documented.

## 4. Architecture Notes
- Build modular components with clear APIs so Boards can interoperate and evolve as the Forge grows.
- Expose a REST + Webhook API for all operations.
- Use a relational DB (SQLite in development) to store users, quests, Experience ledger, and board config.

## 5. Next Steps
1. **(done)** Define database schema and models for Users, Quests, Verifications, and Experience ledger. See `board_mvp/models.py`.
2. **(done)** Implement the Quest state machine and API endpoints.
3. Build the basic web UI or CLI for creating and tracking Quests.
4. Add Experience accounting and weekly decay job.
5. Implement reputation updates tied to verifications.
6. Write integration tests for the quest lifecycle.
7. Move development tracking and CivicForge feedback onto the first Board as soon as possible.
8. Document the stubbed Forge APIs for future expansion.

This MVP will demonstrate the core mechanics—verified action and Experience‑based rewards—while leaving room for the federation and advanced governance envisioned for CivicForge.
