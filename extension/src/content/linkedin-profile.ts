import { linkedinProfileParser } from '../parsers/linkedin-profile';

/** LinkedIn profile content script — adds a floating "Save to Career Navigator"
 *  button. We don't auto-send on every page load because the user may scroll
 *  through many profiles a minute and we don't want to flood the backend. */

function injectButton() {
  if (document.getElementById('cn-save-contact')) return;
  const btn = document.createElement('button');
  btn.id = 'cn-save-contact';
  btn.textContent = '⭐ Save to Career Navigator';
  Object.assign(btn.style, {
    position: 'fixed',
    bottom: '24px',
    right: '24px',
    zIndex: '99999',
    padding: '10px 16px',
    background: '#0f172a',
    color: 'white',
    borderRadius: '14px',
    border: '2px solid #2dd4bf',
    fontFamily: 'system-ui, sans-serif',
    fontWeight: '700',
    cursor: 'pointer',
    boxShadow: '0 4px 0 #2dd4bf',
  } as CSSStyleDeclaration);
  btn.addEventListener('click', () => {
    const profile = linkedinProfileParser.parse(document, location.href);
    if (!profile) {
      btn.textContent = '⚠️ Could not parse profile';
      return;
    }
    btn.textContent = '⌛ Saving…';
    chrome.runtime.sendMessage({ type: 'profile-context', profile }, (response) => {
      if (response?.ok) {
        const colleagues = response.data?.colleagues_inferred ?? 0;
        btn.textContent = colleagues > 0
          ? `✅ Saved (+${colleagues} colleague edges)`
          : '✅ Saved';
      } else {
        btn.textContent = `⚠️ ${response?.error || 'Save failed'}`;
      }
    });
  });
  document.body.appendChild(btn);
}

if (linkedinProfileParser.detect(location.href)) {
  injectButton();
  new MutationObserver(injectButton).observe(document.body, { subtree: true, childList: true });
}
