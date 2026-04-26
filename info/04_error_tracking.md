# Error tracking

## 1. Goals

- **Classify** failures (proxy, CAPTCHA, network, application logic) for faster triage.
- **Retain** a durable record of notable errors during development and pilot runs.
- **Capture the browser state** (responses visible in the page, not only Python exceptions) so long sessions stay auditable.
- **Avoid** logging full secrets or raw tokens.

## 2. Sequential triage rule

Do **not** skip ahead to a new error class while the current blocker is still unexplained. See [08_triage_and_success.md](08_triage_and_success.md).

## 3. Browser-side capture (`capture_browser_error_bundle`)

On selected failures, `new_bot/visa_bot.py` writes:

| Output | Contents |
|--------|----------|
| `new_bot/browser_error_reports/<user>_<reason>_<timestamp>.json` | `url`, `title`, `visible_text` (truncated), `html_snippet`, `html_total_len`, `dom_error_hints`, optional `extra_context` (e.g. server login message fields), paths to screenshot. |
| Same stem `.png` | Full-page screenshot. |
| `Visa_bot/logs/error_register.jsonl` | One JSON line with `reason`, `browser_report_json` (path relative to repo parent), `url`, `error_class`, `username_ref`. Login failures may also include `http_status`, `server_message_type`, `server_message_description` (truncated), `triage_hint` (copied from `extra_context` when present). |

**Config (TOML):** `browser_error_max_text_chars`, `browser_error_max_html_chars`.

Server-side login text is normalized before logging when obvious mojibake appears (for example `DispÃµe` -> `Dispõe`) so repeated patterns stay searchable and readable.

`Questionario` navigation now retries a few times before being classified as `form_flow_error`, so transient post-login navigation failures should produce clearer evidence than a single-shot reload fallback.

**Typical `reason` values:** `login_rejected_server`, `login_rejected_suspect`, `login_submit_timeout`, `form_flow_error`, `critical_playwright`.

## 4. Other surfaces

| Source | Mechanism | Notes |
|--------|-----------|------|
| Python runtime | `logging` + `colorlog` | Levels from `config1.toml`. |
| Legacy screenshots | `new_bot/debug_screenshots/` | Additional PNG on some critical paths. |
| HTML dumps | `new_bot/debug_html/` | From `_save_debug_html()` (e.g. login rejection). |
| Worker / queue | `logger` in `worker`, `main_execution_continuous` | Crashed workers logged and restarted. |
| CAPTCHA | `captcha_stats_report()`, `captcha_router.report()` | Aggregated stats. |
| Telegram | `send_telegram_alert` | Optional alerts. |

For major login/CAPTCHA validation failures, prefer raising while the page is still open and let the outer Playwright handler close resources after `capture_browser_error_bundle()` runs; otherwise reports degrade to `about:blank` / closed-target noise.

## 5. Structured register (JSON Lines)

**Path:** `Visa_bot/logs/error_register.jsonl` (gitignored).

Each line is one JSON object; fields evolve but commonly include:

```json
{
  "ts_utc": "2026-04-14T12:00:00Z",
  "component": "playwright_browser",
  "severity": "error",
  "reason": "form_flow_error",
  "username_ref": "short_handle",
  "error_class": "timeout",
  "browser_report_json": "new_bot/browser_error_reports/…",
  "url": "https://…",
  "build": "new_bot",
  "http_status": 200,
  "server_message_type": "error",
  "triage_hint": "Optional short hint for agents (no secrets)."
}
```

**`error_class` (exemplos estáveis):** `login_server`, `login_server_suspect`, `rate_limited`, `server_http`, `timeout`, `form_flow`; outros continuam via `_classify_proxy_error()`.

`ReCaptchaError` do servidor deve ser lido em dois níveis:
- `mais 0 tentativas` = quota esgotada / bloqueio progressivo (`recaptcha_quota`)
- `mais N tentativas` com `N > 0` = aviso suave; pausar em `failed_retry_later` antes de voltar a testar

**Duplicados:** após `login_rejected_server` (e variantes que já chamam `capture_browser_error_bundle`), e após `form_flow_error`, o handler `critical_playwright` deixa de registar segunda linha para a mesma falha.

## 6. Classification helpers

- `_classify_proxy_error()` maps network strings to categories (`tunnel_fail`, `timeout`, `banned`, `captcha`, etc.).

## 7. Process for agents

1. On a **new** recurring pattern, ensure one bundle exists under `browser_error_reports/` and a line in `error_register.jsonl`.
2. **Fix the current issue** before opening a new tracking thread for unrelated errors.
3. Rotate or archive large log files periodically.
4. Release browser contexts only after successful runs; invalidate them after failed runs so the next bundle is not polluted by stale `about:blank` / closed-target state.

## 8. Gitignore

`logs/`, `debug_screenshots/`, and `browser_error_reports/` are ignored locally (see repo `.gitignore`).
