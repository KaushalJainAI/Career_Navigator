import { useCallback, useEffect, useMemo, useRef, useState, type ComponentProps } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { LayoutGrid, List as ListIcon, Search } from 'lucide-react';
import { Applications } from '../../api/endpoints';
import { errorMessage } from '../../api/client';
import {
  PIPELINE_ORDER, STATUS_LABEL, type AppStatus, type Application,
} from '../../lib/types';
import {
  Alert, Badge, Button, EmptyState, PageHeader, Spinner, inputCls, timeAgo,
} from '../../components/ui';
import { AddJobModal } from '../../components/AddJobModal';

type Tone = NonNullable<ComponentProps<typeof Badge>['tone']>;
type GroupKey = 'to_apply' | 'applied' | 'assessment' | 'interviewing' | 'outcome';

const GROUPS: { key: GroupKey; label: string; statuses: AppStatus[]; tone: Tone }[] = [
  { key: 'to_apply', label: 'To apply', statuses: ['saved', 'tailored', 'ready'], tone: 'slate' },
  { key: 'applied', label: 'Applied', statuses: ['applied'], tone: 'blue' },
  { key: 'assessment', label: 'Assessment', statuses: ['assessment'], tone: 'amber' },
  { key: 'interviewing', label: 'Interviewing', statuses: ['phone', 'onsite'], tone: 'teal' },
  { key: 'outcome', label: 'Outcome', statuses: ['offer', 'rejected', 'withdrawn'], tone: 'green' },
];

const PRACTISE_STATUSES: AppStatus[] = ['assessment', 'phone', 'onsite'];

const BTN = 'inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition';
const PRIMARY_LINK = `${BTN} bg-slate-950 text-white shadow-sm hover:bg-slate-800`;
const TEXT_LINK = 'font-medium text-teal-700 hover:text-teal-800 hover:underline';

const DAY_MS = 86_400_000;

function groupOf(status: AppStatus): GroupKey {
  return GROUPS.find((g) => g.statuses.includes(status))?.key ?? 'to_apply';
}

function statusTone(status: AppStatus): Tone {
  if (status === 'offer') return 'green';
  if (status === 'rejected') return 'red';
  return GROUPS.find((g) => g.statuses.includes(status))?.tone ?? 'slate';
}

function startOfDay(d: Date): Date {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

/** Whole calendar days from today to d (negative = past). */
function dayDiffFrom(d: Date): number {
  return Math.round((startOfDay(d).getTime() - startOfDay(new Date()).getTime()) / DAY_MS);
}

/** Parses a YYYY-MM-DD string as a local date (avoids UTC off-by-one). */
function parseYmd(s: string): Date {
  const [y, m, d] = s.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function relWord(diff: number): string {
  if (diff === 0) return 'today';
  if (diff === 1) return 'tomorrow';
  if (diff === -1) return 'yesterday';
  if (diff > 0) return `in ${diff} days`;
  return `${-diff} days ago`;
}

const fmtShort = (d: Date) => d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
const fmtWeekday = (d: Date) => d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });

function deadlineInfo(ymd: string | null): { text: string; urgent: boolean } | null {
  if (!ymd) return null;
  const d = parseYmd(ymd);
  const diff = dayDiffFrom(d);
  if (diff < 0) return { text: `Deadline passed · ${fmtShort(d)}`, urgent: true };
  return { text: `Apply by ${fmtShort(d)} · ${relWord(diff)}`, urgent: diff <= 2 };
}

function roundText(app: Application): string | null {
  if (!app.next_interview_at) return null;
  const d = new Date(app.next_interview_at);
  const diff = dayDiffFrom(d);
  const label = app.status === 'assessment' ? 'OA' : 'Round';
  const when = diff >= -1 && diff <= 1 ? relWord(diff) : fmtWeekday(d);
  const time = d.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' });
  return `${label} ${when}, ${time}`;
}

function followUpDue(app: Application): boolean {
  return app.status === 'applied' && !!app.follow_up_at && new Date(app.follow_up_at).getTime() <= Date.now();
}

