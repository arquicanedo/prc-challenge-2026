# PRC Data Challenge 2026 leaderboard

<https://prc-challenge-2026.vercel.app>

Best submission per team, for teams with more than one submission.

A static page. It reads `https://prc-leaderboard.fly.dev/data.json`, a small service
that mirrors the competition's own `/leaderboard` endpoint with CORS, groups it
best-per-team, and stores nothing of its own. That endpoint sends no
`access-control-allow-origin`, which is the only reason the mirror exists.

Licensed MIT (see `LICENSE`). The **data** is not covered by that: it comes from the
PRC Data Challenge 2026 API and is only regrouped here.
