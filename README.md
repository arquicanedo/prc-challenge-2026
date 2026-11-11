# PRC Data Challenge 2026 leaderboard

<https://prc-challenge-2026.vercel.app>

The challenge is over. The page is now a static notice congratulating the winners, and
it fetches nothing.

While the challenge ran, this was a live leaderboard: best submission per team, sortable
by column, fed by a small Fly.io service (`prc-leaderboard`) that mirrored the
competition's `/leaderboard` endpoint with CORS, because that endpoint sends no
`access-control-allow-origin`. The service has been shut down and removed from this
tree. The leaderboard page, the mirror and the README describing how to run them are
kept in the history at
[`ba5915f`](https://github.com/arquicanedo/prc-challenge-2026/tree/ba5915f). The
mirror only works while the competition API is still up.

Licensed MIT (see `LICENSE`). The data the leaderboard showed came from the PRC Data
Challenge 2026 API and is not covered by that licence.
