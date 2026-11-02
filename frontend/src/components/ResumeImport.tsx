import { useRef, useState, type DragEvent, type FormEvent } from 'react';
import { CheckCircle2, FileText, Loader2, UploadCloud } from 'lucide-react';
import { Resumes } from '../api/endpoints';
import { errorMessage } from '../api/client';
import type { ResumeUploadResult } from '../lib/types';
import { Alert, Badge, Button, inputCls } from './ui';

const FILE_RE = /\.(pdf|docx|txt)$/i;
const MIN_TEXT = 40;
const SKILL_PREVIEW = 12;

type Json = Record<string, unknown>;
const str = (v: unknown): string => (typeof v === 'string' ? v.trim() : '');
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const obj = (v: unknown): Json => (v && typeof v === 'object' && !Array.isArray(v) ? (v as Json) : {});

/** Turns profile_update.changed keys (e.g. "preference.target_titles") into plain labels. */
const CHANGED_LABELS: Record<string, string> = {
  full_name: 'Name', headline: 'Headline', summary: 'Summary', location: 'Location',
  phone: 'Phone', website: 'Website', linkedin: 'LinkedIn', github: 'GitHub',
  skills: 'Skills', experiences: 'Experience', educations: 'Education', projects: 'Projects',
  'preference.target_titles': 'Target roles', 'preference.locations': 'Locations',
};
function changedLabels(changed: string[]): string[] {
  return Array.from(new Set(changed.map((c) => CHANGED_LABELS[c] ?? c.replace(/^preference\./, 'Job preferences: '))));
}

