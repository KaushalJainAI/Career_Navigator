import { useEffect, useState } from 'react';
import { ListChecks } from 'lucide-react';
import { Network } from '../../api/endpoints';

interface QueueItem {
  id: number;
  action_type: string;
  title: string;
  priority: number;
  due_at: string | null;
  job: number | null;
  contact: number | null;
}

function dueLabel(iso: string | null): { text: string; tone: string } | null {
  if (!iso) return null;
  const now = Date.now();
  const t = new Date(iso).getTime();
  const days = Math.round((t - now) / 86400000);
  if (days < 0) return { text: `${-days}d overdue`, tone: 'bg-red-100 text-red-700' };
  if (days === 0) return { text: 'Due today', tone: 'bg-amber-100 text-amber-700' };
  if (days === 1) return { text: 'Due tomorrow', tone: 'bg-amber-50 text-amber-600' };
  return { text: `In ${days}d`, tone: 'bg-slate-100 text-slate-500' };
}

export function TasksTab() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Network.queue.list('open')
      .then((d) => setItems(d.results ?? d))
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm font-semibold text-slate-400">Loading next actions…</p>;
  if (items.length === 0) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <ListChecks className="mx-auto h-8 w-8 text-slate-300" />
        <p className="mt-2 text-sm font-bold text-slate-600">No open actions</p>
        <p className="text-xs text-slate-400">Networking next-actions (follow-ups, intros to make) show up here, highest priority first.</p>
      </div>
    );
  }

  return (
    <ul className="space-y-2">
      {items.map((it) => {
        const due = dueLabel(it.due_at);
        return (
          <li key={it.id} className="flex items-center gap-3 rounded-2xl bg-white p-4 shadow-sm">
            <span className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-600">
              <ListChecks className="h-4 w-4" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-bold text-slate-800">{it.title}</p>
              <p className="truncate text-xs font-semibold text-slate-500">{it.action_type.replace(/_/g, ' ')}</p>
            </div>
            {due && <span className={`flex-shrink-0 rounded-full px-2 py-0.5 text-[11px] font-black ${due.tone}`}>{due.text}</span>}
            <span className="flex-shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-black text-slate-500">P{it.priority}</span>
          </li>
        );
      })}
    </ul>
  );
}
