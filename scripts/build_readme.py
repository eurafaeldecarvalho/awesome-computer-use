#!/usr/bin/env python3
"""Build README.md, the sortable HTML table, and the star chart from data/."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from yaml_util import load_yaml  # noqa: E402

FONT = ROOT / "assets/fonts/DejaVuSans.ttf"
FONT_BOLD = ROOT / "assets/fonts/DejaVuSans-Bold.ttf"

TYPE_ORDER = ("agent", "harness", "model", "benchmark", "tool")
TYPE_HEADING = {
    "agent": "Agents",
    "harness": "Harnesses",
    "model": "Models",
    "benchmark": "Benchmarks",
    "tool": "Tools",
}
INTERFACE_LABEL = {
    "browser": "browser",
    "desktop": "desktop",
    "desktop-linux": "Linux desktop",
    "desktop-macos": "macOS desktop",
    "desktop-windows": "Windows desktop",
}
EXCLUSION_LABEL = {
    "before_window": "Commit before 2026-08-01",
    "out_of_scope": "Outside desktop and browser",
    "not_screen_loop": "Not a screen, accessibility, or DOM loop",
}


def license_label(record):
    api = record.get("license_spdx") or "unset"
    file_spdx = record.get("license_file_spdx")
    if file_spdx and file_spdx != api:
        return f"{file_spdx} (GitHub API: {api})"
    return api


def interfaces(record):
    return ", ".join(INTERFACE_LABEL[item] for item in record["interface"])


def checked(record):
    verified = record.get("verified_run")
    if not verified:
        return "—"
    word = "Ran" if verified["kind"] == "run" else "Installed"
    return f"[{word}]({verified['log']})"


def short_sha(sha):
    return sha[:10]


def top_agents(entries, limit=10):
    agents = [record for record in entries if record["type"] == "agent" and not record.get("github_path")]
    return sorted(agents, key=lambda record: (-record["stars"], record["name"].lower()))[:limit]


def bar(stars, maximum, width=24):
    if maximum <= 0:
        return ""
    filled = max(1, round(width * stars / maximum))
    return "█" * filled


def entry_block(record):
    runs = record["runs_locally"]
    if record.get("runs_locally_note"):
        runs = f"{runs}. {record['runs_locally_note']}"
    models = record.get("models") or "—"
    task = f"Not tested yet. Listed {record['listed_on']}."
    lines = [
        f"### {record['name']}",
        "",
        record["description"],
        "",
        "| | |",
        "| --- | --- |",
        f"| Repository | [{record['github']}]({record['link']}) |",
        f"| Authors | {record['authors']} |",
        f"| Interface | {interfaces(record)} |",
        f"| Models | {models} |",
        f"| Runs locally | {runs} |",
        f"| License | {license_label(record)} |",
        f"| Stars | {record['stars']:,} |",
        f"| Last commit | {record['last_commit']} (`{short_sha(record['last_commit_sha'])}`) |",
        f"| Shared task | {task} |",
        f"| Checked here | {checked(record)} |",
    ]
    if record.get("github_path"):
        lines.append(
            f"| Scope | Stars are for `{record['github']}`, which contains other projects. "
            f"The commit above is the latest on `{record['github_path']}` "
            f"(`{short_sha(record['repo_last_commit_sha'])}` on the default branch is {record['repo_last_commit']}). |"
        )
    if record.get("stale"):
        lines.append("| Stale | Yes. The tracked commit is 90 days old or older. |")
    source_bits = []
    for url in record.get("sources") or []:
        source_bits.append(f"<{url}>")
    if source_bits:
        lines.extend(["", "Sources: " + ", ".join(source_bits) + "."])
    lines.append("")
    return "\n".join(lines)


def comparison_table(agents):
    header = "| Agent | Interface | Runs locally | License | Stars | Last commit | Checked here |"
    rule = "| --- | --- | --- | --- | ---: | --- | --- |"
    rows = [header, rule]
    for record in agents:
        rows.append(
            "| {name} | {interface} | {runs} | {license} | {stars:,} | {commit} | {checked} |".format(
                name=f"[{record['name']}](#{anchor(record['name'])})",
                interface=interfaces(record),
                runs=record["runs_locally"],
                license=license_label(record),
                stars=record["stars"],
                commit=record["last_commit"],
                checked=checked(record),
            )
        )
    return "\n".join(rows)


def anchor(name):
    # GitHub's automatic heading anchors.
    slug = name.strip().lower()
    kept = []
    prev_dash = False
    for char in slug:
        if char.isalnum():
            kept.append(char)
            prev_dash = False
        elif char in " -_":
            if not prev_dash:
                kept.append("-")
                prev_dash = True
    return "".join(kept).strip("-")


def ascii_chart(agents):
    maximum = max(record["stars"] for record in agents)
    width = max(len(record["name"]) for record in agents)
    lines = ["```text"]
    for record in agents:
        lines.append(f"{record['name']:<{width}}  {record['stars']:>7,}  {bar(record['stars'], maximum)}")
    lines.append("```")
    return "\n".join(lines)


def render_readme(entries_doc, excluded_doc):
    entries = entries_doc["entries"]
    collected = entries_doc["collected_on"]
    tested = sum(1 for record in entries if record["test_status"] == "tested")
    verified = sum(1 for record in entries if record.get("verified_run"))
    stale = [record for record in entries if record.get("stale")]
    agents = top_agents(entries)
    counts = {kind: sum(1 for record in entries if record["type"] == kind) for kind in TYPE_ORDER}
    singular = {"agent": "agent", "harness": "harness", "model": "model", "benchmark": "benchmark", "tool": "tool"}
    count_bits = ", ".join(
        f"{counts[kind]} {singular[kind] if counts[kind] == 1 else TYPE_HEADING[kind].lower()}"
        for kind in TYPE_ORDER
        if counts[kind]
    )

    parts = [
        "# Awesome Computer Use",
        "",
        "Computer-use agents operate software the way a person does: they look at a browser or a desktop, then click, type, and scroll. This is a dated catalog of the agents, harnesses, models, benchmarks, and tools behind that loop. Every star count and last-commit date was read from the GitHub API. A project is marked checked only when this repository installed it or ran it, and the log says which.",
        "",
        f"**{len(entries)} listed · {verified} checked in this repo · {tested} tested on the shared task · GitHub facts collected {collected}.**",
        "",
        "No shared-task cost was measured. There is no cost-by-success chart because that would be invented. The bars below are GitHub stars for the ten highest-star agents whose star count belongs to that repository.",
        "",
        f"![Star counts for the ten highest-star agents, collected {collected}](assets/stars.png)",
        "",
        ascii_chart(agents),
        "",
        "## Ten highest-star agents",
        "",
        comparison_table(agents),
        "",
        "The Anthropic desktop demo is listed under Agents, but it is not in this table: its star count belongs to `anthropics/claude-quickstarts`, which also holds unrelated demos.",
        "",
        f"The full catalog is {count_bits}. [Open `docs/compare.html`](docs/compare.html) in a browser and click a column heading to sort every entry. GitHub's own file view does not run that script.",
        "",
    ]
    for kind in TYPE_ORDER:
        group = [record for record in entries if record["type"] == kind]
        group.sort(key=lambda record: (-record["stars"], record["name"].lower()))
        if not group:
            continue
        parts.append(f"## {TYPE_HEADING[kind]}")
        parts.append("")
        for record in group:
            parts.append(entry_block(record))
    parts.extend(stale_section(stale))
    parts.extend(task_section())
    parts.extend(freshness_section(entries_doc))
    parts.extend(contribute_section())
    parts.extend(related_section(entries_doc))
    parts.extend(excluded_section(excluded_doc))
    parts.extend(made_section(collected))
    parts.extend(license_section())
    return "\n".join(parts).rstrip() + "\n"


def stale_section(stale):
    lines = ["## Stale entries", ""]
    if not stale:
        lines.append("None. On the collection date, every listed commit was under 90 days old.")
        lines.append("")
        return lines
    lines.append("These entries are still listed. The weekly refresh only flags them; it does not delete them.")
    lines.append("")
    lines.append("| Entry | Last commit | Stars |")
    lines.append("| --- | --- | ---: |")
    for record in sorted(stale, key=lambda item: item["last_commit"]):
        lines.append(f"| [{record['name']}]({record['link']}) | {record['last_commit']} | {record['stars']:,} |")
    lines.append("")
    return lines


def task_section():
    return [
        "## Shared task",
        "",
        "The task is the same for every entry: open the static page in [`bench/site`](bench/site/index.html), fill three fields (full name, email, city), and download `result.csv`. Nothing on that page calls another website. The steps and the pass rule are in [`bench/tarefa.md`](bench/tarefa.md). [`bench/run.md`](bench/run.md) is the run book.",
        "",
        "v1 did not run that task with a model. The build environment had no OpenAI, Anthropic, Google, or Browser Use API key, so a model-backed agent could not be scored and no cost per step was computed. Where a tool was executed directly, the log says so and the shared-task cell stays \"not tested yet.\"",
        "",
    ]


def freshness_section(document):
    return [
        "## Freshness",
        "",
        f"Facts in this file were collected on {document['collected_on']} from the GitHub API (`stargazers_count`, `license.spdx_id`, and the latest commit on the default branch). When an entry points at a directory inside a larger repository, the commit date is the latest commit that touched that directory, and the star count is still the parent repository's.",
        "",
        "A weekly GitHub Actions workflow runs `scripts/refresh_metadata.py` and opens a pull request with the new numbers. It does not push to `main`. An entry is marked stale when its tracked commit is 90 days old or older. New entries should already be inside that window; see [CONTRIBUTING.md](CONTRIBUTING.md).",
        "",
        "Link checking runs on every pull request and once a week, with [lychee](https://github.com/lycheeverse/lychee) v0.24.2.",
        "",
    ]


def contribute_section():
    return [
        "## Contributing",
        "",
        "Add or correct an entry with a pull request that edits `data/entries.yml` and regenerates this file. The inclusion rule is in [CONTRIBUTING.md](CONTRIBUTING.md): open source or a public API, real computer use of a browser or desktop, an English README, and a commit since 2026-08-01 that is still under 90 days old.",
        "",
        "To mark an entry tested on the shared task, the pull request has to add a log under `logs/<id>/<date>.md` with the command, the version or commit, the result, the step count, and the cost per step with the price source and the date of that price. Without that log the entry stays \"not tested yet.\"",
        "",
    ]


def related_section(document):
    lines = [
        "## Related lists",
        "",
        "These catalogs cover the same ground. This repository does not copy their wording or their outline. Star counts below were read from the GitHub API on the same day as the entries.",
        "",
        "| List | Stars | Last commit |",
        "| --- | ---: | --- |",
    ]
    for record in document["related_lists"]:
        lines.append(f"| [{record['name']}]({record['link']}) | {record['stars']:,} | {record['last_commit']} |")
    lines.append("")
    for record in document["related_lists"]:
        lines.append(f"**{record['name']}.** {record['note']}")
        lines.append("")
    return lines


def excluded_section(document):
    lines = [
        "## Left out on purpose",
        "",
        "These repositories were checked on the same day and left out. The commit date is the default-branch HEAD from the GitHub API. A later commit does not add the project by itself.",
        "",
        "| Repository | Why | Stars | Last commit |",
        "| --- | --- | ---: | --- |",
    ]
    records = sorted(document["entries"], key=lambda record: -record["stars"])
    for record in records:
        why = EXCLUSION_LABEL[record["exclusion"]]
        detail = record["exclusion_detail"].replace("|", "/")
        lines.append(
            f"| [{record['github']}](https://github.com/{record['github']}) | {why}. {detail} | {record['stars']:,} | {record['last_commit']} |"
        )
    lines.append("")
    return lines


def made_section(collected):
    return [
        "## How this list is made",
        "",
        f"AI assistance: a coding agent collected the GitHub facts on {collected}, wrote the descriptions, and recorded the logs for the rows marked checked. Those logs are the agent's notes, not a maintainer sign-off.",
        "",
        "Descriptions were written for this list from the repository, its license file, or the linked paper. They are not copied from other computer-use lists. Benchmark scores printed by a project are not repeated here unless this repository reproduced them, and none were reproduced.",
        "",
        "Regenerate this file after editing the catalog:",
        "",
        "```bash",
        "python3 -m venv .venv",
        ".venv/bin/pip install -r scripts/requirements.txt",
        ".venv/bin/python scripts/refresh_metadata.py",
        ".venv/bin/python scripts/build_readme.py",
        "```",
        "",
        "`scripts/refresh_metadata.py` needs a GitHub token in `GITHUB_TOKEN` or `gh auth token`. It only rewrites metadata fields. It leaves descriptions, test status, and verified-run logs alone.",
        "",
    ]


def license_section():
    return [
        "## License",
        "",
        "This list is [CC0-1.0](LICENSE). The projects it links to keep their own licenses, named in each entry from the GitHub API or from the license file when the API returns `NOASSERTION`.",
        "",
    ]


def html_escape(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_html(entries_doc):
    rows = []
    for record in entries_doc["entries"]:
        verified = record.get("verified_run")
        checked_text = "—" if not verified else ("ran" if verified["kind"] == "run" else "installed")
        rows.append(
            "<tr>"
            f"<td><a href=\"{html_escape(record['link'])}\">{html_escape(record['name'])}</a></td>"
            f"<td>{html_escape(record['type'])}</td>"
            f"<td>{html_escape(interfaces(record))}</td>"
            f"<td>{html_escape(record['runs_locally'])}</td>"
            f"<td>{html_escape(license_label(record))}</td>"
            f"<td data-sort=\"{record['stars']}\">{record['stars']:,}</td>"
            f"<td>{html_escape(record['last_commit'])}</td>"
            f"<td>{html_escape(checked_text)}</td>"
            f"<td>{html_escape(record['test_status'])}</td>"
            "</tr>"
        )
    body = "\n".join(rows)
    collected = entries_doc["collected_on"]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Computer-use comparison</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #ddd; text-align: left; padding: 0.4rem 0.6rem; }}
    th {{ cursor: pointer; }}
    td:nth-child(6), th:nth-child(6) {{ text-align: right; }}
  </style>
</head>
<body>
  <h1>Computer-use comparison</h1>
  <p>Generated from <code>data/entries.yml</code> on {html_escape(collected)}. Click a heading to sort. This page is a file in the repository, not a hosted site.</p>
  <table id="catalog">
    <thead>
      <tr>
        <th>Name</th>
        <th>Type</th>
        <th>Interface</th>
        <th>Runs locally</th>
        <th>License</th>
        <th>Stars</th>
        <th>Last commit</th>
        <th>Checked here</th>
        <th>Shared task</th>
      </tr>
    </thead>
    <tbody>
{body}
    </tbody>
  </table>
  <script>
    const table = document.getElementById("catalog");
    const headers = Array.from(table.tHead.rows[0].cells);
    headers.forEach((header, index) => {{
      header.addEventListener("click", () => {{
        const body = table.tBodies[0];
        const rows = Array.from(body.rows);
        const ascending = header.dataset.dir !== "asc";
        rows.sort((a, b) => {{
          const left = a.cells[index].dataset.sort || a.cells[index].textContent.trim();
          const right = b.cells[index].dataset.sort || b.cells[index].textContent.trim();
          const leftNumber = Number(left.replace(/,/g, ""));
          const rightNumber = Number(right.replace(/,/g, ""));
          if (left !== "" && right !== "" && !Number.isNaN(leftNumber) && !Number.isNaN(rightNumber)) {{
            return ascending ? leftNumber - rightNumber : rightNumber - leftNumber;
          }}
          return ascending ? left.localeCompare(right) : right.localeCompare(left);
        }});
        headers.forEach((item) => delete item.dataset.dir);
        header.dataset.dir = ascending ? "asc" : "desc";
        rows.forEach((row) => body.appendChild(row));
      }});
    }});
  </script>
</body>
</html>
"""