export function ResumeImport({ onDone }: { onDone?: (r: ResumeUploadResult) => void }) {
  const [tab, setTab] = useState<'file' | 'text'>('file');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<ResumeUploadResult | null>(null);
  const [dragging, setDragging] = useState(false);
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  function finish(r: ResumeUploadResult) {
    setResult(r);
    onDone?.(r);
  }

  function reset() {
    setResult(null);
    setError('');
    setText('');
  }

  async function sendFile(file: File) {
    if (!FILE_RE.test(file.name)) {
      setError('That file type is not supported. Upload a PDF, DOCX or TXT file.');
      return;
    }
    setBusy(true);
    setError('');
    setResult(null);
    try {
      finish(await Resumes.upload(file));
    } catch (e) {
      setError(errorMessage(e, 'Upload failed. Please try again.'));
    } finally {
      setBusy(false);
    }
  }

  async function sendText(e: FormEvent) {
    e.preventDefault();
    const t = text.trim();
    if (t.length < MIN_TEXT) {
      setError(`Paste the full text of your résumé (at least ${MIN_TEXT} characters).`);
      return;
    }
    setBusy(true);
    setError('');
    setResult(null);
    try {
      finish(await Resumes.importText(t));
    } catch (e) {
      setError(errorMessage(e, 'Could not read that text. Please try again.'));
    } finally {
      setBusy(false);
    }
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && !busy) void sendFile(file);
  }

  if (result) {
    if (result.parse_status === 'failed') {
      return (
        <div className="space-y-4">
          <Alert tone="red">
            <p className="font-semibold">We could not read this résumé.</p>
            {result.parse_error && <p className="mt-1 break-words">{result.parse_error}</p>}
          </Alert>
          <p className="text-sm text-slate-600">
            Scanned PDFs (a photo or image of a résumé) cannot be read. Open your résumé, select all the text,
            copy it and paste it instead. Works for Word and Google Docs too.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => { reset(); setTab('text'); }}>Paste text instead</Button>
            <Button variant="secondary" onClick={reset}>Try another file</Button>
          </div>
        </div>
      );
    }
    if (result.parse_status === 'pending') {
      return (
        <div className="space-y-4">
          <Alert tone="amber">Your résumé is still being read. Check again in a moment.</Alert>
          <Button variant="secondary" onClick={reset}>Import another résumé</Button>
        </div>
      );
    }
    return (
      <div className="space-y-5">
        <div className="flex items-center gap-2 text-sm font-semibold text-emerald-700">
          <CheckCircle2 className="h-5 w-5" aria-hidden="true" /> Résumé read. Here is what we found.
        </div>
        <Extracted r={result} />
        <Button variant="ghost" onClick={reset} className="px-0">Import a different résumé</Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div role="tablist" aria-label="How do you want to add your résumé?" className="inline-flex rounded-xl bg-slate-100 p-1">
        {([['file', 'Upload file'], ['text', 'Paste text']] as const).map(([key, label]) => (
          <button
            key={key}
            role="tab"
            type="button"
            aria-selected={tab === key}
            aria-controls={`resume-panel-${key}`}
            id={`resume-tab-${key}`}
            onClick={() => { setTab(key); setError(''); }}
            className={`rounded-lg px-4 py-1.5 text-sm font-semibold transition ${tab === key ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'file' && (
        <div role="tabpanel" id="resume-panel-file" aria-labelledby="resume-tab-file">
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            className="hidden"
            aria-label="Choose your résumé file"
            onChange={(e) => {
              const f = e.target.files?.[0];
              e.target.value = '';
              if (f) void sendFile(f);
            }}
          />
          <div
            role="button"
            tabIndex={0}
            aria-label="Choose a résumé file, or drop one here"
            aria-disabled={busy}
            onClick={() => { if (!busy) inputRef.current?.click(); }}
            onKeyDown={(e) => {
              if ((e.key === 'Enter' || e.key === ' ') && !busy) { e.preventDefault(); inputRef.current?.click(); }
            }}
            onDragOver={(e) => { e.preventDefault(); if (!busy) setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={`grid cursor-pointer place-items-center rounded-2xl border-2 border-dashed px-4 py-10 text-center transition ${
              dragging ? 'border-teal-500 bg-teal-50' : 'border-slate-300 bg-slate-50 hover:border-slate-400'
            } ${busy ? 'cursor-wait opacity-70' : ''}`}
          >
            {busy ? (
              <div className="flex flex-col items-center gap-2 text-sm text-slate-600">
                <Loader2 className="h-6 w-6 animate-spin text-slate-500" aria-hidden="true" />
                <span>Reading your résumé. This takes a few seconds.</span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <span className="grid h-12 w-12 place-items-center rounded-full bg-white text-slate-500 shadow-sm">
                  <UploadCloud className="h-6 w-6" aria-hidden="true" />
                </span>
                <span className="text-sm font-semibold text-slate-900">Drop your résumé here, or tap to choose a file</span>
                <span className="text-xs text-slate-500">PDF, DOCX or TXT</span>
              </div>
            )}
          </div>
          <p className="mt-2 flex items-center gap-1.5 text-xs text-slate-500">
            <FileText className="h-3.5 w-3.5" aria-hidden="true" /> The first résumé you add fills your profile automatically.
          </p>
        </div>
      )}

      {tab === 'text' && (
        <form role="tabpanel" id="resume-panel-text" aria-labelledby="resume-tab-text" onSubmit={sendText} className="space-y-3">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700">Résumé text</span>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={10}
              disabled={busy}
              placeholder="Paste the full text of your résumé here. Name, skills, projects, education and experience all help."
              className={`${inputCls} min-h-[12rem] resize-y leading-relaxed`}
            />
          </label>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-slate-500">{text.trim().length} characters · at least {MIN_TEXT}</span>
            <Button type="submit" loading={busy} disabled={text.trim().length < MIN_TEXT}>
              {busy ? 'Reading…' : 'Read this résumé'}
            </Button>
          </div>
        </form>
      )}

      {error && <Alert tone="red">{error}</Alert>}
    </div>
  );
}

function Extracted({ r }: { r: ResumeUploadResult }) {
  const p = r.parsed_json ?? {};
  const name = str(p.full_name);
  const headline = str(p.headline);
  const skills = arr(p.skills)
    .map((s) => (typeof s === 'string' ? s.trim() : str(obj(s).name)))
    .filter(Boolean);
  const experiences = arr(p.experiences);
  const educations = arr(p.educations).map(obj);
  const projects = arr(p.projects);
  const changed = changedLabels(r.profile_update?.changed ?? []);

  const counts = [
    { label: 'Skills', value: skills.length },
    { label: 'Experience', value: experiences.length },
    { label: 'Projects', value: projects.length },
  ];

  return (
    <div className="space-y-5">
      <div>
        <p className="text-lg font-semibold text-slate-950">{name || 'Name not found'}</p>
        {headline && <p className="text-sm text-slate-600">{headline}</p>}
      </div>

      <dl className="grid grid-cols-3 gap-2">
        {counts.map((c) => (
          <div key={c.label} className="rounded-xl border border-slate-200 bg-slate-50 px-2 py-3 text-center">
            <dt className="text-xs text-slate-500">{c.label}</dt>
            <dd className="text-xl font-bold text-slate-950">{c.value}</dd>
          </div>
        ))}
      </dl>

      {skills.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Skills</p>
          <div className="flex flex-wrap gap-1.5">
            {skills.slice(0, SKILL_PREVIEW).map((s) => <Badge key={s} tone="teal">{s}</Badge>)}
            {skills.length > SKILL_PREVIEW && <Badge>+{skills.length - SKILL_PREVIEW} more</Badge>}
          </div>
        </div>
      )}

      {educations.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Education</p>
          <ul className="space-y-2">
            {educations.map((ed, i) => {
              const degree = [str(ed.degree), str(ed.field_of_study)].filter(Boolean).join(', ');
              const gpa = str(ed.gpa);
              return (
                <li key={i} className="text-sm">
                  <span className="font-medium text-slate-900">{str(ed.institution) || 'Institution not found'}</span>
                  {degree && <span className="text-slate-600"> · {degree}</span>}
                  {gpa && <span className="ml-1 font-semibold text-slate-900">CGPA {gpa}</span>}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Your profile</p>
        {changed.length > 0 ? (
          <p className="text-sm text-slate-700">Filled in: {changed.join(', ')}. You can edit any of it on your profile.</p>
        ) : (
          <p className="text-sm text-slate-600">Nothing new was added. Your existing profile details stay as they are.</p>
        )}
      </div>
    </div>
  );
}
