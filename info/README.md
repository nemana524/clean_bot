# Register `info` — master index

This folder is the **single source of truth** for project governance, analysis, verification, logging expectations, and ongoing work. All agents and humans working on this codebase should read and update these documents as the project evolves.

| Document | Purpose |
|----------|---------|
| [01_comparative_analysis.md](01_comparative_analysis.md) | Side-by-side analysis of `pre_bot` vs `new_bot` (architecture, deltas, risks). |
| [02_role_and_responsibilities.md](02_role_and_responsibilities.md) | Who does what (developer, reviewer, automation agent) and review gates. |
| [03_guidelines_and_regulations.md](03_guidelines_and_regulations.md) | Non-negotiable rules: compliance, security, config hygiene, testing. |
| [04_error_tracking.md](04_error_tracking.md) | How errors are surfaced, logged, classified, and recorded. |
| [05_logging_and_auditing.md](05_logging_and_auditing.md) | Log levels, file vs console, Telegram, CAPTCHA stats, monitors. |
| [06_future_direction.md](06_future_direction.md) | Known gaps, next implementation steps, client handoff checklist. |
| [07_verification_checklist.md](07_verification_checklist.md) | Pre-release and runtime checks. |
| [08_triage_and_success.md](08_triage_and_success.md) | Success definition, sequential triage, browser evidence, 2-day focus. |

## Quick facts

- **Legacy baseline:** `pre_bot/Visa-Appointment-Bot-0120-3-fast.py` (~8.7k lines), config `pre_bot/config1.toml`.
- **Current implementation:** `new_bot/visa_bot.py` (~8.8k lines), config `new_bot/config1.toml`, manifest `new_bot/registry.json`.
- **Runtime:** Python 3.11+ recommended; dependencies in `new_bot/requirements.txt` (Playwright, Redis, httpx, etc.).

## Maintenance rule

When behavior, config keys, or operational procedures change, update the relevant file here in the same change set (or immediately after), so this register stays authoritative.
