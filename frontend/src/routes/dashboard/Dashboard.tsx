import { useEffect } from 'react';
import { useJobsStore } from '../../stores/useJobsStore';

export function Dashboard() {
  const { jobs, fetch, loading } = useJobsStore();
  useEffect(() => { fetch({ remote: true }); }, [fetch]);
  return (
    <section>
      <h1 className="text-xl font-semibold mb-4">Today's matches</h1>
      {loading ? 'Loading…' : (
        <ul className="space-y-2">
          {jobs.map((j) => (
            <li key={j.id} className="bg-white p-3 rounded shadow-sm">
              <a href={`/jobs/${j.id}`} className="font-medium">{j.title}</a>
              <div className="text-sm text-slate-500">
                {j.company?.name} · {j.location} {j.remote && '· Remote'}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
