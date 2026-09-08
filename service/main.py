"""DC2026 leaderboard mirror. Fetches the competition submissions API on demand and
serves it with CORS.

Two reasons it has to exist as a service at all:
  (a) the API sends no access-control-allow-origin, so a browser cannot read it directly;
  (b) GitHub Actions' cron delivered 1 of ~13 expected runs in six and a half hours, and
      Vercel's serverless egress cannot reach the API host at all. Fly's dfw can.

It is built to scale to zero. There is no background timer, because a timer that only
runs while someone happens to be looking is not a schedule, and paying for a machine to
run one 48 times a day for a page read far less often than that is the wrong trade. The
cache is filled by the first request and refreshed behind later ones:

    no cache          -> fetch synchronously (~3s, 7 pages) and serve
    age <  FRESH_S    -> serve cache, no upstream call
    age >= FRESH_S    -> serve cache IMMEDIATELY, refresh in the background

so a visitor only ever waits on the upstream when the cache is genuinely empty, which is
a cold start. Refreshes are single-flight: a burst of viewers triggers one upstream fetch,
not one per request.
"""
import json, os, threading, time, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Deployment-specific values are env-overridable so a fork works without editing code.
# The defaults are this deployment's; none of them is a secret -- COMP is the public
# competition id that appears in the API URL, and the origin is the public page.
COMP = os.environ.get("COMP", "bb3693e1-26bc-4a9e-8619-4fe78b4eab0c")
API = os.environ.get("API") or f"https://datacomp.opensky-network.org/api/competitions/{COMP}/leaderboard"
FRESH_S = int(os.environ.get("FRESH_S", "300"))       # serve without revalidating
PORT = int(os.environ.get("PORT", "8080"))
ALLOWED_ORIGINS = {o for o in os.environ.get(
    "ALLOWED_ORIGINS", "https://prc-challenge-2026.vercel.app").split(",") if o}
MAX_PAGES = 60
TIMEOUT_S = 25

_state = {"payload": None, "fetched_at": 0.0, "error": None, "ok": 0, "fail": 0}
_lock = threading.Lock()
_refreshing = False


def fetch():
    rows, cursor = [], None
    for _ in range(MAX_PAGES):
        url = API + (f"?cursor={urllib.parse.quote(cursor)}" if cursor else "")
        req = urllib.request.Request(url, headers={"accept": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            d = json.load(r)
        rows += d.get("items", [])
        cursor = d.get("nextCursor")
        if not cursor:
            break
    by = {}
    for s in rows:
        by.setdefault(s["teamName"], []).append((s["score"], s["processedAt"]))
    teams = []
    for name, subs in by.items():
        subs.sort(key=lambda x: x[1])
        teams.append({"team": name, "best": min(s for s, _ in subs),
                      "n": len(subs), "lastAt": subs[-1][1]})
    teams.sort(key=lambda t: t["best"])
    return {"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "totalSubmissions": len(rows), "teams": teams}


def _refresh():
    """Fetch and store. Records the failure rather than raising: a stale payload is a
    better answer than a 5xx, and /health is where the staleness becomes visible."""
    global _refreshing
    try:
        p = fetch()
        with _lock:
            _state.update(payload=p, fetched_at=time.time(), error=None)
            _state["ok"] += 1
        print(f"refreshed: {p['totalSubmissions']} submissions", flush=True)
    except Exception as e:
        with _lock:
            _state["error"] = str(e)[:200]
            _state["fail"] += 1
        print(f"refresh failed: {e}", flush=True)
    finally:
        with _lock:
            _refreshing = False


def ensure_fresh():
    """Returns the payload to serve. Blocks ONLY when there is nothing cached at all."""
    global _refreshing
    with _lock:
        payload, age = _state["payload"], time.time() - _state["fetched_at"]
        if payload is not None and age < FRESH_S:
            return payload
        start = not _refreshing
        if start:
            _refreshing = True
    if payload is None:
        _refresh()                      # cold: the caller waits
        with _lock:
            return _state["payload"]
    if start:
        threading.Thread(target=_refresh, daemon=True).start()   # warm: serve stale now
    return payload


class H(BaseHTTPRequestHandler):
    server_version = "svc"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def _send(self, code, body, ctype="application/json", max_age=60):
        b = body.encode()
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(b)))
        origin = self.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            self.send_header("access-control-allow-origin", origin)
            self.send_header("access-control-allow-methods", "GET, HEAD, OPTIONS")
            self.send_header("vary", "Origin")
        self.send_header("cache-control", f"public, max-age={max_age}")
        self.send_header("x-content-type-options", "nosniff")
        self.send_header("referrer-policy", "no-referrer")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(b)

    def do_OPTIONS(self):
        self._send(204, "", "text/plain", max_age=600)

    def do_POST(self): self._send(405, '{"error":"method not allowed"}')
    do_PUT = do_DELETE = do_PATCH = do_POST

    def do_HEAD(self): self.do_GET()

    def do_GET(self):
        path = self.path.split("?")[0]
        # /health must never trigger an upstream fetch: Fly probes it on a timer, and a
        # probe that pulls 7 pages would turn the health check into the traffic source.
        if path == "/health":
            with _lock:
                p, at, err, ok, fail = (_state["payload"], _state["fetched_at"],
                                        _state["error"], _state["ok"], _state["fail"])
            return self._send(200, json.dumps({
                "ok": True, "cached": p is not None,
                "age_s": None if not at else round(time.time() - at),
                "refreshes": ok, "failures": fail, "last_error": err,
            }), max_age=0)
        if path in ("/", "/data.json"):
            p = ensure_fresh()
            if p is None:
                with _lock:
                    err = _state["error"]
                return self._send(503, json.dumps({"error": "upstream unavailable",
                                                   "detail": err}), max_age=0)
            return self._send(200, json.dumps(p))
        self._send(404, json.dumps({"error": "not found"}), max_age=0)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"serving on :{PORT}, fresh window {FRESH_S}s", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
