const fs = require('node:fs');
const path = require('node:path');

const DATA_DIR = path.join(__dirname, '..', 'public', 'data');
let cachedIndex = null;
const poems = new Map();

function readJson(file) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, file), 'utf8'));
}

/** The 41 Canti: [{ n, roman, title, slug, incipit, status }]. */
function index() {
  if (!cachedIndex) cachedIndex = readJson('index.json');
  return cachedIndex;
}

/** One poem's data, or null when `param` is not the number of a known poem. */
function poem(param) {
  if (!/^[1-9]\d?$/.test(String(param))) return null;
  const n = Number(param);
  if (!index().some((p) => p.n === n)) return null;
  if (!poems.has(n)) poems.set(n, readJson(`c${n}.json`));
  return poems.get(n);
}

const facsimiles = new Map();

/** Text, variants and page images of poem n from the team TEI, or null when there is none. */
function facsimile(n) {
  if (!facsimiles.has(n)) {
    const file = path.join(DATA_DIR, 'facs', `c${n}.json`);
    facsimiles.set(n, fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : null);
  }
  return facsimiles.get(n);
}

const translationSets = new Map();

/** The Italian text and every translation of poem n, or null when it has none. */
function translations(n) {
  if (!translationSets.has(n)) {
    const file = path.join(DATA_DIR, 'trad', `c${n}.json`);
    translationSets.set(n, fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : null);
  }
  return translationSets.get(n);
}

const commentarySets = new Map();

/** The commentaries on poem n (oldest edition first), or null when it has none. */
function commentaries(n) {
  if (!commentarySets.has(n)) {
    const file = path.join(DATA_DIR, 'comm', `c${n}.json`);
    commentarySets.set(n, fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : null);
  }
  return commentarySets.get(n);
}

module.exports = { index, poem, facsimile, translations, commentaries };
