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
  const res = await request(app).get(`/leggo/${inf}`);
  assert.equal(res.status, 200);
  assert.deepEqual(tabs(res.text), ['NR25', 'B26', 'F31', 'N35', 'N35c']);
  assert.match(res.text, /class="wtab on" aria-current="page"[^>]*>N35c</);
  assert.match(res.text, /<img src="\/img\/facs\/c12-N35c.jpg"/);
  assert.equal(zones(res.text), 15);
  assert.equal((res.text.match(/<p class="fverse" id="v\d+" data-v="\d+">/g) || []).length, 15);
  assert.match(res.text, /data-place="p4">Dell'ultimo orizzonte<\/a> il guardo esclude\./);
});

test('the variant list shows every witness and the manuscript layers', async () => {
  const res = await request(app).get(`/leggo/${inf}`);
  assert.match(res.text, /<li id="place-p13">/);
  assert.match(res.text, /Penna A 1819/);
  assert.match(res.text, /Immensità il mio pensier s(?:'|&#39;)annega,/); // EJS escapes ' as &#39;, shown as '
  assert.match(res.text, /<span class="wits">NR25 B26<\/span>/);
});

test('another witness shows its own text and page; unknown witnesses fall back to N35c', async () => {
  let res = await request(app).get(`/leggo/${inf}?w=B26`);
  assert.match(res.text, /<img src="\/img\/facs\/c12-B26.jpg"/);
  assert.match(res.text, /data-place="p11">e 'l<\/a> suon di lei/);
  for (const w of ['AN', 'XX', '%3Cscript%3E']) {
    res = await request(app).get(`/leggo/${inf}?w=${w}`);
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
    const res = await request(app).get(`/leggo/${inf}`);
    assert.equal(res.status, 200);
    assert.equal(zones(res.text), 0);
    assert.match(res.text, /<img src="\/img\/facs\/c12-N35c.jpg"/);
    assert.match(res.text, /class="nozones"/);
  } finally {
    data.facsimile = original;
  }
});

test('L\'infinito opens in the facsimile view; other poems keep the text view; old links redirect', async () => {
  const other = index.find((p) => p.n !== inf).n;
  assert.match((await request(app).get(`/leggo/${inf}`)).text, /<p class="fverse"/);
  const plain = (await request(app).get(`/leggo/${other}`)).text;
  assert.match(plain, /<p class="verse/);
  assert.doesNotMatch(plain, /class="fverse"/);
  let res = await request(app).get(`/leggo/${inf}/facsimile?w=B26`);
  assert.equal(res.status, 301);
  assert.equal(res.headers.location, `/leggo/${inf}?w=B26`);
  res = await request(app).get(`/leggo/${inf}/facsimile?w=%3Cx%3E`);
  assert.equal(res.headers.location, `/leggo/${inf}`);
  assert.equal((await request(app).get('/leggo/42/facsimile')).status, 404);
  assert.equal((await request(app).get('/js/facsimile.js')).status, 200);
});

test('the poem selector changes poem by itself; the button exists only without JavaScript', async () => {
  for (const n of [inf, index.find((p) => p.n !== inf).n]) {
    const html = (await request(app).get(`/leggo/${n}`)).text;
    assert.match(html, /<select id="poem-select" name="n" onchange="this.form.submit\(\)">/);
    assert.match(html, /<noscript><button type="submit">/);
    assert.equal((html.match(/<button type="submit">/g) || []).length, 1);
  }
});

test('credits are in the footer, not at the top; no breadcrumb', async () => {
  const res = await request(app).get(`/leggo/${inf}`);
  const footer = res.text.slice(res.text.indexOf('<footer'));
  assert.match(footer, /Roberta Priore, Beatrice Nava/);
  assert.doesNotMatch(res.text.slice(0, res.text.indexOf('<footer')), /Roberta Priore/);
  assert.doesNotMatch(res.text, /← /);
  assert.doesNotMatch((await request(app).get('/')).text.slice(-600), /Roberta Priore/);
});

test('inside a poem the navbar Leggo link returns to that poem', async () => {
  const nav = (html) => html.slice(html.indexOf('<nav class="links"'), html.indexOf('</nav>'));
  assert.match(nav((await request(app).get(`/leggo/${inf}`)).text), new RegExp(`<a href="/leggo/${inf}" class="on">Leggo</a>`));
  assert.match(nav((await request(app).get(`/leggo/${inf}`)).text), new RegExp(`<a href="/leggo/${inf}" class="on">Leggo</a>`));
  assert.match(nav((await request(app).get('/')).text), /<a href="\/leggo" class="">Leggo<\/a>/);
});

test('the popover has everything it needs in the page', async () => {
  const res = await request(app).get(`/leggo/${inf}`);
  assert.match(res.text, /<div class="popover" id="popover" role="dialog" aria-labelledby="popover-title" hidden>/);
  assert.match(res.text, /<button type="button" class="popover-close"/);
  for (let k = 1; k <= 14; k += 1) assert.match(res.text, new RegExp(`<li id="place-p${k}">`));
});

test('no instructions or provisional notice on the facsimile page', async () => {
  const res = await request(app).get(`/leggo/${inf}`);
  assert.doesNotMatch(res.text, /class="hint"/);
  assert.doesNotMatch(res.text, /Provvisorio|Provisional/);
});
