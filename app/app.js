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
  const inPoem = /^\/(?:leggo|confronto|traduco)\/(\d+)(?:\/|$)/.exec(req.path);
  const current = inPoem && data.poem(inPoem[1]);
  res.locals.leggoHref = current ? `/leggo/${current.n}` : '/leggo';
  res.locals.confrontoHref = current && data.facsimile(current.n) ? `/confronto/${current.n}` : '/confronto';
  res.locals.traducoHref = current && data.translations(current.n) ? `/traduco/${current.n}` : '/traduco';
  next();
});

// Modules a poem can have, in navbar order; a module is listed for a poem only when it has data.
const MODULES = [
  { mod: 'leggo', has: () => true },
  { mod: 'confronto', has: (n) => Boolean(data.facsimile(n)) },
  { mod: 'traduco', has: (n) => Boolean(data.translations(n)) },
];

/** Poem header data: the list of poems (available ones as links), previous/next poem within the module. */
function poemNav(poem, mod) {
  const has = MODULES.find((m) => m.mod === mod).has;
  const list = data.index().filter((p) => has(p.n));
  const i = list.findIndex((p) => p.n === poem.n);
  return {
    mod,
    prev: i > 0 ? list[i - 1] : null,
    next: i >= 0 && i < list.length - 1 ? list[i + 1] : null,
    options: data.index().map((p) => ({ n: p.n, roman: p.roman, title: p.title || p.incipit, disabled: !has(p.n) })),
  };
}

app.get('/', (req, res) => res.render('home'));

app.get('/leggo', (req, res) => {
  const requested = data.poem(req.query.n);
  res.redirect(`/leggo/${requested ? requested.n : data.index()[0].n}`);
});

const escapeHtml = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// Verse html with the commented words wrapped in <span class="lem" data-notes="…">, one span per stretch of text
// covered by the same notes. Verses with markup of their own keep their html (their notes stay verse-level).
function markLemmas(poem, notes) {
  const cover = new Map();  // verse n -> [[start, end, key]]
  notes.forEach(({ key, nt }) => (nt.spans || []).forEach(([v, s, e]) => {
    if (!cover.has(v)) cover.set(v, []);
    cover.get(v).push([s, e, key]);
  }));
  const marked = {};
  poem.stanzas.flat().forEach((item) => {
    const spans = cover.get(item.n);
    if (!spans || item.missing || item.html !== escapeHtml(item.text)) return;
    const cuts = [...new Set([0, item.text.length, ...spans.flatMap(([s, e]) => [s, e])])].sort((a, b) => a - b);
    marked[item.n] = cuts.slice(0, -1).map((a, i) => {
      const piece = escapeHtml(item.text.slice(a, cuts[i + 1]));
      const keys = spans.filter(([s, e]) => s <= a && a < e).map(([, , k]) => k);
      return keys.length ? `<span class="lem" data-notes="${keys.join(' ')}">${piece}</span>` : piece;
    }).join('');
  });
  return marked;
}

app.get('/leggo/:n', (req, res, next) => {
  const poem = data.poem(req.params.n);
  if (!poem) return next();
  const title = `${poem.roman}. ${poem.title || poem.incipit}`;
  const comm = data.commentaries(poem.n);
  let cview = null;
  if (comm) {
    const one = comm.commentators.find((c) => c.id === req.query.c);
    if (one) {
      cview = { mode: 'one', sel: one };
    } else {
      // every commentator's notes, grouped by the verse they start at (commentators oldest first)
      const byVerse = new Map();
      comm.commentators.forEach((c) => c.notes.forEach((nt) => {
        if (!byVerse.has(nt.from)) byVerse.set(nt.from, []);
        byVerse.get(nt.from).push({ c, nt });
      }));
      // within a verse, in the order of the text (where each lemma starts); same place: older edition first (stable sort)
      const at = ({ nt }) => (nt.spans && nt.spans.length ? nt.spans[0][1] : 0);
      cview = {
        mode: 'all',
        groups: [...byVerse.keys()].sort((a, b) => a - b).map((v) => ({ v, items: byVerse.get(v).sort((x, y) => at(x) - at(y)) })),
      };
    }
  }
  const shown = !comm ? [] : (cview.mode === 'one' ? [cview.sel] : comm.commentators)
    .flatMap((c) => c.notes.map((nt, i) => ({ key: `n-${c.id}-${i}`, nt })));
  return res.render('leggo', { poem, title, comm, cview, marked: markLemmas(poem, shown), pnav: poemNav(poem, 'leggo') });
});

app.get('/confronto', (req, res) => {
  const requested = data.poem(req.query.n);
  const target = requested && data.facsimile(requested.n) ? requested : data.index().find((p) => data.facsimile(p.n));
  if (!target) return res.status(404).render('404');
  return res.redirect(`/confronto/${target.n}`);
});

app.get('/confronto/:n', (req, res, next) => {
  const poem = data.poem(req.params.n);
  const facs = poem && data.facsimile(poem.n);
  if (!facs) return next();
  const imaged = facs.witnesses.filter((w) => w.image);
  const sel = imaged.find((w) => w.siglum === req.query.w) || imaged.find((w) => w.siglum === 'N35c') || imaged[0];
  return res.render('facsimile', {
    poem, facs, imaged, sel, credits: facs.credits, pnav: poemNav(poem, 'confronto'),
    title: `${poem.roman}. ${poem.title || poem.incipit} · Confronto`,
  });
});

app.get('/lang/:code', (req, res) => {
  const code = ['it', 'en'].includes(req.params.code) ? req.params.code : 'it';
  const next = typeof req.query.next === 'string' && /^\/(?![\/\\])[^\\\x00-\x1f]*$/.test(req.query.next) ? req.query.next : '/';
  res.cookie('lang', code, { maxAge: 365 * 24 * 3600 * 1000, sameSite: 'lax' });
  res.redirect(next);
});

app.get('/progetto', (req, res) => {
  // every commented edition, oldest first, with the poems it comments on
  const editions = new Map();
  data.index().forEach((p) => {
    const comm = data.commentaries(p.n);
    if (!comm) return;
    comm.commentators.forEach((c) => {
      if (!editions.has(c.id)) editions.set(c.id, { ...c, poems: [] });
      editions.get(c.id).poems.push({ n: p.n, label: `${p.roman}. ${p.title || p.incipit}` });
    });
  });
  res.render('progetto', { title: req.__('progetto.title'), editions: [...editions.values()].sort((a, b) => a.year - b.year) });
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

// The facsimile view moved to Confronto; keep old links working.
app.get('/leggo/:n/facsimile', (req, res, next) => {
  const poem = data.poem(req.params.n);
  if (!poem) return next();
  const w = typeof req.query.w === 'string' && /^[A-Z]{1,4}\d{2}c?$/.test(req.query.w) ? `?w=${req.query.w}` : '';
  return res.redirect(301, `/confronto/${poem.n}${w}`);
});

app.use((req, res) => res.status(404).render('404'));

module.exports = app;
