// Commented reading: a verse and the notes on it light up together; clicking a verse brings its first note into view.
(() => {
  const root = document.querySelector('.lcols');
  if (!root) return;
  const verses = [...root.querySelectorAll('.verse[data-v]')];
  const notes = [...root.querySelectorAll('.cnote')];
  const covers = (note, v) => Number(note.dataset.from) <= v && v <= Number(note.dataset.to);
  const clear = () => root.querySelectorAll('.hl').forEach((el) => el.classList.remove('hl'));

  verses.forEach((verse) => {
    const v = Number(verse.dataset.v);
    const mine = () => notes.filter((n) => covers(n, v));
    verse.addEventListener('mouseenter', () => { clear(); verse.classList.add('hl'); mine().forEach((n) => n.classList.add('hl')); });
    verse.addEventListener('mouseleave', clear);
    verse.addEventListener('click', () => {
      const first = mine()[0];
      if (first) first.scrollIntoView({ block: 'nearest', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    });
  });
  notes.forEach((note) => {
    note.addEventListener('mouseenter', () => {
      clear();
      note.classList.add('hl');
      verses.filter((el) => covers(note, Number(el.dataset.v))).forEach((el) => el.classList.add('hl'));
    });
    note.addEventListener('mouseleave', clear);
  });
})();
