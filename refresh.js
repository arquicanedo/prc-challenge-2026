// Regenerates data.json, but only rewrites the file when the leaderboard itself changed.
// The "updated" timestamp alone must not trigger a commit, or every run would redeploy.
const fs = require('fs');
const fn = require('./api/leaderboard.js');

const substantive = o => JSON.stringify({ t: o.totalSubmissions, teams: o.teams });

fn({ method: 'GET' }, {
  setHeader() {},
  status(c) { this._c = c; return this; },
  json(o) {
    if (this._c !== 200) { console.error('refresh failed:', o); process.exit(1); }
    let prev = null;
    try { prev = JSON.parse(fs.readFileSync('data.json', 'utf8')); } catch (e) {}
    if (prev && substantive(prev) === substantive(o)) {
      console.log(`unchanged: ${o.totalSubmissions} submissions, leaving data.json alone`);
      return;
    }
    fs.writeFileSync('data.json', JSON.stringify(o));
    console.log(`data.json written: ${o.totalSubmissions} submissions`);
  },
});
