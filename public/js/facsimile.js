// Text–facsimile alignment: a verse and its zone on the page light up together.
// Without this script the page still works: zones link to their verse (#vN).
(() => {
  const root = document.querySelector('.facs');
  if (!root) return;
  const same = (v) => root.querySelectorAll(`[data-v="${v}"]`);
  const light = (v, cls, on) => same(v).forEach((el) => el.classList.toggle(cls, on));
  const select = (v) => {
    root.querySelectorAll('.sel').forEach((el) => el.classList.remove('sel'));
    if (v) light(v, 'sel', true);
  };
  root.querySelectorAll('[data-v]').forEach((el) => {
    const v = el.dataset.v;
    el.addEventListener('mouseenter', () => light(v, 'hl', true));
    el.addEventListener('mouseleave', () => light(v, 'hl', false));
    el.addEventListener('focus', () => light(v, 'hl', true));
    el.addEventListener('blur', () => light(v, 'hl', false));
    el.addEventListener('click', (e) => {
      if (e.target.closest('a.place')) return;
      select(v);
    });
  });
  const m = /^#v(\d+)$/.exec(window.location.hash);
  if (m) select(m[1]);
})();
