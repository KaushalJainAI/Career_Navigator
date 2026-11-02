import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Clock } from 'lucide-react';
import { Alert, Badge, Button, Card, EmptyState, Field, PageHeader, Spinner, inputCls, timeAgo } from '../../components/ui';
import { Applications, Interview } from '../../api/endpoints';
import { errorMessage } from '../../api/client';
import {
  INTERVIEW_STAGES,
  STATUS_LABEL,
  type Application,
  type AppStatus,
  type InterviewReport,
  type InterviewSession,
  type InterviewTurn,
} from '../../lib/types';

type View = 'start' | 'session' | 'report';
interface StartPayload { application?: number; role?: string; stage: string }

const COMING_UP: AppStatus[] = ['assessment', 'phone', 'onsite'];
const CLOSED: AppStatus[] = ['rejected', 'withdrawn'];
const HR_STYLE = /recruit|\bhr\b|motivation|personal/i;
const SKIPPED = '(skipped)';
const TIMER_SECONDS = 120;

/** Accepts either a bare array or a paginated { results } object. */
function asList<T>(data: unknown): T[] {
  if (Array.isArray(data)) return data as T[];
  if (data && typeof data === 'object' && Array.isArray((data as { results?: unknown }).results)) {
    return (data as { results: T[] }).results;
  }
  return [];
}

/** Backend scores are 0..1; tolerate 0..100 defensively. Returns a whole percentage. */
function pct(v: number | null | undefined): number | null {
  if (v == null || Number.isNaN(v)) return null;
  const frac = v <= 1 ? v : v / 100;
  return Math.round(Math.min(1, Math.max(0, frac)) * 100);
}

function turnScore(t: InterviewTurn): number | null {
  return pct(t.evaluation?.score ?? t.score);
}

function prettify(s: string): string {
  const out = s.replace(/[_-]+/g, ' ').trim();
  return out ? out.charAt(0).toUpperCase() + out.slice(1) : '';
}

function stageLabel(v: string): string {
  return INTERVIEW_STAGES.find((s) => s.value === v)?.label ?? prettify(v);
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return '';
  return new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });
}

function clip(s: string, n = 220): string {
  const t = s.trim();
  return t.length > n ? `${t.slice(0, n).trimEnd()}…` : t;
}

function wordCount(s: string): number {
  const t = s.trim();
  return t ? t.split(/\s+/).length : 0;
}

function fmtClock(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function sortNewest(list: InterviewSession[]): InterviewSession[] {
  return [...list].sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
}

function Meter({ label, value }: { label: string; value: number | null | undefined }) {
  const p = pct(value);
  if (p == null) return null;
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-600">
        <span>{label}</span>
        <span className="font-semibold text-slate-900">{p}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-100" role="meter" aria-label={label}
        aria-valuenow={p} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full rounded-full bg-teal-600" style={{ width: `${p}%` }} />
      </div>
    </div>
  );
}

