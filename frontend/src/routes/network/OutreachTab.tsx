import { useEffect, useState } from 'react';
import { Mail, Check, Plus } from 'lucide-react';
import { Network } from '../../api/endpoints';

interface Outreach {
  id: number;
  contact: { name: string; title?: string; company_name?: string };
  channel: string;
  subject: string;
  draft_body: string;
  approved_body: string;
  status: string;
}
interface ContactLite { id: number; name: string }

const STATUS_TONE: Record<string, string> = {
  drafted: 'bg-slate-100 text-slate-600',
  approved: 'bg-teal-100 text-teal-700',
  sent: 'bg-sky-100 text-sky-700',
  replied: 'bg-emerald-100 text-emerald-700',
  follow_up_due: 'bg-amber-100 text-amber-700',
  closed: 'bg-slate-100 text-slate-500',
};

export function OutreachTab() {
  const [items, setItems] = useState<Outreach[]>([]);
  const [contacts, setContacts] = useState<ContactLite[]>([]);
  const [pick, setPick] = useState<number | ''>('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  function load() {
    Network.outreach.list().then((d) => setItems(d.results ?? d)).catch(() => undefined).finally(() => setLoading(false));
  }
  useEffect(() => {
    load();
    Network.contacts.list().then((d) => setContacts((d.results ?? d).map((c: ContactLite) => ({ id: c.id, name: c.name })))).catch(() => undefined);
  }, []);

  async function draft() {
    if (!pick) return;
    setBusy(true);
    try {
      const created = await Network.outreach.draft(Number(pick));
      setItems((rows) => [created, ...rows]);
      setPick('');
    } finally { setBusy(false); }
  }
  async function approve(id: number) {
    const res = await Network.outreach.approve(id);
    setItems((rows) => rows.map((m) => (m.id === id ? { ...m, ...(res.message ?? { status: 'approved' }) } : m)));
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2 rounded-2xl bg-white p-4 shadow-sm">
        <label className="min-w-48 flex-1">
          <span className="block text-xs font-bold uppercase text-slate-500">Draft outreach to</span>
          <select value={pick} onChange={(e) => setPick(e.target.value ? Number(e.target.value) : '')} className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm">
            <option value="">Select a contact…</option>
            {contacts.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
        <button onClick={draft} disabled={!pick || busy} className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-2 text-sm font-black text-white disabled:opacity-50">
          <Plus className="h-4 w-4" /> {busy ? 'Drafting…' : 'Draft message'}
        </button>
      </div>

      {loading ? (
        <p className="text-sm font-semibold text-slate-400">Loading messages…</p>
      ) : items.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-center">
          <Mail className="mx-auto h-8 w-8 text-slate-300" />
          <p className="mt-2 text-sm font-bold text-slate-600">No outreach drafted yet</p>
          <p className="text-xs text-slate-400">Pick a contact above to draft a referral message.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((m) => (
            <div key={m.id} className="rounded-2xl bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate font-black text-slate-900">{m.subject || 'Outreach message'}</p>
                  <p className="truncate text-xs font-semibold text-slate-500">
                    To {m.contact?.name}{m.contact?.company_name ? ` · ${m.contact.company_name}` : ''} · {m.channel}
                  </p>
                </div>
                <span className={`flex-shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-black capitalize ${STATUS_TONE[m.status] ?? 'bg-slate-100 text-slate-600'}`}>
                  {m.status.replace('_', ' ')}
                </span>
              </div>
              <p className="mt-3 whitespace-pre-line rounded-xl bg-slate-50 p-3 text-xs font-semibold text-slate-600">
                {m.approved_body || m.draft_body}
              </p>
              {m.status === 'drafted' && (
                <button onClick={() => approve(m.id)} className="mt-3 inline-flex items-center gap-2 rounded-xl bg-teal-600 px-3 py-1.5 text-xs font-black text-white hover:bg-teal-700">
                  <Check className="h-3.5 w-3.5" /> Approve to send
                </button>
              )}
              {m.status === 'approved' && (
                <p className="mt-3 inline-flex items-center gap-1 text-xs font-black text-teal-700"><Check className="h-3.5 w-3.5" /> Approved — ready to send</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
