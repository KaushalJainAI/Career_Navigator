import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Building2, Users, Briefcase, Send } from 'lucide-react';
import { Network } from '../../api/endpoints';

interface CompanySummary {
  id: number;
  name: string;
  domain: string;
  careers_url: string;
  ats_type: string;
  contact_count: number;
  job_count: number;
  application_count: number;
}

export function CompaniesPage() {
  const [items, setItems] = useState<CompanySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');

  useEffect(() => {
    Network.companies.list()
      .then((d) => setItems(d.results ?? d))
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  const filtered = q.trim()
    ? items.filter((c) => c.name.toLowerCase().includes(q.trim().toLowerCase()))
    : items;

  return (
    <div className="space-y-4 sm:space-y-6">
      <header>
        <h1 className="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">Companies</h1>
        <p className="text-sm font-semibold text-slate-500 sm:text-base">
          Every company you have a contact, opportunity, or application at — one hub each.
        </p>
      </header>

      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search companies…"
        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold shadow-sm"
      />

      {loading ? (
        <p className="text-sm font-semibold text-slate-400">Loading companies…</p>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
          <Building2 className="mx-auto h-8 w-8 text-slate-300" />
          <p className="mt-2 text-sm font-bold text-slate-600">No companies yet</p>
          <p className="text-xs text-slate-400">Add contacts or apply to jobs and their companies show up here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
          {filtered.map((c) => (
            <Link
              key={c.id}
              to={`/companies/${c.id}`}
              className="group flex flex-col rounded-2xl border border-slate-900/10 bg-white p-3 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg sm:p-5"
            >
              <div className="flex items-center gap-2.5 sm:gap-3">
                <div className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-slate-100 text-base font-black text-slate-700 sm:h-12 sm:w-12 sm:text-xl">
                  {c.name[0] ?? '?'}
                </div>
                <div className="min-w-0">
                  <h2 className="truncate text-sm font-black text-slate-950 group-hover:text-teal-700 sm:text-base">{c.name}</h2>
                  {c.domain && <p className="truncate text-[11px] font-semibold text-slate-400 sm:text-xs">{c.domain}</p>}
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5 text-[11px] font-black sm:mt-4 sm:text-xs">
                <Stat icon={Users} value={c.contact_count} tone="bg-rose-50 text-rose-700" />
                <Stat icon={Briefcase} value={c.job_count} tone="bg-sky-50 text-sky-700" />
                <Stat icon={Send} value={c.application_count} tone="bg-emerald-50 text-emerald-700" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({ icon: Icon, value, tone }: { icon: typeof Users; value: number; tone: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 ${tone}`}>
      <Icon className="h-3 w-3" /> {value}
    </span>
  );
}
