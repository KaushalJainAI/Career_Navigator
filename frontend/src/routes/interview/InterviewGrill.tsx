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
      <section className="max-w-lg mx-auto bg-white p-6 rounded shadow space-y-3">
        <h1 className="text-xl font-semibold">Start an interview grilling session</h1>
        <input className="w-full border p-2 rounded" value={role} onChange={(e) => setRole(e.target.value)} />
        <select className="w-full border p-2 rounded" value={stage} onChange={(e) => setStage(e.target.value)}>
          {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <button
          className="bg-indigo-600 text-white px-4 py-2 rounded"
          disabled={loading}
          onClick={() => start({ role, stage })}
        >
          {loading ? 'Researching…' : 'Begin grilling'}
        </button>
      </section>
    );
  }

  if (current) {
    return (
      <section className="max-w-2xl mx-auto bg-white p-6 rounded shadow space-y-3">
        <div className="text-sm text-slate-500">
          Question {currentIndex + 1} of {questions.length} · {current.category}
        </div>
        <div className="text-lg font-medium">{current.prompt}</div>
        <textarea
          rows={6}
          className="w-full border p-2 rounded"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type your answer…"
        />
        <div className="flex gap-2">
          <button className="bg-indigo-600 text-white px-3 py-2 rounded" onClick={onAnswer}>
            Submit answer
          </button>
        </div>
        {turns.length > 0 && (
          <div className="mt-4 text-sm">
            <div className="font-semibold">Last feedback:</div>
            <div>{turns[turns.length - 1].feedback}</div>
          </div>
        )}
      </section>
    );
  }

  return (
    <section className="max-w-2xl mx-auto bg-white p-6 rounded shadow space-y-3">
      <h2 className="text-xl font-semibold">All questions answered</h2>
      <button className="bg-indigo-600 text-white px-3 py-2 rounded" onClick={onReport}>
        Generate report
      </button>
      {report && (
        <div className="mt-4 space-y-2">
          <div>Overall: {(report.overall_score * 100).toFixed(0)}%</div>
          <div>Gaps: {report.gaps.join(', ')}</div>
          <ul className="list-disc ml-5">
            {report.study_plan.map((p, i) => (
              <li key={i}><strong>{p.topic}</strong>: {p.action}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
