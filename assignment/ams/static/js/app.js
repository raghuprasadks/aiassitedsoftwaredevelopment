async function api(path, options = {}) {
  const token = document.querySelector('meta[name="csrf-token"]')?.content;
  const headers = new Headers(options.headers || {});
  const method = (options.method || 'GET').toUpperCase();
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && token) {
    headers.set('X-CSRFToken', token);
  }
  const response = await fetch(path, { ...options, headers, credentials: 'same-origin' });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.error?.message || 'Request failed');
  return body;
}

function escapeHtml(value) {
  const element = document.createElement('span');
  element.textContent = value == null ? '' : String(value);
  return element.innerHTML;
}

function showToast(message, isError = false) {
  const area = document.getElementById('toast-area');
  if (!area) return;
  const toast = document.createElement('div');
  toast.className = `alert ${isError ? 'alert-danger' : 'alert-success'} shadow`;
  toast.textContent = message;
  area.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

async function loadProfile() {
  try {
    const body = await api('/api/auth/profile');
    const name = document.getElementById('nav-name');
    if (name) name.textContent = body.data.name;
  } catch (error) {
    if (window.location.pathname !== '/login') window.location.assign('/login');
  }
}

document.getElementById('logout-button')?.addEventListener('click', async () => {
  try {
    await api('/api/auth/logout', { method: 'POST' });
    window.location.assign('/login');
  } catch (error) {
    showToast(error.message, true);
  }
});

if (document.getElementById('logout-button')) loadProfile();
