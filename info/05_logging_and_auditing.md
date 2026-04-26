# Logging and auditing

## 1. Configuration (TOML)

Relevant keys in `new_bot/config1.toml`:

- `log_level` — root logger threshold.
- `logger_console_level` / `logger_file_level` — console vs file handlers in `setup_logging()`.
- `log_to_file` — when `true`, file logging is enabled (path resolved in code relative to working directory).

Adjust per environment: **DEBUG** for short investigations only; **INFO** for normal operation.

## 2. What gets logged

- **Process identity:** Logs are prefixed with process id in multi-worker setups.
- **Proxy flow:** Session creation, rotation, scoring updates (via `StateManager` / `ProxyLeaseManager`).
- **CAPTCHA:** Provider selection, dual-service winner, periodic stats (`captcha_stats_report`, router report).
- **Playwright:** Major steps (URLs, form submission milestones); raw server snippets may be truncated (e.g. first 300 chars) — avoid logging full PII.
- **Queue monitor:** Every ~30 seconds in continuous mode — pending queue length and active workers.

## 3. Auditing vs debugging

| Purpose | Tooling |
|---------|---------|
| Audit trail of runs | Timestamped log lines; optional log file if `log_to_file` |
| Forensics on failure | `debug_screenshots/` PNGs on critical Playwright errors |
| CAPTCHA performance | In-memory stats + periodic log lines |
| External alerts | Telegram (`send_telegram_alert`, `send_status_report`) |

## 4. Recommendations

- Enable **file logging** during pilot runs for post-hoc review.
- **Redact** pasted credentials in any issue tracker or chat.
- For compliance, define **retention** for log files and screenshots (e.g. delete after N days).

## 5. Continuous monitoring (manual / automated)

- Watch for **repeated** `[Monitor] Worker crashou` lines — indicates systemic issues (bad deploy, Redis, binary).
- Watch **CAPTCHA** failure bursts — balance, provider outage, or site key change.
