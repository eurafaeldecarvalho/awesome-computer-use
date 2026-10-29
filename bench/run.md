# Run book

The task is defined in [`tarefa.md`](tarefa.md). v1 did not have API keys for OpenAI, Anthropic, Google, or Browser Use, so no model-backed agent was scored and no cost per step exists.

## Checked on 2026-10-29

These were explicit commands, not an agent reading the task. The catalog therefore keeps `test_status: not_tested` for all of them.

| Entry | What happened | Log |
| --- | --- | --- |
| agent-browser 0.41.0 | CLI filled the form and saved `result.csv` | [`logs/agent-browser/2026-10-29.md`](../logs/agent-browser/2026-10-29.md) |
| @playwright/cli 0.1.22 | CLI filled the form and saved `result.csv` | [`logs/playwright-cli/2026-10-29.md`](../logs/playwright-cli/2026-10-29.md) |
| @agent-sh/computer-use-linux 0.7.32 | `doctor` and `windows` ran. The form was not attempted. `apps` failed closed because AT-SPI was off. | [`logs/computer-use-linux/2026-10-29.md`](../logs/computer-use-linux/2026-10-29.md) |

## Not checked

Every other entry. A pull request can add a log. Until that log exists, the entry stays "not tested yet."

## Recording a model-backed run

1. Serve `bench/site` as in `tarefa.md`.
2. Point the agent at `http://127.0.0.1:8765/` and at the goal in `tarefa.md`. Do not pre-fill the fields.
3. Use a disposable machine. Do not use a logged-in personal browser profile.
4. Write the log fields listed in `tarefa.md`, including the token price and the date that price was published.
5. Set `test_status: tested` in `data/entries.yml` only in the same pull request as the log.