def load_font(size, bold=False):
    from PIL import ImageFont

    path = FONT_BOLD if bold else FONT
    if not path.is_file():
        raise SystemExit(f"Missing font {path}")
    return ImageFont.truetype(str(path), size)


def render_stars_png(agents, collected):
    from PIL import Image, ImageDraw

    width, height = 1100, 640
    image = Image.new("RGB", (width, height), "#16181d")
    draw = ImageDraw.Draw(image)
    title = load_font(28, bold=True)
    body = load_font(18)
    small = load_font(15)
    draw.text((40, 28), "GitHub stars, ten highest-star agents", font=title, fill="#f4f6f8")
    draw.text((40, 68), f"Collected {collected}. Not cost and not task success.", font=small, fill="#b7c0cc")
    maximum = max(record["stars"] for record in agents)
    top = 110
    for index, record in enumerate(agents):
        y = top + index * 48
        draw.text((40, y), record["name"], font=body, fill="#f4f6f8")
        bar_width = int(520 * record["stars"] / maximum)
        draw.rectangle((360, y + 4, 360 + bar_width, y + 26), fill="#7eb6ff")
        draw.text((360 + bar_width + 12, y), f"{record['stars']:,}", font=body, fill="#d5dbe3")
    return image


def render_social_png(entries_doc):
    from PIL import Image, ImageDraw

    entries = entries_doc["entries"]
    tested = sum(1 for record in entries if record["test_status"] == "tested")
    verified = sum(1 for record in entries if record.get("verified_run"))
    image = Image.new("RGB", (1280, 640), "#16181d")
    draw = ImageDraw.Draw(image)
    draw.text((72, 120), "Awesome Computer Use", font=load_font(64, bold=True), fill="#f4f6f8")
    draw.text((72, 220), "Desktop and browser agents, dated from the GitHub API.", font=load_font(32), fill="#d5dbe3")
    line = f"{len(entries)} listed   ·   {verified} checked here   ·   {tested} tested on one task"
    draw.text((72, 320), line, font=load_font(28, bold=True), fill="#7eb6ff")
    draw.text((72, 400), f"Facts collected {entries_doc['collected_on']}", font=load_font(24), fill="#b7c0cc")
    return image


