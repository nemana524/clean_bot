# Verification checklist

Use this before declaring a build **ready** for pilot or production.

## Static

- [ ] `python3 -m py_compile new_bot/visa_bot.py` succeeds.
- [ ] `pip install -r new_bot/requirements.txt` succeeds in a clean venv.
- [ ] No new secrets in committed diffs.

## Configuration

- [ ] `new_bot/config1.toml` paths (`proxy_file_path`, `creds_file_path`, `second_form_json_file`) point to existing files or are updated.
- [ ] Booking fields (`consular_post_id`, `nationality_of_country`, `country_of_residence`, `intended_date_of_arrival`, etc.) match client requirements.

## Runtime (staging)

- [ ] `playwright install` completed for the target OS.
- [ ] Redis reachable if using multi-process queue (`redis-cli ping`), or single-worker path verified.
- [ ] Short run: bot starts, loads CSV, workers spawn without immediate crash.
- [ ] CAPTCHA: at least one successful solve path in test (or sandbox key) if permitted.

## Observability

- [ ] Log level appropriate; file logging enabled if auditing is required.
- [ ] Telegram optional: test message path if used.
- [ ] `debug_screenshots/` inspected only on failure; no sensitive sharing.

## Post-run

- [ ] Append notable new errors to `logs/error_register.jsonl` (see [04_error_tracking.md](04_error_tracking.md)).
- [ ] Update `06_future_direction.md` if gaps remain.
