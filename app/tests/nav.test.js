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
const navbar = (html) => html.slice(html.indexOf('<nav class="links"'), html.indexOf('</nav>'));
const tabs = (html) => [...html.matchAll(/<a href="(\/\w+\/\d+)" class="ptab( on)?"/g)].map((m) => `${m[1]}${m[2] ? '*' : ''}`);

test('the title opens a list of the poems (no dropdown, no label)', async () => {
  const html = await get(`/leggo/${plain}`);
  assert.match(html, /<details class="poem-picker"><summary><h1 class="poem-title">XXVIII\. A se stesso<\/h1><\/summary>/);
  assert.doesNotMatch(html, /<select id="poem-select"/);
  const items = html.slice(html.indexOf('<ol class="picker"'), html.indexOf('</ol>', html.indexOf('<ol class="picker"')));
  assert.equal((items.match(/<li/g) || []).length, index.length);
  assert.match(items, /<a href="\/leggo\/28" aria-current="page">/);
  const trad = await get(`/traduco/${inf}`);
  const tItems = trad.slice(trad.indexOf('<ol class="picker"'), trad.indexOf('</ol>', trad.indexOf('<ol class="picker"')));
  assert.equal((tItems.match(/<a href=/g) || []).length, 1); // only L'infinito has translations
  assert.match(tItems, /<span class="off">/);
});

test('previous and next poem arrows follow the module', async () => {
  let html = await get(`/leggo/${inf}`);
  assert.match(html, new RegExp(`<a class="step prev" href="/leggo/${inf - 1}"`));
  assert.match(html, new RegExp(`<a class="step next" href="/leggo/${inf + 1}"`));
  assert.doesNotMatch(await get('/leggo/1'), /class="step prev"/);
  assert.doesNotMatch(await get(`/leggo/${index[index.length - 1].n}`), /class="step next"/);
  html = await get(`/traduco/${inf}`);
  assert.doesNotMatch(html, /class="step (prev|next)"/); // only one poem has translations
});

test('no duplicate module tabs under the title', async () => {
  assert.doesNotMatch(await get(`/leggo/${inf}`), /class="ptabs"/);
  assert.doesNotMatch(await get(`/traduco/${inf}`), /class="ptabs"/);
});

test('the navbar keeps the current poem and hides modules that do not exist yet', async () => {
  let nav = navbar(await get(`/traduco/${inf}`));
  assert.match(nav, new RegExp(`<a href="/leggo/${inf}" class="">Leggo</a>`));
  assert.match(nav, new RegExp(`<a href="/traduco/${inf}" class="on">Traduco</a>`));
  assert.match(nav, new RegExp(`<a href="/confronto/${inf}" class="">Confronto</a>`));
  nav = navbar(await get(`/leggo/${plain}`));
  assert.match(nav, /<a href="\/traduco" class="">Traduco<\/a>/);
  assert.match(nav, /<a href="\/confronto" class="">Confronto<\/a>/);
  assert.doesNotMatch(nav, /Collaziono|Concordanza/);
});

test('the printed title belongs to the text, the same in every view', async () => {
  assert.match(await get(`/leggo/${plain}`), /<p class="print-head"><span>XXVIII\.<\/span><span>A SE STESSO\.<\/span><\/p>/);
  assert.match(await get(`/leggo/${inf}`), /<p class="print-head">/);
  assert.match(await get(`/confronto/${inf}`), /<p class="print-head">/);
  assert.match(await get(`/traduco/${inf}`), /<p class="print-head"><span>XII\.<\/span><span>L(?:'|&#39;)INFINITO\.<\/span><\/p>/);
});

test('the home page describes only what exists', async () => {
  const html = await request(app).get('/').set('Cookie', 'lang=it');
  assert.match(html.text, /con i testimoni a stampa e le traduzioni/);
  assert.doesNotMatch(html.text, /commenti storici/);
});

test('Progetto is the last navbar link, active on its page, and not repeated in the footer', async () => {
  const html = await get('/progetto');
  assert.match(navbar(html), /<a href="\/traduco[^"]*" class="">Traduco<\/a>\s*<a href="\/progetto" class="on">Progetto<\/a>\s*$/);
  assert.match(navbar(await get('/')), /<a href="\/progetto" class="">Progetto<\/a>/);
  assert.doesNotMatch(html.slice(html.indexOf('<footer')), /href="\/progetto"/);
});
