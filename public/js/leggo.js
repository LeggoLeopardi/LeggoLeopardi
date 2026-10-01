// Commented reading: a verse (or an underlined lemma) and the notes on it light up together; clicking brings the
// notes level with the verse and keeps them marked.
(() => {
  const root = document.querySelector('.lcols');
  if (!root) return;
  const panel = root.querySelector('.comm');
  const verses = [...root.querySelectorAll('.verse[data-v]')];
  const notes = [...root.querySelectorAll('.cnote')];
  const lems = [...root.querySelectorAll('.lem')];
  const covers = (note, v) => Number(note.dataset.from) <= v && v <= Number(note.dataset.to);
  const keysOf = (lem) => lem.dataset.notes.split(' ');
  const clear = (cls) => root.querySelectorAll(`.${cls}`).forEach((el) => el.classList.remove(cls));
  const mark = (cls, els) => { clear(cls); els.forEach((el) => el.classList.add(cls)); };
  const behavior = () => (window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth');

  // put the first note level with the verse; if the column does not scroll on its own (narrow screens), just show it
  const align = (first, verse) => {
    if (!first) return;
    if (panel.scrollHeight > panel.clientHeight && getComputedStyle(panel).position === 'sticky') {
      panel.scrollBy({ top: first.getBoundingClientRect().top - verse.getBoundingClientRect().top, behavior: behavior() });
    } else {
      first.scrollIntoView({ block: 'nearest', behavior: behavior() });
    }
  };

  verses.forEach((verse) => {
    const v = Number(verse.dataset.v);
    const mine = () => notes.filter((n) => covers(n, v));
    verse.addEventListener('mouseenter', () => mark('hl', [verse, ...mine()]));
    verse.addEventListener('mouseleave', () => clear('hl'));
    verse.addEventListener('click', () => { mark('sel', [verse, ...mine()]); align(mine()[0], verse); });
  });
  // the words of a note can run over several lines: light them all. Where notes overlap, the word stands for the
  // shortest note covering it (pointing at "ermo" lights "ermo", not the whole verse a longer lemma covers).
  const segsOf = (key) => lems.filter((l) => keysOf(l).includes(key));
  const size = new Map();
  lems.forEach((l) => keysOf(l).forEach((k) => size.set(k, (size.get(k) || 0) + l.textContent.length)));
  const words = (lem) => segsOf(keysOf(lem).reduce((a, b) => (size.get(b) < size.get(a) ? b : a)));
  lems.forEach((lem) => {
    const mine = () => notes.filter((n) => keysOf(lem).includes(n.id));
    lem.addEventListener('mouseenter', () => mark('hl', [lem.closest('.verse'), ...words(lem), ...mine()]));
    lem.addEventListener('click', (e) => {
      e.stopPropagation();
      mark('sel', [...words(lem), ...mine()]);
      align(mine()[0], lem.closest('.verse'));
    });
  });
  notes.forEach((note) => {
    note.addEventListener('mouseenter', () => mark('hl', [
      note,
      ...verses.filter((el) => covers(note, Number(el.dataset.v))),
      ...lems.filter((l) => keysOf(l).includes(note.id)),
    ]));
    note.addEventListener('mouseleave', () => clear('hl'));
  });
})();
