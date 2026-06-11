import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, ArrowUpRight, Briefcase, CheckCircle, Clock, Flame, Radar, Sparkles } from 'lucide-react';
import { useJobsStore } from '../../stores/useJobsStore';
import { Applications } from '../../api/endpoints';

interface DashboardStats {
  active_applications: number;
  new_matches: number;
  interviews_ready: number;
  offers_received: number;
}

interface ResponseAnalytics {
  submitted: number;
  responses: number;
  offers: number;
  response_rate: number;
  funnel: { applied: number; phone: number; onsite: number; offer: number };
  avg_days_to_first_response: number | null;
}

export function Dashboard() {
  const { jobs, fetch, loading } = useJobsStore();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [analytics, setAnalytics] = useState<ResponseAnalytics | null>(null);
  useEffect(() => { fetch({ remote: true }); }, [fetch]);
  useEffect(() => {
    Applications.stats().then(setStats).catch(() => undefined);
    Applications.analytics().then(setAnalytics).catch(() => undefined);
  }, []);

  const kpis = [
    { label: 'Active Applications', value: stats?.active_applications ?? 0, icon: Activity, tone: 'bg-sky-100 text-sky-700' },
    { label: 'New Matches', value: stats?.new_matches ?? 0, icon: Briefcase, tone: 'bg-teal-100 text-teal-700' },
    { label: 'Interviews Ready', value: stats?.interviews_ready ?? 0, icon: Clock, tone: 'bg-amber-100 text-amber-700' },
    { label: 'Offers Received', value: stats?.offers_received ?? 0, icon: CheckCircle, tone: 'bg-emerald-100 text-emerald-700' },
  ];

  return (
    <div className="space-y-6 sm:space-y-8">
      <section className="relative overflow-hidden rounded-[1.5rem] bg-slate-950 p-5 text-white shadow-2xl sm:rounded-[2rem] sm:p-9">
        <div className="career-pulse" />
        <div className="relative grid gap-8 lg:grid-cols-[1fr_340px]">
          <div>
            <div className="mb-4 inline-flex max-w-full items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm font-bold text-teal-200 sm:mb-5">
              <Flame className="h-4 w-4 text-amber-300" />
              <span className="truncate">Keep the streak alive</span>
            </div>
            <h1 className="max-w-3xl text-3xl font-black leading-tight tracking-tight sm:text-5xl">
              One focused session today can move you closer to the offer.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg sm:leading-8">
              Review the strongest matches, apply with tailored materials, then rehearse the interview while your context is fresh.
            </p>
            <div className="mt-6 grid gap-3 min-[420px]:flex min-[420px]:flex-wrap sm:mt-7">
              <Link to="/jobs" className="inline-flex items-center justify-center gap-2 rounded-2xl bg-teal-300 px-5 py-3 font-black text-slate-950 shadow-[0_8px_0_#fbbf24] transition hover:-translate-y-0.5">
                Find roles
                <ArrowUpRight className="h-5 w-5" />
              </Link>
              <Link to="/interview" className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/15 bg-white/10 px-5 py-3 font-black text-white hover:bg-white/15">
                Practice interview
              </Link>
            </div>
          </div>
          <div className="relative min-h-56 rounded-[1.5rem] border border-white/10 bg-white/8 p-5 sm:min-h-64 sm:rounded-[1.75rem]">
            <Radar className="absolute right-5 top-5 h-7 w-7 text-teal-200" />
            <div className="mt-10 grid aspect-square place-items-center rounded-full border border-teal-200/30 bg-teal-300/10">
              <div className="grid h-32 w-32 place-items-center rounded-full border border-amber-300/40 bg-amber-300/10 sm:h-40 sm:w-40">
                <div className="text-center">
                  <div className="text-4xl font-black sm:text-5xl">68%</div>
                  <div className="text-sm font-bold text-slate-300">match momentum</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
              <div key={kpi.label} className="group rounded-[1.25rem] border border-slate-900/10 bg-white p-4 shadow-sm transition hover:-translate-y-1 hover:shadow-xl sm:rounded-[1.5rem] sm:p-5">
              <div className={`mb-4 grid h-11 w-11 place-items-center rounded-2xl sm:mb-5 sm:h-12 sm:w-12 ${kpi.tone}`}>
                <Icon className="h-6 w-6" />
              </div>
              <div className="text-3xl font-black tracking-tight text-slate-950">{stats ? kpi.value : '-'}</div>
              <div className="mt-1 text-sm font-bold text-slate-500">{kpi.label}</div>
            </div>
          );
        })}
      </section>

      {analytics && analytics.submitted > 0 && (
        <section className="rounded-[1.25rem] border border-slate-900/10 bg-white p-5 shadow-sm sm:rounded-[1.5rem] sm:p-6" data-testid="response-analytics">
          <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-xl font-black tracking-tight text-slate-950 sm:text-2xl">Response analytics</h2>
            <span className="text-sm font-bold text-slate-500">
              {analytics.avg_days_to_first_response != null
                ? `Avg ${analytics.avg_days_to_first_response} days to first response`
                : 'No responses yet'}
            </span>
          </div>
          <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Submitted" value={analytics.submitted} />
            <Stat label="Responses" value={analytics.responses} />
            <Stat label="Offers" value={analytics.offers} />
            <Stat label="Response rate" value={`${Math.round(analytics.response_rate * 100)}%`} />
          </div>
          <div className="flex items-end gap-2">
            {([
              ['Applied', analytics.funnel.applied],
              ['Phone', analytics.funnel.phone],
              ['Onsite', analytics.funnel.onsite],
              ['Offer', analytics.funnel.offer],
            ] as const).map(([label, count]) => {
              const pct = analytics.funnel.applied
                ? Math.round((count / analytics.funnel.applied) * 100)
                : 0;
              return (
                <div key={label} className="flex-1 text-center">
                  <div className="flex h-24 items-end justify-center">
                    <div
                      className="w-full rounded-t-lg bg-teal-500/80"
                      style={{ height: `${Math.max(pct, 4)}%` }}
                      data-testid={`funnel-${label.toLowerCase()}`}
                    />
                  </div>
                  <div className="mt-2 text-sm font-black text-slate-900">{count}</div>
                  <div className="text-xs font-bold text-slate-500">{label}</div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      <section>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-black tracking-tight text-slate-950 sm:text-2xl">Today&apos;s strongest matches</h2>
            <p className="text-sm font-semibold text-slate-500">Start where your odds and energy are highest.</p>
          </div>
          <Link to="/jobs" className="hidden rounded-2xl bg-slate-950 px-4 py-2 text-sm font-black text-white sm:inline-flex">View all</Link>
        </div>

        {loading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3].map((i) => <div key={i} className="h-44 animate-pulse rounded-[1.5rem] bg-white/70" />)}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {jobs.slice(0, 6).map((j, index) => (
              <Link key={j.id} to={`/jobs/${j.id}`} className="group relative overflow-hidden rounded-[1.25rem] border border-slate-900/10 bg-white p-4 shadow-sm transition hover:-translate-y-1 hover:shadow-xl sm:rounded-[1.5rem] sm:p-5">
                <div className="absolute right-3 top-3 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-black text-amber-800 sm:right-4 sm:top-4 sm:px-3">
                  #{index + 1} fit
                </div>
                <div className="grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-xl font-black text-slate-700">
                  {j.company?.name?.[0] || '?'}
                </div>
                <h3 className="mt-5 pr-14 text-base font-black text-slate-950 group-hover:text-teal-700 sm:pr-16 sm:text-lg">{j.title}</h3>
                <div className="mt-2 text-sm font-semibold text-slate-500">{j.company?.name} - {j.location}</div>
                <div className="mt-5 flex items-center justify-between gap-3">
                  <span className="inline-flex items-center gap-2 rounded-full bg-teal-50 px-3 py-1 text-xs font-black text-teal-700">
                    <Sparkles className="h-3.5 w-3.5" />
                    {j.remote ? 'Remote ready' : 'Strong profile fit'}
                  </span>
                  <ArrowUpRight className="h-5 w-5 text-slate-400 transition group-hover:text-teal-700" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <div className="text-2xl font-black tracking-tight text-slate-950">{value}</div>
      <div className="mt-0.5 text-xs font-bold text-slate-500">{label}</div>
    </div>
  );
}
