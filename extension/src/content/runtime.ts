import type { ParsedPosting, PostingParser } from '../lib/types';

/** Watch for URL changes (SPA navigation) and re-run the parser; debounce so
 *  rapid mutations don't spam the backend. */
export function runPostingParser(parser: PostingParser) {
  let lastSentId = '';
  let timer: number | undefined;

  function tick() {
    if (!parser.detect(location.href)) return;
    const posting = parser.parse(document, location.href);
    if (!posting) return;
    if (posting.external_id === lastSentId) return;
    lastSentId = posting.external_id;
    sendPosting(posting);
  }

  function schedule() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(tick, 800) as unknown as number;
  }

  // Initial run + SPA listeners.
  schedule();
  window.addEventListener('popstate', schedule);
  const observer = new MutationObserver(schedule);
  observer.observe(document.body, { subtree: true, childList: true });
}

function sendPosting(posting: ParsedPosting) {
  chrome.runtime.sendMessage({ type: 'page-context', posting }, (response) => {
    if (!response?.ok) {
      console.debug('[career-navigator] page-context failed', response);
    }
  });
}

export function attachSubmitListener(opts: {
  parser: string;
  jobIdGetter: () => number | null;
}) {
  document.addEventListener(
    'click',
    (e) => {
      const target = e.target as HTMLElement | null;
      if (!target) return;
      const btn = target.closest('button, input[type=submit], a');
      if (!btn) return;
      const text = (btn.textContent || (btn as HTMLInputElement).value || '').toLowerCase();
      if (!/submit|apply|send application/.test(text)) return;
      const jobId = opts.jobIdGetter();
      if (jobId == null) return;
      chrome.runtime.sendMessage({
        type: 'submit-event',
        payload: {
          job_id: jobId,
          tier: 'autofill',
          parser: opts.parser,
          url: location.href,
        },
      });
    },
    true,
  );
}
