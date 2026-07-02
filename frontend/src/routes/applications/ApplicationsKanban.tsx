import { useEffect, useMemo, useState } from 'react';
import { CalendarClock, ExternalLink, Pencil, AlertTriangle } from 'lucide-react';
import { useApplicationsStore, type Application } from '../../stores/useApplicationsStore';
import { GoalsPanel } from './GoalsPanel';
import { TodosPanel } from './TodosPanel';

const COLUMNS: { key: string; label: string }[] = [
  { key: 'saved', label: 'Saved' },
  { key: 'tailored', label: 'Tailored' },
  { key: 'ready', label: 'Ready to apply' },
  { key: 'applied', label: 'Applied' },
  { key: 'phone', label: 'Phone screen' },
  { key: 'onsite', label: 'Onsite' },
  { key: 'offer', label: 'Offer' },
  { key: 'rejected', label: 'Rejected' },
  { key: 'withdrawn', label: 'Withdrawn' },
];
const ALL_STATUSES = COLUMNS.map((c) => c.key);

// Four tabs group the nine stages along the funnel so the board stays focused.
const TABS: { key: string; label: string; columns: string[] }[] = [
  { key: 'to_apply', label: 'To apply', columns: ['saved', 'tailored', 'ready'] },
  { key: 'applied', label: 'Applied', columns: ['applied'] },
  { key: 'interviewing', label: 'Interviewing', columns: ['phone', 'onsite'] },
  { key: 'outcome', label: 'Outcome', columns: ['offer', 'rejected', 'withdrawn'] },
];

function salaryLabel(a: Application): string | null {
  const lo = a.job_detail?.salary_min;
  const hi = a.job_detail?.salary_max;
  if (!lo && !hi) return null;
  const k = (n?: number | null) => (n ? `$${Math.round(n / 1000)}k` : '');
  return [k(lo), k(hi)].filter(Boolean).join('–');
}

function daysAgo(iso?: string): string | null {
  if (!iso) return null;
  const d = Math.round((Date.now() - new Date(iso).getTime()) / 86400000);
  if (d <= 0) return 'today';
  if (d === 1) return 'yesterday';
  return `${d}d ago`;
}

function followUpBadge(iso?: string | null): { text: string; tone: string } | null {
  if (!iso) return null;
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const d = Math.round((new Date(iso + 'T00:00:00').getTime() - today.getTime()) / 86400000);
  if (d < 0) return { text: `Follow-up ${-d}d overdue`, tone: 'bg-red-100 text-red-700' };
  if (d === 0) return { text: 'Follow up today', tone: 'bg-amber-100 text-amber-700' };
  if (d <= 3) return { text: `Follow up in ${d}d`, tone: 'bg-amber-50 text-amber-600' };
  return { text: `Follow up ${new Date(iso + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`, tone: 'bg-slate-100 text-slate-500' };
}

const ACTIVE = ['saved', 'tailored', 'ready', 'applied', 'phone', 'onsite'];

