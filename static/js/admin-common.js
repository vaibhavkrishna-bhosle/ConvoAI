// Shared helpers for admin pages.
import { csrfToken } from './app.js';

export const $ = (id) => document.getElementById(id);
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/** fetch JSON; throws Error(message) with the server's error text. `err.status` is set. */
export async function api(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { 'X-CSRFToken': csrfToken(), ...(options.body && !(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(body.error || res.statusText);
    err.status = res.status;
    throw err;
  }
  return body;
}

export function toast(message, ms = 3500) {
  let t = $('toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'toast'; t.className = 'toast'; t.setAttribute('role', 'status');
    document.body.appendChild(t);
  }
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, ms);
}

/** Material confirm dialog; resolves true/false. */
export function confirmDialog(title, text, okLabel = 'Delete', danger = true) {
  let dlg = $('confirm-dialog');
  if (!dlg) {
    dlg = document.createElement('md-dialog');
    dlg.id = 'confirm-dialog';
    dlg.type = 'alert';
    dlg.innerHTML = `<div slot="headline" id="confirm-title"></div><div slot="content" id="confirm-text"></div>
      <div slot="actions"><md-text-button id="confirm-cancel">Cancel</md-text-button><md-filled-button id="confirm-ok"></md-filled-button></div>`;
    document.body.appendChild(dlg);
  }
  $('confirm-title').textContent = title;
  $('confirm-text').textContent = text;
  $('confirm-ok').textContent = okLabel;
  $('confirm-ok').classList.toggle('danger', danger);
  return new Promise((resolve) => {
    const done = (v) => { dlg.close(); resolve(v); };
    $('confirm-ok').onclick = () => done(true);
    $('confirm-cancel').onclick = () => done(false);
    dlg.show();
  });
}

/** Show an error inside a dialog's error box. */
export function showError(id, message) {
  const el = $(id);
  el.textContent = message || '';
  el.hidden = !message;
}
