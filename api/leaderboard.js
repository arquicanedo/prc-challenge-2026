// Reads the competition's public submissions API and groups it best-per-team.
const COMP = 'bb3693e1-26bc-4a9e-8619-4fe78b4eab0c';
const API = 'https://datacomp.opensky-network.org/api/competitions/' + COMP + '/leaderboard';
const MAX_PAGES = 60;
const TIMEOUT_MS = 25000;

async function getJSON(url) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(url, { headers: { accept: 'application/json' }, signal: ctl.signal });
    if (!r.ok) throw new Error('upstream ' + r.status);
    return await r.json();
  } finally {
    clearTimeout(timer);
  }
}

module.exports = async (req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.setHeader('allow', 'GET, HEAD');
    return res.status(405).json({ error: 'method not allowed' });
  }
  try {
    const rows = [];
    let cursor = null;
    for (let page = 0; page < MAX_PAGES; page++) {
      const d = await getJSON(cursor ? API + '?cursor=' + encodeURIComponent(cursor) : API);
      rows.push(...(d.items || []));
      cursor = d.nextCursor;
      if (!cursor) break;
    }
    const byTeam = new Map();
    for (const s of rows) {
      const t = byTeam.get(s.teamName) || { team: s.teamName, subs: [] };
      t.subs.push({ score: s.score, at: s.processedAt });
      byTeam.set(s.teamName, t);
    }
    const teams = [...byTeam.values()].map(t => {
      t.subs.sort((a, b) => a.at.localeCompare(b.at));
      return {
        team: t.team,
        best: Math.min(...t.subs.map(s => s.score)),
        n: t.subs.length,
        lastAt: t.subs[t.subs.length - 1].at,
      };
    }).sort((a, b) => a.best - b.best);
    res.setHeader('cache-control', 's-maxage=120, stale-while-revalidate=600');
    res.setHeader('x-content-type-options', 'nosniff');
    res.status(200).json({ updated: new Date().toISOString(), totalSubmissions: rows.length, teams });
  } catch (e) {
    res.status(502).json({ error: 'upstream unavailable' });
  }
};
