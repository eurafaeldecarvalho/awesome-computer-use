# Shared task

Every entry is judged against this task, or left as not tested yet. The page is [`site/index.html`](site/index.html). It is static. It does not call any other website.

## Goal

Serve the page from this repository, open it, fill three fields, and download `result.csv`.

| Field | `id` | Value |
| --- | --- | --- |
| Full name | `full_name` | Ada Lovelace |
| Email | `email` | ada@example.com |
| City | `city` | London |

Then activate the button labeled Download CSV (`id="download"`).

## Pass

The downloaded file, or the CSV the page shows in `#csv`, is exactly:

```text
full_name,email,city
Ada Lovelace,ada@example.com,London
```

`#status` reads `Saved result.csv`.

Anything short of that is `failed` or `partial`. Do not mark the entry `tested` without a log.

## How to serve the page

From the repository root:

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory bench/site
```

Open `http://127.0.0.1:8765/`.

## What a tested log must contain

Write `logs/<id>/<YYYY-MM-DD>.md` with:

- the command you ran
- the version or git commit
- the result: `ok`, `failed`, or `partial`
- the number of model steps
- the cost per step in US dollars, the published price you used, and the date of that price
- a short copy of the CSV or the error

Do not add screenshots to the log. Cost without a price source and a price date does not count.
