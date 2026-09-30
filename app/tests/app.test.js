const { test } = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const request = require('supertest');

// The app must not depend on the working directory (Vercel runs it from elsewhere).
process.chdir(os.tmpdir());
const app = require(path.join(__dirname, '..', 'app.js'));
const index = require(path.join(__dirname, '..', '..', 'public', 'data', 'index.json'));

test('home lists every canto from index.json', async () => {
  assert.equal(index.length, 41);
  const res = await request(app).get('/');
  assert.equal(res.status, 200);
  assert.equal((res.text.match(/<li class="canto">/g) || []).length, index.length);
  assert.match(res.text, /<html lang="it">/);
});

test('language switch sets a cookie and redirects only to local paths', async () => {
  let res = await request(app).get('/lang/en?next=/leggo/12');
  assert.equal(res.status, 302);
  assert.equal(res.headers.location, '/leggo/12');
  assert.match(res.headers['set-cookie'].join(';'), /lang=en/);
  res = await request(app).get('/lang/en?next=//evil.example');
  assert.equal(res.headers.location, '/');
  res = await request(app).get('/').set('Cookie', 'lang=en');
  assert.match(res.text, /<html lang="en">/);
});

test('unknown pages are 404 with the site layout', async () => {
  const res = await request(app).get('/nope');
  assert.equal(res.status, 404);
  assert.match(res.text, /Leggo <b>Leopardi<\/b>/);
});

test('language switch rejects backslash tricks that browsers read as //', async () => {
  for (const next of ['/%5Cevil.example', '/%5C%5Cevil.example', '/%09/evil.example']) {
    const res = await request(app).get(`/lang/en?next=${next}`);
    assert.equal(res.headers.location, '/', next);
  }
});

test('no status tags in the poem list and no source badge in Leggo; WikiLeopardi credited in the footer', async () => {
  const home = (await request(app).get('/')).text;
  assert.doesNotMatch(home, /class="st /);
  const leggo = (await request(app).get('/leggo/12')).text;
  assert.doesNotMatch(leggo, /class="badge"/);
  for (const html of [home, leggo]) {
    assert.match(html.slice(html.indexOf('<footer')), /WikiLeopardi/);
  }
});