def png_bytes(image):
    import io

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def write_outputs(readme, html, stars_png, social_png):
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "compare.html").write_text(html, encoding="utf-8")
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "stars.png").write_bytes(stars_png)
    (assets / "social-preview.png").write_bytes(social_png)


def main():
    check = "--check" in sys.argv
    entries_doc = load_yaml(ROOT / "data/entries.yml")
    excluded_doc = load_yaml(ROOT / "data/excluded.yml")
    readme = render_readme(entries_doc, excluded_doc)
    html = render_html(entries_doc)
    agents = top_agents(entries_doc["entries"])
    stars_png = png_bytes(render_stars_png(agents, entries_doc["collected_on"]))
    social_png = png_bytes(render_social_png(entries_doc))
    if check:
        problems = []
        current = {
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").is_file() else "",
            "docs/compare.html": (ROOT / "docs/compare.html").read_text(encoding="utf-8") if (ROOT / "docs/compare.html").is_file() else "",
            "assets/stars.png": (ROOT / "assets/stars.png").read_bytes() if (ROOT / "assets/stars.png").is_file() else b"",
            "assets/social-preview.png": (ROOT / "assets/social-preview.png").read_bytes() if (ROOT / "assets/social-preview.png").is_file() else b"",
        }
        expected = {
            "README.md": readme,
            "docs/compare.html": html,
            "assets/stars.png": stars_png,
            "assets/social-preview.png": social_png,
        }
        for name, value in expected.items():
            if current[name] != value:
                problems.append(name)
        if problems:
            print("Generated files differ from data/: " + ", ".join(problems), file=sys.stderr)
            print("Run: python scripts/build_readme.py", file=sys.stderr)
            return 1
        print("generated files match")
        return 0
    write_outputs(readme, html, stars_png, social_png)
    print(f"wrote README.md ({len(entries_doc['entries'])} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
