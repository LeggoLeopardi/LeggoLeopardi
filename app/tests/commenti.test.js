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
const who = (html) => [...html.matchAll(/<p class="cwho">([^<]+)<\/p>/g)].map((m) => m[1]);

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

test('the sources come after the notes; verses and notes are linked', async () => {
  const html = await get(`/leggo/${inf}`);
  assert.ok(html.indexOf('<section class="csources"') > html.lastIndexOf('<li class="cnote'));
  assert.match(html, /Firenze, G\. C\. Sansoni, 1895/);
  assert.match(html, /<p class="verse" id="v1" data-v="1">/);
  assert.equal((await request(app).get('/js/leggo.js')).status, 200);
});

test('poems without commentaries keep the plain text', async () => {
  const html = await get(`/leggo/${plain}`);
  assert.doesNotMatch(html, /<section class="comm"/);
  assert.match(html, /Or poserai per sempre,/);
});
