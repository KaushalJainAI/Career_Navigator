import { useEffect, useMemo, useState } from 'react';
import { useJobsStore } from '../../stores/useJobsStore';
import { useApplicationsStore } from '../../stores/useApplicationsStore';
import { Link, useNavigate } from 'react-router-dom';
import { Search, MapPin, Building, ChevronRight, SlidersHorizontal, ArrowUpDown, X, ListChecks, Hourglass, Plus, RefreshCw } from 'lucide-react';
import { GhostRiskBadge } from '../../components/GhostRiskBadge';
import { Jobs } from '../../api/endpoints';
import { rejectionCooldown } from '../../lib/cooldown';

const STATUS_LABEL: Record<string, string> = {
  saved: 'Saved', tailored: 'Tailored', ready: 'Ready', applied: 'Applied',
  phone: 'Phone screen', onsite: 'Onsite', offer: 'Offer', rejected: 'Rejected', withdrawn: 'Withdrawn',
};

type SortKey = 'relevance' | 'ghost_asc' | 'company_az' | 'title_az';

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'ghost_asc', label: 'Lowest ghost risk' },
  { value: 'company_az', label: 'Company (A–Z)' },
  { value: 'title_az', label: 'Title (A–Z)' },
];

export function JobsList() {
  const { jobs, fetch, loading } = useJobsStore();
  const applications = useApplicationsStore((s) => s.applications);
  const fetchApps = useApplicationsStore((s) => s.fetch);
  const [q, setQ] = useState('');
  const [sort, setSort] = useState<SortKey>('relevance');
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [hideGhost, setHideGhost] = useState(false);
  const [adding, setAdding] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState('');

  async function refreshJobs() {
    setRefreshing(true);
    setRefreshMsg('');
    try {
      const out = await Jobs.refresh();
      setRefreshMsg(out.detail || 'Job sources refreshed.');
      await fetch();
    } catch (e) {
      const err = e as { response?: { status?: number; data?: { detail?: string } } };
      if (err.response?.status === 429) {
        setRefreshMsg('You refreshed recently — give it a few minutes before trying again.');
      } else {
        setRefreshMsg(err.response?.data?.detail || 'Could not refresh right now. Please try again.');
      }
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => { fetch(); }, [fetch]);
  useEffect(() => { fetchApps().catch(() => undefined); }, [fetchApps]);

  // Association: map each job that's in the pipeline to its application.
  const appByJob = useMemo(() => {
    const m = new Map<number, (typeof applications)[number]>();
    for (const a of applications) m.set(a.job, a);
    return m;
  }, [applications]);

  const visibleJobs = useMemo(() => {
    let out = [...jobs];
    if (remoteOnly) out = out.filter((j) => j.remote);
    if (hideGhost) out = out.filter((j) => !(typeof j.ghost_risk === 'number' && j.ghost_risk >= 60));

    switch (sort) {
      case 'ghost_asc':
        out.sort((a, b) => (a.ghost_risk ?? 0) - (b.ghost_risk ?? 0));
        break;
      case 'company_az':
        out.sort((a, b) => (a.company?.name ?? '').localeCompare(b.company?.name ?? ''));
        break;
      case 'title_az':
        out.sort((a, b) => (a.title ?? '').localeCompare(b.title ?? ''));
        break;
      default:
        break; // relevance = backend order
    }
    return out;
  }, [jobs, remoteOnly, hideGhost, sort]);

  const activeFilters = (remoteOnly ? 1 : 0) + (hideGhost ? 1 : 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-800">Discover Jobs</h1>
          <p className="text-slate-500 text-sm mt-1">Find and apply to positions matching your profile.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={refreshJobs}
            disabled={refreshing}
            title="Search the configured job sources for new postings"
            className="inline-flex items-center justify-center gap-1.5 rounded-xl border-2 border-slate-900 bg-white px-4 py-2.5 text-sm font-black text-slate-900 transition hover:bg-slate-50 disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Searching…' : 'Find new jobs'}
          </button>
          <button
            onClick={() => setAdding(true)}
            className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-black text-white shadow-[0_4px_0_#2dd4bf] transition hover:bg-slate-800"
          >
            <Plus className="h-4 w-4" /> Add a job
          </button>
        </div>
      </div>

      {refreshMsg && (
        <div className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-2.5 text-sm font-semibold text-teal-800">
          {refreshMsg}
        </div>
      )}

      {adding && <AddJobForm onClose={() => setAdding(false)} />}

      {/* Search Bar */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-slate-400" />
        </div>
        <input
          className="block w-full rounded-xl border border-slate-200 bg-white py-3 pl-10 pr-3 leading-5 shadow-sm transition-all placeholder:text-sm placeholder-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500 sm:placeholder:text-base"
          placeholder="Search for roles, companies, or keywords..."
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            fetch({ search: e.target.value });
          }}
        />
      </div>

      {/* Filter + Sort bar */}
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="hidden items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-slate-400 sm:inline-flex">
          <SlidersHorizontal className="h-3.5 w-3.5" /> Filters
        </span>

        <button
          onClick={() => setRemoteOnly((v) => !v)}
          className={`rounded-full border px-3 py-1.5 text-xs font-bold transition ${
            remoteOnly
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
              : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
          }`}
        >
          Remote only
        </button>

        <button
          onClick={() => setHideGhost((v) => !v)}
          className={`rounded-full border px-3 py-1.5 text-xs font-bold transition ${
            hideGhost
              ? 'border-amber-200 bg-amber-50 text-amber-700'
              : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
          }`}
        >
          Hide high ghost-risk
        </button>

        {activeFilters > 0 && (
          <button
            onClick={() => { setRemoteOnly(false); setHideGhost(false); }}
            className="inline-flex items-center gap-1 text-xs font-bold text-slate-500 hover:text-slate-800"
          >
            <X className="h-3.5 w-3.5" /> Clear
          </button>
        )}

        {/* Sort — pushed to the right */}
        <label className="ml-auto inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-600">
          <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
          <span className="hidden sm:inline">Sort</span>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            className="cursor-pointer bg-transparent font-bold text-slate-800 focus:outline-none"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>
      </div>

      {/* Job List */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-28 bg-slate-200 animate-pulse rounded-xl" />)}
        </div>
      ) : (
        <div className="space-y-2.5 sm:space-y-4">
          {!loading && (
            <p className="text-xs font-semibold text-slate-400">
              {visibleJobs.length} {visibleJobs.length === 1 ? 'job' : 'jobs'}
              {activeFilters > 0 && jobs.length !== visibleJobs.length ? ` of ${jobs.length}` : ''}
            </p>
          )}
          {visibleJobs.length === 0 && (
            <div className="text-center py-12 bg-white rounded-xl border border-dashed border-slate-300">
              <Search className="mx-auto h-12 w-12 text-slate-300 mb-3" />
              <h3 className="text-lg font-medium text-slate-900">No jobs found</h3>
              <p className="text-slate-500">
                {activeFilters > 0 ? 'Try clearing filters or adjusting your search.' : 'Try adjusting your search terms.'}
              </p>
            </div>
          )}
          {visibleJobs.map((j) => {
            const app = appByJob.get(j.id);
            const cool = app ? rejectionCooldown(app) : null;
            return (
            <Link
              key={j.id}
              to={`/jobs/${j.id}`}
              className="group block rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition-all duration-200 hover:border-brand-300 hover:shadow-md sm:p-5"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-2.5 sm:gap-4">
                  <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-slate-100 text-base font-bold text-slate-500 sm:h-12 sm:w-12 sm:text-xl">
                    {j.company?.name?.[0] || '?'}
                  </div>
                  <div className="min-w-0">
                    <h2 className="text-sm font-bold text-slate-800 transition-colors group-hover:text-brand-600 sm:text-lg">
                      {j.title}
                    </h2>
                    <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-slate-500 sm:mt-2 sm:gap-x-4 sm:text-sm">
                      <span className="flex min-w-0 items-center gap-1.5">
                        <Building className="h-4 w-4 flex-shrink-0 text-slate-400" />
                        {j.company?.name}
                      </span>
                      <span className="flex min-w-0 items-center gap-1.5">
                        <MapPin className="h-4 w-4 flex-shrink-0 text-slate-400" />
                        {j.location}
                      </span>
                      {j.remote && (
                        <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 font-medium rounded text-xs border border-emerald-100">
                          Remote
                        </span>
                      )}
                      {typeof j.ghost_risk === 'number' && j.ghost_risk >= 30 && (
                        <GhostRiskBadge score={j.ghost_risk} band={j.ghost_band} />
                      )}
                      {app && (
                        cool?.active ? (
                          <span className="inline-flex items-center gap-1 rounded border border-rose-100 bg-rose-50 px-2 py-0.5 text-xs font-bold text-rose-700">
                            <Hourglass className="h-3 w-3" /> Reapply in {cool.daysLeft}d
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded border border-teal-100 bg-teal-50 px-2 py-0.5 text-xs font-bold text-teal-700">
                            <ListChecks className="h-3 w-3" /> In pipeline · {STATUS_LABEL[app.status] ?? app.status}
                          </span>
                        )
                      )}
                    </div>
                  </div>
                </div>
                <div className="hidden items-center text-brand-600 opacity-0 transition-opacity group-hover:opacity-100 sm:flex">
                  <span className="text-sm font-medium mr-1">View Details</span>
                  <ChevronRight className="w-5 h-5" />
                </div>
              </div>
            </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

function AddJobForm({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const refetch = useJobsStore((s) => s.fetch);
  const [f, setF] = useState({
    title: '', company_name: '', location: '', remote: false,
    apply_url: '', salary_min: '', salary_max: '', description: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  function set<K extends keyof typeof f>(k: K, v: (typeof f)[K]) { setF((s) => ({ ...s, [k]: v })); }

  const canSave = f.title.trim() && f.company_name.trim() && !saving;

  async function submit() {
    if (!canSave) return;
    setSaving(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        title: f.title.trim(),
        company_name: f.company_name.trim(),
        location: f.location.trim(),
        remote: f.remote,
        apply_url: f.apply_url.trim(),
        description: f.description.trim(),
      };
      if (f.salary_min) payload.salary_min = Number(f.salary_min);
      if (f.salary_max) payload.salary_max = Number(f.salary_max);
      const created = await Jobs.create(payload);
      await refetch().catch(() => undefined);
      onClose();
      navigate(`/jobs/${created.id}`);
    } catch (e) {
      const detail = (e as { response?: { data?: Record<string, string[]> } })?.response?.data;
      const first = detail && Object.values(detail)[0];
      setError(Array.isArray(first) ? first[0] : 'Could not add the job. Check the fields and try again.');
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/50 p-4 pt-12 sm:pt-20" onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-2xl sm:p-6" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-black tracking-tight text-slate-900">Add a job</h2>
            <p className="text-xs font-semibold text-slate-500">Found a role elsewhere? Add it to track, tailor and prep for it.</p>
          </div>
          <button onClick={onClose} className="grid h-9 w-9 place-items-center rounded-xl text-slate-400 hover:bg-slate-100 hover:text-slate-600" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-3">
          <Field label="Job title" required value={f.title} onChange={(v) => set('title', v)} placeholder="Senior Backend Engineer" />
          <Field label="Company" required value={f.company_name} onChange={(v) => set('company_name', v)} placeholder="Acme Robotics" />
          <div className="grid grid-cols-2 gap-3">
            <Field label="Location" value={f.location} onChange={(v) => set('location', v)} placeholder="Remote / SF" />
            <label className="flex items-end gap-2 pb-2">
              <input type="checkbox" checked={f.remote} onChange={(e) => set('remote', e.target.checked)} className="h-4 w-4 rounded border-slate-300" />
              <span className="text-sm font-bold text-slate-600">Remote</span>
            </label>
          </div>
          <Field label="Apply URL" value={f.apply_url} onChange={(v) => set('apply_url', v)} placeholder="https://…" />
          <div className="grid grid-cols-2 gap-3">
            <Field label="Salary min" type="number" value={f.salary_min} onChange={(v) => set('salary_min', v)} placeholder="120000" />
            <Field label="Salary max" type="number" value={f.salary_max} onChange={(v) => set('salary_max', v)} placeholder="160000" />
          </div>
          <label className="block">
            <span className="block text-xs font-bold uppercase text-slate-500">Description</span>
            <textarea value={f.description} onChange={(e) => set('description', e.target.value)} rows={4} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none" placeholder="Paste the job description — it powers match scoring and tailoring." />
          </label>
        </div>

        {error && <p className="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-sm font-bold text-rose-700">{error}</p>}

        <div className="mt-4 flex gap-2">
          <button onClick={submit} disabled={!canSave} className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-black text-white shadow-[0_4px_0_#2dd4bf] transition hover:bg-slate-800 disabled:opacity-50 disabled:shadow-none">
            {saving ? 'Adding…' : 'Add job'}
          </button>
          <button onClick={onClose} className="rounded-xl bg-slate-100 px-4 py-2 text-sm font-black text-slate-600 hover:bg-slate-200">Cancel</button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, placeholder, type = 'text', required = false }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string; required?: boolean }) {
  return (
    <label className="block">
      <span className="block text-xs font-bold uppercase text-slate-500">{label}{required && <span className="text-teal-600"> *</span>}</span>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none" />
    </label>
  );
}
