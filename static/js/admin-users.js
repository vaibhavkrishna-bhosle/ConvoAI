// Admin → Users: create, edit (role, password, active, collection access), delete.
import { $, api, confirmDialog, esc, showError, toast } from './admin-common.js';

let users = [];
let me = null;
let collections = {};
let editing = null;

function fmtDate(iso) {
  if (!iso) return 'Never';
  return new Date(`${iso.replace(' ', 'T')}Z`).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function render() {
  $('user-rows').innerHTML = users.map((u) => `
    <tr data-id="${u.id}" class="${u.is_active ? '' : 'inactive'}">
      <td><div class="doc-cell"><span class="avatar small">${esc(u.name.split(/\s+/).map((p) => p[0]).slice(0, 2).join('').toUpperCase())}</span>
        <div><div class="doc-title">${esc(u.name)}${u.id === me ? ' <span class="badge">You</span>' : ''}${u.is_active ? '' : ' <span class="badge err">Inactive</span>'}</div>
        <div class="muted doc-meta">${esc(u.email)}</div></div></div></td>
      <td><span class="badge ${u.role === 'admin' ? 'primary' : ''}">${u.role === 'admin' ? 'Admin' : 'User'}</span></td>
      <td>${u.role === 'admin' ? '<span class="muted">All collections</span>'
        : (u.collection_ids.map((id) => collections[id] ? `<span class="coll-pill" style="--c:${esc(collections[id].color)}"><md-icon>${esc(collections[id].icon)}</md-icon>${esc(collections[id].name)}</span>` : '').join(' ') || '<span class="badge warn">None</span>')}</td>
      <td class="muted">${fmtDate(u.last_login_at)}</td>
      <td>${u.conversations}</td>
      <td class="row-actions">
        <md-icon-button data-act="edit" aria-label="Edit ${esc(u.name)}"><md-icon>edit</md-icon></md-icon-button>
        <md-icon-button data-act="delete" aria-label="Delete ${esc(u.name)}" ${u.id === me ? 'disabled' : ''}><md-icon>delete</md-icon></md-icon-button>
      </td>
    </tr>`).join('');
}

async function load() {
  const [u, c] = await Promise.all([api('/api/users'), api('/api/collections')]);
  users = u.users;
  me = u.me;
  collections = Object.fromEntries(c.collections.map((x) => [x.id, x]));
  render();
}

function syncAdminNote() {
  const isAdmin = $('u-role').value === 'admin';
  $('u-admin-note').hidden = !isAdmin;
  $('u-collections').classList.toggle('disabled', isAdmin);
}

function openDialog(user) {
  editing = user;
  $('user-dialog-title').textContent = user ? `Edit ${user.name}` : 'New user';
  $('u-name').value = user?.name || '';
  $('u-email').value = user?.email || '';
  $('u-password').value = '';
  $('u-password').label = user ? 'New password (leave blank to keep)' : 'Password (at least 8 characters)';
  $('u-role').value = user?.role || 'user';
  $('u-active').selected = user ? user.is_active : true;
  document.querySelectorAll('#u-collections md-checkbox').forEach((cb) => {
    cb.checked = !!user?.collection_ids.includes(Number(cb.value));
  });
  syncAdminNote();
  showError('u-error', '');
  $('user-dialog').show();
}

$('u-role').addEventListener('change', syncAdminNote);

$('u-save').addEventListener('click', async () => {
  const body = {
    name: $('u-name').value,
    email: $('u-email').value,
    role: $('u-role').value,
    is_active: $('u-active').selected,
    collection_ids: [...document.querySelectorAll('#u-collections md-checkbox')].filter((cb) => cb.checked).map((cb) => Number(cb.value)),
  };
  if (!editing || $('u-password').value) body.password = $('u-password').value;
  try {
    if (editing) await api(`/api/users/${editing.id}`, { method: 'PATCH', body: JSON.stringify(body) });
    else await api('/api/users', { method: 'POST', body: JSON.stringify(body) });
    $('user-dialog').close();
    toast(editing ? 'User updated' : 'User created');
    load();
  } catch (err) {
    showError('u-error', err.message);
  }
});

$('new-user').addEventListener('click', () => openDialog(null));

$('user-rows').addEventListener('click', async (e) => {
  const btn = e.target.closest('[data-act]');
  if (!btn || btn.disabled) return;
  const user = users.find((u) => u.id === Number(btn.closest('tr').dataset.id));
  if (btn.dataset.act === 'edit') { openDialog(user); return; }
  if (!await confirmDialog('Delete user?', `${user.name}'s account and their ${user.conversations} chat(s) will be deleted. This can't be undone. To keep their history, deactivate the account instead.`)) return;
  try {
    await api(`/api/users/${user.id}`, { method: 'DELETE' });
    toast(`Deleted ${user.name}`);
    load();
  } catch (err) { toast(err.message, 5000); }
});

load();
