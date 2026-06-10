import type { AutofillPayload, AutofillResult, ParsedPosting, PostingParser } from '../lib/types';

/** Watch for URL changes (SPA navigation) and re-run the parser; debounce so
 *  rapid mutations don't spam the backend. */
export function runPostingParser(parser: PostingParser) {
  let lastSentId = '';
  let currentJobId: number | null = null;
  let lastFilled: Record<string, string> = {};
  let timer: number | undefined;

  function tick() {
    if (!parser.detect(location.href)) return;
    const posting = parser.parse(document, location.href);
    if (!posting) return;
    if (posting.external_id === lastSentId) return;
    lastSentId = posting.external_id;
    sendPosting(posting, (jobId, autofill) => {
      currentJobId = jobId;
      if (autofill) {
        lastFilled = applyAutofill(document, autofill).filled;
      }
    });
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
  attachSubmitListener({
    parser: parser.id,
    jobIdGetter: () => currentJobId,
    fieldValuesGetter: () => lastFilled,
  });
}

function sendPosting(
  posting: ParsedPosting,
  onAutofill?: (jobId: number | null, autofill: AutofillPayload | null) => void,
) {
  chrome.runtime.sendMessage({ type: 'page-context', posting }, (response) => {
    if (!response?.ok) {
      console.debug('[career-navigator] page-context failed', response);
      return;
    }
    onAutofill?.(response.data?.job_id ?? null, response.autofill ?? null);
  });
}

export function attachSubmitListener(opts: {
  parser: string;
  jobIdGetter: () => number | null;
  fieldValuesGetter?: () => Record<string, string>;
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
          field_values: opts.fieldValuesGetter?.() ?? {},
        },
      });
    },
    true,
  );
}

const FIELD_ALIASES: Record<string, string[]> = {
  full_name: ['full name', 'name', 'candidate name', 'first and last name'],
  email: ['email', 'e-mail'],
  phone: ['phone', 'mobile', 'telephone', 'contact number'],
  linkedin: ['linkedin', 'linkedin profile'],
  github: ['github', 'git hub'],
};

export function applyAutofill(doc: Document, payload: AutofillPayload): AutofillResult {
  const result: AutofillResult = { filled: {}, skipped: {} };
  const fields = payload.fields || {};
  const confidence = payload.field_confidence || {};

  for (const [key, value] of Object.entries(fields)) {
    if (!value || (confidence[key] ?? 0) < 0.8) {
      result.skipped[key] = 'low_confidence_or_empty';
      continue;
    }

    const input = findInputForField(doc, key);
    if (!input) {
      result.skipped[key] = 'field_not_found';
      continue;
    }
    if (input.value.trim()) {
      result.skipped[key] = 'already_filled';
      continue;
    }

    input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    result.filled[key] = value;
  }

  return result;
}

function findInputForField(doc: Document, key: string): HTMLInputElement | null {
  const candidates = Array.from(
    doc.querySelectorAll<HTMLInputElement>('input:not([type]), input[type="text"], input[type="email"], input[type="tel"], input[type="url"]'),
  ).filter((input) => !input.disabled && !input.readOnly);

  return candidates.find((input) => inputMatches(input, key, doc)) ?? null;
}

function inputMatches(input: HTMLInputElement, key: string, doc: Document): boolean {
  const haystack = [
    input.name,
    input.id,
    input.placeholder,
    input.getAttribute('aria-label') || '',
    input.labels ? Array.from(input.labels).map((label) => label.textContent || '').join(' ') : '',
    labelForId(doc, input.id),
  ].join(' ').toLowerCase();

  return (FIELD_ALIASES[key] || [key]).some((alias) => haystack.includes(alias));
}

function labelForId(doc: Document, id: string): string {
  if (!id) return '';
  return doc.querySelector(`label[for="${CSS.escape(id)}"]`)?.textContent || '';
}
