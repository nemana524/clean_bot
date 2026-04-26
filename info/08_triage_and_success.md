# Triage discipline, success criteria, and timeboxing

## Strict success criterion

**Success** means one **complete, correct booking** for the applicant: the flow reaches the intended outcome (including PDF / confirmation as defined by the client), with data matching `config1.toml` and consular rules. Partial logins or incomplete forms do not count as success.

Site **behavior and policy** (what is bookable, when) are for the **client** to decide; engineering focuses on **reliability, speed, and traceability** of each run.

## Sequential error handling (no skipping)

To avoid confusion in long sessions, use this order:

1. **Stop** on the first failure that blocks progress.
2. **Capture** evidence for *that* failure (see [04_error_tracking.md](04_error_tracking.md)) before changing multiple things at once.
3. **Fix or classify** that failure (config, proxy, CAPTCHA, selector, session).
4. **Re-run** and confirm the fix; only then treat the *next* error as the active issue.

If a second error appears while fixing the first, **still finish diagnosing the first** unless it is clearly a cascade of the same root cause (e.g. session lost → all subsequent pages fail). In that case, document “root cause: session lost” and fix session stability first.

When a user lands in `failed_retry_later`, treat it as a paused terminal state for that run. Change one lever first (proxy pool, CAPTCHA, credentials, timing), then manually reset the CSV status to `pending` or `false` before retrying.

## Evidence from the browser (primary)

The bot records **what the browser actually shows**, not only Python stack traces:

- **`new_bot/browser_error_reports/*.json`** — URL, title, visible text, HTML snippet, DOM error hints, optional `extra_context` (e.g. server login message type/description), paired **`.png`** screenshot.
- **`logs/error_register.jsonl`** — one JSON line per capture with pointer to the report file.
- **Logs** — login API JSON / raw snippets where the code already logs `result_data`.

Use these artifacts to decide whether the problem is **server-side message**, **DOM / UI**, **network/proxy**, or **CAPTCHA**.

## Rapid recovery playbook (when something breaks)

1. Open the latest **`browser_error_reports`** JSON for the failing `reason` (e.g. `login_rejected_server`, `form_flow_error`).
2. Read **`extra_context`** and **`dom_error_hints`** first, then **`visible_text`**.
3. Cross-check **`url`** and official portal constraints (cookies, session, rescheduling limits, document formats — see FAQ-style content on the portal and your captured notes).
4. Adjust **one lever** (proxy pool, CAPTCHA balance, `intended_date_of_arrival`, timing) and re-test.

## Two-day delivery focus

Prioritize, in order:

1. **End-to-end booking** on staging/test accounts with **`browser_error_reports`** + logs proving stability.
2. **Config accuracy** (dates, post, nationality) and **proxy/CAPTCHA** health.
3. Nice-to-haves (extra automation, refactors) only if time remains.

Update [06_future_direction.md](06_future_direction.md) when a gap is closed or deferred.
