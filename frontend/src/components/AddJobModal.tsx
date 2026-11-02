import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react';
import { isAxiosError } from 'axios';
import { Jobs } from '../api/endpoints';
import { errorMessage } from '../api/client';
import { Alert, Button, Field, Modal, inputCls } from './ui';

export interface AddedJob { id: number; application_id: number; title: string }

interface AddJobModalProps {
  open: boolean;
  onClose: () => void;
  onAdded?: (job: AddedJob) => void;
}

type Step = 'link' | 'form';

interface FormState {
  url: string;
  title: string;
  company: string;
  location: string;
  remote: boolean;
  applyLink: string;
  deadline: string;
  notes: string;
  description: string;
}

const EMPTY: FormState = {
  url: '', title: '', company: '', location: '', remote: false,
  applyLink: '', deadline: '', notes: '', description: '',
};

const MIN_DESCRIPTION = 50;

/** POST /jobs/add/ returns the saved job plus the pipeline application id. */
interface AddJobResponse {
  id?: number;
  title?: string;
  application_id?: number;
  job?: { id?: number; title?: string };
}

function toAdded(data: AddJobResponse, fallbackTitle: string): AddedJob | null {
  const id = data.job?.id ?? data.id;
  const appId = data.application_id;
  const title = data.job?.title ?? data.title ?? fallbackTitle;
  if (typeof id !== 'number' || typeof appId !== 'number') return null;
  return { id, application_id: appId, title };
}

/** True when the backend could not read the link and wants the user to paste details. */
function needsDetails(err: unknown): boolean {
  if (!isAxiosError(err) || err.response?.status !== 400) return false;
  const data = err.response.data as { needs_details?: boolean } | undefined;
  return Boolean(data?.needs_details);
}

