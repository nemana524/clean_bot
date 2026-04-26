# Future direction

This section tracks **known gaps** and **planned** work to bring `new_bot` to client-ready quality. Update as tasks complete.

## Completed baseline (current)

- CAPTCHA polling interval and max iterations configurable.
- Queue idle poll interval configurable (`queue_check_interval`).
- Per-user retry count configurable (`max_user_attempts`).
- Low CAPTCHA balance wait configurable (`captcha_balance_wait_sec`).
- UI and humanization delay scaling (`fast_ui_delays`, `ui_wait_scale`, `fast_human_delays`, `human_delay_scale`).
- `registry.json` documents rationale and limitations.
- **Browser error bundles:** `capture_browser_error_bundle()` writes JSON + screenshot under `browser_error_reports/`, appends to `logs/error_register.jsonl`, including login rejection / timeout / form-flow / critical paths.

## Two-day milestone (priority order)

1. Prove **repeatable successful booking** with captures showing clean runs.
2. Stabilize **proxy + CAPTCHA + config** using `browser_error_reports` for any failure.
3. Defer non-essential refactors.

## Recommended next steps

1. **Secrets:** Move API keys and Telegram token to environment variables; keep TOML for non-secret defaults only.
2. **Sniper / slot refresh:** If the client requires automated periodic slot polling, implement an explicit Playwright loop aligned with `sniper_poll_interval` / `sniper_keepalive`, with backoff and rate limits.
3. **pre_bot parity:** Add `requirements.txt` under `pre_bot` if legacy runs must be reproduced, or document that `new_bot` is the only supported runtime.
4. **Optional:** `logging.Handler` to auto-append all ERROR logs to `error_register.jsonl` (browser bundle already covers major Playwright failures).
5. **Tests:** Minimal smoke tests (import `visa_bot`, mock Redis, dry-run config load) in CI if introduced.

## Client handoff checklist

- [ ] Config validated for intended travel dates and post ID.
- [ ] Proxies tested; rotation policy understood.
- [ ] CAPTCHA accounts funded; dual-service behavior verified once.
- [ ] Redis available for multi-worker mode (or accept in-memory limitations).
- [ ] `info/` reviewed with client stakeholders (roles, logging, regulations).
