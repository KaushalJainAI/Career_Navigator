import { useEffect, useState } from 'react';
import { useJobsStore } from '../../stores/useJobsStore';
import { Link } from 'react-router-dom';

export function JobsList() {
  const { jobs, fetch, loading } = useJobsStore();
  const [q, setQ] = useState('');
  useEffect(() => { fetch(); }, [fetch]);
  return (
    <section>
      <input className="border p-2 rounded w-full mb-4" placeholder="Search jobs…"
             value={q} onChange={(e) => { setQ(e.target.value); fetch({ search: e.target.value }); }} />
      {loading ? 'Loading…' : (
        <ul className="space-y-2">
          {jobs.map((j) => (
            <li key={j.id} className="bg-white p-3 rounded shadow-sm flex justify-between">
              <div>
                <Link to={`/jobs/${j.id}`} className="font-medium">{j.title}</Link>
                <div className="text-sm text-slate-500">{j.company?.name} · {j.location}</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
