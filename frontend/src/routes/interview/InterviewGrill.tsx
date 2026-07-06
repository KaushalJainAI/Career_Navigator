import { useState } from 'react';
import {
  Mic2, Briefcase, Building2, Phone, Code2, Boxes, MessageSquare, Target,
  ShieldCheck, ClipboardList, Sparkles, ArrowRight, RotateCcw, Trophy,
} from 'lucide-react';
import { useInterviewStore } from '../../stores/useInterviewStore';
import { CreditCost, CreditWall, insufficientCredits, type CreditShortfall } from '../../components/Credits';
import { useBillingStore } from '../../stores/useBillingStore';

const STAGE_META: { key: string; label: string; desc: string; icon: typeof Phone }[] = [
  { key: 'recruiter', label: 'Recruiter screen', desc: 'Motivation, background & logistics', icon: Phone },
  { key: 'tech_phone', label: 'Technical phone', desc: 'Coding fundamentals & problem-solving', icon: Code2 },
  { key: 'system_design', label: 'System design', desc: 'Architecture, trade-offs & scale', icon: Boxes },
  { key: 'behavioral', label: 'Behavioral / onsite', desc: 'STAR stories on impact & teamwork', icon: MessageSquare },
  { key: 'role_specific', label: 'Role-specific', desc: 'Deep questions for this exact role', icon: Target },
];

const DIFFICULTIES: { key: string; label: string }[] = [
  { key: 'easy', label: 'Warm-up' },
  { key: 'medium', label: 'Realistic' },
  { key: 'hard', label: 'Brutal' },
];

