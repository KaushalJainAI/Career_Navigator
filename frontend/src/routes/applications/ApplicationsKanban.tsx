import { useEffect } from 'react';
import { useApplicationsStore } from '../../stores/useApplicationsStore';

const COLUMNS = ['saved', 'tailored', 'ready', 'applied', 'phone', 'onsite', 'offer', 'rejected'];

export function ApplicationsKanban() {
  const { applications, fetch, setStatus } = useApplicationsStore();
  useEffect(() => { fetch(); }, [fetch]);
  return (
    <section>
      <h1 className="text-xl font-semibold mb-4">Applications</h1>
      <div className="grid grid-cols-4 gap-3">
        {COLUMNS.map((col) => (
          <div key={col} className="bg-slate-100 rounded p-2">
            <h3 className="text-sm font-medium uppercase text-slate-600 mb-2">{col}</h3>
            <ul className="space-y-2">
              {applications.filter((a) => a.status === col).map((a) => (
                <li key={a.id} className="bg-white p-2 rounded shadow-sm">
                  <div className="text-sm">Job #{a.job}</div>
                  <div className="text-xs text-slate-500">{a.tier_used}</div>
                  <select
                    className="text-xs mt-1"
                    value={a.status}
                    onChange={(e) => setStatus(a.id, e.target.value)}
                  >
                    {COLUMNS.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