/** Earliest upcoming date (deadline or next round) in ms; Infinity when there is none. */
function urgencyKey(app: Application): number {
  const today = startOfDay(new Date()).getTime();
  const candidates: number[] = [];
  if (app.deadline) {
    const t = parseYmd(app.deadline).getTime();
    if (t >= today) candidates.push(t);
  }
  if (app.next_interview_at) {
    const t = new Date(app.next_interview_at).getTime();
    if (t >= today) candidates.push(t);
  }
  return candidates.length ? Math.min(...candidates) : Infinity;
}

function byUpdatedDesc(a: Application, b: Application): number {
  return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
}

/** Board column order: soonest deadline / next round first, then most recently updated. */
function byUrgency(a: Application, b: Application): number {
  const ka = urgencyKey(a);
  const kb = urgencyKey(b);
  if (ka !== kb) return ka < kb ? -1 : 1;
  return byUpdatedDesc(a, b);
}

type SortBy = 'deadline' | 'next' | 'updated';

function listComparator(sortBy: SortBy): (a: Application, b: Application) => number {
  if (sortBy === 'updated') return byUpdatedDesc;
  const pick = (a: Application): number | null => {
    if (sortBy === 'deadline') return a.deadline ? parseYmd(a.deadline).getTime() : null;
    return a.next_interview_at ? new Date(a.next_interview_at).getTime() : null;
  };
  return (a, b) => {
    const x = pick(a);
    const y = pick(b);
    if (x == null && y == null) return byUpdatedDesc(a, b);
    if (x == null) return 1;
    if (y == null) return -1;
    return x - y || byUpdatedDesc(a, b);
  };
}

interface RowProps {
  app: Application;
  busy: boolean;
  flash: boolean;
  onStatus: (status: AppStatus) => void;
  onFollowUp: () => void;
}

function StatusSelect({ app, busy, onStatus }: Pick<RowProps, 'app' | 'busy' | 'onStatus'>) {
  return (
    <select
      aria-label={`Status for ${app.job_detail.company.name}, ${app.job_detail.title}`}
      value={app.status}
      disabled={busy}
      onChange={(e) => onStatus(e.target.value as AppStatus)}
      className={`${inputCls} py-1.5 text-xs disabled:opacity-60`}
    >
      {PIPELINE_ORDER.map((s) => (
        <option key={s} value={s}>{STATUS_LABEL[s]}</option>
      ))}
    </select>
  );
}

function FollowUpButton({ busy, onFollowUp }: { busy: boolean; onFollowUp: () => void }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <Badge tone="amber">Follow-up due</Badge>
      <Button variant="secondary" loading={busy} onClick={onFollowUp} className="px-3 py-1 text-xs">
        I followed up
      </Button>
    </span>
  );
}

function ApplicationCard({ app, busy, flash, onStatus, onFollowUp }: RowProps) {
  const job = app.job_detail;
  const deadline = deadlineInfo(app.deadline);
  const round = roundText(app);
  const due = followUpDue(app);
  const notes = app.notes.trim();
  return (
    <article
      id={`app-${app.id}`}
      className={`scroll-mt-24 rounded-xl border bg-white p-3 shadow-sm transition ${
        flash ? 'border-teal-500 ring-2 ring-teal-500 ring-offset-2' : 'border-slate-200'
      }`}
    >
      <div className="min-w-0">
        <p className="truncate font-bold text-slate-950">{job.company.name}</p>
        <p className="truncate text-sm text-slate-600">{job.title}</p>
      </div>
      <div className="mt-2">
        <Badge tone={statusTone(app.status)}>{STATUS_LABEL[app.status]}</Badge>
      </div>
      <div className="mt-2 space-y-1 text-xs text-slate-500">
        {deadline && <p className={deadline.urgent ? 'font-medium text-red-600' : ''}>{deadline.text}</p>}
        {round && <p>{round}</p>}
        {app.applied_at && <p>Applied {timeAgo(app.applied_at)}</p>}
      </div>
      {due && <div className="mt-2"><FollowUpButton busy={busy} onFollowUp={onFollowUp} /></div>}
      {notes && <p className="mt-2 truncate text-xs italic text-slate-500">{notes}</p>}
      <div className="mt-3">
        <StatusSelect app={app} busy={busy} onStatus={onStatus} />
      </div>
      <div className="mt-2 flex gap-4 text-sm">
        <Link to={`/jobs/${app.job}`} className={TEXT_LINK}>Open</Link>
        {PRACTISE_STATUSES.includes(app.status) && (
          <Link to={`/practice?application=${app.id}`} className={TEXT_LINK}>Practise</Link>
        )}
      </div>
    </article>
  );
}

