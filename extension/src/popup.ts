async function load() {
  const settings = await chrome.storage.local.get(['backend', 'token']);
  (document.getElementById('backend') as HTMLInputElement).value = settings.backend || 'http://localhost:8000';
  (document.getElementById('token') as HTMLInputElement).value = settings.token || '';
}

async function saveAndTest() {
  const backend = (document.getElementById('backend') as HTMLInputElement).value.trim();
  const token = (document.getElementById('token') as HTMLInputElement).value.trim();
  await chrome.storage.local.set({ backend, token });
  const status = document.getElementById('status')!;
  status.className = 'status';
  status.textContent = 'Testing…';
  try {
    const resp = await fetch(`${backend}/api/v1/auth/me/`, {
      headers: { Authorization: `Token ${token}` },
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const me = await resp.json();
    status.className = 'status ok';
    status.textContent = `Connected as ${me.email}`;
  } catch (err) {
    status.className = 'status err';
    status.textContent = `Failed: ${(err as Error).message}`;
  }
}

load();
document.getElementById('save')!.addEventListener('click', saveAndTest);
