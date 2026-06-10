import { useEffect } from 'react';
import { useApplicationsStore } from '../../stores/useApplicationsStore';

const COLUMNS = ['saved', 'tailored', 'ready', 'applied', 'phone', 'onsite', 'offer', 'rejected'];

export function ApplicationsKanban() {
  const { applications, fetch, setStatus } = useApplicationsStore();
  useEffect(() => { fetch(); }, [fetch]);
  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-black tracking-tight text-slate-950">Applications</h1>
        <p className="mt-1 text-sm font-semibold text-slate-500">Track each opportunity from saved role to offer.</p>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {COLUMNS.map((col) => {
          const items = applications.filter((a) => a.status === col);
          return (
            <div key={col} className="min-h-28 rounded-2xl bg-slate-100 p-3">
              <div className="mb-3 flex items-center justify-between gap-2">
                <h3 className="text-xs font-black uppercase tracking-wide text-slate-600">{col}</h3>
                <span className="rounded-full bg-white px-2 py-0.5 text-xs font-black text-slate-500">{items.length}</span>
              </div>
              <ul className="space-y-2">
                {items.map((a) => (
                  <li key={a.id} className="rounded-xl bg-white p-3 shadow-sm">
                    <div className="text-sm font-bold text-slate-800">{a.job_detail?.title || `Job #${a.job}`}</div>
                    <div className="mt-1 text-xs font-semibold text-slate-500">
                      {a.job_detail?.company?.name || 'Unknown company'}{a.job_detail?.location ? ` - ${a.job_detail.location}` : ''}
                    </div>
                    <div className="mt-1 text-xs font-semibold text-slate-500">{a.tier_used || 'assist'}</div>
                    <select
                      className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm"
                      value={a.status}
                      onChange={(e) => setStatus(a.id, e.target.value)}
                    >
                      {COLUMNS.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}