function ApplicationRow({ app, busy, flash, onStatus, onFollowUp }: RowProps) {
  const job = app.job_detail;
  const deadline = deadlineInfo(app.deadline);
  const round = roundText(app);
  const due = followUpDue(app);
  return (
    <li
      id={`app-${app.id}`}
      className={`scroll-mt-24 grid gap-2 px-4 py-3 transition md:grid-cols-[minmax(0,1.3fr)_minmax(0,1.6fr)_minmax(0,1.3fr)_minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1fr)_auto] md:items-center md:gap-3 ${
        flash ? 'bg-teal-50 ring-2 ring-inset ring-teal-500' : ''
      }`}
    >
      <div className="min-w-0">
        <p className="truncate font-bold text-slate-950">{job.company.name}</p>
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm text-slate-700">{job.title}</p>
      </div>
      <div><StatusSelect app={app} busy={busy} onStatus={onStatus} /></div>
      <div className={`text-xs ${deadline?.urgent ? 'font-medium text-red-600' : 'text-slate-500'}`}>
        <span className="mr-1 text-slate-400 md:hidden">Deadline:</span>
        {deadline?.text ?? '—'}
      </div>
      <div className="text-xs text-slate-500">
        <span className="mr-1 text-slate-400 md:hidden">Next round:</span>
        {round ?? '—'}
      </div>
      <div className="text-xs text-slate-500">
        <span className="mr-1 text-slate-400 md:hidden">Applied:</span>
        {app.applied_at ? timeAgo(app.applied_at) : '—'}
      </div>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        {due && <FollowUpButton busy={busy} onFollowUp={onFollowUp} />}
        <Link to={`/jobs/${app.job}`} className={TEXT_LINK}>Open</Link>
        {PRACTISE_STATUSES.includes(app.status) && (
          <Link to={`/practice?application=${app.id}`} className={TEXT_LINK}>Practise</Link>
        )}
      </div>
    </li>
  );
}

