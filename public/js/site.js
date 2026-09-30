// Lists that open from a title or a picker (<details>): one open at a time; Esc or a click outside closes them.
(() => {
  const pickers = [...document.querySelectorAll('details.poem-picker, details.list-picker')];
  if (!pickers.length) return;
  pickers.forEach((d) => d.addEventListener('toggle', () => {
    if (d.open) pickers.forEach((o) => { if (o !== d) o.open = false; });
  }));
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const open = pickers.find((d) => d.open);
    if (open) {
      open.open = false;
      open.querySelector('summary').focus();
    }
  });
  document.addEventListener('click', (e) => {
    pickers.forEach((d) => { if (d.open && !d.contains(e.target)) d.open = false; });
  });
})();
