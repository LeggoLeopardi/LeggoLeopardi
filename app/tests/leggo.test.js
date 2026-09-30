const { test } = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const request = require('supertest');

process.chdir(os.tmpdir());
const app = require(path.join(__dirname, '..', 'app.js'));
const index = require(path.join(__dirname, '..', '..', 'public', 'data', 'index.json'));
const byN = (n) => require(path.join(__dirname, '..', '..', 'public', 'data', `c${n}.json`));

test('every canto has a Leggo page', async () => {
  for (const p of index) {
    const res = await request(app).get(`/leggo/${p.n}`);
    assert.equal(res.status, 200, `canto ${p.roman}`);
  }
});

test("L'infinito renders all 15 verses exactly, numbered every 5", async () => {
  const n = index.find((p) => p.slug === 'l-infinito').n;
  const res = await request(app).get(`/leggo/${n}`);
  assert.match(res.text, /Sempre caro mi fu quest’ermo colle,/);
  assert.match(res.text, /Dell'ultimo orizzonte il guardo esclude\./);
  assert.match(res.text, /E il naufragar m’è dolce in questo mare\./);
  assert.equal((res.text.match(/<p class="verse/g) || []).length, 15);
  assert.match(res.text, /<span class="vn">5<\/span>/);
  assert.doesNotMatch(res.text, /<span class="vn">4<\/span>/);
  assert.match(res.text, /class="badge"/);
});

test('missing, unnumbered and speaker lines are visible', async () => {
  const consalvo = index.find((p) => p.slug === 'consalvo').n;
  let res = await request(app).get(`/leggo/${consalvo}`);
  assert.match(res.text, /<p class="verse missing" id="v130">/);
  const frag = index.find((p) => byN(p.n).stanzas.flat().some((i) => i.type === 'label')).n;
  res = await request(app).get(`/leggo/${frag}`);
  assert.match(res.text, /<p class="speaker">/);
  assert.match(res.text, /class="verse unnumbered"/);
});

test('bad poem addresses are 404, never 500', async () => {
  for (const bad of ['0', '42', 'abc', '12abc', '-1', '01', '1.5']) {
    const res = await request(app).get(`/leggo/${bad}`);
    assert.equal(res.status, 404, bad);
  }
});

test('selector and bare /leggo redirect to a known poem only', async () => {
  let res = await request(app).get('/leggo?n=12');
  assert.equal(res.headers.location, '/leggo/12');
  res = await request(app).get('/leggo?n=99');
  assert.equal(res.headers.location, `/leggo/${index[0].n}`);
  res = await request(app).get('/leggo');
  assert.equal(res.headers.location, `/leggo/${index[0].n}`);
});
