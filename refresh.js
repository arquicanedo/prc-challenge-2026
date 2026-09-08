// Regenerates data.json.
const fs = require('fs');
const fn = require('./api/leaderboard.js');
fn({ method: 'GET' }, {
  setHeader() {},
  status(c) { this._c = c; return this; },
  json(o) {
    if (this._c !== 200) { console.error('refresh failed:', o); process.exit(1); }
    fs.writeFileSync('data.json', JSON.stringify(o));
    console.log(`data.json written: ${o.totalSubmissions} submissions`);
  },
});
