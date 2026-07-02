import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, ArrowUpRight, Briefcase, CheckCircle, Clock, Flame, Radar, Sparkles,
  ShieldAlert, ScanSearch, Wand2, Rocket, BellRing, Mic2, Users, ShieldCheck, FileCheck2, Zap } from 'lucide-react';
import { useJobsStore } from '../../stores/useJobsStore';
import { Applications } from '../../api/endpoints';
import { CreditCost } from '../../components/Credits';
import { useBillingStore } from '../../stores/useBillingStore';

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

  const pipeline = [
    { label: 'Matches', value: stats?.new_matches ?? 0, tone: 'text-teal-200' },
    { label: 'Active', value: stats?.active_applications ?? 0, tone: 'text-sky-200' },
    { label: 'Interviews', value: stats?.interviews_ready ?? 0, tone: 'text-amber-200' },
    { label: 'Offers', value: stats?.offers_received ?? 0, tone: 'text-emerald-200' },
  ];

  return (
    <div className="space-y-8 sm:space-y-12">
      <section className="relative overflow-hidden rounded-[1.5rem] bg-slate-950 p-6 text-white shadow-2xl sm:rounded-[2.25rem] sm:p-10 lg:p-12">
        <div className="career-pulse" />
        <div className="relative grid gap-8 lg:grid-cols-[1.15fr_360px] lg:gap-12">
          <div>
            <div className="mb-4 inline-flex max-w-full items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-bold text-teal-200 sm:mb-6 sm:text-sm">
              <Flame className="h-4 w-4 text-amber-300" />
              <span className="truncate">Your AI-powered job hunt, end to end</span>
            </div>
            <h1 className="max-w-3xl text-[2rem] font-black leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
              Land the offer <span className="text-teal-300">faster</span> — with less busywork.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300 sm:mt-5 sm:text-lg sm:leading-8">
              Career Navigator finds real openings, tailors your resume for each one, files the application, and grills you for the interview — so every session moves you closer to the offer.
            </p>
            <div className="mt-6 grid gap-3 min-[420px]:flex min-[420px]:flex-wrap sm:mt-8">
              <Link to="/jobs" className="inline-flex items-center justify-center gap-2 rounded-2xl bg-teal-300 px-5 py-3 text-sm font-black text-slate-950 shadow-[0_8px_0_#fbbf24] transition hover:-translate-y-0.5 sm:px-6 sm:text-base">
                Find roles
                <ArrowUpRight className="h-5 w-5" />
              </Link>
              <Link to="/interview" className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/15 bg-white/10 px-5 py-3 text-sm font-black text-white transition hover:bg-white/15 sm:px-6 sm:text-base">
                Practice interview
              </Link>
            </div>
            <ul className="mt-6 flex flex-wrap gap-x-4 gap-y-2 text-xs font-bold text-slate-300 sm:mt-8 sm:gap-x-6 sm:text-sm">
              {[
                [ShieldCheck, 'Ghost-job shield'],
                [FileCheck2, 'ATS-safe exports'],
                [Zap, 'Real-time alerts'],
              ].map(([Icon, label]) => (
                <li key={label as string} className="inline-flex items-center gap-2">
                  <Icon className="h-4 w-4 text-teal-300" />
                  {label as string}
                </li>
              ))}
            </ul>
          </div>
          <div className="relative rounded-[1.5rem] border border-white/10 bg-white/[0.07] p-5 backdrop-blur sm:rounded-[1.75rem] sm:p-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black uppercase tracking-wide text-teal-200 sm:text-sm">Your pipeline right now</span>
              <Radar className="h-6 w-6 text-teal-200" />
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3">
              {pipeline.map((p) => (
                <div key={p.label} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className={`text-3xl font-black tracking-tight sm:text-4xl ${p.tone}`}>{stats ? p.value : '-'}</div>
                  <div className="mt-1 text-xs font-bold text-slate-300 sm:text-sm">{p.label}</div>
                </div>
              ))}
            </div>
            <Link to="/applications" className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-white/10 px-4 py-2.5 text-sm font-black text-white transition hover:bg-white/15">
              Open pipeline <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      <HowItWorks />

      <section className="grid animate-stagger grid-cols-2 gap-2.5 sm:gap-4 md:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
              <div key={kpi.label} className="group rounded-2xl border border-slate-900/10 bg-white p-3 shadow-sm transition hover:-translate-y-1 hover:shadow-xl sm:rounded-[1.5rem] sm:p-5">
              <div className={`mb-2.5 grid h-8 w-8 place-items-center rounded-xl sm:mb-5 sm:h-12 sm:w-12 sm:rounded-2xl ${kpi.tone}`}>
                <Icon className="h-4 w-4 sm:h-6 sm:w-6" />
              </div>
              <div className="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">{stats ? kpi.value : '-'}</div>
              <div className="mt-0.5 text-xs font-bold text-slate-500 sm:mt-1 sm:text-sm">{kpi.label}</div>
            </div>
          );
        })}
      </section>

      {analytics && analytics.submitted > 0 && (
        <section className="rounded-[1.25rem] border border-slate-900/10 bg-white p-5 shadow-sm sm:rounded-[1.5rem] sm:p-6" data-testid="response-analytics">
          <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">Response analytics</h2>
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

      <FeatureShowcase />

      <section>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">Today&apos;s strongest matches</h2>
            <p className="text-sm font-semibold text-slate-500 sm:text-base">Start where your odds and energy are highest.</p>
          </div>
          <Link to="/jobs" className="hidden rounded-2xl bg-slate-950 px-4 py-2 text-sm font-black text-white sm:inline-flex">View all</Link>
        </div>

        {loading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3].map((i) => <div key={i} className="h-44 animate-pulse rounded-[1.5rem] bg-white/70" />)}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2.5 sm:gap-4 md:grid-cols-2 xl:grid-cols-3">
            {jobs.slice(0, 6).map((j, index) => (
              <Link key={j.id} to={`/jobs/${j.id}`} className="group relative overflow-hidden rounded-2xl border border-slate-900/10 bg-white p-3 shadow-sm transition hover:-translate-y-1 hover:shadow-xl sm:rounded-[1.5rem] sm:p-5">
                <div className="absolute right-2 top-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-black text-amber-800 sm:right-4 sm:top-4 sm:px-3 sm:py-1 sm:text-xs">
                  #{index + 1}
                </div>
                <div className="grid h-9 w-9 place-items-center rounded-xl bg-slate-100 text-base font-black text-slate-700 sm:h-12 sm:w-12 sm:rounded-2xl sm:text-xl">
                  {j.company?.name?.[0] || '?'}
                </div>
                <h3 className="mt-3 line-clamp-2 pr-6 text-sm font-black text-slate-950 group-hover:text-teal-700 sm:mt-5 sm:line-clamp-none sm:pr-16 sm:text-lg">{j.title}</h3>
                <div className="mt-1 truncate text-xs font-semibold text-slate-500 sm:mt-2 sm:text-sm">{j.company?.name} · {j.location}</div>
                <div className="mt-3 flex items-center justify-between gap-2 sm:mt-5">
                  <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2 py-0.5 text-[10px] font-black text-teal-700 sm:gap-2 sm:px-3 sm:py-1 sm:text-xs">
                    <Sparkles className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                    {j.remote ? 'Remote' : 'Good fit'}
                  </span>
                  <ArrowUpRight className="hidden h-5 w-5 text-slate-400 transition group-hover:text-teal-700 sm:block" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function HowItWorks() {
  const steps = [
    {
      icon: ScanSearch, tone: 'bg-sky-100 text-sky-700',
      title: 'Find roles worth chasing',
      blurb: 'We pull fresh openings, score each against your profile, and flag ghost jobs — so you only spend energy where it counts.',
    },
    {
      icon: Wand2, tone: 'bg-violet-100 text-violet-700',
      title: 'Apply in minutes, not hours',
      blurb: 'AI tailors your resume per job with a truthfulness check, exports ATS-safe files, then prepares the application for one-tap approval.',
    },
    {
      icon: Mic2, tone: 'bg-teal-100 text-teal-700',
      title: 'Walk into interviews ready',
      blurb: 'Rehearse with a company-specific grill agent scored on a STAR rubric, and get a study plan for exactly the gaps that matter.',
    },
  ];
  return (
    <section>
      <div className="mb-5 sm:mb-6">
        <span className="text-xs font-black uppercase tracking-wide text-teal-700 sm:text-sm">How it works</span>
        <h2 className="mt-1 text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">Three steps from lead to offer</h2>
      </div>
      <div className="grid animate-stagger gap-4 md:grid-cols-3">
        {steps.map((s, i) => {
          const Icon = s.icon;
          return (
            <div key={s.title} className="relative rounded-[1.25rem] border border-slate-900/10 bg-white p-5 shadow-sm sm:rounded-[1.5rem] sm:p-6">
              <div className="flex items-center gap-3">
                <div className={`grid h-11 w-11 place-items-center rounded-2xl sm:h-12 sm:w-12 ${s.tone}`}>
                  <Icon className="h-6 w-6" />
                </div>
                <span className="text-4xl font-black tracking-tighter text-slate-200 sm:text-5xl">{i + 1}</span>
              </div>
              <h3 className="mt-4 text-lg font-black tracking-tight text-slate-950 sm:text-xl">{s.title}</h3>
              <p className="mt-1.5 text-sm font-semibold leading-6 text-slate-500">{s.blurb}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function FeatureShowcase() {
  const cost = useBillingStore((s) => s.costByReason);
  const features = [
    {
      icon: ShieldAlert, to: '/jobs', tone: 'bg-rose-100 text-rose-700',
      title: 'Ghost-Job Shield',
      blurb: 'Every posting gets a ghost-risk score from repost patterns, staleness and missing salary — so you stop wasting applications on jobs that were never real.',
      badge: 'On every job',
    },
    {
      icon: ScanSearch, to: '/jobs', tone: 'bg-sky-100 text-sky-700',
      title: 'Explainable match scores',
      blurb: 'See exactly which skills matched and which are missing — not just a number — with reasons you can act on before you apply.',
      badge: 'Free',
    },
    {
      icon: Wand2, to: '/applications', tone: 'bg-violet-100 text-violet-700',
      title: 'Tailored resume + ATS export',
      blurb: 'AI rewrites your resume for each job with a truthfulness check, then exports a clean, single-column ATS-safe .txt or .docx.',
      cost: cost.tailor_resume,
    },
    {
      icon: Rocket, to: '/applications', tone: 'bg-amber-100 text-amber-700',
      title: 'Tiered auto-apply',
      blurb: 'Assist, autofill, or fully autonomous — the agent prepares everything and always pauses for your one-tap approval before submitting.',
      cost: cost.autonomous_apply,
    },
    {
      icon: Mic2, to: '/interview', tone: 'bg-teal-100 text-teal-700',
      title: 'Interview Grill Agent',
      blurb: 'Company-researched question banks and a live grilling round scored against a STAR rubric, ending in a personalised study plan.',
      cost: cost.mock_interview,
    },
    {
      icon: Users, to: '/connections', tone: 'bg-rose-100 text-rose-700',
      title: 'Referrals & outreach',
      blurb: 'Track contacts, get referral suggestions per job, draft outreach messages, and work a prioritised list of next actions.',
      badge: 'Free',
    },
    {
      icon: BellRing, to: '/settings', tone: 'bg-emerald-100 text-emerald-700',
      title: 'Real-time job alerts',
      blurb: 'Save a search once and get pinged — in-app, email, or browser push — the moment a matching role appears. Even when the tab is closed.',
      badge: 'Free',
    },
  ];

  return (
    <section>
      <div className="mb-5 sm:mb-6">
        <span className="text-xs font-black uppercase tracking-wide text-teal-700 sm:text-sm">Everything in one place</span>
        <h2 className="mt-1 text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">Your whole job hunt, handled</h2>
        <p className="mt-1 text-sm font-semibold text-slate-500 sm:text-base">Reading &amp; matching is always free — AI actions spend a few credits.</p>
      </div>
      <div className="grid animate-stagger grid-cols-2 gap-2.5 sm:gap-4 md:grid-cols-2 xl:grid-cols-3">
        {features.map((f) => {
          const Icon = f.icon;
          return (
            <Link key={f.title} to={f.to} className="group flex flex-col rounded-2xl border border-slate-900/10 bg-white p-3 shadow-sm transition hover:-translate-y-1 hover:shadow-xl sm:rounded-[1.25rem] sm:p-5">
              <div className="flex items-center justify-between gap-1">
                <div className={`grid h-8 w-8 place-items-center rounded-xl sm:h-11 sm:w-11 sm:rounded-2xl ${f.tone}`}>
                  <Icon className="h-4 w-4 sm:h-6 sm:w-6" />
                </div>
                {f.cost ? <CreditCost cost={f.cost} /> : (
                  <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-black text-slate-500 sm:px-2 sm:text-[11px]">{f.badge}</span>
                )}
              </div>
              <h3 className="mt-2.5 text-sm font-black leading-tight text-slate-950 group-hover:text-teal-700 sm:mt-4 sm:text-base">{f.title}</h3>
              <p className="mt-1 hidden flex-1 text-sm font-semibold leading-6 text-slate-500 sm:block">{f.blurb}</p>
              <span className="mt-3 hidden items-center gap-1 text-sm font-black text-slate-900 sm:inline-flex">
                Open <ArrowUpRight className="h-4 w-4 text-slate-400 transition group-hover:text-teal-700" />
              </span>
            </Link>
          );
        })}
      </div>
    </section>
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
