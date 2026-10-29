#!/usr/bin/env python3
"""Validate catalog fields. Fails if a test or verified-run mark has no log."""

import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from yaml_util import load_yaml  # noqa: E402

TYPES = {"agent", "harness", "model", "benchmark", "tool"}
INTERFACES = {"browser", "desktop", "desktop-linux", "desktop-macos", "desktop-windows"}
RUNS = {"yes", "no", "partial"}
BANNED = ("star this", "please star", "give us a star", "give a star", "don't forget to star")
SHA = re.compile(r"^[0-9a-f]{40}$")


def age_days(day_text, today):
    year, month, day = (int(part) for part in day_text.split("-"))
    return (today - date(year, month, day)).days


def require(errors, ok, message):
    if not ok:
        errors.append(message)


def check_record(record, today, stale_days, errors, ids):
    name = record.get("id") or record.get("github")
    require(errors, name not in ids, f"duplicate id {name}")
    ids.add(name)
    for field in ("github", "stars", "last_commit", "last_commit_sha", "metadata_fetched_at"):
        require(errors, record.get(field) not in (None, ""), f"{name}: missing {field}")
    require(errors, isinstance(record.get("stars"), int) and record["stars"] >= 0, f"{name}: stars must be a non-negative int")
    require(errors, bool(SHA.match(record.get("last_commit_sha") or "")), f"{name}: last_commit_sha is not 40 hex chars")
    if record.get("repo_last_commit_sha"):
        require(errors, bool(SHA.match(record["repo_last_commit_sha"])), f"{name}: repo_last_commit_sha is not 40 hex chars")
    require(errors, record.get("stale") is (age_days(record["last_commit"], today) >= stale_days), f"{name}: stale flag does not match the commit date")
    description = record.get("github_description") or ""
    own = (record.get("description") or "").strip()
    if own and description and own == description.strip():
        errors.append(f"{name}: description copies the GitHub description")
    for phrase in BANNED:
        if phrase in own.lower() or phrase in (record.get("note") or "").lower():
            errors.append(f"{name}: contains '{phrase}'")


def check_entries(document, errors):
    today = date.fromisoformat(document["collected_on"])
    stale_days = int(document["stale_after_days"])
    ids = set()
    require(errors, document.get("entries"), "entries.yml has no entries")
    for record in document["entries"]:
        name = record.get("id", "?")
        check_record(record, today, stale_days, errors, ids)
        for field in (
            "name",
            "link",
            "authors",
            "type",
            "interface",
            "runs_locally",
            "description",
            "listed_on",
            "test_status",
            "sources",
        ):
            require(errors, record.get(field) not in (None, "", []), f"{name}: missing {field}")
        require(errors, record.get("type") in TYPES, f"{name}: bad type {record.get('type')}")
        require(errors, record.get("runs_locally") in RUNS, f"{name}: bad runs_locally")
        if record.get("runs_locally") != "yes":
            require(errors, record.get("runs_locally_note"), f"{name}: runs_locally_note required")
        interfaces = record.get("interface") or []
        require(errors, isinstance(interfaces, list) and interfaces, f"{name}: interface must be a list")
        for item in interfaces:
            require(errors, item in INTERFACES, f"{name}: unknown interface {item}")
        description = (record.get("description") or "").strip()
        require(errors, len(description) >= 80, f"{name}: description is too short")
        require(errors, record.get("link", "").startswith("https://"), f"{name}: link must be https")
        require(errors, record["github"] in record["link"], f"{name}: link does not contain the github slug")
        status = record.get("test_status")
        require(errors, status in {"not_tested", "tested"}, f"{name}: bad test_status")
        if status == "tested":
            for field in ("test_date", "test_version", "test_result", "test_steps", "cost_per_step_usd", "price_source", "price_date", "test_log"):
                require(errors, record.get(field) not in (None, ""), f"{name}: tested but missing {field}")
            require(errors, record.get("test_result") in {"ok", "failed", "partial"}, f"{name}: bad test_result")
            log = ROOT / record["test_log"]
            require(errors, log.is_file(), f"{name}: test log missing at {record.get('test_log')}")
        else:
            for field in ("test_result", "cost_per_step_usd", "test_log"):
                require(errors, field not in record, f"{name}: {field} set without test_status tested")
        verified = record.get("verified_run")
        if verified:
            for field in ("kind", "date", "version", "how", "log"):
                require(errors, verified.get(field), f"{name}: verified_run missing {field}")
            require(errors, verified.get("kind") in {"run", "install"}, f"{name}: bad verified_run.kind")
            log = ROOT / verified["log"]
            require(errors, log.is_file(), f"{name}: verified_run log missing")
            if log.is_file():
                text = log.read_text(encoding="utf-8")
                require(errors, verified["version"] in text, f"{name}: log does not mention the recorded version")
                require(errors, "not tested" in text.lower() or "shared task" in text.lower(), f"{name}: log does not say what was not claimed")
        listed = record.get("listed_on") or ""
        require(errors, bool(re.match(r"^\d{4}-\d{2}-\d{2}$", listed)), f"{name}: listed_on must be YYYY-MM-DD")
        if re.match(r"^\d{4}-\d{2}-\d{2}$", listed):
            require(errors, listed <= today.isoformat(), f"{name}: listed_on is after the collection date")


def check_excluded(document, errors):
    today = date.fromisoformat(document["collected_on"])
    stale_days = int(document["stale_after_days"])
    ids = set()
    for record in document["entries"]:
        check_record(record, today, stale_days, errors, ids)
        require(errors, record.get("exclusion") in {"before_window", "out_of_scope", "not_screen_loop"}, f"{record.get('github')}: bad exclusion")
        require(errors, len(record.get("exclusion_detail") or "") >= 40, f"{record.get('github')}: exclusion_detail too short")


def check_bench(errors):
    html = (ROOT / "bench/site/index.html").read_text(encoding="utf-8")
    for field in ("full_name", "email", "city", "download"):
        require(errors, f'id="{field}"' in html, f"bench form missing #{field}")
    require(errors, "result.csv" in html, "bench form does not mention result.csv")


def main():
    errors = []
    entries = load_yaml(ROOT / "data/entries.yml")
    excluded = load_yaml(ROOT / "data/excluded.yml")
    require(errors, entries.get("collected_on") == excluded.get("collected_on"), "collected_on differs between data files")
    check_entries(entries, errors)
    check_excluded(excluded, errors)
    today = date.fromisoformat(entries["collected_on"])
    seen = set()
    for record in entries.get("related_lists") or []:
        check_record(record, today, int(entries["stale_after_days"]), errors, seen)
        require(errors, record.get("note"), f"{record.get('github')}: related list missing note")
        require(errors, record.get("link", "").startswith("https://github.com/"), f"{record.get('github')}: related link")
    check_bench(errors)
    for name in ("assets/stars.png", "assets/social-preview.png"):
        path = ROOT / name
        require(errors, path.is_file() and path.stat().st_size > 5000, f"missing generated image {name}")
    if errors:
        print(f"{len(errors)} catalog error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    tested = sum(1 for record in entries["entries"] if record["test_status"] == "tested")
    verified = sum(1 for record in entries["entries"] if record.get("verified_run"))
    print(f"ok: {len(entries['entries'])} listed, {tested} tested, {verified} verified runs or installs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
