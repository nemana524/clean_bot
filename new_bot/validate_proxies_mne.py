#!/usr/bin/env python3
"""Test each line in a proxy list against MNE without overwriting input by default."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

BASE = "https://pedidodevistos.mne.gov.pt/VistosOnline/"


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_mne_ok{input_path.suffix}")


def parse_proxy_line(line: str) -> tuple[str, str, str, str] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = line.split(":")
    if len(parts) < 4:
        return None
    ip, port, user = parts[0], parts[1], parts[2]
    pwd = ":".join(parts[3:])
    return ip, port, user, pwd


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=Path("verified_proxies.txt"))
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write kept proxies to a separate file. Defaults to <input>_mne_ok.txt.",
    )
    ap.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input file in place after creating a timestamped backup.",
    )
    ap.add_argument(
        "--allow-empty-output",
        action="store_true",
        help="Allow an in-place overwrite even when zero proxies were kept.",
    )
    ap.add_argument("--delay", type=float, default=2.5, help="Seconds between checks")
    ap.add_argument("--timeout", type=float, default=25.0)
    args = ap.parse_args()

    if args.in_place and args.output is not None:
        ap.error("--output cannot be combined with --in-place")

    output_path = args.input if args.in_place else (args.output or default_output_path(args.input))
    try:
        same_path = output_path.resolve() == args.input.resolve()
    except OSError:
        same_path = output_path == args.input
    if same_path and not args.in_place:
        ap.error("Refusing to overwrite the input file without --in-place")

    raw = args.input.read_text(encoding="utf-8", errors="replace").splitlines()
    lines = [ln for ln in raw if ln.strip()]
    ok_lines: list[str] = []
    bad: list[tuple[str, str]] = []

    print(f"Testing {len(lines)} entries against {BASE} (delay={args.delay}s)...", flush=True)

    for i, line in enumerate(lines):
        parsed = parse_proxy_line(line)
        if not parsed:
            print(f"[skip format] {line[:60]!r}", flush=True)
            continue
        ip, port, user, pwd = parsed
        proxy_url = f"http://{quote(user, safe='')}:{quote(pwd, safe='')}@{ip}:{port}"
        label = f"{ip}:{port}"
        try:
            with httpx.Client(proxy=proxy_url, timeout=args.timeout, verify=True, follow_redirects=True) as c:
                r = c.get(BASE)
            code = r.status_code
            if code == 403:
                bad.append((label, f"HTTP {code} blocked"))
                print(f"[BAD]  {label} -> {code}", flush=True)
            elif code >= 500:
                bad.append((label, f"HTTP {code}"))
                print(f"[BAD]  {label} -> {code}", flush=True)
            elif code in (200, 301, 302, 303, 307, 308):
                ok_lines.append(line.strip())
                print(f"[OK]   {label} -> {code}", flush=True)
            else:
                ok_lines.append(line.strip())
                print(f"[OK?]  {label} -> {code} (keeping)", flush=True)
        except Exception as e:
            bad.append((label, str(e)[:120]))
            print(f"[BAD]  {label} -> {e!s}", flush=True)

        if i + 1 < len(lines):
            time.sleep(args.delay)

    if args.in_place and not ok_lines and not args.allow_empty_output:
        print(
            "\nRefusing to overwrite the live proxy file with zero kept proxies. "
            "Review the report first or rerun with --allow-empty-output if that is truly intended.",
            flush=True,
        )
        return 2

    backup_path = None
    if args.in_place:
        ts = time.strftime("%Y%m%d_%H%M%S")
        backup_path = args.input.with_name(f"{args.input.name}.bak.{ts}")
        backup_path.write_text(
            args.input.read_text(encoding="utf-8", errors="replace"),
            encoding="utf-8",
        )

    output_path.write_text("\n".join(ok_lines) + ("\n" if ok_lines else ""), encoding="utf-8")
    report_path = output_path.parent / "proxy_validation_report.txt"
    report_lines = [
        f"URL: {BASE}",
        f"Kept: {len(ok_lines)} / {len(lines)}",
        f"Output: {output_path}",
        "",
        "Removed:",
    ]
    if backup_path is not None:
        report_lines.insert(3, f"Backup: {backup_path}")
    for b, reason in bad:
        report_lines.append(f"  {b}: {reason}")
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"\nKept {len(ok_lines)} / {len(lines)} lines -> {output_path}", flush=True)
    if backup_path is not None:
        print(f"Backup -> {backup_path}", flush=True)
    print(f"Report -> {report_path}", flush=True)
    if bad:
        print("\nRemoved summary (first 20):", flush=True)
        for b, reason in bad[:20]:
            print(f"  {b}: {reason}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