export function AddJobModal({ open, onClose, onAdded }: AddJobModalProps) {
  const [step, setStep] = useState<Step>('link');
  const [form, setForm] = useState<FormState>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  // Start fresh every time the modal opens.
  useEffect(() => {
    if (!open) return;
    setForm(EMPTY);
    setStep('link');
    setBusy(false);
    setError(null);
    setInfo(null);
  }, [open]);

  const patch = (p: Partial<FormState>) => setForm((f) => ({ ...f, ...p }));
  const field = (key: keyof FormState) => (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    patch({ [key]: e.target.value } as Partial<FormState>);

  const descLen = form.description.trim().length;
  const formValid = Boolean(form.title.trim() && form.company.trim() && descLen >= MIN_DESCRIPTION);

  function enterManually() {
    patch({ applyLink: form.applyLink || form.url.trim() });
    setError(null);
    setInfo(null);
    setStep('form');
  }

  function finish(job: AddedJob) {
    onAdded?.(job);
    onClose();
  }

  async function fetchLink(e: FormEvent) {
    e.preventDefault();
    const link = form.url.trim();
    if (!link || busy) return;
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      const data = (await Jobs.add({ url: link })) as AddJobResponse;
      setBusy(false);
      const added = toAdded(data, link);
      if (!added) {
        setError('The job was saved but the response was unexpected. Check your Pipeline before adding it again.');
        return;
      }
      finish(added);
    } catch (err) {
      setBusy(false);
      if (needsDetails(err)) {
        patch({ applyLink: link });
        setInfo("We couldn't read that page. Paste the job details below. It takes about a minute.");
        setStep('form');
      } else {
        setError(errorMessage(err));
      }
    }
  }

  async function submitManual(e: FormEvent) {
    e.preventDefault();
    if (!formValid || busy) return;
    setBusy(true);
    setError(null);
    const payload: Record<string, unknown> = {
      title: form.title.trim(),
      company: form.company.trim(),
      description: form.description.trim(),
      remote: form.remote,
    };
    if (form.location.trim()) payload.location = form.location.trim();
    if (form.applyLink.trim()) payload.url = form.applyLink.trim();
    if (form.deadline) payload.deadline = form.deadline;
    if (form.notes.trim()) payload.notes = form.notes.trim();
    try {
      const data = (await Jobs.add(payload)) as AddJobResponse;
      setBusy(false);
      const added = toAdded(data, form.title.trim());
      if (!added) {
        setError('The job was saved but the response was unexpected. Check your Pipeline before adding it again.');
        return;
      }
      finish(added);
    } catch (err) {
      setBusy(false);
      setError(errorMessage(err));
    }
  }

  if (step === 'link') {
    return (
      <Modal open={open} onClose={onClose} title="Add a job" wide>
        <form onSubmit={fetchLink} className="space-y-4">
          <p className="text-sm text-slate-600">
            Found a job on a company careers page, Greenhouse, Lever or Ashby? Paste the link and we will fill in the details.
          </p>
          <Field label="Job link">
            <input
              className={inputCls}
              type="url"
              inputMode="url"
              placeholder="https://"
              value={form.url}
              onChange={field('url')}
              autoFocus
            />
          </Field>
          {error && <Alert tone="red">{error}</Alert>}
          <p className="text-xs text-slate-500">
            No link? Campus drives, referrals and LinkedIn posts are fine too. Enter their details manually.
          </p>
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
            <Button type="button" variant="ghost" onClick={enterManually} disabled={busy}>
              Enter details manually
            </Button>
            <Button type="submit" loading={busy} disabled={!form.url.trim()}>
              Fetch
            </Button>
          </div>
        </form>
      </Modal>
    );
  }

  return (
    <Modal open={open} onClose={onClose} title="Add a job" wide>
      <form onSubmit={submitManual} className="space-y-4">
        {info && <Alert tone="amber">{info}</Alert>}
        {error && <Alert tone="red">{error}</Alert>}

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Job title *">
            <input className={inputCls} required value={form.title} onChange={field('title')} placeholder="e.g. Software Engineer Intern" />
          </Field>
          <Field label="Company *">
            <input className={inputCls} required value={form.company} onChange={field('company')} placeholder="e.g. Acme Technologies" />
          </Field>
          <Field label="Location">
            <input className={inputCls} value={form.location} onChange={field('location')} placeholder="e.g. Bengaluru" />
          </Field>
          <label className="flex items-center gap-2 self-end pb-2 text-sm font-medium text-slate-700">
            <input
              type="checkbox"
              checked={form.remote}
              onChange={(e) => patch({ remote: e.target.checked })}
              className="h-4 w-4 rounded border-slate-300 accent-slate-950"
            />
            Remote role
          </label>
          <Field label="Apply link" hint="Where you will actually apply. Filled from the link you pasted, if any.">
            <input className={inputCls} type="url" inputMode="url" value={form.applyLink} onChange={field('applyLink')} placeholder="https://" />
          </Field>
          <Field label="Application deadline" hint="Leave empty if there is none.">
            <input className={inputCls} type="date" value={form.deadline} onChange={field('deadline')} />
          </Field>
        </div>

        <Field label="Notes" hint="Rounds, timings, CTC, eligibility. Anything you want to remember.">
          <input
            className={inputCls}
            value={form.notes}
            onChange={field('notes')}
            placeholder="On-campus drive · CGPA ≥ 7 · CTC 12 LPA · OA on 14 Nov"
          />
        </Field>

        <Field label="Job description *" hint="Paste the full JD. We use it to score your fit and tailor your résumé.">
          <textarea
            className={`${inputCls} min-h-40 resize-y`}
            required
            value={form.description}
            onChange={field('description')}
            placeholder="Paste the job description here"
          />
        </Field>
        <p className={`-mt-2 text-xs ${descLen >= MIN_DESCRIPTION ? 'text-slate-500' : 'text-amber-700'}`}>
          {descLen >= MIN_DESCRIPTION
            ? `${descLen} characters`
            : `Add at least ${MIN_DESCRIPTION - descLen} more characters to the description.`}
        </p>

        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
          <Button type="button" variant="ghost" onClick={() => { setError(null); setInfo(null); setStep('link'); }} disabled={busy}>
            Back
          </Button>
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center">
            {!formValid && <span className="text-xs text-slate-500 sm:mr-2">Fill in the fields marked *</span>}
            <Button type="submit" loading={busy} disabled={!formValid}>
              Add job
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  );
}
