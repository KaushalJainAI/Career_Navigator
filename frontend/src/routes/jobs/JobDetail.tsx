import { Link, useParams } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';
import {
  CheckCircle2, ExternalLink, ShieldCheck, MapPin, Banknote, Clock,
  Building2, Sparkles, XCircle, CalendarDays, Globe2, Hourglass, ListChecks,
} from 'lucide-react';
import { Jobs, Applications, Tailoring } from '../../api/endpoints';
import { GhostRiskBadge, type GhostBand } from '../../components/GhostRiskBadge';
import { CreditCost, CreditWall, insufficientCredits, type CreditShortfall } from '../../components/Credits';
import { useBillingStore } from '../../stores/useBillingStore';
import { useApplicationsStore } from '../../stores/useApplicationsStore';
import { rejectionCooldown } from '../../lib/cooldown';

const STATUS_LABEL: Record<string, string> = {
  saved: 'Saved', tailored: 'Tailored', ready: 'Ready to apply', applied: 'Applied',
  phone: 'Phone screen', onsite: 'Onsite', offer: 'Offer', rejected: 'Rejected', withdrawn: 'Withdrawn',
};

interface Job {
  id: number;
  title: string;
  description: string;
  apply_url: string;
  company: { name: string; domain?: string };
  ghost_risk?: number;
  ghost_band?: GhostBand;
  ghost_reasons?: string[];
  location?: string;
  remote?: boolean;
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  posted_at?: string;
  // AI-generated, cached on the posting. Absent until someone generates it.
  ai_breakdown?: {
    responsibilities?: string[];
    requirements?: string[];
    benefits?: string[];
    about_company?: string;
    model?: string;
  };
}

interface MatchReason {
  kind: 'positive' | 'negative' | 'neutral';
  title: string;
  detail: string;
}

interface Match {
  score: number;
  breakdown: Record<string, number>;
  gaps: string[];
  matched_skills?: string[];
  explanation?: MatchReason[];
}

type ApplyTier = 'assist' | 'autofill' | 'autonomous';

interface PreparedApplication {
  tier: ApplyTier;
  status: string;
  apply_url: string;
  approval_token?: string;
  next_actions: string[];
  application: { id: number };
}

interface GeneratedMaterials {
  resume?: { id: number; content: { raw_text?: string; summary?: string } };
  coverLetter?: { id: number; content: string };
}

function money(n?: number, currency = 'USD') {
  if (!n) return null;
  const sym = currency === 'USD' ? '$' : currency === 'INR' ? '₹' : currency === 'EUR' ? '€' : '';
  return `${sym}${(n / 1000).toFixed(0)}k`;
}

function timeAgo(iso?: string) {
  if (!iso) return null;
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days}d ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

/** Strip HTML to a rough plain-text length check so we know if the description
 *  is too thin to show on its own. */
function textLength(html: string) {
  return html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().length;
}

/** Signature card: hard black border + teal offset shadow, echoing the logo /
 *  active-nav treatment used across the app. */
const CARD = 'rounded-3xl border-2 border-slate-900 bg-white shadow-[6px_6px_0_#0f172a]';

/** Editorial section header with a teal accent bar and a mono index. */
function SectionHead({ index, title }: { index: string; title: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="h-6 w-1.5 flex-shrink-0 rounded-full bg-teal-400" />
      <span className="font-mono text-xs font-black tracking-widest text-teal-600">{index}</span>
      <h2 className="text-lg font-black tracking-tight text-slate-900">{title}</h2>
    </div>
  );
}

/** SVG ring gauge for the match score — the page's visual centrepiece. */
function MatchRing({ pct }: { pct: number }) {
  const r = 46;
  const c = 2 * Math.PI * r;
  const off = c * (1 - pct / 100);
  const color = pct >= 75 ? '#2dd4bf' : pct >= 50 ? '#fbbf24' : '#f87171';
  return (
    <div className="relative grid flex-shrink-0 place-items-center">
      <svg width="118" height="118" viewBox="0 0 120 120" className="-rotate-90">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#1e293b" strokeWidth="9" />
        <circle cx="60" cy="60" r={r} fill="none" stroke={color} strokeWidth="9" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off} />
      </svg>
      <div className="absolute text-center">
        <div className="text-3xl font-black leading-none text-white">{pct}%</div>
        <div className="mt-1 font-mono text-[10px] font-black uppercase tracking-widest text-teal-300">Match</div>
      </div>
    </div>
  );
}

