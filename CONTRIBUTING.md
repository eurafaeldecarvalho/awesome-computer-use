# Contributing

This list is [CC0-1.0](LICENSE). A pull request that adds text licenses that text under CC0 as well.

## What belongs here

All of the following have to be true:

1. **Open source, or a public API.** The entry links a public repository or a documented public API. Private demos and slide decks do not qualify.
2. **Real computer use.** The project operates a browser or a desktop through screenshots, an accessibility tree, or the DOM (or it is a benchmark, model, or tool built for that loop). Chatbots, generic agent frameworks, and mobile-only benchmarks do not qualify.
3. **English README.** A translation can sit beside it. The English text has to be enough to tell what the project does.
4. **Active since 2026-08-01.** The default-branch commit (or, for a directory inside a larger repository, the latest commit that touched that directory) is on or after 2026-08-01 and is still under 90 days old when you open the pull request.
5. **Original description.** Write one or two factual sentences. Do not paste the project's README, and do not paste text from another list. Link the repository, and name the authors or the organization that publishes it. If you use a paper for the author line, link the paper.

## How to add an entry

Edit `data/entries.yml` only. Do not hand-edit `README.md`, `docs/compare.html`, or the PNGs under `assets/`. Regenerate them:

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python scripts/refresh_metadata.py
.venv/bin/python scripts/build_readme.py
.venv/bin/python scripts/check_entries.py
```

`refresh_metadata.py` fills stars, the SPDX id from the GitHub API, and the commit date. Leave those fields for the script. Keep `test_status: not_tested` unless you are also adding a log.

## Marking an entry tested

"Tested" means the project attempted the shared task in [`bench/tarefa.md`](bench/tarefa.md).

The pull request must add `logs/<id>/<YYYY-MM-DD>.md` with:

- the command
- the version or commit
- the result: `ok`, `failed`, or `partial`
- the number of model steps
- the cost per step in US dollars
- the published token price, and the date of that price

Set the matching fields on the entry (`test_status`, `test_date`, `test_version`, `test_result`, `test_steps`, `cost_per_step_usd`, `price_source`, `price_date`, `test_log`). Without the log, the entry stays "not tested yet."

A verified run is narrower: this repository installed the project or executed it, and `verified_run` points at a log that says how. Driving a CLI by hand is a verified run of that CLI. It is not a pass of the shared task.

Do not add screenshots. Do not ask for stars.
