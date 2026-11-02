import { useEffect, useState, type ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { AxiosError } from 'axios';
import { CheckCircle2, Circle, ExternalLink } from 'lucide-react';
import { Applications, Jobs, Tailoring } from '../../api/endpoints';
import { errorMessage } from '../../api/client';
import { GhostRiskBadge } from '../../components/GhostRiskBadge';
import {
  Alert, Badge, Button, Card, EmptyState, Field, FitRing, inputCls, ReasonList,
  salaryLabel, Spinner, timeAgo, VerdictBadge,
} from '../../components/ui';
import {
  PIPELINE_ORDER, STATUS_LABEL, type AppStatus, type Application, type CoverLetter,
  type JobDetailData, type MatchData, type TailoredResume,
} from '../../lib/types';

type Tab = 'jd' | 'resume' | 'cover';
type Busy = 'save' | 'resume' | 'cover' | null;

/** Statuses before the candidate has applied on the company site. */
const PRE_APPLY: AppStatus[] = ['saved', 'tailored', 'ready'];
/** Statuses where an online test or interview round is coming up. */
const INTERVIEW_STATUSES: AppStatus[] = ['assessment', 'phone', 'onsite'];

const LINK_PRIMARY = 'inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800';
const LINK_SECONDARY = 'inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-900 transition hover:bg-slate-50';
const TEXT_ACTION = 'text-sm font-semibold text-teal-700 hover:underline';

const dateFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });

// ---------- helpers ----------

function httpStatus(e: unknown): number | undefined {
  return (e as AxiosError | undefined)?.response?.status;
}

function asList(data: unknown): Application[] {
  if (Array.isArray(data)) return data as Application[];
  const results = (data as { results?: Application[] } | null)?.results;
  return results ?? [];
}

function fmtDate(iso: string | null | undefined): string {
  return iso ? dateFmt.format(new Date(iso)) : '';
}

/** Parses a YYYY-MM-DD string as a local calendar day (avoids UTC off-by-one). */
function parseDay(ymd: string): Date {
  const [y, m, d] = ymd.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function deadlineLabel(ymd: string): string {
  const day = parseDay(ymd);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const n = Math.round((day.getTime() - today.getTime()) / 86400000);
  const abs = dateFmt.format(day);
  if (n < 0) return `Deadline passed ${-n === 1 ? 'yesterday' : `${-n} days ago`} · ${abs}`;
  if (n === 0) return `Deadline today · ${abs}`;
  if (n === 1) return `Deadline tomorrow · ${abs}`;
  return `Deadline in ${n} days · ${abs}`;
}

/** ISO timestamp -> value for a datetime-local input (local time). */
function toLocalInput(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

async function loadMatch(id: number): Promise<{ match: MatchData | null; noProfile: boolean }> {
  try {
    return { match: (await Jobs.match(id)) as MatchData, noProfile: false };
  } catch (e) {
    return { match: null, noProfile: httpStatus(e) === 400 };
  }
}

/** Missing materials (404) are normal, so failures just mean "not generated yet". */
async function loadMaterials(appId: number): Promise<{ resume: TailoredResume | null; cover: CoverLetter | null }> {
  const [resume, cover] = await Promise.all([
    Tailoring.getResume(appId).then((r: TailoredResume) => r).catch(() => null),
    Tailoring.getCoverLetter(appId).then((c: CoverLetter) => c).catch(() => null),
  ]);
  return { resume, cover };
}

// ---------- small presentational pieces ----------

function Chips({ items, tone }: { items: string[]; tone: 'green' | 'amber' }) {
  if (!items.length) return <p className="text-sm text-slate-500">None yet.</p>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((s) => <Badge key={s} tone={tone}>{s}</Badge>)}
    </div>
  );
}

