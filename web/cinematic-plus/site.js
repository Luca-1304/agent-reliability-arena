document.documentElement.classList.add('js');

const menuButton = document.querySelector('[data-menu]');
const navigation = document.querySelector('[data-nav]');

function setMenu(open) {
  if (!menuButton || !navigation) return;
  navigation.classList.toggle('is-open', open);
  menuButton.setAttribute('aria-expanded', String(open));
}

menuButton?.addEventListener('click', () => {
  setMenu(!navigation?.classList.contains('is-open'));
});

navigation?.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => setMenu(false));
});

addEventListener('keydown', (event) => {
  if (event.key === 'Escape') setMenu(false);
});
