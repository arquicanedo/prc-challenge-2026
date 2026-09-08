# PRC Data Challenge 2026 leaderboard

<https://prc-challenge-2026.vercel.app>

Best submission per team.

A static page. It reads `https://prc-leaderboard.fly.dev/data.json`, a small service
that mirrors the competition's own `/leaderboard` endpoint with CORS, groups it
best-per-team, and stores nothing of its own. That endpoint sends no
`access-control-allow-origin`, which is the only reason the mirror exists.

Licensed MIT (see `LICENSE`). The **data** is not covered by that: it comes from the
PRC Data Challenge 2026 API and is only regrouped here.

## service/

The mirror itself, so this is a complete fork rather than a page pointing at someone
else's host. ~150 lines, no database, no credentials.

It pages through the competition's `/leaderboard` endpoint, groups every scored submission
best-per-team, and serves the result with CORS. It exists because that endpoint sends no
`access-control-allow-origin`, and because the two obvious places to run the fetch both
failed: GitHub Actions' cron delivered 1 of ~13 expected runs in six and a half hours, and
Vercel's serverless egress cannot reach the API host at all.

No background timer. The cache is filled by the first request and refreshed behind later
ones, so only a cold start ever waits on the upstream:

    no cache        fetch synchronously (~3 s, 7 pages) and serve
    age <  FRESH_S  serve cache, no upstream call
    age >= FRESH_S  serve cache immediately, refresh in the background

Refreshes are single-flight, and a failed refresh keeps the stale payload rather than
returning a 5xx -- `/health` is where staleness and failures become visible, and it never
triggers an upstream fetch itself because the platform probes it on a timer.

    GET /  or  /data.json    the payload
    GET /health              cached?, age_s, refreshes, failures, last_error

Everything is env-overridable, so a fork needs no code edits:

    COMP              competition id (default: this challenge's, which is public)
    API               full endpoint, if you would rather set it directly
    ALLOWED_ORIGINS   comma-separated list of origins allowed to read it via CORS
    FRESH_S           seconds before a response triggers a background refresh (300)
    PORT              listen port (8080)

Deploy: `fly launch` from `service/`, then point the page's `fetch()` at your host.
`fly.toml` pins `dfw` because the API host times out from some other regions.
