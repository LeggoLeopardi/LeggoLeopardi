const { test } = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const request = require('supertest');

process.chdir(os.tmpdir());
const app = require(path.join(__dirname, '..', 'app.js'));
const index = require(path.join(__dirname, '..', '..', 'public', 'data', 'index.json'));
const inf = index.find((p) => p.slug === 'l-infinito').n;
const plain = index.find((p) => p.slug === 'a-se-stesso').n;
const get = async (url) => (await request(app).get(url)).text;
const who = (html) => [...html.matchAll(/<p class="cwho"><a [^>]*>([^<]+)<\/a><\/p>/g)].map((m) => m[1]);

test('Leggo on L\'infinito: the poem and all the commentaries, grouped by verse', async () => {
  const html = await get(`/leggo/${inf}`);
  assert.equal((html.match(/<p class="verse/g) || []).length, 15);
  assert.match(html, /<section class="comm"/);
  const v1 = html.slice(html.indexOf('<div class="cgroup" data-v="1">'), html.indexOf('<div class="cgroup" data-v="2">'));
  assert.deepEqual(who(v1), ['Fornaciari 1889', 'Castagnola 1893', 'Straccali 1895', 'Levi 1921']);
  assert.match(v1, /data-from="1" data-to="3"/);
  assert.match(v1, /<b class="clemma">ermo colle\.<\/b> Il monte Tabor/);
  assert.match(html, /class="cnote added"/);
});

test('one commentator at a time, with its introduction; unknown ids show all', async () => {
  let html = await get(`/leggo/${inf}?c=straccali_1895`);
  assert.equal((html.match(/<li class="cnote/g) || []).length, 10);
  assert.match(html, /Questa e le cinque seguenti poesie furono/);
  assert.match(html, /<a href="\?c=straccali_1895" aria-current="true">/);
  assert.match(html, /<span class="cv">vv\. 2–3<\/span>/);
  html = await get(`/leggo/${inf}?c=%3Cscript%3E`);
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /<div class="cgroup" data-v="1">/);
});

test('the editions index is on Progetto; commentator names link to it; verses and notes are linked', async () => {
  const html = await get(`/leggo/${inf}`);
  assert.doesNotMatch(html, /class="csources"/);
  assert.match(html, /<p class="cwho"><a href="\/progetto#straccali_1895">Straccali 1895<\/a><\/p>/);
  assert.match(html, /<p class="verse" id="v1" data-v="1">/);
  assert.equal((await request(app).get('/js/leggo.js')).status, 200);
});

test('poems without commentaries keep the plain text', async () => {
  const html = await get(`/leggo/${plain}`);
  assert.doesNotMatch(html, /<section class="comm"/);
  assert.match(html, /Or poserai per sempre,/);
});

test('Progetto: the project and the index of commented editions', async () => {
  const res = await request(app).get('/progetto').set('Cookie', 'lang=it');
  assert.equal(res.status, 200);
  const ids = [...res.text.matchAll(/<li class="edition" id="([^"]+)">/g)].map((m) => m[1]);
  assert.deepEqual(ids, ['fornaciari_1889', 'castagnola_1893', 'straccali_1895', 'straccali-antognoni_1919', 'levi_1921']);
  assert.match(res.text, /I canti di Giacomo Leopardi commentati da Alfredo Straccali, 2ª edizione riveduta e corretta, Firenze, G\. C\. Sansoni, 1895/);
  assert.match(res.text, /<a href="\/leggo\/12\?c=straccali_1895">XII\. L(?:'|&#39;)infinito<\/a>/);
  assert.match(res.text, /Trascrizione dall(?:'|&#39;)immagine della pagina, da verificare\./);
});
