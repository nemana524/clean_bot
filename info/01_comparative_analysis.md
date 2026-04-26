# Comparative analysis: `pre_bot` vs `new_bot`

## 1. Scope and lineage

Both trees implement the same conceptual system: a **Playwright-based** automation stack for the Portuguese visa online flow (`pedidodevistos.mne.gov.pt`), with **TLS/httpx** sessions, **multi-provider reCAPTCHA** solving (Anti-Captcha, 2Captcha, CapMonster, CapSolver), **proxy rotation and scoring**, **Redis-backed dynamic work queue** (with in-memory fallback), **Telegram** alerts, CSV credential tracking, and extensive **browser fingerprint / stealth** scripts.

`new_bot/visa_bot.py` is a direct derivative of `pre_bot/Visa-Appointment-Bot-0120-3-fast.py` with targeted performance and reliability tuning plus a small set of new configuration knobs. Line counts differ by roughly **+47 lines** in `new_bot` (mostly helpers and substituted call sites).

## 2. Structural similarity

- **Shared:** Same major components (grep-able structure matches): `TLSClient`, `StateManager`, `ProxyLeaseManager`, `CAPTCHARouter`, `TokenBuffer`, `ProxyCookiePool`, `BrowserContextPool`, `HumanSimulator`, `solve_recaptcha_v2`, `playwright_login` / `_playwright_login_internal`, `Login`, `WorkQueue`, `worker`, `main_execution_continuous`, etc.
- **pre_bot only:** Single monolithic script + `config1.toml`; no `requirements.txt` in-folder (dependencies implied by imports).
- **new_bot additions:** `requirements.txt`, `registry.json` (build metadata and rationale summary), extended `config1.toml` comments and new keys.

## 3. Documented behavioral differences (verified in code)

| Area | `pre_bot` | `new_bot` |
|------|-----------|-----------|
| CAPTCHA result polling | Fixed loop: `range(30)` with `_time.sleep(3)` (~90s max, 3s granularity) | Configurable: `captcha_poll_interval_sec` (default 1.5s) × `captcha_max_poll_iterations` (default 60) |
| Low CAPTCHA balance wait | `await asyncio.sleep(300)` in `Login` | `captcha_balance_wait_sec` (default 120) |
| Worker queue idle polling | `check_interval` passed as literal **10** from `main_execution_continuous` | `queue_check_interval` from config (default **3**) |
| Retries per user in `worker` | `max_user_attempts = 2` (hardcoded) | `max_user_attempts` from config via `_cfg_int(..., 4)` |
| Schedule UI fixed waits | `wait_for_timeout(2000)`, `(1500)`, `(3000)` in schedule branch | Same durations routed through `_ui_wait()` when `fast_ui_delays` + `ui_wait_scale` |
| Humanization delays | Fixed random ranges in `HumanSimulator` | Same logic but scaled by `_human_delay_scale()` / `_hs_delay()` when `fast_human_delays` + `human_delay_scale` |

## 4. Configuration

- **Shared sensitive surface:** Both `config1.toml` files embed API keys, Telegram credentials, and account defaults. **These must not be copied into public docs** and should be rotated if they were ever exposed.
- **new_bot-only keys (examples):** `captcha_poll_interval_sec`, `captcha_max_poll_iterations`, `max_workers`, `queue_check_interval`, `max_user_attempts`, `captcha_balance_wait_sec`, `fast_ui_delays`, `ui_wait_scale`, `fast_human_delays`, `human_delay_scale`.

## 5. Accuracy vs speed (honest assessment)

- **Speed:** `new_bot` reduces several fixed waits and tightens CAPTCHA polling and queue polling; this should shorten typical cycles when the bottleneck is configuration or idle polling.
- **Accuracy:** “Accuracy” here is mostly **correct alignment of booking dates with available slots and site rules** (see comments in `new_bot/config1.toml`). The code changes do not replace the need for **correct `intended_date_of_arrival`**, valid proxies, and CAPTCHA balance. Misconfiguration still yields zero usable slots or failed logins.

## 6. Known limitations (both)

- **Sniper / prewarm TOML keys** (`sniper_poll_interval`, `prewarm_mode`, etc.) are documented in config; full automatic slot-refresh loops may still require additional Playwright flow work (as noted in `registry.json`).
- **Success rate** depends on external factors: site changes, proxy quality, CAPTCHA provider performance, and account state.

## 7. Static verification performed (2026-04-14)

- `python3 -m py_compile new_bot/visa_bot.py` — **passed** (syntax OK).

Further verification (runtime, Playwright, Redis) is listed in [07_verification_checklist.md](07_verification_checklist.md).
