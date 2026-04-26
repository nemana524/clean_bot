# Guidelines and strict regulations

## 1. Legal and ethical use

- Automation must comply with **terms of service** of the target site and applicable law. The team is responsible for confirming that unattended or high-frequency booking behavior is permitted.
- This codebase is a **technical tool**; misuse (credential stuffing, circumventing security controls beyond allowed use) is out of scope and must not be assisted.

## 2. Secrets and configuration

- **Never** store live API keys, Telegram bot tokens, or passwords in documentation under `info/` or in example snippets in a way that duplicates production values.
- Prefer **environment variables** or a secret manager for production; keep `config1.toml` as local template with placeholders when sharing.
- If credentials appear in git history, **rotate** them at the provider.

## 3. Code change discipline

- One logical change per task; avoid unrelated formatting or refactors.
- Match existing style (imports, logging, Portuguese log messages where already used).
- New features should be **configurable** via TOML when they affect timing, retries, or provider behavior.

## 4. Data handling

- CSV files (`creds_2.csv`, etc.) may contain **personal data**. Restrict file permissions; do not upload to public channels.
- Debug screenshots under `debug_screenshots/` may contain PII; treat as sensitive.

## 5. Dependencies

- Install from `new_bot/requirements.txt` in a virtual environment.
- Run `playwright install` after dependency install for browser binaries.

## 6. Operations

- **Redis:** Optional but recommended for multi-worker queue; set `REDIS_HOST` / `REDIS_PORT` if not localhost.
- **Monitoring:** Parent process logs queue depth every ~30s in continuous mode; see [05_logging_and_auditing.md](05_logging_and_auditing.md).
- **Proxy validation:** Use `python validate_proxies_mne.py --input verified_proxies.txt` to write a separate reviewed output file first. Only overwrite the live proxy file with `--in-place`, which now creates a backup.
- **Direct mode isolation:** if `use_proxy=false`, never share cached browser/session cookies across different usernames on the same local IP.

## 7. Documentation duty

Any change that affects operators or reviewers **must** update the relevant `info/*.md` file in the same delivery window.
