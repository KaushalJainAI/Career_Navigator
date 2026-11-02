import { useCallback, useEffect, useRef, useState, type MouseEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { isAxiosError } from 'axios';
import { Briefcase, Check, Plus, RefreshCw } from 'lucide-react';
import { Applications, Jobs } from '../../api/endpoints';
import { errorMessage } from '../../api/client';
import type { AppStatus, FeedJob, FeedResponse, RefreshResult } from '../../lib/types';
import { STATUS_LABEL } from '../../lib/types';
import {
  Alert, Badge, Button, Card, EmptyState, FitRing, PageHeader, Spinner, VerdictBadge,
  inputCls, salaryLabel, timeAgo,
} from '../../components/ui';
import { GhostRiskBadge } from '../../components/GhostRiskBadge';
import { AddJobModal, type AddedJob } from '../../components/AddJobModal';

const PAGE_SIZE = 30;
const FIT_OPTIONS: { value: number; label: string }[] = [
  { value: 0, label: 'All' },
  { value: 50, label: 'Good 50+' },
  { value: 70, label: 'Strong 70+' },
];

type Params = Record<string, string | number | boolean>;

interface RefreshState {
  result: RefreshResult | null;
  error: string | null;
  needsTargets: boolean;
}

function initialMinFit(raw: string | null): number {
  const n = Number(raw);
  if (n >= 70) return 70;
  if (n >= 50) return 50;
  return 0;
}

export function JobsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [searchInput, setSearchInput] = useState('');
  const [q, setQ] = useState('');
  const [minFit, setMinFit] = useState<number>(() => initialMinFit(searchParams.get('min_fit')));
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [showApplied, setShowApplied] = useState(false);
  const [showGhost, setShowGhost] = useState(false);

  const [data, setData] = useState<FeedResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [savingIds, setSavingIds] = useState<Set<number>>(() => new Set());

  const [refreshing, setRefreshing] = useState(false);
  const [refresh, setRefresh] = useState<RefreshState | null>(null);
  const [addOpen, setAddOpen] = useState(false);

  // Debounce the search box into q.
  useEffect(() => {
    const t = setTimeout(() => setQ(searchInput.trim()), 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  // Latest request wins; older responses are dropped.
  const reqRef = useRef(0);

  const load = useCallback(async (offset: number, append: boolean) => {
    const id = ++reqRef.current;
    if (append) setLoadingMore(true);
    else setLoading(true);
    setError(null);
    const params: Params = {
      limit: PAGE_SIZE,
      offset,
      status: showApplied ? 'all' : 'new',
      hide_ghost: showGhost ? 0 : 1,
    };
    if (q) params.q = q;
    if (remoteOnly) params.remote = 1;
    if (minFit > 0) params.min_fit = minFit;
    try {
      const res: FeedResponse = await Jobs.feed(params);
      if (id !== reqRef.current) return;
      setData((prev) => (append && prev ? { ...res, results: [...prev.results, ...res.results] } : res));
    } catch (e) {
      if (id !== reqRef.current) return;
      setError(errorMessage(e, 'Could not load jobs. Please try again.'));
    } finally {
      if (id === reqRef.current) {
        setLoading(false);
        setLoadingMore(false);
      }
    }
  }, [q, minFit, remoteOnly, showApplied, showGhost]);

  useEffect(() => {
    void load(0, false);
  }, [load]);

  const runRefresh = useCallback(async () => {
    setRefreshing(true);
    setRefresh(null);
    try {
      const result: RefreshResult = await Jobs.refresh();
      setRefresh({ result, error: null, needsTargets: false });
    } catch (e) {
      setRefresh({
        result: null,
        error: errorMessage(e, 'The job search failed. Please try again.'),
        needsTargets: isAxiosError(e) && e.response?.status === 400,
      });
    } finally {
      setRefreshing(false);
    }
    void load(0, false);
  }, [load]);

  // ?refresh=1 starts a search once, then drops the param so reloads do not repeat it.
  const autoRan = useRef(false);
  useEffect(() => {
    if (autoRan.current || searchParams.get('refresh') !== '1') return;
    autoRan.current = true;
    const next = new URLSearchParams(searchParams);
    next.delete('refresh');
    setSearchParams(next, { replace: true });
    void runRefresh();
  }, [searchParams, setSearchParams, runRefresh]);

  async function saveJob(e: MouseEvent, job: FeedJob) {
    e.preventDefault();
    e.stopPropagation();
    if (savingIds.has(job.id)) return;
    setSavingIds((s) => new Set(s).add(job.id));
    setActionError(null);
    try {
      const app = (await Applications.create(job.id)) as { id: number; status?: AppStatus };
      const application = { id: app.id, status: app.status ?? 'saved' };
      setData((d) => d && {
        ...d,
        results: d.results.map((r) => (r.id === job.id ? { ...r, application } : r)),
      });
    } catch (err) {
      setActionError(`Could not save “${job.title}”. ${errorMessage(err)}`);
    } finally {
      setSavingIds((s) => {
        const next = new Set(s);
        next.delete(job.id);
        return next;
      });
    }
  }

  function clearFilters() {
    setSearchInput('');
    setMinFit(0);
    setRemoteOnly(false);
    setShowApplied(false);
    setShowGhost(false);
  }

  function onAdded(job: AddedJob) {
    navigate(`/jobs/${job.id}`);
  }

  const results = data?.results ?? [];
  const hasFilters = Boolean(q) || minFit > 0 || remoteOnly || showApplied || showGhost;

  return (
    <div>
      <PageHeader
        title="Jobs"
        subtitle="Ranked by how well they fit your profile"
        actions={
          <>
            <Button variant="secondary" onClick={() => void runRefresh()} loading={refreshing} disabled={refreshing}>
              {!refreshing && <RefreshCw className="h-4 w-4" />}
              Find new jobs
            </Button>
            <Button onClick={() => setAddOpen(true)}>
              <Plus className="h-4 w-4" />
              Add a job
            </Button>
          </>
        }
      />

      {refreshing && (
        <div className="mb-4">
          <Spinner label="Searching company boards… this can take up to a minute" />
        </div>
      )}

      {refresh && !refreshing && (
        <div className="mb-4">
          {refresh.error ? (
            <Alert tone="red">
              {refresh.error}
              {refresh.needsTargets && (
                <>
                  {' '}
                  <Link to="/setup?step=targets" className="font-semibold underline">Set your target roles</Link>
                </>
              )}
            </Alert>
          ) : refresh.result && (() => {
            const ok = refresh.result.sources.filter((s) => s.ok).length;
            const failed = refresh.result.sources.filter((s) => !s.ok).map((s) => s.source);
            const n = refresh.result.new_jobs;
            const tone = failed.length ? 'amber' : n > 0 ? 'green' : 'slate';
            return (
              <Alert tone={tone}>
                Found {n} new job{n === 1 ? '' : 's'} from {ok} source{ok === 1 ? '' : 's'}.
                {failed.length > 0 && <> Could not reach: {failed.join(', ')}.</>}
              </Alert>
            );
          })()}
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex flex-col gap-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <input
            type="search"
            aria-label="Search jobs"
            placeholder="Search title, company or skill"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className={`${inputCls} sm:max-w-xs`}
          />
          <div role="group" aria-label="Minimum fit" className="inline-flex w-fit rounded-xl border border-slate-200 bg-white p-1">
            {FIT_OPTIONS.map((o) => (
              <button
                key={o.value}
                type="button"
                aria-pressed={minFit === o.value}
                onClick={() => setMinFit(o.value)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                  minFit === o.value ? 'bg-slate-950 text-white' : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap gap-x-5 gap-y-2">
          <Toggle label="Remote only" checked={remoteOnly} onChange={setRemoteOnly} />
          <Toggle label="Show already-applied" checked={showApplied} onChange={setShowApplied} />
          <Toggle label="Show likely ghost jobs" checked={showGhost} onChange={setShowGhost} />
        </div>
      </div>

      {actionError && <div className="mb-4"><Alert tone="red">{actionError}</Alert></div>}

      {loading && !data && <Spinner />}

      {error && !data && (
        <Alert tone="red">
          {error}{' '}
          <button type="button" onClick={() => void load(0, false)} className="font-semibold underline">Try again</button>
        </Alert>
      )}

      {data && !data.has_profile && (
        <EmptyState
          icon={<Briefcase className="h-5 w-5" />}
          title="Add your résumé first so we can rank jobs for you"
          action={<Link to="/setup"><Button>Add your résumé</Button></Link>}
        >
          Upload your résumé or paste its text. We use it to score how well each job fits you.
        </EmptyState>
      )}

      {data && data.has_profile && data.total_jobs === 0 && (
        <EmptyState
          icon={<Briefcase className="h-5 w-5" />}
          title="No jobs yet"
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <Button variant="secondary" onClick={() => void runRefresh()} loading={refreshing}>Find new jobs</Button>
              <Button onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" />Add a job</Button>
            </div>
          }
        >
          Search company boards for roles that match your targets. Campus drives and referrals can be added manually.
        </EmptyState>
      )}

      {data && data.has_profile && data.total_jobs > 0 && data.count === 0 && (
        <EmptyState
          title="No jobs match these filters"
          action={hasFilters ? <Button variant="secondary" onClick={clearFilters}>Clear filters</Button> : undefined}
        >
          Try a lower fit score or turn off the filters above.
        </EmptyState>
      )}

      {data && data.has_profile && results.length > 0 && (
        <>
          <p className="mb-3 text-sm text-slate-500">
            {data.count} job{data.count === 1 ? '' : 's'} · showing best matches first
          </p>
          <div className={`space-y-3 transition-opacity ${loading ? 'opacity-60' : ''}`} aria-busy={loading}>
            {results.map((job) => (
              <JobRow key={job.id} job={job} saving={savingIds.has(job.id)} onSave={saveJob} />
            ))}
          </div>
          {results.length < data.count && (
            <div className="mt-6 flex justify-center">
              <Button variant="secondary" onClick={() => void load(results.length, true)} loading={loadingMore}>
                Load more
              </Button>
            </div>
          )}
        </>
      )}

      <AddJobModal open={addOpen} onClose={() => setAddOpen(false)} onAdded={onAdded} />
    </div>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="inline-flex items-center gap-2 text-sm text-slate-700"
    >
      <span className={`relative inline-flex h-5 w-9 shrink-0 rounded-full transition ${checked ? 'bg-slate-950' : 'bg-slate-300'}`}>
        <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition ${checked ? 'left-[18px]' : 'left-0.5'}`} />
      </span>
      {label}
    </button>
  );
}

function JobRow({
  job, saving, onSave,
}: { job: FeedJob; saving: boolean; onSave: (e: MouseEvent, job: FeedJob) => void }) {
  const salary = salaryLabel(job.salary_min, job.salary_max, job.salary_currency);
  const posted = timeAgo(job.posted_at || job.created_at);
  const firstReason = job.reasons[0];
  const missing = job.missing_skills.slice(0, 4);

  return (
    <div className="flex items-start gap-3">
      <Card className="flex min-w-0 flex-1 items-start gap-4 transition hover:border-slate-300">
        <Link
          to={`/jobs/${job.id}`}
          className="flex min-w-0 flex-1 items-start gap-4 rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
        >
          <FitRing fit={job.fit} verdict={job.verdict} size={52} />
          <div className="min-w-0 flex-1">
            <div className="font-semibold text-slate-950 break-words">{job.title}</div>
            <div className="mt-0.5 text-sm text-slate-600">
              {job.company.name}
              {' · '}
              {job.location || 'Location not listed'}
              {job.remote && <> · <Badge tone="blue">Remote</Badge></>}
              {salary && <> · {salary}</>}
            </div>
            <div className="mt-0.5 text-xs text-slate-500">
              Posted {posted || 'recently'}{job.source && <> · via {job.source}</>}
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <VerdictBadge verdict={job.verdict} />
              {job.ghost_band !== 'low' && <GhostRiskBadge score={job.ghost_risk} band={job.ghost_band} />}
              {job.application && <Badge tone="teal">{STATUS_LABEL[job.application.status]}</Badge>}
            </div>

            {(job.matched_skills.length > 0 || missing.length > 0) && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {job.matched_skills.slice(0, 5).map((s) => (
                  <span key={s} className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">{s}</span>
                ))}
                {missing.map((s) => (
                  <span key={s} className="rounded-full border border-dashed border-red-200 px-2 py-0.5 text-xs text-red-600">
                    missing: {s}
                  </span>
                ))}
              </div>
            )}

            {firstReason && (
              <p className="mt-2 text-sm text-slate-500">
                <span className="font-medium text-slate-700">{firstReason.title}</span>
                {firstReason.detail && <> — {firstReason.detail}</>}
              </p>
            )}
          </div>
        </Link>
      </Card>

      <div className="shrink-0 pt-5">
        {job.application ? (
          <span className="inline-flex items-center gap-1 whitespace-nowrap text-sm font-medium text-emerald-700">
            <Check className="h-4 w-4" /> Saved ✓
          </span>
        ) : (
          <Button
            variant="secondary"
            loading={saving}
            onClick={(e) => onSave(e, job)}
            aria-label={`Save ${job.title} at ${job.company.name}`}
            className="px-3"
          >
            Save
          </Button>
        )}
      </div>
    </div>
  );
}
