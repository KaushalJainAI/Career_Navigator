import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { CheckCircle2, ExternalLink, ShieldCheck } from 'lucide-react';
import { Jobs, Applications, Tailoring } from '../../api/endpoints';
import { GhostRiskBadge, type GhostBand } from '../../components/GhostRiskBadge';

interface Job {
  id: number;
  title: string;
  description: string;
  apply_url: string;
  company: { name: string };
  ghost_risk?: number;
  ghost_band?: GhostBand;
  ghost_reasons?: string[];
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

export function JobDetail() {
  const { id } = useParams();
  const jobId = Number(id);
  const [job, setJob] = useState<Job | null>(null);
  const [match, setMatch] = useState<Match | null>(null);
  const [prepared, setPrepared] = useState<PreparedApplication | null>(null);
  const [busyTier, setBusyTier] = useState<ApplyTier | null>(null);
  const [materials, setMaterials] = useState<GeneratedMaterials>({});
  const [materialsBusy, setMaterialsBusy] = useState(false);

  useEffect(() => {
    Jobs.detail(jobId).then(setJob);
    Jobs.match(jobId).then(setMatch).catch(() => undefined);
  }, [jobId]);

  async function apply(tier: ApplyTier) {
    setBusyTier(tier);
    try {
      const result = await Applications.prepare(jobId, tier);
      setPrepared(result);
      setMaterials({});
    } finally {
      setBusyTier(null);
    }
  }

  async function generateMaterials() {
    if (!prepared) return;
    setMaterialsBusy(true);
    try {
      const [resume, coverLetter] = await Promise.all([
        Tailoring.resume(prepared.application.id),
        Tailoring.coverLetter(prepared.application.id),
      ]);
      setMaterials({ resume, coverLetter });
    } finally {
      setMaterialsBusy(false);
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

  if (!job) return <p>Loading...</p>;
  return (
    <section className="space-y-5">
      <div>
        <h1 className="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">{job.title}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <span className="text-sm font-semibold text-slate-600 sm:text-base">{job.company?.name}</span>
          {typeof job.ghost_risk === 'number' && (
            <GhostRiskBadge score={job.ghost_risk} band={job.ghost_band} reasons={job.ghost_reasons} showScore />
          )}
        </div>
      </div>
      {typeof job.ghost_risk === 'number' && (job.ghost_band ?? '') === 'high' && job.ghost_reasons?.length ? (
        <div className="rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-800">
          <div className="font-black">High ghost-job risk — verify this role is genuinely open before investing time.</div>
          <ul className="mt-2 list-disc pl-5">
            {job.ghost_reasons.map((reason) => <li key={reason}>{reason}</li>)}
          </ul>
        </div>
      ) : null}
      {match && (
        <div className="rounded-2xl bg-white p-4 shadow-sm" data-testid="match-card">
          <div className="font-medium">Match score: {(match.score * 100).toFixed(0)}%</div>
          {match.explanation && match.explanation.length > 0 ? (
            <ul className="mt-3 space-y-2">
              {match.explanation.map((reason) => (
                <li key={reason.title} className="flex items-start gap-2 text-sm" data-kind={reason.kind}>
                  <span className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${
                    reason.kind === 'positive' ? 'bg-emerald-500'
                      : reason.kind === 'negative' ? 'bg-red-500' : 'bg-slate-400'
                  }`} />
                  <span>
                    <span className="font-bold text-slate-800">{reason.title}</span>
                    <span className="text-slate-600"> — {reason.detail}</span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            match.gaps?.length > 0 && (
              <div className="text-sm text-amber-700">Gaps: {match.gaps.join(', ')}</div>
            )
          )}
        </div>
      )}
      <article className="prose max-w-none rounded-2xl bg-white p-4 text-sm leading-7 sm:p-5 sm:text-base" dangerouslySetInnerHTML={{ __html: job.description }} />
      <div className="grid gap-2 sm:flex sm:flex-wrap">
        <button className="rounded-xl bg-slate-950 px-4 py-3 font-bold text-white disabled:opacity-60" disabled={!!busyTier} onClick={() => apply('assist')}>
          {busyTier === 'assist' ? 'Preparing...' : 'Assist apply'}
        </button>
        <button className="rounded-xl bg-teal-600 px-4 py-3 font-bold text-white disabled:opacity-60" disabled={!!busyTier} onClick={() => apply('autofill')}>
          {busyTier === 'autofill' ? 'Preparing...' : 'Autofill handoff'}
        </button>
        <button className="rounded-xl bg-red-600 px-4 py-3 font-bold text-white disabled:opacity-60" disabled={!!busyTier} onClick={() => apply('autonomous')}>
          {busyTier === 'autonomous' ? 'Preparing...' : 'Autonomous review'}
        </button>
      </div>
      {prepared && (
        <div className="rounded-2xl border border-teal-100 bg-white p-4 shadow-sm sm:p-5">
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
              {materialsBusy ? 'Generating...' : 'Generate materials'}
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
