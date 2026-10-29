#!/usr/bin/env python3
"""Refresh stars, SPDX ids, and commit dates from the GitHub API.

Writes data/entries.yml and data/excluded.yml. Does not push anywhere.
A stale entry is one whose tracked commit is 90 days old or older.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from yaml_util import dump_yaml, load_yaml  # noqa: E402

API = "https://api.github.com"
STALE_DAYS = 90


def token():
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(key)
        if value:
            return value
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise SystemExit(f"No GitHub token available: {exc}") from exc


def api_get(url, auth, retries=3):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {auth}",
            "User-Agent": "awesome-computer-use-refresh",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response), None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            last_error = f"HTTP {exc.code} for {url}: {body}"
            if exc.code not in (403, 429, 502, 503) or attempt == retries - 1:
                return None, last_error
        except urllib.error.URLError as exc:
            last_error = f"URL error for {url}: {exc.reason}"
            if attempt == retries - 1:
                return None, last_error
        time.sleep(2 * (attempt + 1))
    return None, last_error


def commit_date(commit):
    raw = commit["commit"]["committer"]["date"]
    return raw[:10], commit["sha"]


def age_days(day_text, today):
    year, month, day = (int(part) for part in day_text.split("-"))
    return (today - date(year, month, day)).days


def refresh_record(record, auth, today, fetched_at):
    slug = record["github"]
    repo, error = api_get(f"{API}/repos/{slug}", auth)
    if error:
        record["metadata_error"] = error
        return False
    branch = repo.get("default_branch") or "main"
    commit, error = api_get(f"{API}/repos/{slug}/commits/{branch}", auth)
    if error:
        record["metadata_error"] = error
        return False
    repo_day, repo_sha = commit_date(commit)
    record["stars"] = int(repo["stargazers_count"])
    license_info = repo.get("license") or {}
    record["license_spdx"] = license_info.get("spdx_id")
    record["github_description"] = repo.get("description")
    record["repo_last_commit"] = repo_day
    record["repo_last_commit_sha"] = repo_sha
    record["default_branch"] = branch
    tracked_day, tracked_sha = repo_day, repo_sha
    github_path = record.get("github_path")
    if github_path:
        encoded = urllib.request.quote(github_path, safe="/")
        path_url = f"{API}/repos/{slug}/commits?path={encoded}&sha={branch}&per_page=1"
        commits, error = api_get(path_url, auth)
        if error or not commits:
            record["metadata_error"] = error or f"No commits for path {github_path}"
            return False
        tracked_day, tracked_sha = commit_date(commits[0])
    record["last_commit"] = tracked_day
    record["last_commit_sha"] = tracked_sha
    record["stale"] = age_days(tracked_day, today) >= STALE_DAYS
    record["metadata_fetched_at"] = fetched_at
    record.pop("metadata_error", None)
    return True


def refresh_file(path, key, auth, today, fetched_at):
    document = load_yaml(path)
    failures = []
    changes = []
    before = json.dumps(document.get(key), sort_keys=True, default=str)
    for record in document[key]:
        previous = {
            "stars": record.get("stars"),
            "last_commit": record.get("last_commit"),
            "license_spdx": record.get("license_spdx"),
            "stale": record.get("stale"),
        }
        ok = refresh_record(record, auth, today, fetched_at)
        if not ok:
            failures.append(f"{record.get('id') or record.get('github')}: {record.get('metadata_error')}")
            continue
        current = {
            "stars": record.get("stars"),
            "last_commit": record.get("last_commit"),
            "license_spdx": record.get("license_spdx"),
            "stale": record.get("stale"),
        }
        if current != previous:
            changes.append(
                {
                    "id": record.get("id") or record.get("github"),
                    "before": previous,
                    "after": current,
                }
            )
    document["collected_on"] = today.isoformat()
    document["stale_after_days"] = STALE_DAYS
    after = json.dumps(document.get(key), sort_keys=True, default=str)
    dump_yaml(document, path)
    return failures, changes, before != after


def main():
    auth = token()
    now = datetime.now(timezone.utc)
    today = now.date()
    fetched_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    all_failures = []
    report = {"fetched_at": fetched_at, "files": {}}
    jobs = [
        ("data/entries.yml", "entries"),
        ("data/entries.yml", "related_lists"),
        ("data/excluded.yml", "entries"),
    ]
    for filename, key in jobs:
        failures, changes, dirty = refresh_file(ROOT / filename, key, auth, today, fetched_at)
        all_failures.extend(failures)
        report["files"][f"{filename}#{key}"] = {"changed_records": changes, "rewritten": dirty}
    print(json.dumps(report, indent=2))
    if all_failures:
        print("Refresh failures:", file=sys.stderr)
        for line in all_failures:
            print(line, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