function FeedbackPanel({ turn }: { turn: InterviewTurn }) {
  const ev = turn.evaluation;
  const score = turnScore(turn);
  const strengths = ev?.strengths ?? [];
  const gaps = ev?.gaps ?? [];
  const text = ev?.feedback || turn.feedback;
  return (
    <div className="space-y-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Overall score</p>
        <p className="text-3xl font-bold text-slate-950">{score != null ? `${score}%` : '—'}</p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Meter label="Structure" value={ev?.structure} />
        <Meter label="Specificity" value={ev?.specificity} />
        <Meter label="Outcome" value={ev?.outcome} />
        <Meter label="Ownership" value={ev?.ownership} />
      </div>
      {text && <p className="whitespace-pre-line text-sm leading-6 text-slate-700">{text}</p>}
      {strengths.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-semibold text-slate-900">Strengths</p>
          <div className="flex flex-wrap gap-1.5">
            {strengths.map((s, i) => <Badge key={i} tone="green">{s}</Badge>)}
          </div>
        </div>
      )}
      {gaps.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-semibold text-slate-900">Gaps to fix</p>
          <ul className="list-disc space-y-1 pl-5 text-sm text-amber-800">
            {gaps.map((g, i) => <li key={i}>{g}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Optional 2-minute countdown to simulate pressure. Mounted per question (keyed) so it resets. */
function PressureTimer() {
  const [left, setLeft] = useState(TIMER_SECONDS);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000);
    return () => window.clearInterval(id);
  }, [running]);

  useEffect(() => {
    if (left === 0) setRunning(false);
  }, [left]);

  const label = running ? 'Stop' : left === 0 ? 'Restart' : left === TIMER_SECONDS ? 'Start 2-min timer' : 'Resume';

  function toggle() {
    if (left === 0) {
      setLeft(TIMER_SECONDS);
      setRunning(true);
      return;
    }
    setRunning((r) => !r);
  }

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl bg-slate-50 px-3 py-2">
      <Clock className="h-4 w-4 text-slate-500" aria-hidden="true" />
      <span className={`font-mono text-base font-semibold tabular-nums ${left === 0 ? 'text-amber-700' : 'text-slate-900'}`}>
        {fmtClock(left)}
      </span>
      {left === 0 && <span className="text-xs text-amber-700">Time's up. Wrap up your answer.</span>}
      <Button type="button" variant="secondary" className="ml-auto !py-1.5" onClick={toggle}>{label}</Button>
    </div>
  );
}

function AppRow({ app, selected, onSelect }: { app: Application; selected: boolean; onSelect: () => void }) {
  const job = app.job_detail;
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className={`flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left transition ${
        selected ? 'border-slate-950 bg-slate-50 ring-1 ring-slate-950' : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
      }`}
    >
      <span aria-hidden="true"
        className={`mt-1 grid h-4 w-4 shrink-0 place-items-center rounded-full border ${selected ? 'border-slate-950' : 'border-slate-300'}`}>
        {selected && <span className="h-2 w-2 rounded-full bg-slate-950" />}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-semibold text-slate-950">{job?.company?.name ?? 'Company'}</span>
        <span className="block truncate text-sm text-slate-600">{job?.title ?? 'Role'}</span>
        <span className="mt-1.5 flex flex-wrap items-center gap-2">
          <Badge>{STATUS_LABEL[app.status]}</Badge>
          {app.next_interview_at && (
            <span className="text-xs font-medium text-slate-700">Next round · {fmtDateTime(app.next_interview_at)}</span>
          )}
        </span>
      </span>
    </button>
  );
}

