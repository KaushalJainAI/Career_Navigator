import { useEffect, useState } from 'react';
import { Target, Plus, Trash2, Check } from 'lucide-react';
import { Goals } from '../../api/endpoints';

interface Goal {
  id: number;
  title: string;
  metric: string;
  metric_label: string;
  target: number;
  period: string;
  period_label: string;
  manual_progress: number;
  current: number;
}

const METRICS = [
  { value: 'applications', label: 'Applications submitted' },
  { value: 'interviews', label: 'Interviews reached' },
  { value: 'offers', label: 'Offers received' },
  { value: 'custom', label: 'Custom (track manually)' },
];
const PERIODS = [
  { value: 'week', label: 'This week' },
  { value: 'month', label: 'This month' },
  { value: 'all', label: 'All time' },
];

export function GoalsPanel() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState('');
  const [metric, setMetric] = useState('applications');
  const [target, setTarget] = useState(10);
  const [period, setPeriod] = useState('week');

  function load() {
    Goals.list().then((d) => setGoals(d.results ?? d)).catch(() => undefined);
  }
  useEffect(load, []);

  async function add() {
    if (!title.trim()) return;
    await Goals.create({ title, metric, target, period });
    setTitle(''); setTarget(10); setMetric('applications'); setPeriod('week'); setAdding(false);
    load();
  }
  async function bump(g: Goal) {
    const updated = await Goals.patch(g.id, { manual_progress: g.manual_progress + 1 });
    setGoals((rows) => rows.map((r) => (r.id === g.id ? { ...r, ...updated } : r)));
  }
  async function remove(id: number) {
    await Goals.remove(id);
    setGoals((rows) => rows.filter((r) => r.id !== id));
  }

  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="inline-flex items-center gap-2 text-sm font-black uppercase tracking-wide text-slate-500">
          <Target className="h-4 w-4 text-slate-400" /> Goals
        </h2>
        <button onClick={() => setAdding((v) => !v)} className="inline-flex items-center gap-1 rounded-xl bg-slate-100 px-3 py-1.5 text-xs font-black text-slate-700 hover:bg-slate-200">
          <Plus className="h-3.5 w-3.5" /> New goal
        </button>
      </div>

      {adding && (
        <div className="mb-4 grid gap-2 rounded-2xl bg-slate-50 p-3 sm:grid-cols-2">
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm sm:col-span-2" placeholder="Goal title, e.g. Apply to 15 roles" value={title} onChange={(e) => setTitle(e.target.value)} />
          <select className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={metric} onChange={(e) => setMetric(e.target.value)}>
            {METRICS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
          <select className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={period} onChange={(e) => setPeriod(e.target.value)} disabled={metric === 'custom'}>
            {PERIODS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
          </select>
          <label className="flex items-center gap-2 text-sm font-semibold text-slate-600">
            Target
            <input type="number" min={1} className="w-24 rounded-xl border border-slate-200 px-3 py-2 text-sm" value={target} onChange={(e) => setTarget(Number(e.target.value))} />
          </label>
          <button onClick={add} className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-black text-white">Add goal</button>
        </div>
      )}

      {goals.length === 0 ? (
        <p className="text-sm text-slate-400">No goals yet — set a weekly target to keep momentum.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {goals.map((g) => {
            const pct = g.target ? Math.min(100, Math.round((g.current / g.target) * 100)) : 0;
            const done = g.current >= g.target;
            return (
              <div key={g.id} className="group rounded-2xl border border-slate-200 p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-black text-slate-900">{g.title}</p>
                  <button onClick={() => remove(g.id)} className="text-slate-300 opacity-0 transition group-hover:opacity-100 hover:text-red-600" aria-label="Delete goal">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                <p className="mt-0.5 text-xs font-bold uppercase text-slate-400">{g.metric_label} · {g.period_label}</p>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className={`text-2xl font-black ${done ? 'text-teal-600' : 'text-slate-950'}`}>{g.current}</span>
                  <span className="text-sm font-bold text-slate-400">/ {g.target}</span>
                  {done && <Check className="h-4 w-4 text-teal-600" />}
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div className={`h-full rounded-full ${done ? 'bg-teal-500' : 'bg-slate-900'}`} style={{ width: `${pct}%` }} />
                </div>
                {g.metric === 'custom' && (
                  <button onClick={() => bump(g)} className="mt-3 inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-black text-slate-700 hover:bg-slate-200">
                    <Plus className="h-3 w-3" /> Log one
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