function Fact({ icon: Icon, label, value }: { icon: typeof MapPin; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3 border-b border-dashed border-slate-200 pb-3 last:border-0 last:pb-0">
      <span className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-slate-900 text-teal-300">
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0">
        <p className="font-mono text-[10px] font-black uppercase tracking-widest text-slate-400">{label}</p>
        <p className="truncate text-sm font-bold text-slate-800">{value}</p>
      </div>
    </div>
  );
}

function ListBlock({ index, title, items, numbered }: { index: string; title: string; items: string[]; numbered?: boolean }) {
  return (
    <section className={`${CARD} p-6`}>
      <SectionHead index={index} title={title} />
      <ul className="mt-4 space-y-3">
        {items.map((it, i) => (
          <li key={it} className="flex gap-3 text-sm leading-6 text-slate-700">
            {numbered ? (
              <span className="mt-0.5 grid h-5 w-5 flex-shrink-0 place-items-center rounded-md bg-teal-50 font-mono text-[11px] font-black text-teal-700">{i + 1}</span>
            ) : (
              <span className="mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-slate-400" />
            )}
            <span>{it}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function JobDetail() {
  const { id } = useParams();
  const jobId = Number(id);
  const [job, setJob] = useState<Job | null>(null);
  const [match, setMatch] = useState<Match | null>(null);
  const [prepared, setPrepared] = useState<PreparedApplication | null>(null);
  const [busyTier, setBusyTier] = useState<ApplyTier | null>(null);
  const [materials, setMaterials] = useState<GeneratedMaterials>({});
  const [materialsBusy, setMaterialsBusy] = useState(false);
  const [breakdownBusy, setBreakdownBusy] = useState(false);
  const [breakdownError, setBreakdownError] = useState<string | null>(null);
  const [creditWall, setCreditWall] = useState<CreditShortfall | null>(null);
  const cost = useBillingStore((s) => s.costByReason);
  const refreshBalance = useBillingStore((s) => s.refresh);
  const applications = useApplicationsStore((s) => s.applications);
  const fetchApps = useApplicationsStore((s) => s.fetch);

  useEffect(() => {
    Jobs.detail(jobId).then(setJob);
    Jobs.match(jobId).then(setMatch).catch(() => undefined);
    fetchApps().catch(() => undefined);
  }, [jobId, fetchApps]);

  // Association: does this job already sit in the user's pipeline?
  const myApp = useMemo(() => applications.find((a) => a.job === jobId), [applications, jobId]);
  const cool = myApp ? rejectionCooldown(myApp) : null;
  const applyLocked = !!cool?.active;

  async function apply(tier: ApplyTier) {
    if (applyLocked) return;
    setBusyTier(tier);
    setCreditWall(null);
    try {
      const result = await Applications.prepare(jobId, tier);
      setPrepared(result);
      setMaterials({});
      fetchApps().catch(() => undefined);
      if (tier === 'autonomous') refreshBalance();
    } catch (e) {
      const short = insufficientCredits(e);
      if (short) setCreditWall(short);
    } finally {
      setBusyTier(null);
    }
  }

  async function generateMaterials() {
    if (!prepared) return;
    setMaterialsBusy(true);
    setCreditWall(null);
    try {
      const [resume, coverLetter] = await Promise.all([
        Tailoring.resume(prepared.application.id),
        Tailoring.coverLetter(prepared.application.id),
      ]);
      setMaterials({ resume, coverLetter });
      refreshBalance();
    } catch (e) {
      const short = insufficientCredits(e);
      if (short) setCreditWall(short);
    } finally {
      setMaterialsBusy(false);
    }
  }

  async function generateBreakdown() {
    if (!job) return;
    setBreakdownBusy(true);
    setBreakdownError(null);
    setCreditWall(null);
    try {
      const data = await Jobs.breakdown(job.id);
      setJob((prev) => (prev ? { ...prev, ai_breakdown: data } : prev));
      refreshBalance();
    } catch (e) {
      const short = insufficientCredits(e);
      if (short) setCreditWall(short);
      else setBreakdownError("Couldn't generate a breakdown for this posting. Please try again.");
    } finally {
      setBreakdownBusy(false);
    }
  }

  async function downloadResume(fmt: 'txt' | 'docx') {
    if (!prepared) return;
    const blob = await Tailoring.exportResume(prepared.application.id, fmt);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `resume-ats.${fmt}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  // Everything on this page is either real (from the posting / match / AI
  // breakdown) or shown as an explicit empty state — we never fabricate content.
  const view = useMemo(() => {
    const lo = money(job?.salary_min, job?.salary_currency);
    const hi = money(job?.salary_max, job?.salary_currency);
    const salary = lo && hi ? `${lo}–${hi}` : lo || hi || null;
    const bd = job?.ai_breakdown;
    return {
      responsibilities: bd?.responsibilities ?? [],
      requirements: bd?.requirements ?? [],
      benefits: bd?.benefits ?? [],
      about: bd?.about_company?.trim() || null,
      hasBreakdown: !!(bd?.responsibilities?.length || bd?.requirements?.length),
      salary,
      location: job?.location?.trim() || null,
      remote: !!job?.remote,
      posted: timeAgo(job?.posted_at),
      descriptionIsThin: !job || textLength(job.description || '') < 220,
    };
  }, [job]);

  const matchPct = match ? Math.round(match.score * 100) : null;

  if (!job) return <p className="p-4 text-sm font-semibold text-slate-500">Loading…</p>;

  return (
    <section className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      {/* ── Hero: dark statement panel with the match gauge ── */}
      <div className="relative overflow-hidden rounded-3xl border-2 border-slate-900 bg-slate-950 p-6 shadow-[8px_8px_0_#2dd4bf] sm:p-8">
        <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-teal-500/10 blur-2xl" />
        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              <span className="font-mono text-[11px] font-black uppercase tracking-widest text-teal-300">{job.company?.name}</span>
              {typeof job.ghost_risk === 'number' && (
                <GhostRiskBadge score={job.ghost_risk} band={job.ghost_band} reasons={job.ghost_reasons} showScore />
              )}
            </div>
            <h1 className="mt-2 text-2xl font-black leading-tight tracking-tight text-white sm:text-4xl">{job.title}</h1>
            <div className="mt-4 flex flex-wrap gap-2 text-xs font-bold text-slate-200">
              {view.location && <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1.5"><MapPin className="h-3.5 w-3.5 text-teal-300" />{view.location}</span>}
              {view.remote && <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1.5"><Globe2 className="h-3.5 w-3.5 text-teal-300" />Remote-friendly</span>}
              {view.salary && <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1.5"><Banknote className="h-3.5 w-3.5 text-teal-300" />{view.salary}</span>}
              {view.posted && <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1.5"><Clock className="h-3.5 w-3.5 text-teal-300" />Posted {view.posted}</span>}
            </div>
          </div>
          {matchPct !== null && <MatchRing pct={matchPct} />}
        </div>
      </div>

      {typeof job.ghost_risk === 'number' && (job.ghost_band ?? '') === 'high' && job.ghost_reasons?.length ? (
        <div className="rounded-2xl border-2 border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <div className="font-black">High ghost-job risk — verify this role is genuinely open before investing time.</div>
          <ul className="mt-2 list-disc pl-5">
            {job.ghost_reasons.map((reason) => <li key={reason}>{reason}</li>)}
          </ul>
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main column */}
        <div className="space-y-6 lg:col-span-2">
          {/* Match / skills card */}
          <div className={`${CARD} p-6`} data-testid="match-card">
            <SectionHead index="01" title="Your match for this role" />
            <p className="mt-1 pl-5 text-xs font-semibold text-slate-500">Scored against your resume, skills and experience.</p>

            {match ? (
              <>
                {/* breakdown */}
                {match.breakdown && Object.keys(match.breakdown).length > 0 && (
                  <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {Object.entries(match.breakdown).map(([k, v]) => (
                      <div key={k} className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-center">
                        <p className="text-2xl font-black text-slate-900">{Math.round(v * 100)}<span className="text-sm text-slate-400">%</span></p>
                        <p className="font-mono text-[10px] font-black uppercase tracking-widest text-slate-500">{k}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* matched / missing skills */}
                <div className="mt-5 grid gap-4 sm:grid-cols-2">
                  <div className="rounded-2xl border border-emerald-100 bg-emerald-50/40 p-4">
                    <p className="flex items-center gap-1.5 font-mono text-[11px] font-black uppercase tracking-widest text-emerald-700">
                      <Sparkles className="h-3.5 w-3.5" /> Skills you have · {match.matched_skills?.length ?? 0}
                    </p>
                    <div className="mt-2.5 flex flex-wrap gap-1.5">
                      {(match.matched_skills ?? []).map((s) => (
                        <span key={s} className="rounded-lg border border-emerald-200 bg-white px-2.5 py-1 text-xs font-bold text-emerald-700">{s}</span>
                      ))}
                      {(match.matched_skills ?? []).length === 0 && <span className="text-xs text-slate-400">—</span>}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-red-100 bg-red-50/40 p-4">
                    <p className="flex items-center gap-1.5 font-mono text-[11px] font-black uppercase tracking-widest text-red-700">
                      <XCircle className="h-3.5 w-3.5" /> Skills to add · {match.gaps?.length ?? 0}
                    </p>
                    <div className="mt-2.5 flex flex-wrap gap-1.5">
                      {(match.gaps ?? []).map((s) => (
                        <span key={s} className="rounded-lg border border-red-200 bg-white px-2.5 py-1 text-xs font-bold text-red-700">{s}</span>
                      ))}
                      {(match.gaps ?? []).length === 0 && <span className="text-xs text-slate-400">None — great fit!</span>}
                    </div>
                  </div>
                </div>

                {/* explanation reasons */}
                {match.explanation && match.explanation.length > 0 && (
                  <ul className="mt-5 space-y-2.5 border-t-2 border-dashed border-slate-200 pt-5">
                    {match.explanation.map((reason) => (
                      <li key={reason.title} className="flex items-start gap-2.5 text-sm" data-kind={reason.kind}>
                        <span className={`mt-1.5 h-2.5 w-2.5 flex-shrink-0 rounded-sm ${
                          reason.kind === 'positive' ? 'bg-emerald-500' : reason.kind === 'negative' ? 'bg-red-500' : 'bg-slate-400'
                        }`} />
                        <span>
                          <span className="font-black text-slate-900">{reason.title}</span>
                          <span className="text-slate-600"> — {reason.detail}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            ) : (
              <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-5 text-center">
                <p className="text-sm font-bold text-slate-700">No match score yet</p>
                <p className="mx-auto mt-1 max-w-sm text-xs font-semibold text-slate-500">
                  Upload and parse a resume in your profile and we&apos;ll score how well you fit this role — skills you have, gaps to close, and why.
                </p>
                <Link to="/profile" className="mt-3 inline-flex items-center gap-1.5 rounded-xl bg-slate-950 px-4 py-2 text-xs font-black text-white hover:bg-slate-800">
                  Add your resume <ExternalLink className="h-3.5 w-3.5" />
                </Link>
              </div>
            )}
          </div>

          {/* About the role (raw description) */}
          {(!view.descriptionIsThin || job.description) && (
            <section className={`${CARD} p-6`}>
              <SectionHead index="02" title="About the role" />
              {view.descriptionIsThin ? (
                <p className="mt-4 text-sm leading-7 text-slate-700">{job.description.replace(/<[^>]*>/g, '')}</p>
              ) : (
                <article
                  className="prose prose-sm mt-4 max-w-none leading-7 text-slate-700"
                  dangerouslySetInnerHTML={{ __html: job.description }}
                />
              )}
            </section>
          )}

          {view.hasBreakdown ? (
            <>
              {view.responsibilities.length > 0 && <ListBlock index="03" title="What you'll do" items={view.responsibilities} numbered />}
              {view.requirements.length > 0 && <ListBlock index="04" title="What we're looking for" items={view.requirements} />}
              {view.benefits.length > 0 && <ListBlock index="05" title="Perks & benefits" items={view.benefits} />}
              <p className="pl-1 text-[11px] font-semibold text-slate-400">
                Responsibilities, requirements and perks above were expanded from the posting by AI — treat them as a guide, not the official listing.
              </p>
            </>
          ) : (
            <section className={`${CARD} p-6`}>
              <SectionHead index="03" title="Role breakdown" />
              <p className="mt-3 text-sm leading-6 text-slate-600">
                This posting doesn&apos;t include a structured breakdown. Generate one and AI will read the
                description and lay out the likely responsibilities, requirements, perks and a short company
                summary — cached on this job, so it&apos;s free for everyone after the first run.
              </p>
              <button
                onClick={generateBreakdown}
                disabled={breakdownBusy}
                className="mt-4 inline-flex items-center gap-2 rounded-xl bg-slate-950 px-5 py-3 text-sm font-black text-white transition hover:bg-slate-800 disabled:opacity-50"
              >
                <Sparkles className="h-4 w-4 text-teal-300" />
                {breakdownBusy ? 'Generating…' : 'Generate AI breakdown'}
                {cost.job_breakdown ? <CreditCost cost={cost.job_breakdown} className="!bg-white/20 !text-white" /> : null}
              </button>
              {breakdownError && <p className="mt-3 text-xs font-bold text-red-600">{breakdownError}</p>}
            </section>
          )}
        </div>

        {/* Sidebar */}
        <aside className="space-y-6">
          <div className={`${CARD} p-6 lg:sticky lg:top-20`}>
            <div className="flex items-center gap-2.5">
              <span className="h-6 w-1.5 rounded-full bg-teal-400" />
              <h2 className="font-mono text-xs font-black uppercase tracking-widest text-slate-900">Job overview</h2>
            </div>
            <div className="mt-4 space-y-3">
              {view.location && <Fact icon={MapPin} label="Location" value={`${view.location}${view.remote ? ' · Remote OK' : ''}`} />}
              {!view.location && view.remote && <Fact icon={Globe2} label="Location" value="Remote" />}
              {view.salary && <Fact icon={Banknote} label="Salary range" value={view.salary} />}
              {view.posted && <Fact icon={CalendarDays} label="Posted" value={view.posted} />}
              {job.apply_url && <Fact icon={ExternalLink} label="Apply link" value={new URL(job.apply_url).hostname.replace(/^www\./, '')} />}
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="flex items-center gap-2 font-mono text-xs font-black uppercase tracking-widest text-slate-500">
              <Building2 className="h-4 w-4" /> About {job.company?.name}
            </h2>
            {view.about ? (
              <p className="mt-3 text-sm leading-6 text-slate-700">{view.about}</p>
            ) : (
              <p className="mt-3 text-sm leading-6 text-slate-400">
                No company summary yet.{!view.hasBreakdown && ' Generating the role breakdown adds one.'}
              </p>
            )}
            {job.company?.domain && (
              <a href={`https://${job.company.domain}`} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1.5 text-sm font-black text-teal-700 hover:underline">
                Visit website <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
          </div>
        </aside>
      </div>

      {/* ── Association: this job is already in the pipeline ── */}
      {myApp && (
        <div className={`flex flex-wrap items-center justify-between gap-3 rounded-2xl border-2 p-4 ${
          cool?.active ? 'border-rose-200 bg-rose-50' : 'border-teal-200 bg-teal-50'
        }`}>
          <div className="flex items-center gap-3">
            <span className={`grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl ${cool?.active ? 'bg-rose-500 text-white' : 'bg-teal-500 text-white'}`}>
              {cool?.active ? <Hourglass className="h-4 w-4" /> : <ListChecks className="h-4 w-4" />}
            </span>
            <div>
              <p className={`text-sm font-black ${cool?.active ? 'text-rose-800' : 'text-teal-800'}`}>
                In your pipeline · {STATUS_LABEL[myApp.status] ?? myApp.status}
              </p>
              {cool?.active ? (
                <p className="text-xs font-semibold text-rose-700">
                  Rejected — cool-down active. You can reapply in {cool.daysLeft} day{cool.daysLeft === 1 ? '' : 's'} (on {cool.untilLabel}).
                </p>
              ) : cool ? (
                <p className="text-xs font-semibold text-teal-700">Previous rejection&apos;s cool-down has passed — you&apos;re free to reapply.</p>
              ) : (
                <p className="text-xs font-semibold text-teal-700">Track it on your applications board.</p>
              )}
            </div>
          </div>
          <Link to="/applications" className="inline-flex items-center gap-1.5 rounded-xl bg-slate-950 px-3 py-2 text-xs font-black text-white hover:bg-slate-800">
            View in pipeline <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        </div>
      )}

      {/* ── Apply actions: dark statement panel ── */}
      <div className="rounded-3xl border-2 border-slate-900 bg-slate-950 p-6 shadow-[6px_6px_0_#2dd4bf] sm:p-7">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-black text-white">Ready to apply?</h2>
            <p className="mt-0.5 text-xs font-semibold text-slate-400">Pick how much you want us to automate — we tailor your resume and cover letter to this role.</p>
          </div>
          <span className="font-mono text-[10px] font-black uppercase tracking-widest text-teal-300">Assist &amp; autofill · free</span>
        </div>
        {applyLocked && (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-400/40 bg-rose-500/10 px-3 py-2 text-xs font-bold text-rose-200">
            <Hourglass className="h-4 w-4" />
            Applying is paused during the {cool?.daysLeft}-day rejection cool-down (until {cool?.untilLabel}).
          </div>
        )}
        <div className="mt-5 grid gap-2 sm:flex sm:flex-wrap sm:items-center">
          <button className="rounded-xl bg-white px-5 py-3 font-black text-slate-950 transition hover:bg-slate-100 disabled:opacity-40" disabled={!!busyTier || applyLocked} onClick={() => apply('assist')}>
            {busyTier === 'assist' ? 'Preparing…' : 'Assist apply'}
          </button>
          <button className="rounded-xl bg-teal-400 px-5 py-3 font-black text-slate-950 transition hover:bg-teal-300 disabled:opacity-40" disabled={!!busyTier || applyLocked} onClick={() => apply('autofill')}>
            {busyTier === 'autofill' ? 'Preparing…' : 'Autofill handoff'}
          </button>
          <button className="inline-flex items-center gap-2 rounded-xl bg-red-500 px-5 py-3 font-black text-white transition hover:bg-red-400 disabled:opacity-40 sm:ml-auto" disabled={!!busyTier || applyLocked} onClick={() => apply('autonomous')}>
            {busyTier === 'autonomous' ? 'Preparing…' : 'Autonomous review'}
            {cost.autonomous_apply ? <CreditCost cost={cost.autonomous_apply} className="!bg-white/20 !text-white" /> : null}
          </button>
        </div>
      </div>

      {creditWall && <CreditWall info={creditWall} />}

      {prepared && (
        <div className="rounded-3xl border-2 border-teal-400 bg-white p-5 shadow-[6px_6px_0_#2dd4bf] sm:p-6">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-teal-600" />
            <div>
              <h2 className="font-black text-slate-950">
                {prepared.tier === 'assist' && 'Application saved for assisted apply'}
                {prepared.tier === 'autofill' && 'Autofill handoff is ready'}
                {prepared.tier === 'autonomous' && 'Autonomous flow is paused for review'}
              </h2>
              <p className="mt-1 text-sm font-semibold text-slate-500">
                Application #{prepared.application.id} is now {prepared.status}.
              </p>
            </div>
          </div>
          <ul className="mt-4 space-y-2 text-sm text-slate-700">
            {prepared.next_actions.map((action) => (
              <li key={action} className="flex gap-2">
                <span className="mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-teal-500" />
                <span>{action}</span>
              </li>
            ))}
          </ul>
          <div className="mt-4 flex flex-wrap gap-2">
            <button className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-60" disabled={materialsBusy} onClick={generateMaterials}>
              {materialsBusy ? 'Generating…' : 'Generate materials'}
              {(cost.tailor_resume || cost.cover_letter) ? (
                <CreditCost cost={(cost.tailor_resume ?? 0) + (cost.cover_letter ?? 0)} className="!bg-white/20 !text-white" />
              ) : null}
            </button>
            <button className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-800 hover:bg-slate-50" onClick={() => downloadResume('txt')}>
              ATS resume .txt
            </button>
            <button className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-800 hover:bg-slate-50" onClick={() => downloadResume('docx')}>
              .docx
            </button>
            {prepared.apply_url && (
              <a className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2 text-sm font-bold text-white" href={prepared.apply_url} target="_blank" rel="noreferrer">
                Open apply link
                <ExternalLink className="h-4 w-4" />
              </a>
            )}
            {prepared.approval_token && (
              <span className="inline-flex items-center gap-2 rounded-xl bg-amber-100 px-4 py-2 text-sm font-black text-amber-900">
                <ShieldCheck className="h-4 w-4" />
                Approval token issued
              </span>
            )}
          </div>
          {(materials.resume || materials.coverLetter) && (
            <div className="mt-5 grid gap-3 lg:grid-cols-2">
              {materials.resume && (
                <section className="rounded-xl bg-slate-50 p-3">
                  <h3 className="text-sm font-black text-slate-900">Tailored resume</h3>
                  <p className="mt-2 max-h-52 overflow-auto whitespace-pre-wrap text-sm leading-6 text-slate-700">
                    {materials.resume.content.raw_text || materials.resume.content.summary || 'Generated resume content is ready.'}
                  </p>
                </section>
              )}
              {materials.coverLetter && (
                <section className="rounded-xl bg-slate-50 p-3">
                  <h3 className="text-sm font-black text-slate-900">Cover letter</h3>
                  <p className="mt-2 max-h-52 overflow-auto whitespace-pre-wrap text-sm leading-6 text-slate-700">
                    {materials.coverLetter.content}
                  </p>
                </section>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
