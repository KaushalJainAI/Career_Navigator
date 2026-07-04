import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bookmark, Plus, Search, X, Trash2, ArrowUpRight } from 'lucide-react';
import { useApplicationsStore } from '../../stores/useApplicationsStore';
import { Jobs } from '../../api/endpoints';

interface JobOption { id: number; title: string; company?: { name?: string }; location?: string }

function salaryLabel(lo?: number | null, hi?: number | null): string | null {
  if (!lo && !hi) return null;
  const k = (n?: number | null) => (n ? `$${Math.round(n / 1000)}k` : '');
  return [k(lo), k(hi)].filter(Boolean).join('–');
}

/** Dashboard "Saved jobs" — the roles the user has parked to act on later, with
 *  a quick way to add another straight from the dashboard. */
export function SavedJobs() {
  const { applications, fetch, create, remove } = useApplicationsStore();
  const [adding, setAdding] = useState(false);

  useEffect(() => { fetch(); }, [fetch]);

  const saved = applications.filter((a) => a.status === 'saved');
  const existingJobIds = useMemo(() => new Set(applications.map((a) => a.job)), [applications]);

  return (
    <section>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">
            <Bookmark className="h-6 w-6 text-teal-600" /> Saved jobs
          </h2>
          <p className="text-sm font-semibold text-slate-500 sm:text-base">Roles you&apos;ve parked to tailor and apply to.</p>
        </div>
        <button
          onClick={() => setAdding((v) => !v)}
          className="inline-flex items-center gap-1.5 rounded-2xl bg-slate-950 px-4 py-2 text-sm font-black text-white transition hover:bg-slate-800"
        >
          <Plus className="h-4 w-4" /> Add job
        </button>
      </div>

      {adding && (
        <div className="mb-4">
          <AddSavedJob existingJobIds={existingJobIds} onAdd={(id) => create(id, undefined, 'saved')} onClose={() => setAdding(false)} />
        </div>
      )}

      {saved.length === 0 ? (
        <div className="rounded-[1.25rem] border border-dashed border-slate-300 bg-white/60 p-8 text-center sm:rounded-[1.5rem]">
          <Bookmark className="mx-auto h-8 w-8 text-slate-300" />
          <p className="mt-2 text-sm font-black text-slate-700">No saved jobs yet</p>
          <p className="text-xs font-semibold text-slate-500">Add one above, or save roles from Discover below.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2.5 sm:gap-4 md:grid-cols-2 xl:grid-cols-3">
          {saved.map((a) => {
            const salary = salaryLabel(a.job_detail?.salary_min, a.job_detail?.salary_max);
            return (
              <div key={a.id} className="group relative overflow-hidden rounded-2xl border border-slate-900/10 bg-white p-3 shadow-sm transition hover:-translate-y-1 hover:shadow-xl sm:rounded-[1.5rem] sm:p-5">
                <button
                  onClick={() => { if (window.confirm('Remove this saved job?')) remove(a.id); }}
                  className="absolute right-2 top-2 grid h-7 w-7 place-items-center rounded-full bg-slate-100 text-slate-400 opacity-0 transition hover:bg-rose-100 hover:text-rose-600 group-hover:opacity-100"
                  aria-label="Remove saved job"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
                <Link to={`/jobs/${a.job}`} className="block">
                  <div className="grid h-9 w-9 place-items-center rounded-xl bg-slate-100 text-base font-black text-slate-700 sm:h-12 sm:w-12 sm:rounded-2xl sm:text-xl">
                    {a.job_detail?.company?.name?.[0] || '?'}
                  </div>
                  <h3 className="mt-3 line-clamp-2 pr-6 text-sm font-black text-slate-950 group-hover:text-teal-700 sm:mt-4 sm:text-lg">
                    {a.job_detail?.title || `Job #${a.job}`}
                  </h3>
                  <div className="mt-1 truncate text-xs font-semibold text-slate-500 sm:text-sm">
                    {a.job_detail?.company?.name || 'Unknown'}{a.job_detail?.location ? ` · ${a.job_detail.location}` : ''}
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-2 sm:mt-4">
                    {salary ? (
                      <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-black text-emerald-700 sm:text-xs">{salary}</span>
                    ) : <span />}
                    <ArrowUpRight className="hidden h-5 w-5 text-slate-400 transition group-hover:text-teal-700 sm:block" />
                  </div>
                </Link>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function AddSavedJob({
  existingJobIds, onAdd, onClose,
}: {
  existingJobIds: Set<number>;
  onAdd: (jobId: number) => Promise<unknown>;
  onClose: () => void;
}) {
  const [q, setQ] = useState('');
  const [jobs, setJobs] = useState<JobOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    Jobs.list(q ? { search: q } : {})
      .then((data: { results?: JobOption[] } | JobOption[]) => setJobs(Array.isArray(data) ? data : data.results ?? []))
      .catch(() => setJobs([]))
      .finally(() => setLoading(false));
  }, [q]);

  const options = jobs.filter((j) => !existingJobIds.has(j.id)).slice(0, 8);

  async function pick(id: number) {
    setBusy(id);
    try { await onAdd(id); onClose(); } finally { setBusy(null); }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            autoFocus
            className="w-full rounded-xl border border-slate-200 py-2 pl-9 pr-3 text-sm"
            placeholder="Search jobs to save…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <button onClick={onClose} className="grid h-9 w-9 place-items-center rounded-xl text-slate-400 hover:bg-slate-100 hover:text-slate-600" aria-label="Close">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-2 max-h-64 space-y-1 overflow-auto">
        {loading && <p className="px-2 py-2 text-xs font-semibold text-slate-400">Loading…</p>}
        {!loading && options.length === 0 && (
          <p className="px-2 py-2 text-xs font-semibold text-slate-400">No matching jobs. Try a different search, or browse Discover below.</p>
        )}
        {options.map((j) => (
          <button
            key={j.id}
            onClick={() => pick(j.id)}
            disabled={busy != null}
            className="flex w-full items-center justify-between gap-2 rounded-xl px-2.5 py-2 text-left transition hover:bg-slate-50 disabled:opacity-60"
          >
            <span className="min-w-0">
              <span className="block truncate text-sm font-bold text-slate-800">{j.title}</span>
              <span className="block truncate text-xs font-semibold text-slate-500">
                {j.company?.name || 'Unknown'}{j.location ? ` · ${j.location}` : ''}
              </span>
            </span>
            {busy === j.id
              ? <span className="text-xs font-black text-teal-600">Saving…</span>
              : <Plus className="h-4 w-4 flex-shrink-0 text-slate-400" />}
          </button>
        ))}
      </div>
    </div>
  );
}
