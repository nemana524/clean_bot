# Roles and responsibilities

This project uses **strict verification**: every change should be attributable, reviewable, and aligned with client requirements.

## Roles

### 1. Client / product owner

- Provides **functional requirements**, legal/compliance constraints, and acceptance criteria.
- Approves scope for automation against official sites and owns account/data policies.

### 2. Lead developer (human)

- Owns **architecture decisions**, merges, and releases.
- Ensures `info/` stays updated when behavior or ops change.
- Rotates **secrets** if leaked; never commits real production keys to shared repos.

### 3. Implementing engineer (human or AI agent)

- Implements changes **only in scope** of the agreed task.
- Runs checks from [07_verification_checklist.md](07_verification_checklist.md) before handoff.
- **Logs errors** per [04_error_tracking.md](04_error_tracking.md) when discovering failures during work.
- Updates this register when introducing new config keys, log paths, or operational steps.

### 4. Reviewer / auditor

- Reviews diffs for **security** (secrets, injection, logging of PII), **correctness**, and **consistency** with `03_guidelines_and_regulations.md`.
- Confirms that **error and log** documentation still matches the code.

## Review gates (minimum)

1. **Static:** Python compiles; no unintended secret additions in commits.
2. **Config:** All new TOML keys documented in `new_bot/config1.toml` comments or in `info/`.
3. **Runtime (when possible):** dry-run or staging with test credentials; Playwright and Redis as per checklist.
4. **Handoff:** Update `06_future_direction.md` if known follow-ups remain.

## AI agent-specific duties

- Treat `info/` as the **continuity anchor** across sessions.
- Prefer **small, focused diffs**; avoid drive-by refactors.
- When monitoring “all errors and logs,” rely on **`browser_error_reports/*.json`**, **`logs/error_register.jsonl`**, and logs — and follow **sequential triage** in [08_triage_and_success.md](08_triage_and_success.md): do not abandon the current failure because a new one appeared.
