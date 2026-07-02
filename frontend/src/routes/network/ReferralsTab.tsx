import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Gift, ArrowUpRight } from 'lucide-react';
import { Network } from '../../api/endpoints';

interface Referral {
  id: number;
  job: number;
  contact: { name: string; title?: string; company_name?: string };
  score: number;
  reason: string;
  status: string;
  next_action: string;
}

const STATUS_TONE: Record<string, string> = {
  suggested: 'bg-slate-100 text-slate-600',
  contacted: 'bg-sky-100 text-sky-700',
  referred: 'bg-teal-100 text-teal-700',
  declined: 'bg-red-100 text-red-700',
  closed: 'bg-slate-100 text-slate-500',
};

export function ReferralsTab() {
  const [items, setItems] = useState<Referral[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Network.referrals.list()
      .then((d) => setItems(d.results ?? d))
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm font-semibold text-slate-400">Loading referral opportunities…</p>;
  if (items.length === 0) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <Gift className="mx-auto h-8 w-8 text-slate-300" />
        <p className="mt-2 text-sm font-bold text-slate-600">No referral opportunities yet</p>
        <p className="text-xs text-slate-400">Open a job and use “Find referrers” to surface contacts who can refer you.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {items.map((r) => (
        <div key={r.id} className="rounded-2xl bg-white p-4 shadow-sm">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate font-black text-slate-900">{r.contact?.name}</p>
              <p className="truncate text-xs font-semibold text-slate-500">
                {[r.contact?.title, r.contact?.company_name].filter(Boolean).join(' · ')}
              </p>
            </div>
            <span className="flex-shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-black text-amber-700">
              match {r.score}
            </span>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-black capitalize ${STATUS_TONE[r.status] ?? 'bg-slate-100 text-slate-600'}`}>{r.status}</span>
            {r.job ? <Link to={`/jobs/${r.job}`} className="inline-flex items-center gap-1 text-[11px] font-black text-slate-500 hover:text-slate-800">View role <ArrowUpRight className="h-3 w-3" /></Link> : null}
          </div>
          {r.reason && <p className="mt-2 text-xs font-semibold text-slate-500">{r.reason}</p>}
          {r.next_action && <p className="mt-2 text-xs font-bold text-slate-700">→ {r.next_action}</p>}
        </div>
      ))}
    </div>
  );
}
