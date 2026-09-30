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
  next();
});

app.get('/', (req, res) => res.render('home'));

app.get('/lang/:code', (req, res) => {
  const code = ['it', 'en'].includes(req.params.code) ? req.params.code : 'it';
  const next = typeof req.query.next === 'string' && /^\/(?!\/)/.test(req.query.next) ? req.query.next : '/';
  res.cookie('lang', code, { maxAge: 365 * 24 * 3600 * 1000, sameSite: 'lax' });
  res.redirect(next);
});

app.use((req, res) => res.status(404).render('404'));

module.exports = app;
