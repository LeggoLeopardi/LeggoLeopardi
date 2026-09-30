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

  // Variants of a place, in a popover under its line (a bottom sheet on phones).
  // The content is copied from the variant list at the bottom of the page, which stays as the fallback.
  const pop = document.getElementById('popover');
  if (!pop) return;
  const title = pop.querySelector('#popover-title');
  const body = pop.querySelector('.popover-body');
  const closeButton = pop.querySelector('.popover-close');
  const narrow = window.matchMedia('(max-width: 800px)');
  let opener = null;

  const unmark = () => root.querySelectorAll('a.place.on').forEach((a) => a.classList.remove('on'));
  const close = () => {
    if (pop.hidden) return;
    pop.hidden = true;
    unmark();
    if (opener) opener.focus();
    opener = null;
  };
  const open = (a) => {
    const item = document.getElementById(`place-${a.dataset.place}`);
    if (!item) return;
    title.textContent = `${title.dataset.label} · ${item.querySelector('.where').textContent}`;
    body.replaceChildren(item.querySelector('ul').cloneNode(true));
    unmark();
    root.querySelectorAll(`a.place[data-place="${a.dataset.place}"]`).forEach((x) => x.classList.add('on'));
    pop.hidden = false;
    if (narrow.matches) {
      pop.style.left = '';
      pop.style.top = '';
    } else {
      const host = root.getBoundingClientRect();
      const line = (a.closest('.fverse, .facs-head span') || a).getBoundingClientRect();
      const word = a.getBoundingClientRect();
      const left = Math.max(0, Math.min(word.left - host.left, host.width - pop.offsetWidth));
      pop.style.left = `${left}px`;
      pop.style.top = `${line.bottom - host.top + 6}px`;
    }
    opener = a;
    closeButton.focus();
  };

  root.addEventListener('click', (e) => {
    const a = e.target.closest('a.place');
    if (a && !a.closest('#popover')) {
      e.preventDefault();
      open(a);
    } else if (!pop.hidden && !e.target.closest('#popover')) {
      close();
    }
  });
  closeButton.addEventListener('click', close);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') close();
  });
})();
