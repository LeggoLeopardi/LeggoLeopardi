const { test } = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const request = require('supertest');

process.chdir(os.tmpdir());
const app = require(path.join(__dirname, '..', 'app.js'));
const data = require(path.join(__dirname, '..', 'data.js'));
const index = require(path.join(__dirname, '..', '..', 'public', 'data', 'index.json'));
const inf = index.find((p) => p.slug === 'l-infinito').n;
const tabs = (html) => [...html.matchAll(/<a href="\?w=([^"]+)" data-w/g)].map((m) => m[1]);
const zones = (html) => (html.match(/<a class="zone"/g) || []).length;

test("L'infinito: N35c text next to its page, one zone per verse", async () => {
  const res = await request(app).get(`/leggo/${inf}/facsimile`);
  assert.equal(res.status, 200);
  assert.deepEqual(tabs(res.text), ['NR25', 'B26', 'F31', 'N35', 'N35c']);
  assert.match(res.text, /class="wtab on" aria-current="page"[^>]*>N35c</);
  assert.match(res.text, /<img src="\/img\/facs\/c12-N35c.jpg"/);
  assert.equal(zones(res.text), 15);
  assert.equal((res.text.match(/<p class="fverse" id="v\d+" data-v="\d+">/g) || []).length, 15);
  assert.match(res.text, /data-place="p4">Dell'ultimo orizzonte<\/a> il guardo esclude\./);
});

test('the variant list shows every witness and the manuscript layers', async () => {
  const res = await request(app).get(`/leggo/${inf}/facsimile`);
  assert.match(res.text, /<li id="place-p13">/);
  assert.match(res.text, /Penna A 1819/);
  assert.match(res.text, /Immensità il mio pensier s(?:'|&#39;)annega,/); // EJS escapes ' as &#39;, shown as '
  assert.match(res.text, /<span class="wits">NR25 B26<\/span>/);
});

test('another witness shows its own text and page; unknown witnesses fall back to N35c', async () => {
  let res = await request(app).get(`/leggo/${inf}/facsimile?w=B26`);
  assert.match(res.text, /<img src="\/img\/facs\/c12-B26.jpg"/);
  assert.match(res.text, /data-place="p11">e 'l<\/a> suon di lei/);
  for (const w of ['AN', 'XX', '%3Cscript%3E']) {
    res = await request(app).get(`/leggo/${inf}/facsimile?w=${w}`);
    assert.match(res.text, /<img src="\/img\/facs\/c12-N35c.jpg"/, w);
    assert.doesNotMatch(res.text, /<script>/);
  }
});

test('a page without verse zones is shown whole', async () => {
  const original = data.facsimile;
  data.facsimile = (n) => {
    const f = structuredClone(original(n));
    f.witnesses.forEach((w) => { w.zones = null; });
    return f;
  };
  try {
    const res = await request(app).get(`/leggo/${inf}/facsimile`);
    assert.equal(res.status, 200);
    assert.equal(zones(res.text), 0);
    assert.match(res.text, /<img src="\/img\/facs\/c12-N35c.jpg"/);
    assert.match(res.text, /class="nozones"/);
  } finally {
    data.facsimile = original;
  }
});

test('only poems with a facsimile have the page, and Leggo links to it', async () => {
  const other = index.find((p) => p.n !== inf).n;
  assert.equal((await request(app).get(`/leggo/${other}/facsimile`)).status, 404);
  assert.equal((await request(app).get('/leggo/42/facsimile')).status, 404);
  assert.match((await request(app).get(`/leggo/${inf}`)).text, new RegExp(`href="/leggo/${inf}/facsimile"`));
  assert.doesNotMatch((await request(app).get(`/leggo/${other}`)).text, /\/facsimile"/);
  assert.equal((await request(app).get('/js/facsimile.js')).status, 200);
});