export function PracticePage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [view, setView] = useState<View>('start');

  // Start screen state
  const [apps, setApps] = useState<Application[]>([]);
  const [appsLoading, setAppsLoading] = useState(true);
  const [appsError, setAppsError] = useState('');
  const [selectedId, setSelectedId] = useState<number | null>(() => {
    const n = Number(params.get('application'));
    return Number.isFinite(n) && n > 0 ? n : null;
  });
  const [role, setRole] = useState('');
  const [stageChoice, setStageChoice] = useState<string | null>(null);
  const [history, setHistory] = useState<InterviewSession[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState('');

  // Shared
  const [error, setError] = useState('');
  const [starting, setStarting] = useState(false);
  const [setup, setSetup] = useState<StartPayload | null>(null);

  // Session state
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [idx, setIdx] = useState(0);
  const [turns, setTurns] = useState<Record<number, InterviewTurn>>({});
  const [draft, setDraft] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Report state
  const [report, setReport] = useState<InterviewReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  const questions = useMemo(
    () => [...(session?.questions ?? [])].sort((a, b) => a.order - b.order),
    [session],
  );

  const { comingUp, others } = useMemo(() => {
    const byNextRound = (a: Application, b: Application) => {
      const x = a.next_interview_at ? new Date(a.next_interview_at).getTime() : Infinity;
      const y = b.next_interview_at ? new Date(b.next_interview_at).getTime() : Infinity;
      return x === y ? 0 : x < y ? -1 : 1;
    };
    const visible = apps.filter((a) => !CLOSED.includes(a.status));
    return {
      comingUp: visible.filter((a) => COMING_UP.includes(a.status)).sort(byNextRound),
      others: visible.filter((a) => !COMING_UP.includes(a.status)),
    };
  }, [apps]);

  const stage = stageChoice ?? (selectedId != null ? 'tech_phone' : 'cs_fundamentals');
  const hasTarget = selectedId != null || role.trim().length > 0;

  useEffect(() => {
    let alive = true;
    Applications.list()
      .then((d: unknown) => { if (alive) setApps(asList<Application>(d)); })
      .catch((e) => { if (alive) setAppsError(errorMessage(e, 'Could not load your applications.')); })
      .finally(() => { if (alive) setAppsLoading(false); });
    return () => { alive = false; };
  }, []);

  const loadHistory = useCallback(() => {
    setHistoryLoading(true);
    setHistoryError('');
    Interview.list()
      .then((d: unknown) => setHistory(sortNewest(asList<InterviewSession>(d))))
      .catch((e) => setHistoryError(errorMessage(e, 'Could not load past sessions.')))
      .finally(() => setHistoryLoading(false));
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  async function startPractice(payload: StartPayload) {
    setStarting(true);
    setError('');
    try {
      const s = (await Interview.start(payload)) as InterviewSession;
      setSetup(payload);
      setSession(s);
      setTurns({});
      setIdx(0);
      setDraft('');
      setReport(null);
      setView('session');
    } catch (e) {
      setError(errorMessage(e, 'Could not start practice. Please try again.'));
    } finally {
      setStarting(false);
    }
  }

  function startFromForm() {
    if (selectedId != null) startPractice({ application: selectedId, stage });
    else startPractice({ role: role.trim(), stage });
  }

  async function submitAnswer(text: string) {
    const current = questions[idx];
    if (!session || !current) return;
    const at = idx;
    setSubmitting(true);
    setError('');
    try {
      const t = (await Interview.answer(session.id, text)) as InterviewTurn;
      setTurns((prev) => ({ ...prev, [at]: t }));
    } catch (e) {
      setError(errorMessage(e, 'Could not submit your answer. Your draft is still here.'));
    } finally {
      setSubmitting(false);
    }
  }

  async function loadReport() {
    if (!session) return;
    setReportLoading(true);
    setError('');
    try {
      setReport((await Interview.report(session.id)) as InterviewReport);
    } catch (e) {
      setError(errorMessage(e, 'Could not build your report. Please try again.'));
    } finally {
      setReportLoading(false);
    }
  }

  function next() {
    if (idx < questions.length - 1) {
      setIdx(idx + 1);
      setDraft('');
      setError('');
    } else {
      setView('report');
      loadReport();
    }
  }

  function backToPractice() {
    setView('start');
    setSession(null);
    setReport(null);
    setTurns({});
    setDraft('');
    setError('');
    loadHistory();
  }

  function leave() {
    if (window.confirm('Leave this session? You can start a new one any time.')) backToPractice();
  }

  function onSubmitForm(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const text = draft.trim();
    if (text) submitAnswer(text);
  }

  // ---------- Start screen ----------
  const renderGroup = (title: string, list: Application[]) =>
    list.length === 0 ? null : (
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
        {list.map((a) => (
          <AppRow
            key={a.id}
            app={a}
            selected={a.id === selectedId}
            onSelect={() => setSelectedId(a.id === selectedId ? null : a.id)}
          />
        ))}
      </div>
    );

  const startView = (
    <>
      <PageHeader
        title="Practice"
        subtitle="Rehearse real questions for a specific company, then get feedback"
      />
      {error && <div className="mb-4"><Alert tone="red">{error}</Alert></div>}

      <div className="space-y-4">
        <Card>
          <h2 className="text-base font-semibold text-slate-950">Practise for an application</h2>
          <p className="mt-1 text-sm text-slate-500">Questions are tailored to a job you are applying to.</p>
          <div className="mt-4">
            {appsLoading ? (
              <Spinner label="Loading your applications…" />
            ) : appsError ? (
              <Alert tone="red">{appsError}</Alert>
            ) : apps.length === 0 ? (
              <EmptyState
                title="No applications yet"
                action={<Button variant="secondary" onClick={() => navigate('/jobs')}>Find jobs</Button>}
              >
                Save a job from Jobs, then come back here to practise for it.
              </EmptyState>
            ) : (
              <div className="space-y-5">
                {comingUp.length === 0 && others.length === 0 && (
                  <p className="text-sm text-slate-500">All your applications are closed. Practise for a role below.</p>
                )}
                {renderGroup('Coming up', comingUp)}
                {renderGroup('Other applications', others)}
              </div>
            )}
          </div>
        </Card>

        <Card>
          <h2 className="text-base font-semibold text-slate-950">Or practise for a role</h2>
          <p className="mt-1 text-sm text-slate-500">Use this when the company is not in your pipeline yet.</p>
          <div className="mt-4">
            <Field
              label="Role"
              hint={selectedId != null ? 'Not used while an application is selected above.' : 'Used only when no application is selected.'}
            >
              <input
                className={inputCls}
                value={role}
                disabled={selectedId != null}
                onChange={(e) => setRole(e.target.value)}
                placeholder="e.g. Software Engineer Intern"
              />
            </Field>
          </div>
        </Card>

        <Card>
          <fieldset>
            <legend className="text-base font-semibold text-slate-950">Round type</legend>
            <p className="mt-1 text-sm text-slate-500">What kind of round are you preparing for?</p>
            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              {INTERVIEW_STAGES.map((s) => {
                const on = stage === s.value;
                return (
                  <label
                    key={s.value}
                    className={`flex cursor-pointer items-start gap-3 rounded-xl border px-4 py-3 transition ${
                      on ? 'border-slate-950 bg-slate-50 ring-1 ring-slate-950' : 'border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="stage"
                      value={s.value}
                      checked={on}
                      onChange={() => setStageChoice(s.value)}
                      className="mt-1 accent-slate-950"
                    />
                    <span>
                      <span className="block text-sm font-semibold text-slate-950">{s.label}</span>
                      <span className="block text-xs text-slate-500">{s.hint}</span>
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        </Card>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Button
            onClick={startFromForm}
            disabled={!hasTarget}
            loading={starting}
            className="w-full sm:w-auto"
          >
            {starting ? 'Preparing questions…' : 'Start practice'}
          </Button>
          {!hasTarget && <p className="text-sm text-slate-500">Pick an application or type a role to begin.</p>}
        </div>

        <Card>
          <h2 className="text-base font-semibold text-slate-950">Past sessions</h2>
          <div className="mt-3">
            {historyLoading ? (
              <Spinner label="Loading sessions…" />
            ) : historyError ? (
              <Alert tone="red">{historyError}</Alert>
            ) : history.length === 0 ? (
              <p className="text-sm text-slate-500">No sessions yet. Your practice rounds will be listed here.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {history.map((h) => {
                  const done = /done|complete|finish|report/i.test(h.status);
                  const ago = timeAgo(h.started_at);
                  return (
                    <li key={h.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-slate-950">{h.role || 'Practice'}</p>
                        <p className="text-xs text-slate-500">
                          {stageLabel(h.stage)} · {fmtDate(h.started_at)}{ago ? ` · ${ago}` : ''}
                        </p>
                      </div>
                      <Badge tone={done ? 'green' : 'slate'}>{prettify(h.status) || 'Started'}</Badge>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </Card>
      </div>
    </>
  );

  // ---------- Session screen ----------
  const total = questions.length;
  const answered = Object.keys(turns).length;
  const current = questions[idx];
  const turn = turns[idx];
  const isLast = idx === total - 1;
  const hrStyle = current ? HR_STYLE.test(current.category) : false;

  const sessionView = session && (
    <>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-900">
            Question {Math.min(idx + 1, total)} of {total}
          </p>
          <p className="truncate text-xs text-slate-500">{session.role || 'Practice'} · {stageLabel(session.stage)}</p>
        </div>
        <Button variant="ghost" onClick={leave} className="!px-2">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Leave
        </Button>
      </div>

      <div className="mb-6 h-1.5 overflow-hidden rounded-full bg-slate-200" role="progressbar"
        aria-label="Session progress" aria-valuemin={0} aria-valuemax={total} aria-valuenow={answered}>
        <div className="h-full rounded-full bg-teal-600 transition-all" style={{ width: `${total ? (answered / total) * 100 : 0}%` }} />
      </div>

      {error && <div className="mb-4"><Alert tone="red">{error}</Alert></div>}

      {total === 0 || !current ? (
        <EmptyState
          title="No questions came back"
          action={<Button variant="secondary" onClick={backToPractice}>Back to Practice</Button>}
        >
          Try starting a new session.
        </EmptyState>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px]">
          <Card className="space-y-5 sm:p-6">
            <Badge tone="teal">{prettify(current.category)}</Badge>
            <h2 className="text-xl font-semibold leading-8 text-slate-950 sm:text-2xl sm:leading-9">{current.prompt}</h2>

            {turn ? (
              <>
                <FeedbackPanel turn={turn} />
                <div className="flex justify-end">
                  <Button onClick={next} className="w-full sm:w-auto">
                    {isLast ? 'Finish & see report' : 'Next question'}
                    {!isLast && <ArrowRight className="h-4 w-4" aria-hidden="true" />}
                  </Button>
                </div>
              </>
            ) : (
              <>
                <PressureTimer key={current.id} />
                <form onSubmit={onSubmitForm} className="space-y-3">
                  <Field
                    label="Your answer"
                    hint={hrStyle
                      ? 'Keep it short and specific.'
                      : 'Aim for 60–120 seconds spoken. Structure: situation → what you did → result (with a number).'}
                  >
                    <textarea
                      rows={8}
                      className={`${inputCls} leading-6`}
                      value={draft}
                      disabled={submitting}
                      onChange={(e) => setDraft(e.target.value)}
                      placeholder="Type your answer the way you would say it out loud."
                    />
                  </Field>
                  <p className="text-xs text-slate-500" aria-live="polite">{wordCount(draft)} words</p>
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <Button type="submit" loading={submitting} disabled={!draft.trim()} className="w-full sm:w-auto">
                      Submit answer
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={submitting}
                      onClick={() => submitAnswer(SKIPPED)}
                      className="w-full sm:w-auto"
                    >
                      Skip
                    </Button>
                  </div>
                </form>
              </>
            )}
          </Card>

          <aside>
            <Card className="p-4">
              <details open>
                <summary className="cursor-pointer text-sm font-semibold text-slate-950">
                  Previous answers ({answered})
                </summary>
                {answered === 0 ? (
                  <p className="mt-3 text-sm text-slate-500">Your scored answers will appear here.</p>
                ) : (
                  <ul className="mt-3 space-y-3">
                    {questions.map((q, i) => {
                      const t = turns[i];
                      if (!t) return null;
                      const s = turnScore(t);
                      return (
                        <li key={q.id} className="flex items-start gap-2 text-sm">
                          <span className="min-w-0 flex-1">
                            <span className="block text-xs text-slate-500">Q{i + 1}</span>
                            <span className="block text-slate-800">{clip(q.prompt, 90)}</span>
                          </span>
                          <span className="shrink-0 font-semibold text-slate-950">{s != null ? `${s}%` : '—'}</span>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </details>
            </Card>
          </aside>
        </div>
      )}
    </>
  );

  // ---------- Report screen ----------
  const reportView = (
    <>
      <PageHeader
        title="Your report"
        subtitle={session ? `${session.role || 'Practice'} · ${stageLabel(session.stage)}` : undefined}
      />
      {error && <div className="mb-4"><Alert tone="red">{error}</Alert></div>}

      {reportLoading ? (
        <Spinner label="Writing your report…" />
      ) : !report ? (
        <Button onClick={loadReport} className="w-full sm:w-auto">{error ? 'Try again' : 'Generate report'}</Button>
      ) : (
        <div className="space-y-4">
          <Card>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Overall score</p>
            <p className="mt-1 text-4xl font-bold text-slate-950">{pct(report.overall_score) ?? '—'}%</p>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <h2 className="text-base font-semibold text-slate-950">Strengths</h2>
              {report.strengths.length === 0 ? (
                <p className="mt-2 text-sm text-slate-500">No strengths were flagged this time.</p>
              ) : (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {report.strengths.map((s, i) => <Badge key={i} tone="green">{s}</Badge>)}
                </div>
              )}
            </Card>
            <Card>
              <h2 className="text-base font-semibold text-slate-950">Gaps</h2>
              {report.gaps.length === 0 ? (
                <p className="mt-2 text-sm text-slate-500">No gaps were flagged this time.</p>
              ) : (
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-amber-800">
                  {report.gaps.map((g, i) => <li key={i}>{g}</li>)}
                </ul>
              )}
            </Card>
          </div>

          <Card>
            <h2 className="text-base font-semibold text-slate-950">Study plan</h2>
            {report.study_plan.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">No study plan yet.</p>
            ) : (
              <ol className="mt-3 space-y-3">
                {report.study_plan.map((p, i) => (
                  <li key={i} className="flex gap-3 text-sm">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-semibold text-slate-700">{i + 1}</span>
                    <span>
                      <span className="block font-semibold text-slate-950">{p.topic}</span>
                      <span className="text-slate-600">{p.action}</span>
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </Card>

          <Card>
            <h2 className="text-base font-semibold text-slate-950">Question by question</h2>
            <ol className="mt-3 divide-y divide-slate-100">
              {questions.map((q, i) => {
                const t = turns[i];
                const s = t ? turnScore(t) : null;
                return (
                  <li key={q.id} className="py-3">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-semibold text-slate-950">Q{i + 1}. {q.prompt}</p>
                      <Badge tone={s != null && s >= 70 ? 'green' : s != null && s >= 40 ? 'amber' : 'slate'}>
                        {s != null ? `${s}%` : 'Not answered'}
                      </Badge>
                    </div>
                    {t && (
                      <p className="mt-1.5 text-sm leading-6 text-slate-600">
                        {clip(t.user_answer ?? '', 200) || 'No answer text.'}
                      </p>
                    )}
                  </li>
                );
              })}
            </ol>
          </Card>

          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
            <Button
              onClick={() => setup && startPractice(setup)}
              disabled={!setup}
              loading={starting}
              className="w-full sm:w-auto"
            >
              {starting ? 'Preparing questions…' : 'Practise again (same setup)'}
            </Button>
            <Button variant="secondary" onClick={backToPractice} className="w-full sm:w-auto">
              Back to Practice
            </Button>
            {session?.job != null && (
              <Link
                to={`/jobs/${session.job}`}
                className="px-2 py-2 text-center text-sm font-semibold text-slate-700 underline-offset-4 hover:underline"
              >
                Back to application
              </Link>
            )}
          </div>
        </div>
      )}
    </>
  );

  if (view === 'session' && session) return sessionView;
  if (view === 'report') return reportView;
  return startView;
}
