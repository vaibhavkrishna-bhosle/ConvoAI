// Shared shell behaviour: account menu, flash dismissal.

const avatarBtn = document.getElementById('account-button');
const accountMenu = document.getElementById('account-menu');
if (avatarBtn && accountMenu) {
  avatarBtn.addEventListener('click', () => { accountMenu.open = !accountMenu.open; });
}

document.getElementById('menu-signout')?.addEventListener('click', () => {
  document.getElementById('signout-form').submit();
});

document.querySelectorAll('[data-dismiss-flash]').forEach((btn) => {
  btn.addEventListener('click', () => btn.closest('.flash')?.remove());
});

export function csrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content || '';
}
