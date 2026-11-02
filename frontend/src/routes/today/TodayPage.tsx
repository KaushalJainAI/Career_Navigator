import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { CalendarClock, Check, ChevronRight, Circle, Compass, Mail, Mic2, Send, Sparkles, type LucideIcon } from 'lucide-react';
import { Applications } from '../../api/endpoints';
import { errorMessage } from '../../api/client';
import type { TodayData, TodayStep } from '../../lib/types';
import { Alert, Button, Card, EmptyState, FitRing, PageHeader, Spinner } from '../../components/ui';
import { AddJobModal } from '../../components/AddJobModal';

const KIND_ICON: Record<TodayStep['kind'], LucideIcon> = {
  interview: Mic2,
  follow_up: Mail,
  apply: Send,
  discover: Compass,
  setup: Sparkles,
  deadline: CalendarClock,
};

const BTN = 'inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition';
const PRIMARY_LINK = `${BTN} bg-slate-950 text-white shadow-sm hover:bg-slate-800`;
const SECONDARY_LINK = `${BTN} border border-slate-200 bg-white text-slate-900 hover:bg-slate-50`;

/** Where the setup card should send the user next, based on what is still missing. */
function setupTarget(s: TodayData['setup']): string {
  if (!s.has_resume) return '/setup';
  if (!s.has_targets) return '/setup?step=targets';
  if (!s.has_jobs) return '/jobs?refresh=1';
  return '/setup';
}

