// The poem list under the title (<details>): close it with Esc or a click outside.
(() => {
  const picker = document.querySelector('.poem-picker');
  if (!picker) return;
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && picker.open) {
      picker.open = false;
      picker.querySelector('summary').focus();
    }
  });
  document.addEventListener('click', (e) => {
    if (picker.open && !picker.contains(e.target)) picker.open = false;
  });
})();
