import { describe, expect, it, vi } from 'vitest';
import { applyAutofill, attachSubmitListener } from '../src/content/runtime';
import type { AutofillPayload } from '../src/lib/types';

function htmlDoc(body: string): Document {
  return new DOMParser().parseFromString(`<!doctype html><html><body>${body}</body></html>`, 'text/html');
}

const autofill: AutofillPayload = {
  application_id: 7,
  fields: {
    full_name: 'Alice Doe',
    email: 'alice@example.com',
    phone: '1234567890',
    linkedin: 'https://linkedin.com/in/alice',
    github: 'https://github.com/alice',
  },
  field_confidence: {
    full_name: 1,
    email: 1,
    phone: 0.9,
    linkedin: 0.9,
    github: 0.9,
  },
};

describe('applyAutofill', () => {
  it('fills empty matching fields and dispatches input/change events', () => {
    const doc = htmlDoc(`
      <label for="name">Full name</label><input id="name" />
      <input name="candidate_email" type="email" />
      <input placeholder="Phone number" type="tel" />
    `);
    const name = doc.querySelector<HTMLInputElement>('#name')!;
    const onInput = vi.fn();
    const onChange = vi.fn();
    name.addEventListener('input', onInput);
    name.addEventListener('change', onChange);

    const result = applyAutofill(doc, autofill);

    expect(name.value).toBe('Alice Doe');
    expect(doc.querySelector<HTMLInputElement>('input[type="email"]')?.value).toBe('alice@example.com');
    expect(doc.querySelector<HTMLInputElement>('input[type="tel"]')?.value).toBe('1234567890');
    expect(result.filled).toMatchObject({
      full_name: 'Alice Doe',
      email: 'alice@example.com',
      phone: '1234567890',
    });
    expect(onInput).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it('does not overwrite existing user-entered values', () => {
    const doc = htmlDoc('<input name="email" type="email" value="typed@example.com" />');

    const result = applyAutofill(doc, autofill);

    expect(doc.querySelector<HTMLInputElement>('input')?.value).toBe('typed@example.com');
    expect(result.skipped.email).toBe('already_filled');
  });

  it('skips low-confidence values', () => {
    const doc = htmlDoc('<input name="phone" type="tel" />');
    const result = applyAutofill(doc, {
      application_id: null,
      fields: { phone: '123' },
      field_confidence: { phone: 0.5 },
    });

    expect(doc.querySelector<HTMLInputElement>('input')?.value).toBe('');
    expect(result.skipped.phone).toBe('low_confidence_or_empty');
  });
});

describe('attachSubmitListener', () => {
  it('records filled values when the user clicks an apply button', () => {
    const sendMessage = vi.fn();
    vi.stubGlobal('chrome', { runtime: { sendMessage } });

    attachSubmitListener({
      parser: 'greenhouse',
      jobIdGetter: () => 42,
      fieldValuesGetter: () => ({ email: 'alice@example.com' }),
    });

    const button = document.createElement('button');
    button.textContent = 'Submit application';
    document.body.appendChild(button);
    button.click();

    expect(sendMessage).toHaveBeenCalledWith({
      type: 'submit-event',
      payload: {
        job_id: 42,
        tier: 'autofill',
        parser: 'greenhouse',
        url: 'http://localhost:3000/',
        field_values: { email: 'alice@example.com' },
      },
    });
  });
});
