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
  const res = await request(app).get(`/confronto/${inf}`);
  assert.equal(res.status, 200);
  assert.deepEqual(tabs(res.text), ['NR25', 'B26', 'F31', 'N35', 'N35c']);
  assert.match(res.text, /class="wtab on" aria-current="page"><span>N35c<\/span>/);
  assert.match(res.text, /<img src="\/img\/facs\/c12-N35c.jpg"/);
  assert.equal(zones(res.text), 15);
  assert.equal((res.text.match(/<p class="fverse" id="v\d+" data-v="\d+">/g) || []).length, 15);
  assert.match(res.text, /data-place="p4">Dell'ultimo orizzonte<\/a> il guardo esclude\./);
});

test('the variant list shows every witness and the manuscript layers', async () => {
  const res = await request(app).get(`/confronto/${inf}`);
  assert.match(res.text, /<li id="place-p13">/);
  assert.match(res.text, /Penna A 1819/);
  assert.match(res.text, /Immensità il mio pensier s(?:'|&#39;)annega,/); // EJS escapes ' as &#39;, shown as '
  assert.match(res.text, /<span class="wits">NR25 B26<\/span>/);
});

test('another witness shows its own text and page; unknown witnesses fall back to N35c', async () => {
  let res = await request(app).get(`/confronto/${inf}?w=B26`);
  assert.match(res.text, /<img src="\/img\/facs\/c12-B26.jpg"/);
  assert.match(res.text, /data-place="p11">e 'l<\/a> suon di lei/);
  for (const w of ['AN', 'XX', '%3Cscript%3E']) {
    res = await request(app).get(`/confronto/${inf}?w=${w}`);
    assert.match(res.text, /<img src="\/img\/facs\/c12-N35c.jpg"/, w);
    assert.doesNotMatch(res.text, /<script>/);
  }
});

test('a page without verse zones is shown whole', async () => {
  const original = data.facsimile;
  data.facsimile = (n) => {
    const real = original(n);
    if (!real) return real; // other poems have no facsimile
    const f = structuredClone(real);
    f.witnesses.forEach((w) => { w.zones = null; });
    return f;
  };
  try {
    const res = await request(app).get(`/confronto/${inf}`);
    assert.equal(res.status, 200);
    assert.equal(zones(res.text), 0);
    assert.match(res.text, /<img src="\/img\/facs\/c12-N35c.jpg"/);
    assert.match(res.text, /class="nozones"/);
  } finally {
    data.facsimile = original;
  }
});

test('Confronto has the facsimile view; old facsimile links redirect there', async () => {
  const other = index.find((p) => p.n !== inf).n;
  assert.match((await request(app).get(`/confronto/${inf}`)).text, /<p class="fverse"/);
  assert.equal((await request(app).get(`/confronto/${other}`)).status, 404);
  assert.equal((await request(app).get('/confronto/42')).status, 404);
  let res = await request(app).get(`/leggo/${inf}/facsimile?w=B26`);
  assert.equal(res.status, 301);
  assert.equal(res.headers.location, `/confronto/${inf}?w=B26`);
  res = await request(app).get(`/leggo/${inf}/facsimile?w=%3Cx%3E`);
  assert.equal(res.headers.location, `/confronto/${inf}`);
  assert.equal((await request(app).get('/confronto')).headers.location, `/confronto/${inf}`);
  assert.equal((await request(app).get('/js/facsimile.js')).status, 200);
});

test('the witness description is a tooltip on its tab, not a line of text', async () => {
  const html = (await request(app).get(`/confronto/${inf}`)).text;
  assert.doesNotMatch(html, /class="wlabel"/);
  assert.match(html, /<a href="\?w=B26" data-w="B26" class="wtab"[^>]*><span>B26<\/span><span class="tip" role="tooltip">Versi del Conte Giacomo Leopardi, Bologna/);
});

test('credits are in the footer, not at the top; no breadcrumb', async () => {
  const res = await request(app).get(`/confronto/${inf}`);
  const footer = res.text.slice(res.text.indexOf('<footer'));
  assert.match(footer, /Roberta Priore, Beatrice Nava/);
  assert.doesNotMatch(res.text.slice(0, res.text.indexOf('<footer')), /Roberta Priore/);
  assert.doesNotMatch(res.text, /← /);
  assert.doesNotMatch((await request(app).get('/')).text.slice(-600), /Roberta Priore/);
});

test('inside a poem the navbar links keep the poem', async () => {
  const nav = (html) => html.slice(html.indexOf('<nav class="links"'), html.indexOf('</nav>'));
  const fromConfronto = nav((await request(app).get(`/confronto/${inf}`)).text);
  assert.match(fromConfronto, new RegExp(`<a href="/leggo/${inf}" class="">Leggo</a>`));
  assert.match(fromConfronto, new RegExp(`<a href="/confronto/${inf}" class="on">Confronto</a>`));
  assert.match(nav((await request(app).get(`/leggo/${inf}`)).text), new RegExp(`<a href="/leggo/${inf}" class="on">Leggo</a>`));
  assert.match(nav((await request(app).get('/')).text), /<a href="\/leggo" class="">Leggo<\/a>/);
});

test('the popover has everything it needs in the page', async () => {
  const res = await request(app).get(`/confronto/${inf}`);
  assert.match(res.text, /<div class="popover" id="popover" role="dialog" aria-labelledby="popover-title" hidden>/);
  assert.match(res.text, /<button type="button" class="popover-close"/);
  for (let k = 1; k <= 14; k += 1) assert.match(res.text, new RegExp(`<li id="place-p${k}">`));
});

test('no instructions or provisional notice on the facsimile page', async () => {
  const res = await request(app).get(`/confronto/${inf}`);
  assert.doesNotMatch(res.text, /class="hint"/);
  assert.doesNotMatch(res.text, /Provvisorio|Provisional/);
});
