import { useEffect, useState } from 'react';
import { ListChecks, Plus, Trash2 } from 'lucide-react';
import { Todos } from '../../api/endpoints';

interface Todo {
  id: number;
  title: string;
  done: boolean;
  due_on: string | null;
  application: number | null;
  application_title: string | null;
}

function dueLabel(due: string | null): { text: string; tone: string } | null {
  if (!due) return null;
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const d = new Date(due + 'T00:00:00');
  const days = Math.round((d.getTime() - today.getTime()) / 86400000);
  if (days < 0) return { text: `${-days}d overdue`, tone: 'bg-red-100 text-red-700' };
  if (days === 0) return { text: 'Due today', tone: 'bg-amber-100 text-amber-700' };
  if (days === 1) return { text: 'Due tomorrow', tone: 'bg-amber-50 text-amber-600' };
  return { text: `In ${days}d`, tone: 'bg-slate-100 text-slate-500' };
}

export function TodosPanel() {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [title, setTitle] = useState('');
  const [due, setDue] = useState('');

  function load() {
    Todos.list().then((d) => setTodos(d.results ?? d)).catch(() => undefined);
  }
  useEffect(load, []);

  async function add() {
    if (!title.trim()) return;
    const created = await Todos.create({ title, due_on: due || null });
    setTodos((rows) => [created, ...rows]);
    setTitle(''); setDue('');
  }
  async function toggle(t: Todo) {
    const updated = await Todos.patch(t.id, { done: !t.done });
    setTodos((rows) => rows.map((r) => (r.id === t.id ? { ...r, ...updated } : r)));
  }
  async function remove(id: number) {
    await Todos.remove(id);
    setTodos((rows) => rows.filter((r) => r.id !== id));
  }

  const openCount = todos.filter((t) => !t.done).length;

  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="inline-flex items-center gap-2 text-sm font-black uppercase tracking-wide text-slate-500">
          <ListChecks className="h-4 w-4 text-slate-400" /> To-dos
        </h2>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-black text-slate-500">{openCount} open</span>
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        <input
          className="min-w-40 flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm"
          placeholder="Add a task, e.g. Follow up with recruiter"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') add(); }}
        />
        <input type="date" className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={due} onChange={(e) => setDue(e.target.value)} />
        <button onClick={add} className="inline-flex items-center gap-1 rounded-xl bg-slate-950 px-3 py-2 text-sm font-black text-white"><Plus className="h-4 w-4" /> Add</button>
      </div>

      {todos.length === 0 ? (
        <p className="text-sm text-slate-400">Nothing to do yet. Add follow-ups so nothing slips.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {todos.map((t) => {
            const due = dueLabel(t.due_on);
            return (
              <li key={t.id} className="group flex items-center gap-3 py-2.5">
                <button
                  onClick={() => toggle(t)}
                  className={`grid h-5 w-5 flex-shrink-0 place-items-center rounded-md border ${t.done ? 'border-teal-500 bg-teal-500 text-white' : 'border-slate-300 bg-white'}`}
                  aria-label={t.done ? 'Mark not done' : 'Mark done'}
                >
                  {t.done && <span className="text-[11px] font-black">✓</span>}
                </button>
                <div className="min-w-0 flex-1">
                  <p className={`truncate text-sm font-bold ${t.done ? 'text-slate-400 line-through' : 'text-slate-800'}`}>{t.title}</p>
                  {t.application_title && <p className="truncate text-xs font-semibold text-slate-400">{t.application_title}</p>}
                </div>
                {due && !t.done && <span className={`flex-shrink-0 rounded-full px-2 py-0.5 text-[11px] font-black ${due.tone}`}>{due.text}</span>}
                <button onClick={() => remove(t.id)} className="flex-shrink-0 text-slate-300 opacity-0 transition group-hover:opacity-100 hover:text-red-600" aria-label="Delete task">
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