export function InterviewGrill() {
  const { sessionId, questions, turns, currentIndex, start, answer, generateReport, loading } =
    useInterviewStore();
  const [role, setRole] = useState('Senior Backend Engineer');
  const [company, setCompany] = useState('');
  const [stage, setStage] = useState('behavioral');
  const [difficulty, setDifficulty] = useState('medium');
  const [text, setText] = useState('');
  const [report, setReport] = useState<{ overall_score: number; gaps: string[]; study_plan: { topic: string; action: string }[] } | null>(null);
  const [creditWall, setCreditWall] = useState<CreditShortfall | null>(null);
  const cost = useBillingStore((s) => s.costByReason);
  const refreshBalance = useBillingStore((s) => s.refresh);

  const current = questions[currentIndex];

  async function onStart() {
    setCreditWall(null);
    try {
      await start({ role, stage, difficulty, company_name: company.trim() || undefined });
      refreshBalance();
    } catch (e) {
      const short = insufficientCredits(e);
      if (short) setCreditWall(short);
    }
  }

  async function onAnswer() {
    if (!text.trim()) return;
    await answer(text);
    setText('');
  }

  async function onReport() {
    const r = await generateReport();
    setReport(r as typeof report);
  }

  // ---- Setup screen ----
  if (!sessionId) {
    return (
      <section className="mx-auto max-w-2xl space-y-6">
        <div className="relative overflow-hidden rounded-[1.75rem] bg-slate-950 p-6 text-white shadow-2xl sm:p-8">
          <div className="career-pulse" />
          <div className="relative">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-black text-teal-200 sm:text-sm">
              <Mic2 className="h-4 w-4" /> Interview Grill Agent
            </span>
            <h1 className="mt-4 text-3xl font-black leading-tight tracking-tight sm:text-4xl">
              Walk in ready to be <span className="text-teal-300">grilled</span>.
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-slate-300 sm:text-base">
              We research the company, build a question bank tuned to the role, then run a live grilling round and score every answer against a STAR rubric — ending with a personalised study plan.
            </p>
            <ul className="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-xs font-bold text-slate-300 sm:text-sm">
              <li className="inline-flex items-center gap-2"><Building2 className="h-4 w-4 text-teal-300" /> Company-researched</li>
              <li className="inline-flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-teal-300" /> STAR-scored answers</li>
              <li className="inline-flex items-center gap-2"><ClipboardList className="h-4 w-4 text-teal-300" /> Study plan at the end</li>
            </ul>
          </div>
        </div>

        <div className="space-y-6 rounded-[1.75rem] border border-slate-900/10 bg-white p-5 shadow-sm sm:p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="block text-xs font-bold uppercase text-slate-500">Target role</span>
              <div className="relative mt-1.5">
                <Briefcase className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input className="w-full rounded-2xl border border-slate-200 py-2.5 pl-9 pr-3 text-sm focus:border-slate-400 focus:outline-none" value={role} onChange={(e) => setRole(e.target.value)} placeholder="Senior Backend Engineer" />
              </div>
            </label>
            <label className="block">
              <span className="block text-xs font-bold uppercase text-slate-500">Company <span className="font-semibold normal-case text-slate-400">· optional</span></span>
              <div className="relative mt-1.5">
                <Building2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input className="w-full rounded-2xl border border-slate-200 py-2.5 pl-9 pr-3 text-sm focus:border-slate-400 focus:outline-none" value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Stripe — sharpens the questions" />
              </div>
            </label>
          </div>

          <div>
            <span className="block text-xs font-bold uppercase text-slate-500">Interview stage</span>
            <div className="mt-2 grid gap-2.5 sm:grid-cols-2">
              {STAGE_META.map((s) => {
                const Icon = s.icon;
                const active = stage === s.key;
                return (
                  <button
                    key={s.key}
                    type="button"
                    onClick={() => setStage(s.key)}
                    className={`flex items-start gap-3 rounded-2xl border p-3 text-left transition ${active ? 'border-slate-950 bg-slate-950 text-white shadow-[0_4px_0_#2dd4bf]' : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'}`}
                  >
                    <div className={`grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl ${active ? 'bg-white/15 text-teal-200' : 'bg-slate-100 text-slate-500'}`}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <div className={`text-sm font-black ${active ? 'text-white' : 'text-slate-900'}`}>{s.label}</div>
                      <div className={`text-xs font-semibold ${active ? 'text-slate-300' : 'text-slate-500'}`}>{s.desc}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <span className="block text-xs font-bold uppercase text-slate-500">Intensity</span>
            <div className="mt-2 flex flex-wrap gap-2">
              {DIFFICULTIES.map((d) => {
                const active = difficulty === d.key;
                return (
                  <button
                    key={d.key}
                    type="button"
                    onClick={() => setDifficulty(d.key)}
                    className={`rounded-full px-4 py-2 text-sm font-black transition ${active ? 'bg-slate-950 text-white shadow-[0_3px_0_#2dd4bf]' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                  >
                    {d.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="border-t border-slate-100 pt-5">
            <button
              className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-teal-300 px-6 py-3.5 text-base font-black text-slate-950 shadow-[0_6px_0_#0d9488] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-70 disabled:hover:translate-y-0"
              disabled={loading || !role.trim()}
              onClick={onStart}
            >
              {loading ? (
                <><Sparkles className="h-5 w-5 animate-pulse" /> Researching &amp; building your grill…</>
              ) : (
                <>Begin grilling <ArrowRight className="h-5 w-5" />
                  {cost.mock_interview ? <CreditCost cost={cost.mock_interview} className="!bg-slate-950/15 !text-slate-900" /> : null}
                </>
              )}
            </button>
            {creditWall && <div className="mt-3"><CreditWall info={creditWall} /></div>}
            <p className="mt-3 text-center text-xs font-semibold text-slate-400">
              Preparation only — a private rehearsal, never a live-interview copilot.
            </p>
          </div>
        </div>
      </section>
    );
  }

  // ---- Live grilling screen ----
  if (current) {
    const answered = currentIndex;
    const pct = questions.length ? Math.round((answered / questions.length) * 100) : 0;
    const last = turns[turns.length - 1];
    return (
      <section className="mx-auto max-w-2xl space-y-4">
        <div>
          <div className="flex items-center justify-between text-sm font-black text-slate-500">
            <span>Question {currentIndex + 1} of {questions.length}</span>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-black text-slate-600">{current.category}</span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-teal-400 transition-all duration-500" style={{ width: `${pct}%` }} />
          </div>
        </div>

        <div className="rounded-2xl border border-slate-900/10 bg-white p-5 shadow-sm sm:p-6">
          <div className="text-lg font-black leading-7 text-slate-950">{current.prompt}</div>
          <textarea
            rows={8}
            className="mt-4 w-full rounded-xl border border-slate-200 p-3 text-sm focus:border-slate-400 focus:outline-none"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Structure it: Situation → Task → Action → Result."
          />
          <button
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-black text-white shadow-[0_4px_0_#2dd4bf] transition hover:bg-slate-800 disabled:opacity-50 sm:w-auto"
            onClick={onAnswer}
            disabled={!text.trim() || loading}
          >
            Submit answer <ArrowRight className="h-4 w-4" />
          </button>
        </div>

        {last && (
          <div className="rounded-2xl border border-teal-100 bg-teal-50/60 p-4">
            <div className="flex items-center gap-2 text-sm font-black text-teal-800">
              <Sparkles className="h-4 w-4" /> Feedback on your last answer
              {typeof last.score === 'number' && (
                <span className="ml-auto rounded-full bg-white px-2.5 py-0.5 text-xs font-black text-teal-700">{Math.round(last.score * 100)}%</span>
              )}
            </div>
            <p className="mt-1.5 text-sm font-semibold leading-6 text-teal-900/80">{last.feedback}</p>
          </div>
        )}
      </section>
    );
  }

  // ---- Wrap-up / report screen ----
  return (
    <section className="mx-auto max-w-2xl space-y-4">
      <div className="rounded-2xl border border-slate-900/10 bg-white p-6 text-center shadow-sm">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-teal-100 text-teal-700">
          <Trophy className="h-7 w-7" />
        </div>
        <h2 className="mt-3 text-2xl font-black tracking-tight text-slate-950">Grilling complete</h2>
        <p className="mt-1 text-sm font-semibold text-slate-500">You answered all {questions.length} questions. Generate your scored report and study plan.</p>
        {!report && (
          <button className="mt-4 inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-950 px-5 py-3 text-sm font-black text-white shadow-[0_4px_0_#2dd4bf] transition hover:bg-slate-800" onClick={onReport} disabled={loading}>
            {loading ? 'Scoring…' : 'Generate report'} <ClipboardList className="h-4 w-4" />
          </button>
        )}
      </div>

      {report && (
        <>
          <div className="rounded-2xl border border-slate-900/10 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm font-black uppercase tracking-wide text-slate-500">Overall score</span>
              <span className="text-4xl font-black tracking-tight text-slate-950">{(report.overall_score * 100).toFixed(0)}%</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
              <div className="h-full rounded-full bg-teal-400" style={{ width: `${Math.round(report.overall_score * 100)}%` }} />
            </div>
            {report.gaps.length > 0 && (
              <div className="mt-5">
                <div className="text-xs font-black uppercase tracking-wide text-slate-500">Gaps to close</div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {report.gaps.map((g, i) => <span key={i} className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-800">{g}</span>)}
                </div>
              </div>
            )}
          </div>

          {report.study_plan.length > 0 && (
            <div className="rounded-2xl border border-slate-900/10 bg-white p-6 shadow-sm">
              <div className="text-xs font-black uppercase tracking-wide text-slate-500">Your study plan</div>
              <ul className="mt-3 space-y-2.5">
                {report.study_plan.map((p, i) => (
                  <li key={i} className="flex gap-3 rounded-xl bg-slate-50 p-3">
                    <div className="grid h-6 w-6 flex-shrink-0 place-items-center rounded-lg bg-slate-950 text-xs font-black text-white">{i + 1}</div>
                    <div><span className="text-sm font-black text-slate-900">{p.topic}</span><span className="text-sm font-semibold text-slate-600"> — {p.action}</span></div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <button onClick={() => window.location.reload()} className="inline-flex items-center gap-2 text-sm font-black text-slate-500 hover:text-slate-800">
            <RotateCcw className="h-4 w-4" /> Start another session
          </button>
        </>
      )}
    </section>
  );
}