export function ApplicationsKanban() {
  const { applications, fetch, setStatus, patchApp } = useApplicationsStore();
  const [activeTab, setActiveTab] = useState('to_apply');
  useEffect(() => { fetch(); }, [fetch]);

  const countFor = (cols: string[]) => applications.filter((a) => cols.includes(a.status)).length;
  const columns = COLUMNS.filter((c) => TABS.find((t) => t.key === activeTab)?.columns.includes(c.key));

  const dueSoon = useMemo(() => {
    const today = new Date(); today.setHours(0, 0, 0, 0);
    return applications.filter((a) => {
      if (!a.follow_up_on || !ACTIVE.includes(a.status)) return false;
      return new Date(a.follow_up_on + 'T00:00:00').getTime() <= today.getTime() + 86400000; // due today/overdue/tomorrow
    });
  }, [applications]);

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-black tracking-tight text-slate-950">Applications</h1>
        <p className="mt-1 text-sm font-semibold text-slate-500">Track every role from saved to offer — set goals, keep follow-ups on time, and never lose a thread.</p>
      </div>

      {dueSoon.length > 0 && (
        <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
          <div>
            <p className="font-black text-amber-800">{dueSoon.length} follow-up{dueSoon.length > 1 ? 's' : ''} need attention</p>
            <p className="mt-0.5 text-sm font-semibold text-amber-700">
              {dueSoon.map((a) => a.job_detail?.company?.name || a.job_detail?.title).filter(Boolean).join(', ')}
            </p>
          </div>
        </div>
      )}

      <GoalsPanel />
      <TodosPanel />

      <div>
        <h2 className="mb-3 text-sm font-black uppercase tracking-wide text-slate-500">Pipeline</h2>
        <div className="mb-4 flex flex-wrap gap-2">
          {TABS.map((tab) => {
            const count = countFor(tab.columns);
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`inline-flex items-center gap-2 rounded-2xl px-4 py-2 text-sm font-black transition ${active ? 'bg-slate-950 text-white shadow-[0_4px_0_#2dd4bf]' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              >
                {tab.label}
                <span className={`rounded-full px-2 py-0.5 text-xs font-black ${active ? 'bg-white/20 text-white' : 'bg-white text-slate-500'}`}>{count}</span>
              </button>
            );
          })}
        </div>
        <div key={activeTab} className="grid animate-fade-in grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {columns.map((col) => {
            const items = applications.filter((a) => a.status === col.key);
            return (
              <div key={col.key} className="min-h-24 rounded-2xl bg-slate-100 p-3">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <h3 className="text-xs font-black uppercase tracking-wide text-slate-600">{col.label}</h3>
                  <span className="rounded-full bg-white px-2 py-0.5 text-xs font-black text-slate-500">{items.length}</span>
                </div>
                <ul className="space-y-2">
                  {items.map((a) => (
                    <ApplicationCard key={a.id} app={a} onStatus={setStatus} onPatch={patchApp} />
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function ApplicationCard({
  app, onStatus, onPatch,
}: {
  app: Application;
  onStatus: (id: number, status: string) => Promise<void>;
  onPatch: (id: number, payload: Partial<Application>) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [nextAction, setNextAction] = useState(app.next_action ?? '');
  const [followUp, setFollowUp] = useState(app.follow_up_on ?? '');
  const [notes, setNotes] = useState(app.notes ?? '');
  const [saving, setSaving] = useState(false);

  const salary = salaryLabel(app);
  const applied = daysAgo(app.created_at);
  const follow = followUpBadge(app.follow_up_on);

  async function save() {
    setSaving(true);
    await onPatch(app.id, { next_action: nextAction, follow_up_on: followUp || null, notes });
    setSaving(false);
    setEditing(false);
  }

  return (
    <li className="rounded-xl bg-white p-3 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-bold text-slate-800">{app.job_detail?.title || `Job #${app.job}`}</div>
          <div className="mt-0.5 truncate text-xs font-semibold text-slate-500">
            {app.job_detail?.company?.name || 'Unknown company'}{app.job_detail?.location ? ` · ${app.job_detail.location}` : ''}
          </div>
        </div>
        <button onClick={() => setEditing((v) => !v)} className="flex-shrink-0 text-slate-300 hover:text-slate-600" aria-label="Edit application">
          <Pencil className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {salary && <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-black text-emerald-700">{salary}</span>}
        {app.tier_used && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-black text-slate-500">{app.tier_used}</span>}
        {applied && <span className="text-[11px] font-semibold text-slate-400">applied {applied}</span>}
      </div>

      {app.next_action && !editing && (
        <p className="mt-2 text-xs font-semibold text-slate-600">→ {app.next_action}</p>
      )}
      {follow && !editing && (
        <span className={`mt-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-black ${follow.tone}`}>
          <CalendarClock className="h-3 w-3" />{follow.text}
        </span>
      )}

      {editing ? (
        <div className="mt-3 space-y-2 rounded-lg bg-slate-50 p-2">
          <input className="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-xs" placeholder="Next action" value={nextAction} onChange={(e) => setNextAction(e.target.value)} />
          <label className="block text-[11px] font-bold uppercase text-slate-400">Follow up on
            <input type="date" className="mt-1 w-full rounded-lg border border-slate-200 px-2 py-1.5 text-xs" value={followUp ?? ''} onChange={(e) => setFollowUp(e.target.value)} />
          </label>
          <textarea className="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-xs" rows={2} placeholder="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
          <div className="flex items-center gap-2">
            <button onClick={save} disabled={saving} className="rounded-lg bg-slate-950 px-3 py-1.5 text-xs font-black text-white disabled:opacity-60">{saving ? 'Saving…' : 'Save'}</button>
            <button onClick={() => setEditing(false)} className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-black text-slate-600">Cancel</button>
            {app.job_detail?.apply_url && (
              <a href={app.job_detail.apply_url} target="_blank" rel="noreferrer" className="ml-auto inline-flex items-center gap-1 text-xs font-black text-slate-500 hover:text-slate-800">
                Posting <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>
      ) : (
        <select
          className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm"
          value={app.status}
          onChange={(e) => onStatus(app.id, e.target.value)}
        >
          {ALL_STATUSES.map((s) => <option key={s} value={s}>{COLUMNS.find((c) => c.key === s)?.label ?? s}</option>)}
        </select>
      )}
    </li>
  );
}