function CheckRow({ done, label, hint, children }: { done: boolean; label: string; hint?: string; children?: ReactNode }) {
  const Icon = done ? CheckCircle2 : Circle;
  return (
    <li className="flex gap-3">
      <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${done ? 'text-teal-600' : 'text-slate-300'}`} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-900">
          <span className="sr-only">{done ? 'Done: ' : 'To do: '}</span>
          {label}
        </p>
        {hint && <p className="text-xs text-slate-500">{hint}</p>}
        {children && <div className="mt-2">{children}</div>}
      </div>
    </li>
  );
}

function GeneratePrompt({ text, buttonLabel, loading, disabled, onClick }: {
  text: string; buttonLabel: string; loading: boolean; disabled: boolean; onClick: () => void;
}) {
  return (
    <div className="rounded-xl bg-slate-50 p-5 text-center">
      <p className="mx-auto max-w-prose text-sm text-slate-600">{text}</p>
      <div className="mt-4 flex justify-center">
        <Button onClick={onClick} loading={loading} disabled={disabled}>{buttonLabel}</Button>
      </div>
    </div>
  );
}

function DeadlineField({ value, onSave }: { value: string | null; onSave: (v: string | null) => void }) {
  const [local, setLocal] = useState(value ?? '');
  return (
    <Field label="Application deadline" hint={local ? deadlineLabel(local) : 'Optional. Campus drives often have a cut-off date.'}>
      <input
        type="date"
        className={inputCls}
        value={local}
        onChange={(e) => {
          setLocal(e.target.value);
          if (e.target.value !== (value ?? '')) onSave(e.target.value || null);
        }}
      />
    </Field>
  );
}

function NextRoundField({ value, onSave }: { value: string | null; onSave: (iso: string | null) => void }) {
  const initial = toLocalInput(value);
  const [local, setLocal] = useState(initial);
  return (
    <Field label="Next round date" hint="Assessment, interview or HR round. Saved when you click away.">
      <input
        type="datetime-local"
        className={inputCls}
        value={local}
        onChange={(e) => setLocal(e.target.value)}
        onBlur={() => {
          if (local !== initial) onSave(local ? new Date(local).toISOString() : null);
        }}
      />
    </Field>
  );
}

function NotesField({ value, onSave }: { value: string; onSave: (v: string) => void }) {
  const [local, setLocal] = useState(value);
  return (
    <Field label="Notes" hint="Referral name, contact, what to prepare. Saved when you click away.">
      <textarea
        className={inputCls}
        rows={3}
        value={local}
        onChange={(e) => setLocal(e.target.value)}
        onBlur={() => {
          if (local !== value) onSave(local);
        }}
      />
    </Field>
  );
}

// ---------- next-step (side) card ----------

interface NextStepProps {
  job: JobDetailData;
  application: Application | null;
  resume: TailoredResume | null;
  cover: CoverLetter | null;
  busy: Busy;
  onSaveForLater: () => void;
  onTailor: () => void;
  onGoTab: (t: Tab) => void;
  onPatch: (payload: Record<string, unknown>, msg: string) => Promise<void>;
}

function NextStepCard({ job, application, resume, cover, busy, onSaveForLater, onTailor, onGoTab, onPatch }: NextStepProps) {
  const [askApplied, setAskApplied] = useState(false);
  const [patching, setPatching] = useState(false);

  if (!application) {
    return (
      <Card>
        <h2 className="text-base font-semibold text-slate-950">Your next step</h2>
        <p className="mt-1 text-sm text-slate-600">
          Save this job and build a résumé tailored to it. Then apply on the company site.
        </p>
        <div className="mt-4 grid gap-2">
          <Button onClick={onTailor} loading={busy === 'resume'} disabled={!!busy}>Save &amp; tailor my résumé</Button>
          <Button variant="secondary" onClick={onSaveForLater} loading={busy === 'save'} disabled={!!busy}>Save for later</Button>
        </div>
      </Card>
    );
  }

  if (PRE_APPLY.includes(application.status)) {
    return (
      <Card>
        <h2 className="text-base font-semibold text-slate-950">Your next step</h2>
        <p className="mt-1 text-sm text-slate-600">Get these ready, then apply on the company site.</p>
        <ul className="mt-4 space-y-4">
          <CheckRow done={!!resume} label="Tailored résumé" hint="Reordered from your real experience">
            {resume ? (
              <button type="button" className={TEXT_ACTION} onClick={() => onGoTab('resume')}>Review</button>
            ) : (
              <Button variant="secondary" onClick={onTailor} loading={busy === 'resume'} disabled={!!busy}>Tailor now</Button>
            )}
          </CheckRow>
          <CheckRow done={!!cover} label="Cover letter (optional)" hint="Only if the form asks for one, or you want to stand out">
            <button type="button" className={TEXT_ACTION} onClick={() => onGoTab('cover')}>
              {cover ? 'Review' : 'Write one'}
            </button>
          </CheckRow>
          <CheckRow done={false} label="Apply on company site">
            <Button
              variant="secondary"
              disabled={!job.apply_url}
              onClick={() => {
                window.open(job.apply_url, '_blank', 'noopener,noreferrer');
                setAskApplied(true);
              }}
            >
              Open application page <ExternalLink className="h-4 w-4" aria-hidden="true" />
            </Button>
            {askApplied && (
              <div className="mt-3 rounded-xl bg-slate-50 p-3">
                <p className="text-sm font-medium text-slate-900">Did you submit the application?</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button
                    loading={patching}
                    onClick={async () => {
                      setPatching(true);
                      await onPatch({ status: 'applied' }, 'Marked as applied');
                      setPatching(false);
                    }}
                  >
                    Yes, mark as applied
                  </Button>
                  <Button variant="ghost" onClick={() => setAskApplied(false)} disabled={patching}>Not yet</Button>
                </div>
              </div>
            )}
          </CheckRow>
        </ul>
        <div className="mt-5 border-t border-slate-100 pt-4">
          <DeadlineField value={application.deadline} onSave={(v) => onPatch({ deadline: v }, 'Deadline saved')} />
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <h2 className="text-base font-semibold text-slate-950">Your next step</h2>
      <div className="mt-4">
        <Field label="Status">
          <select
            className={inputCls}
            value={application.status}
            onChange={(e) => {
              const next = e.target.value as AppStatus;
              void onPatch({ status: next }, `Status set to ${STATUS_LABEL[next]}`);
            }}
          >
            {PIPELINE_ORDER.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
          </select>
        </Field>
      </div>

      {INTERVIEW_STATUSES.includes(application.status) && (
        <Link to={`/practice?application=${application.id}`} className={`${LINK_PRIMARY} mt-3 w-full`}>
          Practise for this interview
        </Link>
      )}

      <ul className="mt-3 space-y-1 text-sm text-slate-600">
        {application.applied_at && (
          <li>Applied {timeAgo(application.applied_at)} · {fmtDate(application.applied_at)}</li>
        )}
        {application.follow_up_at && <li>Follow up on {fmtDate(application.follow_up_at)}</li>}
      </ul>

      <div className="mt-5 space-y-4 border-t border-slate-100 pt-4">
        <NextRoundField
          key={`next-${application.id}`}
          value={application.next_interview_at}
          onSave={(iso) => onPatch({ next_interview_at: iso }, 'Interview date saved')}
        />
        <DeadlineField
          key={`deadline-${application.id}`}
          value={application.deadline}
          onSave={(v) => onPatch({ deadline: v }, 'Deadline saved')}
        />
        <NotesField
          key={`notes-${application.id}`}
          value={application.notes ?? ''}
          onSave={(v) => onPatch({ notes: v }, 'Notes saved')}
        />
      </div>
    </Card>
  );
}

// ---------- fit card ----------

function FitCard({ match, noProfile }: { match: MatchData | null; noProfile: boolean }) {
  return (
    <Card>
      <h2 className="text-base font-semibold text-slate-950">Your fit</h2>
      {noProfile ? (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-slate-600">Add your résumé to see your fit</p>
          <Link to="/setup" className={LINK_PRIMARY}>Add résumé</Link>
        </div>
      ) : !match ? (
        <p className="mt-3 text-sm text-slate-500">Fit is unavailable right now.</p>
      ) : (
        <>
          <div className="mt-4 flex items-center gap-4">
            <FitRing fit={match.fit} verdict={match.verdict} size={80} />
            <VerdictBadge verdict={match.verdict} />
          </div>
          {(match.explanation ?? []).length > 0 && (
            <div className="mt-5">
              <ReasonList reasons={match.explanation ?? []} />
            </div>
          )}
          <div className="mt-5 space-y-4">
            <div>
              <h3 className="mb-2 text-sm font-semibold text-slate-900">You have</h3>
              <Chips items={match.matched_skills ?? []} tone="green" />
            </div>
            <div>
              <h3 className="mb-2 text-sm font-semibold text-slate-900">Missing</h3>
              <Chips items={match.missing_skills ?? []} tone="amber" />
              <p className="mt-2 text-xs text-slate-500">
                If you have a missing skill, add it to your profile and it will count.
              </p>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}

// ---------- materials ----------

interface Shared {
  busy: Busy;
  onGenerateResume: () => void;
  onGenerateCover: () => void;
  onResumeUpdated: (r: TailoredResume) => void;
  onCoverUpdated: (c: CoverLetter) => void;
  onError: (msg: string | null) => void;
  announce: (msg: string) => void;
}

function ResumeEditor({ job, resume, ctx }: { job: JobDetailData; resume: TailoredResume; ctx: Shared }) {
  const c = resume.content;
  const [summary, setSummary] = useState(c.summary);
  const [skillsText, setSkillsText] = useState(c.skills.map((s) => s.name).join(', '));
  const [bullets, setBullets] = useState<string[]>(c.experiences.map((e) => e.bullets.join('\n')));
  // Remounted (via key) whenever the saved résumé is replaced, so this snapshot is the saved state.
  const [snapshot] = useState(() => JSON.stringify([c.summary, c.skills.map((s) => s.name).join(', '), c.experiences.map((e) => e.bullets.join('\n'))]));
  const [saving, setSaving] = useState(false);
  const [downloading, setDownloading] = useState<'docx' | 'txt' | null>(null);

  const current = JSON.stringify([summary, skillsText, bullets]);
  const dirty = current !== snapshot;
  const diff = resume.diff_from_master;
  const coverage = diff?.keyword_coverage;

  const changes: [string, string][] = [];
  if (diff?.skills_moved_up?.length) changes.push(['Skills moved up', diff.skills_moved_up.join(', ')]);
  if (diff?.reordered_roles?.length) changes.push(['Roles reordered', diff.reordered_roles.join(', ')]);
  if (diff?.bullets_trimmed) changes.push(['Bullets trimmed', String(diff.bullets_trimmed)]);
  if (diff?.skills_added_from_experience?.length) changes.push(['Skills found in your experience', diff.skills_added_from_experience.join(', ')]);

  async function save() {
    setSaving(true);
    ctx.onError(null);
    try {
      await Tailoring.editResume(resume.id, {
        summary,
        skills: skillsText.split(',').map((s) => s.trim()).filter(Boolean).map((name) => ({ name })),
        experiences: bullets.map((b) => ({ bullets: b.split('\n').map((s) => s.trim()).filter(Boolean) })),
      });
      ctx.onResumeUpdated(await Tailoring.getResume(resume.application_id));
      ctx.announce('Résumé edits saved');
    } catch (e) {
      ctx.onError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  async function download(fmt: 'docx' | 'txt') {
    setDownloading(fmt);
    ctx.onError(null);
    try {
      const blob = await Tailoring.exportResume(resume.application_id, fmt);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${job.company.name}-${job.title}-resume.${fmt}`.replace(/[^\w.-]+/g, '-');
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      ctx.onError(errorMessage(e));
    } finally {
      setDownloading(null);
    }
  }

  function regenerate() {
    if (dirty && !window.confirm('Regenerate your résumé? Your unsaved edits will be lost.')) return;
    ctx.onGenerateResume();
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        {coverage != null && (
          <Badge tone={coverage >= 70 ? 'green' : 'amber'}>Keyword coverage {coverage}%</Badge>
        )}
        <span className="text-xs text-slate-500">Compared with the job description</span>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-slate-900">What changed</h3>
        {changes.length ? (
          <ul className="mt-2 space-y-1 text-sm text-slate-700">
            {changes.map(([k, v]) => <li key={k}><span className="font-medium">{k}:</span> {v}</li>)}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-slate-500">Your master résumé already matched this role well.</p>
        )}
      </div>

      {diff?.suggestions?.length > 0 && (
        <Alert tone="amber">
          <p className="font-semibold">Suggestions to strengthen this application</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {diff.suggestions.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </Alert>
      )}

      {diff?.verification?.length > 0 && (
        <Alert tone="slate">
          <p className="font-semibold">Check before you send</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {diff.verification.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </Alert>
      )}

      <div className="space-y-4 rounded-xl border border-slate-200 p-4">
        <Field label="Summary">
          <textarea className={inputCls} rows={4} value={summary} onChange={(e) => setSummary(e.target.value)} />
        </Field>
        <Field label="Skills" hint="Comma-separated. The first ones are shown first.">
          <input className={inputCls} value={skillsText} onChange={(e) => setSkillsText(e.target.value)} />
        </Field>
        {c.experiences.map((e, i) => (
          <div key={`${e.title}-${e.company}-${i}`} className="space-y-2">
            <p className="text-sm font-semibold text-slate-900">{e.title} · {e.company}</p>
            <Field label="Bullets (one per line)">
              <textarea
                className={inputCls}
                rows={4}
                value={bullets[i] ?? ''}
                onChange={(ev) => setBullets((prev) => prev.map((b, j) => (j === i ? ev.target.value : b)))}
              />
            </Field>
          </div>
        ))}
        {c.projects.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-semibold text-slate-900">Projects</p>
            {c.projects.map((p, i) => (
              <div key={`${p.name}-${i}`} className="text-sm">
                <p className="font-medium text-slate-800">{p.name}</p>
                {p.description && <p className="whitespace-pre-line text-slate-600">{p.description}</p>}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={save} loading={saving} disabled={!dirty || saving}>Save edits</Button>
        <Button variant="secondary" onClick={() => download('docx')} loading={downloading === 'docx'} disabled={!!downloading}>
          Download .docx
        </Button>
        <Button variant="secondary" onClick={() => download('txt')} loading={downloading === 'txt'} disabled={!!downloading}>
          Download .txt
        </Button>
        <Button variant="ghost" onClick={regenerate} loading={ctx.busy === 'resume'} disabled={!!ctx.busy}>Regenerate</Button>
      </div>
      {dirty && <p className="text-xs text-slate-500">Downloads use your last saved version. Save edits first.</p>}
    </div>
  );
}

function CoverEditor({ cover, ctx }: { cover: CoverLetter; ctx: Shared }) {
  const [text, setText] = useState(cover.content);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const dirty = text !== cover.content;

  async function save() {
    setSaving(true);
    ctx.onError(null);
    try {
      await Tailoring.editCoverLetter(cover.id, text);
      ctx.onCoverUpdated(await Tailoring.getCoverLetter(cover.application_id));
      ctx.announce('Cover letter saved');
    } catch (e) {
      ctx.onError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      ctx.onError('Could not copy automatically. Select the text and copy it manually.');
    }
  }

  function regenerate() {
    if (dirty && !window.confirm('Regenerate your cover letter? Your unsaved edits will be lost.')) return;
    ctx.onGenerateCover();
  }

  return (
    <div className="space-y-4">
      {cover.verification?.length ? (
        <Alert tone="slate">
          <p className="font-semibold">Check before you send</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {cover.verification.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </Alert>
      ) : null}
      <Field label="Cover letter">
        <textarea className={inputCls} rows={16} value={text} onChange={(e) => setText(e.target.value)} />
      </Field>
      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={save} loading={saving} disabled={!dirty || saving}>Save</Button>
        <Button variant="secondary" onClick={copy}>{copied ? 'Copied' : 'Copy to clipboard'}</Button>
        <Button variant="ghost" onClick={regenerate} loading={ctx.busy === 'cover'} disabled={!!ctx.busy}>Regenerate</Button>
      </div>
    </div>
  );
}

function MaterialsCard({ tab, onTab, job, resume, resumeRev, cover, coverRev, ctx }: {
  tab: Tab; onTab: (t: Tab) => void; job: JobDetailData;
  resume: TailoredResume | null; resumeRev: number;
  cover: CoverLetter | null; coverRev: number; ctx: Shared;
}) {
  const tabs: { key: Tab; label: string }[] = [
    { key: 'jd', label: 'Job description' },
    { key: 'resume', label: 'Tailored résumé' },
    { key: 'cover', label: 'Cover letter' },
  ];
  return (
    <Card>
      <div className="flex flex-wrap gap-1 rounded-xl bg-slate-100 p-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            aria-pressed={tab === t.key}
            onClick={() => onTab(t.key)}
            className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
              tab === t.key ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-5">
        {tab === 'jd' && (
          job.description_text
            ? <p className="max-w-prose whitespace-pre-line text-sm leading-7 text-slate-700">{job.description_text}</p>
            : <p className="text-sm text-slate-500">No description was provided. Open the application page to read the full role.</p>
        )}

        {tab === 'resume' && (
          resume
            ? <ResumeEditor key={resumeRev} job={job} resume={resume} ctx={ctx} />
            : (
              <GeneratePrompt
                text="We reorder your real skills, bullets and projects so the most relevant ones come first, and write a factual summary. Nothing is invented."
                buttonLabel="Generate résumé"
                loading={ctx.busy === 'resume'}
                disabled={!!ctx.busy}
                onClick={ctx.onGenerateResume}
              />
            )
        )}

        {tab === 'cover' && (
          cover
            ? <CoverEditor key={coverRev} cover={cover} ctx={ctx} />
            : (
              <GeneratePrompt
                text="A short cover letter written from your real experience and this role's requirements. You can edit it before you send it."
                buttonLabel="Generate cover letter"
                loading={ctx.busy === 'cover'}
                disabled={!!ctx.busy}
                onClick={ctx.onGenerateCover}
              />
            )
        )}
      </div>
    </Card>
  );
}

// ---------- page ----------

export function JobWorkspace() {
  const { id } = useParams();
  const jobId = Number(id);

  const [job, setJob] = useState<JobDetailData | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [match, setMatch] = useState<MatchData | null>(null);
  const [noProfile, setNoProfile] = useState(false);
  const [application, setApplication] = useState<Application | null>(null);
  const [resume, setResume] = useState<TailoredResume | null>(null);
  const [resumeRev, setResumeRev] = useState(0);
  const [cover, setCover] = useState<CoverLetter | null>(null);
  const [coverRev, setCoverRev] = useState(0);
  const [tab, setTab] = useState<Tab>('jd');
  const [busy, setBusy] = useState<Busy>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setNotFound(false);
      setLoadError(null);
      if (!Number.isFinite(jobId)) {
        setNotFound(true);
        setLoading(false);
        return;
      }
      try {
        const detail = (await Jobs.detail(jobId)) as JobDetailData;
        const [applications, m] = await Promise.all([Applications.list(), loadMatch(jobId)]);
        const app = asList(applications).find((a) => a.job === jobId) ?? null;
        const mats = app ? await loadMaterials(app.id) : { resume: null, cover: null };
        if (cancelled) return;
        setJob(detail);
        setMatch(m.match);
        setNoProfile(m.noProfile);
        setApplication(app);
        setResume(mats.resume);
        setCover(mats.cover);
      } catch (e) {
        if (cancelled) return;
        if (httpStatus(e) === 404) setNotFound(true);
        else setLoadError(errorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [jobId]);

  function announce(msg: string) {
    setNotice(msg);
    window.setTimeout(() => setNotice((n) => (n === msg ? null : n)), 2500);
  }

  function applyResume(r: TailoredResume) {
    setResume(r);
    setResumeRev((v) => v + 1);
  }

  function applyCover(c: CoverLetter) {
    setCover(c);
    setCoverRev((v) => v + 1);
  }

  async function ensureApplication(): Promise<Application> {
    if (application) return application;
    const created = (await Applications.create(jobId)) as Application;
    setApplication(created);
    return created;
  }

  async function saveForLater() {
    setBusy('save');
    setError(null);
    try {
      await ensureApplication();
      announce('Saved to your pipeline');
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  async function generateResume() {
    setBusy('resume');
    setError(null);
    try {
      const app = await ensureApplication();
      await Tailoring.resume(app.id);
      applyResume(await Tailoring.getResume(app.id));
      announce('Résumé tailored to this job');
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  async function generateCover() {
    setBusy('cover');
    setError(null);
    try {
      const app = await ensureApplication();
      await Tailoring.coverLetter(app.id);
      applyCover(await Tailoring.getCoverLetter(app.id));
      announce('Cover letter ready');
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  async function patchApplication(payload: Record<string, unknown>, msg: string) {
    if (!application) return;
    setError(null);
    try {
      const updated = (await Applications.patch(application.id, payload)) as Partial<Application>;
      setApplication((prev) => (prev ? ({ ...prev, ...payload, ...updated } as Application) : prev));
      announce(msg);
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  function goTab(t: Tab) {
    setTab(t);
    document.getElementById('materials')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  if (loading) return <Spinner label="Loading job…" />;

  if (!job) {
    if (notFound) {
      return (
        <EmptyState
          title="We couldn't find this job"
          action={<Link to="/jobs" className={LINK_SECONDARY}>Back to jobs</Link>}
        >
          It may have been removed. Browse your job feed for current matches.
        </EmptyState>
      );
    }
    return (
      <div className="space-y-4">
        <Alert tone="red">{loadError ?? 'Something went wrong. Please try again.'}</Alert>
        <Link to="/jobs" className={TEXT_ACTION}>← Back to jobs</Link>
      </div>
    );
  }

  const salary = salaryLabel(job.salary_min, job.salary_max, job.salary_currency);

  const ctx: Shared = {
    busy,
    onGenerateResume: generateResume,
    onGenerateCover: generateCover,
    onResumeUpdated: applyResume,
    onCoverUpdated: applyCover,
    onError: setError,
    announce,
  };

  return (
    <section>
      <header className="mb-6">
        <Link to="/jobs" className="text-sm font-medium text-slate-500 hover:text-slate-900">
          <span aria-hidden="true">←</span> Jobs
        </Link>
        <h1 className="mt-3 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">{job.title}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-slate-600">
          <span className="font-semibold text-slate-800">{job.company.name}</span>
          {job.location && <span>{job.location}</span>}
          {job.remote && <Badge tone="teal">Remote</Badge>}
          {salary && <span>{salary}</span>}
          {job.posted_at && (
            <span title={fmtDate(job.posted_at)}>Posted {timeAgo(job.posted_at)} · {fmtDate(job.posted_at)}</span>
          )}
          <GhostRiskBadge score={job.ghost_risk} band={job.ghost_band} reasons={job.ghost_reasons} />
        </div>
      </header>

      {job.ghost_band === 'high' && (
        <div className="mb-5">
          <Alert tone="amber">
            <p className="font-semibold">This posting shows signs of a ghost job — verify it is open before investing time</p>
            {job.ghost_reasons.length > 0 && (
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {job.ghost_reasons.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            )}
          </Alert>
        </div>
      )}

      {notice && <div className="mb-5"><Alert tone="green">{notice}</Alert></div>}
      {error && <div className="mb-5"><Alert tone="red">{error}</Alert></div>}

      <div className="grid gap-5 lg:grid-cols-3">
        <aside className="order-first space-y-5 lg:order-last lg:sticky lg:top-6 lg:self-start">
          <NextStepCard
            job={job}
            application={application}
            resume={resume}
            cover={cover}
            busy={busy}
            onSaveForLater={saveForLater}
            onTailor={generateResume}
            onGoTab={goTab}
            onPatch={patchApplication}
          />
        </aside>

        <div className="min-w-0 space-y-5 lg:col-span-2">
          <FitCard match={match} noProfile={noProfile} />
          <div id="materials">
            <MaterialsCard
              tab={tab}
              onTab={setTab}
              job={job}
              resume={resume}
              resumeRev={resumeRev}
              cover={cover}
              coverRev={coverRev}
              ctx={ctx}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
