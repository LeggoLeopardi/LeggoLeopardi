const path = require('node:path');
const express = require('express');
const cookieParser = require('cookie-parser');
const i18n = require('i18n');
const data = require('./data');

i18n.configure({
  locales: ['it', 'en'],
  defaultLocale: 'it',
  directory: path.join(__dirname, 'locales'),
  cookie: 'lang',
  updateFiles: false,
  objectNotation: true,
});

const app = express();
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(cookieParser());
app.use(i18n.init);
app.use(express.static(path.join(__dirname, '..', 'public')));
app.use((req, res, next) => {
  res.locals.canti = data.index();
  res.locals.lang = req.getLocale();
  res.locals.path = req.path;
  const inPoem = /^\/(?:leggo|traduco)\/(\d+)(?:\/|$)/.exec(req.path);
  const current = inPoem && data.poem(inPoem[1]);
  res.locals.leggoHref = current ? `/leggo/${current.n}` : '/leggo';
  res.locals.traducoHref = current && data.translations(current.n) ? `/traduco/${current.n}` : '/traduco';
  next();
});

// Modules a poem can have, in navbar order; a module is listed for a poem only when it has data.
const MODULES = [
  { mod: 'leggo', has: () => true },
  { mod: 'traduco', has: (n) => Boolean(data.translations(n)) },
];

/** Poem header data: selector options, previous/next poem within the module, and the poem's module tabs. */
function poemNav(poem, mod) {
  const has = MODULES.find((m) => m.mod === mod).has;
  const list = data.index().filter((p) => has(p.n));
  const i = list.findIndex((p) => p.n === poem.n);
  const tabs = MODULES.filter((m) => m.has(poem.n)).map((m) => ({ mod: m.mod, href: `/${m.mod}/${poem.n}`, on: m.mod === mod }));
  return {
    mod,
    prev: i > 0 ? list[i - 1] : null,
    next: i >= 0 && i < list.length - 1 ? list[i + 1] : null,
    tabs: tabs.length > 1 ? tabs : [],
    options: data.index().map((p) => ({ n: p.n, label: `${p.roman}. ${p.title || p.incipit}`, disabled: !has(p.n) })),
  };
}

app.get('/', (req, res) => res.render('home'));

app.get('/leggo', (req, res) => {
  const requested = data.poem(req.query.n);
  res.redirect(`/leggo/${requested ? requested.n : data.index()[0].n}`);
});

app.get('/leggo/:n', (req, res, next) => {
  const poem = data.poem(req.params.n);
  if (!poem) return next();
  const title = `${poem.roman}. ${poem.title || poem.incipit}`;
  const facs = data.facsimile(poem.n);
  if (!facs) return res.render('leggo', { poem, title, pnav: poemNav(poem, 'leggo') });
  // Poems with the team TEI and page images open in the text–variants–facsimile view.
  const imaged = facs.witnesses.filter((w) => w.image);
  const sel = imaged.find((w) => w.siglum === req.query.w) || imaged.find((w) => w.siglum === 'N35c') || imaged[0];
  return res.render('facsimile', { poem, facs, imaged, sel, credits: facs.credits, title, pnav: poemNav(poem, 'leggo') });
});

app.get('/lang/:code', (req, res) => {
  const code = ['it', 'en'].includes(req.params.code) ? req.params.code : 'it';
  const next = typeof req.query.next === 'string' && /^\/(?![\/\\])[^\\\x00-\x1f]*$/.test(req.query.next) ? req.query.next : '/';
  res.cookie('lang', code, { maxAge: 365 * 24 * 3600 * 1000, sameSite: 'lax' });
  res.redirect(next);
});

app.get('/traduco', (req, res) => {
  const requested = data.poem(req.query.n);
  const target = requested && data.translations(requested.n)
    ? requested : data.index().find((p) => data.translations(p.n));
  if (!target) return res.status(404).render('404');
  return res.redirect(`/traduco/${target.n}`);
});

app.get('/traduco/:n', (req, res, next) => {
  const poem = data.poem(req.params.n);
  const trad = poem && data.translations(poem.n);
  if (!trad) return next();
  const byId = (id) => trad.translations.find((t) => t.id === id);
  const t1 = byId(req.query.t) || trad.translations[0];
  const t2 = req.query.t2 && req.query.t2 !== t1.id ? byId(req.query.t2) : null;
  const groups = [];
  trad.translations.forEach((t) => {
    let g = groups.find((x) => x.lang === t.lang);
    if (!g) groups.push((g = { lang: t.lang, items: [] }));
    g.items.push(t);
  });
  return res.render('traduco', {
    poem, trad, t1, t2, groups, pnav: poemNav(poem, 'traduco'),
    title: `${poem.roman}. ${poem.title || poem.incipit} · Traduco`,
  });
});

// The facsimile view became the default Leggo view for its poems; keep old links working.
app.get('/leggo/:n/facsimile', (req, res, next) => {
  const poem = data.poem(req.params.n);
  if (!poem) return next();
  const w = typeof req.query.w === 'string' && /^[A-Z]{1,4}\d{2}c?$/.test(req.query.w) ? `?w=${req.query.w}` : '';
  res.redirect(301, `/leggo/${poem.n}${w}`);
});

app.use((req, res) => res.status(404).render('404'));

module.exports = app;
