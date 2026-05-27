import { useState } from 'react';
import { useInterviewStore } from '../../stores/useInterviewStore';

const STAGES = ['recruiter', 'tech_phone', 'system_design', 'behavioral', 'role_specific'];

export function InterviewGrill() {
  const { sessionId, questions, turns, currentIndex, start, answer, generateReport, loading } =
    useInterviewStore();
  const [role, setRole] = useState('Senior Backend Engineer');
  const [stage, setStage] = useState('behavioral');
  const [text, setText] = useState('');
  const [report, setReport] = useState<{ overall_score: number; gaps: string[]; study_plan: { topic: string; action: string }[] } | null>(null);

  const current = questions[currentIndex];

  async function onAnswer() {
    if (!text.trim()) return;
    await answer(text);
    setText('');
  }

  async function onReport() {
    const r = await generateReport();
    setReport(r as typeof report);
  }

  if (!sessionId) {
    return (
      <section className="mx-auto max-w-lg space-y-4 rounded-2xl bg-white p-5 shadow-sm sm:p-6">
        <h1 className="text-2xl font-black tracking-tight text-slate-950">Start an interview grilling session</h1>
        <input className="w-full rounded-xl border border-slate-200 p-3" value={role} onChange={(e) => setRole(e.target.value)} />
        <select className="w-full rounded-xl border border-slate-200 p-3" value={stage} onChange={(e) => setStage(e.target.value)}>
          {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <button
          className="w-full rounded-xl bg-indigo-600 px-4 py-3 font-bold text-white sm:w-auto"
          disabled={loading}
          onClick={() => start({ role, stage })}
        >
          {loading ? 'Researching...' : 'Begin grilling'}
        </button>
      </section>
    );
  }

  if (current) {
    return (
      <section className="mx-auto max-w-2xl space-y-4 rounded-2xl bg-white p-5 shadow-sm sm:p-6">
        <div className="text-sm font-semibold text-slate-500">
          Question {currentIndex + 1} of {questions.length} - {current.category}
        </div>
        <div className="text-lg font-bold leading-7 text-slate-950">{current.prompt}</div>
        <textarea
          rows={7}
          className="w-full rounded-xl border border-slate-200 p-3"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type your answer..."
        />
        <button className="w-full rounded-xl bg-indigo-600 px-4 py-3 font-bold text-white sm:w-auto" onClick={onAnswer}>
          Submit answer
        </button>
        {turns.length > 0 && (
          <div className="mt-4 rounded-xl bg-slate-50 p-3 text-sm">
            <div className="font-bold text-slate-800">Last feedback:</div>
            <div className="mt-1 text-slate-600">{turns[turns.length - 1].feedback}</div>
          </div>
        )}
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-2xl space-y-4 rounded-2xl bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-2xl font-black tracking-tight text-slate-950">All questions answered</h2>
      <button className="w-full rounded-xl bg-indigo-600 px-4 py-3 font-bold text-white sm:w-auto" onClick={onReport}>
        Generate report
      </button>
      {report && (
        <div className="mt-4 space-y-2 text-sm leading-6">
          <div>Overall: {(report.overall_score * 100).toFixed(0)}%</div>
          <div>Gaps: {report.gaps.join(', ')}</div>
          <ul className="ml-5 list-disc">
            {report.study_plan.map((p, i) => (
              <li key={i}><strong>{p.topic}</strong>: {p.action}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