export function PipelinePage() {
  const [searchParams] = useSearchParams();
  const [apps, setApps] = useState<Application[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState<Set<number>>(() => new Set());
  const [view, setView] = useState<'board' | 'list'>('board');
  const [query, setQuery] = useState('');
  const [groupFilter, setGroupFilter] = useState<GroupKey | 'all'>('all');
  const [sortBy, setSortBy] = useState<SortBy>('deadline');
  const [addOpen, setAddOpen] = useState(false);
  const [flashId, setFlashId] = useState<number | null>(null);
  const handledFocus = useRef<number | null>(null);

  const focusParam = searchParams.get('focus');
  const focusId = focusParam && !Number.isNaN(Number(focusParam)) ? Number(focusParam) : null;

  const loadApps = useCallback(async () => {
    try {
      const r = (await Applications.list()) as Application[] | { results: Application[] };
      setApps(Array.isArray(r) ? r : (r.results ?? []));
      setLoadError(null);
    } catch (e) {
      setLoadError(errorMessage(e, "Couldn't load your pipeline. Please try again."));
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    void loadApps();
  }, [loadApps]);

  useEffect(() => {
    if (!notice) return;
    const t = window.setTimeout(() => setNotice(null), 3000);
    return () => window.clearTimeout(t);
  }, [notice]);

  // Scroll to and briefly highlight ?focus=<id> once the data is in.
  useEffect(() => {
    if (!loaded || focusId == null || handledFocus.current === focusId) return;
    handledFocus.current = focusId;
    const el = document.getElementById(`app-${focusId}`);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
    setFlashId(focusId);
    window.setTimeout(() => setFlashId((cur) => (cur === focusId ? null : cur)), 3000);
  }, [loaded, focusId]);

  function setBusy(id: number, on: boolean) {
    setPending((prev) => {
      const next = new Set(prev);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  async function changeStatus(app: Application, status: AppStatus) {
    if (status === app.status) return;
    setActionError(null);
    setBusy(app.id, true);
    setApps((list) => list.map((a) => (a.id === app.id ? { ...a, status } : a)));
    try {
      const updated = (await Applications.patch(app.id, { status })) as Partial<Application> | null;
      if (updated && typeof updated === 'object') {
        setApps((list) => list.map((a) => (a.id === app.id
          ? { ...a, ...updated, id: a.id, status: updated.status ?? status }
          : a)));
      }
    } catch (e) {
      setApps((list) => list.map((a) => (a.id === app.id ? { ...a, status: app.status } : a)));
      setActionError(errorMessage(e));
    } finally {
      setBusy(app.id, false);
    }
  }

  async function markFollowedUp(app: Application) {
    setActionError(null);
    setBusy(app.id, true);
    try {
      await Applications.followedUp(app.id);
      setNotice(`Follow-up logged for ${app.job_detail.company.name}.`);
      await loadApps();
    } catch (e) {
      setActionError(errorMessage(e));
    } finally {
      setBusy(app.id, false);
    }
  }

  const groupCounts = useMemo(() => {
    const counts: Record<GroupKey, number> = { to_apply: 0, applied: 0, assessment: 0, interviewing: 0, outcome: 0 };
    for (const a of apps) counts[groupOf(a.status)] += 1;
    return counts;
  }, [apps]);

  const boardColumns = useMemo(
    () => GROUPS.map((g) => ({
      ...g,
      items: apps.filter((a) => groupOf(a.status) === g.key).sort(byUrgency),
    })),
    [apps],
  );

  const listRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return apps
      .filter((a) => groupFilter === 'all' || groupOf(a.status) === groupFilter)
      .filter((a) => !q
        || a.job_detail.company.name.toLowerCase().includes(q)
        || a.job_detail.title.toLowerCase().includes(q))
      .sort(listComparator(sortBy));
  }, [apps, query, groupFilter, sortBy]);

  const header = (
    <PageHeader
      title="Pipeline"
      subtitle="Every company you're in process with"
      actions={
        <>
          <div role="group" aria-label="View" className="inline-flex rounded-xl border border-slate-200 bg-white p-1">
            <button
              type="button"
              aria-pressed={view === 'board'}
              onClick={() => setView('board')}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                view === 'board' ? 'bg-slate-950 text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <LayoutGrid className="h-4 w-4" aria-hidden /> Board
            </button>
            <button
              type="button"
              aria-pressed={view === 'list'}
              onClick={() => setView('list')}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                view === 'list' ? 'bg-slate-950 text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <ListIcon className="h-4 w-4" aria-hidden /> List
            </button>
          </div>
          <Button variant="secondary" onClick={() => setAddOpen(true)}>Add a job</Button>
        </>
      }
    />
  );

  const modal = (
    <AddJobModal
      open={addOpen}
      onClose={() => setAddOpen(false)}
      onAdded={() => { void loadApps(); }}
    />
  );

  if (!loaded) {
    return (
      <div>
        {header}
        <Spinner label="Loading your applications…" />
        {modal}
      </div>
    );
  }

  if (loadError && apps.length === 0) {
    return (
      <div>
        {header}
        <Alert tone="red">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>{loadError}</span>
            <Button variant="secondary" onClick={() => { setLoaded(false); void loadApps(); }}>Try again</Button>
          </div>
        </Alert>
        {modal}
      </div>
    );
  }

  if (apps.length === 0) {
    return (
      <div>
        {header}
        <EmptyState title="No applications yet">
          Save jobs from the Jobs page, or add one you found through a campus drive or a referral.
        </EmptyState>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <Link to="/jobs" className={PRIMARY_LINK}>Browse jobs</Link>
          <Button variant="secondary" onClick={() => setAddOpen(true)}>Add a job</Button>
        </div>
        {modal}
      </div>
    );
  }

  const cardProps = (app: Application) => ({
    app,
    busy: pending.has(app.id),
    flash: flashId === app.id,
    onStatus: (status: AppStatus) => void changeStatus(app, status),
    onFollowUp: () => void markFollowedUp(app),
  });

  return (
    <div>
      {header}

      {loadError && <div className="mb-4"><Alert tone="red">{loadError}</Alert></div>}
      {actionError && <div className="mb-4"><Alert tone="red">{actionError}</Alert></div>}
      {notice && <div className="mb-4"><Alert tone="green">{notice}</Alert></div>}

      <div className="mb-5 flex flex-wrap gap-2">
        {GROUPS.map((g) => (
          <Badge key={g.key} tone={g.tone} className="px-3 py-1 text-sm">
            {g.label} <span className="font-bold">{groupCounts[g.key]}</span>
          </Badge>
        ))}
      </div>

      {view === 'board' ? (
        <div className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-3 md:grid md:grid-cols-5 md:overflow-visible">
          {boardColumns.map((col) => (
            <section
              key={col.key}
              aria-label={col.label}
              className="w-[82%] shrink-0 snap-start rounded-2xl border border-slate-200 bg-slate-50/70 p-3 md:w-auto md:shrink"
            >
              <header className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-900">{col.label}</h2>
                <span className="rounded-full bg-white px-2 py-0.5 text-xs font-medium text-slate-600 ring-1 ring-slate-200">
                  {col.items.length}
                </span>
              </header>
              {col.items.length === 0 ? (
                <p className="rounded-xl border border-dashed border-slate-300 px-3 py-6 text-center text-xs text-slate-400">
                  Nothing here
                </p>
              ) : (
                <div className="space-y-3">
                  {col.items.map((app) => (
                    <ApplicationCard key={app.id} {...cardProps(app)} />
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      ) : (
        <div>
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <label className="relative min-w-[12rem] flex-1">
              <span className="sr-only">Search company or role</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search company or role"
                className={`${inputCls} pl-9`}
              />
            </label>
            <label className="block">
              <span className="sr-only">Filter by stage</span>
              <select
                value={groupFilter}
                onChange={(e) => setGroupFilter(e.target.value as GroupKey | 'all')}
                className={`${inputCls} w-auto`}
              >
                <option value="all">All stages</option>
                {GROUPS.map((g) => <option key={g.key} value={g.key}>{g.label}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="sr-only">Sort by</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortBy)}
                className={`${inputCls} w-auto`}
              >
                <option value="deadline">Sort: deadline</option>
                <option value="next">Sort: next round</option>
                <option value="updated">Sort: recently updated</option>
              </select>
            </label>
          </div>

          {listRows.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-slate-300 px-6 py-10 text-center text-sm text-slate-500">
              No applications match these filters.
            </p>
          ) : (
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="hidden border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500 md:grid md:grid-cols-[minmax(0,1.3fr)_minmax(0,1.6fr)_minmax(0,1.3fr)_minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1fr)_auto] md:gap-3">
                <span>Company</span>
                <span>Role</span>
                <span>Status</span>
                <span>Deadline</span>
                <span>Next round</span>
                <span>Applied</span>
                <span>Actions</span>
              </div>
              <ul className="divide-y divide-slate-100">
                {listRows.map((app) => (
                  <ApplicationRow key={app.id} {...cardProps(app)} />
                ))}
              </ul>
            </div>
          )}
          <p className="mt-3 text-xs text-slate-500">
            Showing {listRows.length} of {apps.length}
          </p>
        </div>
      )}

      {modal}
    </div>
  );
}
