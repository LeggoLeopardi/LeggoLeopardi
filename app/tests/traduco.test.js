const { test } = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const request = require('supertest');

process.chdir(os.tmpdir());
const app = require(path.join(__dirname, '..', 'app.js'));
const index = require(path.join(__dirname, '..', '..', 'public', 'data', 'index.json'));
const inf = index.find((p) => p.slug === 'l-infinito').n;
const cols = (html) => (html.match(/<section class="tcol/g) || []).length;

test('/traduco goes to the first poem with translations; poems without them are 404', async () => {
  const res = await request(app).get('/traduco');
  assert.equal(res.status, 302);
  assert.equal(res.headers.location, `/traduco/${inf}`);
  assert.equal((await request(app).get('/traduco?n=1')).headers.location, `/traduco/${inf}`);
  assert.equal((await request(app).get('/traduco/1')).status, 404);
  assert.equal((await request(app).get('/traduco/42')).status, 404);
});

test('the Italian text next to the first translation, the pickers grouped by language', async () => {
  const res = await request(app).get(`/traduco/${inf}`);
  assert.equal(res.status, 200);
  assert.equal(cols(res.text), 2);
  assert.match(res.text, /Sempre caro mi fu quest’ermo colle,/);
  assert.match(res.text, /Stets war mir theuer dieser öde Hügel/);
  assert.match(res.text, /<select id="t-select" name="t" onchange="this.form.submit\(\)"/);
  assert.deepEqual([...res.text.matchAll(/<optgroup label="([^"]+)">/g)].map((m) => m[1]).slice(0, 5),
    ['Tedesco', 'Inglese', 'Spagnolo', 'Francese', 'Russo']);
  // the texts start side by side; the sources come after them
  assert.doesNotMatch(res.text, /class="tsource"/);
  assert.ok(res.text.indexOf('<section class="tsources"') > res.text.lastIndexOf('<section class="tcol'));
});

test('choosing one or two translations; bad ids fall back', async () => {
  let res = await request(app).get(`/traduco/${inf}?t=ru_akhmatova_1967`);
  assert.match(res.text, /Всегда был мил мне этот холм пустынный/);
  assert.match(res.text, /<option value="ru_akhmatova_1967" selected>/);
  res = await request(app).get(`/traduco/${inf}?t=fr_sainte-beuve_1844&t2=en_townsend_1887`);
  assert.equal(cols(res.text), 3);
  assert.match(res.text, /J’aimai toujours ce point de colline déserte,/);
  assert.match(res.text, /This lonely hill to me was ever dear,/);
  res = await request(app).get(`/traduco/${inf}?t=%3Cscript%3E&t2=fr_sainte-beuve_1844`);
  assert.doesNotMatch(res.text, /<script>/);
  assert.match(res.text, /Stets war mir theuer/);
  res = await request(app).get(`/traduco/${inf}?t=en_townsend_1887&t2=en_townsend_1887`);
  assert.equal(cols(res.text), 2);
});

test('prose translations are paragraphs, sources and rights are in the details', async () => {
  let res = await request(app).get(`/traduco/${inf}?t=fr_aulard_1880`);
  assert.match(res.text, /<p class="tprose">Toujours chères me furent/);
  res = await request(app).get(`/traduco/${inf}?t=fr_sainte-beuve_1844`);
  assert.match(res.text, /«Revue des deux mondes»/);
  assert.match(res.text, /<a href="https:\/\/fr.wikisource.org\/wiki\/L%E2%80%99Infini_%28trad._Sainte-Beuve%29" target="_blank" rel="noopener">Wikisource<\/a>/);
  res = await request(app).get(`/traduco/${inf}?t=ru_akhmatova_1967`);
  assert.match(res.text, /Protetto da diritto d(?:'|&#39;)autore/);
});

test('the navbar links to Traduco', async () => {
  const res = await request(app).get('/');
  assert.match(res.text, /<a href="\/traduco" class="">Traduco<\/a>/);
});
