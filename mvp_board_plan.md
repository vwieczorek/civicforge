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
The MVP implements a very small reputation system. Reputation increases when
quests are verified and decreases on failed work. A more robust Bayesian or
agreement model for dual attestation remains a future improvement.
Reputation should ultimately feed back into verifier selection and dispute
resolution.

### 2.4 Experience Point Economy
Experience rewards and decay are implemented with fixed values in the code.
Future work should move these into configurable settings so rewards scale with
impact and decay can be tuned per Board. Users spend Experience to post new
Quests and optionally boost visibility. Balances are tracked in an experience
ledger and can be reduced by running the `run_decay` job.

### 2.5 Moderation & Disputes
These features are not implemented yet. The intent is for Board‑level
moderators to handle disputes first with a simple escalation hook to the Forge
council. Implementation details remain a TODO.

### 2.6 Stats and Impact
Stats tracking has not been implemented. The Board should eventually record
metrics for quests completed, reputation changes, and Experience earned or
spent. An endpoint to export these stats for the Composite Community Impact
Index will be needed.

## 3. Forge Stubs
The current codebase does not yet provide these stubs. Planned tasks include:
- A placeholder service for verifying global identity (`Uglobal`) that simply returns a mock verification response.
- Minimal API endpoints for registering Boards and for submitting feature proposals to the Forge registry (`Fregistry`). These should initially just log the request.
- Documentation for cross‑Board collaboration hooks (`Xglobal`).

## 4. Architecture Notes
- Build modular components with clear APIs so Boards can interoperate and evolve as the Forge grows.
- Expose a REST + Webhook API for all operations.
- Use a relational DB (SQLite in development) to store users, quests, Experience ledger, and board config.

## 5. Next Steps
1. **(done)** Define database schema and models for Users, Quests, Verifications, and Experience ledger. See `board_mvp/models.py`.
2. **(done)** Implement the Quest state machine and API endpoints.
3. **(done)** Build the basic CLI for creating and tracking Quests. See `board_mvp/cli.py`.
4. **(done)** Add Experience accounting and weekly decay job. Experience rewards
   are logged in `experience_ledger`, and `run_decay` reduces balances weekly.
   * Tests around decay scheduling and persistence have been added.
5. **(done)** Implement reputation updates tied to verifications. Reputation now
   increments for performers and verifiers in `verify_quest`.
6. **(done)** Build a minimal web UI for creating and tracking Quests so
   nontechnical users can interact with the Board. See `board_mvp/web.py`.
   * Web UI now includes quest claiming and verification forms with basic error
     handling.
7. **(done)** Write integration tests for the quest lifecycle.
   * Tests now cover the web UI routes as well.
8. **(in progress)** Move development tracking and CivicForge feedback onto the first Board once the basic web UI is usable.
   * A helper script `board_mvp/seed_tasks.py` seeds the Board with initial quests for upcoming work.
   * Next agent: continue adding tasks through the web UI and reference them in pull request descriptions.
9. Document and implement the Forge API stubs described above.

### Potential Issues
- SQLite connection is global and not thread-safe; FastAPI may need connection
  pooling if run with multiple workers.
- Reputation adjustments are simplistic and should evolve into a more robust
  reliability model.
- Weekly decay currently requires manual invocation via the CLI; scheduling
  should be automated in production.
- Initial web UI lacks authentication or CSRF protection; any user can submit
  forms directly.

This MVP will demonstrate the core mechanics—verified action and Experience‑based rewards—while leaving room for the federation and advanced governance envisioned for CivicForge.