export function TodayPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<TodayData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [addOpen, setAddOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData((await Applications.today()) as TodayData);
    } catch (e) {
      setError(errorMessage(e, "Couldn't load your day. Please try again."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!notice) return;
    const t = window.setTimeout(() => setNotice(null), 3000);
    return () => window.clearTimeout(t);
  }, [notice]);

  async function markFollowedUp(step: TodayStep) {
    if (step.application_id == null) return;
    setBusyId(step.application_id);
    setActionError(null);
    try {
      await Applications.followedUp(step.application_id);
      setNotice('Follow-up logged. Nice work.');
      await load();
    } catch (e) {
      setActionError(errorMessage(e));
    } finally {
      setBusyId(null);
    }
  }

  const todayLabel = new Intl.DateTimeFormat('en-IN', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date());

  const header = (
    <PageHeader
      title="Today"
      subtitle={todayLabel}
      actions={<Button variant="secondary" onClick={() => setAddOpen(true)}>Add a job</Button>}
    />
  );

  const modal = (
    <AddJobModal
      open={addOpen}
      onClose={() => setAddOpen(false)}
      onAdded={(job) => {
        setAddOpen(false);
        navigate(`/jobs/${job.id}`);
      }}
    />
  );

  if (!data) {
    return (
      <div>
        {header}
        {error && (
          <Alert tone="red">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span>{error}</span>
              <Button variant="secondary" onClick={() => void load()}>Try again</Button>
            </div>
          </Alert>
        )}
        {loading && !error && <Spinner label="Loading your day…" />}
        {modal}
      </div>
    );
  }

  const { setup, steps, week, stats, top_matches } = data;
  const goal = Math.max(week.goal, 0);
  const pct = goal > 0 ? Math.min(100, Math.round((week.applied / goal) * 100)) : 0;

  const statTiles: { label: string; value: string; to: string; title?: string }[] = [
    { label: 'Jobs available', value: String(stats.jobs_available), to: '/jobs' },
    { label: 'Strong matches', value: String(stats.strong_matches), to: '/jobs?min_fit=70' },
    { label: 'In progress', value: String(stats.in_progress), to: '/pipeline' },
    { label: 'Applied', value: String(stats.applied), to: '/pipeline' },
    { label: 'Responses', value: String(stats.responses), to: '/pipeline' },
    {
      label: 'Response rate',
      value: stats.response_rate == null ? '—' : `${Math.round(stats.response_rate * 100)}%`,
      to: '/pipeline',
      title: 'Responses divided by applications submitted',
    },
    { label: 'Interviewing', value: String(stats.interviewing), to: '/pipeline' },
    { label: 'Offers', value: String(stats.offers), to: '/pipeline' },
  ];

  const setupItems = [
    { label: 'Résumé added', done: setup.has_resume },
    { label: 'Target roles set', done: setup.has_targets },
    { label: 'Jobs found', done: setup.has_jobs },
  ];

  return (
    <div>
      {header}

      {error && (
        <div className="mb-5">
          <Alert tone="red">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span>{error}</span>
              <Button variant="secondary" onClick={() => void load()}>Try again</Button>
            </div>
          </Alert>
        </div>
      )}
      {actionError && <div className="mb-5"><Alert tone="red">{actionError}</Alert></div>}
      {notice && <div className="mb-5"><Alert tone="green">{notice}</Alert></div>}

      {!setup.complete && (
        <Card className="mb-5 border-teal-200 bg-teal-50/40">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <h2 className="text-lg font-bold text-slate-950">Let's get you set up</h2>
              <ul className="mt-3 space-y-2">
                {setupItems.map((item) => (
                  <li key={item.label} className="flex items-center gap-2 text-sm">
                    {item.done
                      ? <Check className="h-4 w-4 text-emerald-600" aria-hidden />
                      : <Circle className="h-4 w-4 text-slate-300" aria-hidden />}
                    <span className={item.done ? 'text-slate-500 line-through' : 'text-slate-900'}>{item.label}</span>
                  </li>
                ))}
              </ul>
            </div>
            <Link to={setupTarget(setup)} className={`${PRIMARY_LINK} shrink-0`}>Continue setup</Link>
          </div>
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-5 [&>*]:min-w-0">
        <Card className="lg:col-span-3">
          <h2 className="text-lg font-bold text-slate-950">Next steps</h2>
          {steps.length === 0 ? (
            <div className="mt-3">
              <EmptyState title="You're all caught up.">
                Find new jobs or practise an interview.
              </EmptyState>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                <Link to="/jobs?refresh=1" className={PRIMARY_LINK}>Find new jobs</Link>
                <Link to="/practice" className={SECONDARY_LINK}>Practise an interview</Link>
              </div>
            </div>
          ) : (
            <ul className="mt-3 divide-y divide-slate-100">
              {steps.map((step, i) => {
                const Icon = KIND_ICON[step.kind];
                const isFollowUp = step.kind === 'follow_up' && step.application_id != null;
                return (
                  <li key={`${step.kind}-${step.application_id ?? 'none'}-${i}`} className="flex gap-3 py-4">
                    <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-teal-50 text-teal-700">
                      <Icon className="h-4 w-4" aria-hidden />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="break-words font-semibold text-slate-950">{step.title}</p>
                      {step.detail && <p className="mt-0.5 text-sm text-slate-600">{step.detail}</p>}
                      <div className="mt-3 flex flex-wrap gap-2">
                        {isFollowUp ? (
                          <>
                            <Button
                              loading={busyId === step.application_id}
                              onClick={() => void markFollowedUp(step)}
                            >
                              I followed up
                            </Button>
                            <Link to={`/pipeline?focus=${step.application_id}`} className={SECONDARY_LINK}>Open</Link>
                          </>
                        ) : (
                          <Link to={step.action.to} className={PRIMARY_LINK}>{step.action.label}</Link>
                        )}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <div className="space-y-5 lg:col-span-2">
          <Card>
            <h2 className="text-lg font-bold text-slate-950">This week</h2>
            {goal > 0 ? (
              <>
                <p className="mt-1 text-sm text-slate-600">
                  {week.applied} of {goal} applications this week
                </p>
                <div
                  role="progressbar"
                  aria-label="Applications this week"
                  aria-valuemin={0}
                  aria-valuemax={goal}
                  aria-valuenow={week.applied}
                  className="mt-3 h-2.5 w-full overflow-hidden rounded-full bg-slate-100"
                >
                  <div className="h-full rounded-full bg-teal-600 transition-all" style={{ width: `${pct}%` }} />
                </div>
              </>
            ) : (
              <p className="mt-1 text-sm text-slate-600">
                No weekly goal yet. <Link to="/profile" className="font-medium text-slate-900 underline">Set one in your profile</Link>.
              </p>
            )}

            <div className="mt-4 grid grid-cols-2 gap-2">
              {statTiles.map((tile) => (
                <Link
                  key={tile.label}
                  to={tile.to}
                  title={tile.title}
                  className="rounded-xl border border-slate-200 bg-slate-50 p-3 transition hover:bg-slate-100"
                >
                  <div className="text-xl font-bold text-slate-950">{tile.value}</div>
                  <div className="text-xs text-slate-500">{tile.label}</div>
                </Link>
              ))}
            </div>
          </Card>

          <Card>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-bold text-slate-950">Best matches for you</h2>
              <Link to="/jobs" className="text-sm font-medium text-teal-700 hover:text-teal-800">See all jobs</Link>
            </div>
            {top_matches.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">
                No matches yet.{' '}
                <Link to="/jobs?refresh=1" className="font-medium text-slate-900 underline">Find jobs</Link>{' '}
                to see your best fits here.
              </p>
            ) : (
              <ul className="mt-3 divide-y divide-slate-100">
                {top_matches.map((m) => {
                  const place = m.location || (m.remote ? 'Remote' : '');
                  return (
                    <li key={m.id}>
                      <Link to={`/jobs/${m.id}`} className="flex items-center gap-3 py-3 transition hover:bg-slate-50">
                        <FitRing fit={m.fit} verdict={m.verdict} size={48} />
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-semibold text-slate-950">{m.title}</p>
                          <p className="truncate text-sm text-slate-500">
                            {m.company.name}{place && ` · ${place}`}
                          </p>
                        </div>
                        <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" aria-hidden />
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </Card>
        </div>
      </div>

      {modal}
    </div>
  );
}
