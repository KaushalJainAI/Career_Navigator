/** MV3 service worker: receives content-script messages, talks to backend. */

import { postPageContext, postProfileContext, postSubmitEvent, getAutofill } from './lib/api';
import type { RuntimeMessage } from './lib/types';

chrome.runtime.onMessage.addListener((msg: RuntimeMessage, _sender, sendResponse) => {
  (async () => {
    try {
      if (msg.type === 'page-context') {
        const data = await postPageContext(msg.posting);
        // If a job_id came back, immediately fetch autofill so the content
        // script can surface field suggestions.
        let autofill: unknown = null;
        if (data.job_id) {
          autofill = await getAutofill(data.job_id).catch(() => null);
        }
        sendResponse({ ok: true, data, autofill });
      } else if (msg.type === 'profile-context') {
        const data = await postProfileContext(msg.profile);
        sendResponse({ ok: true, data });
      } else if (msg.type === 'submit-event') {
        const data = await postSubmitEvent(msg.payload);
        sendResponse({ ok: true, data });
      } else {
        sendResponse({ ok: false, error: 'unknown message type' });
      }
    } catch (err) {
      sendResponse({ ok: false, error: (err as Error).message });
    }
  })();
  return true; // async response
});
