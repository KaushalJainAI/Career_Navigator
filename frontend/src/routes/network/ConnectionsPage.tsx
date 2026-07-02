import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Users, Plus, Trash2, Pencil, Mail, ExternalLink, Search, Network as NetworkIcon, Building2, Gift, ListChecks } from 'lucide-react';
import { Network } from '../../api/endpoints';
import { ReferralsTab } from './ReferralsTab';
import { OutreachTab } from './OutreachTab';
import { TasksTab } from './TasksTab';

const NETWORK_TABS = [
  { key: 'contacts', label: 'Contacts', icon: Users },
  { key: 'referrals', label: 'Referrals', icon: Gift },
  { key: 'outreach', label: 'Outreach', icon: Mail },
  { key: 'tasks', label: 'Next actions', icon: ListChecks },
];

export function ConnectionsPage() {
  const [tab, setTab] = useState('contacts');
  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-black tracking-tight text-slate-950">Connections</h1>
        <p className="mt-1 text-sm font-semibold text-slate-500">
          Your network is your best referral channel — track who you know, get referral suggestions, draft outreach, and stay on top of next actions.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {NETWORK_TABS.map((t) => {
          const Icon = t.icon;
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`inline-flex items-center gap-2 rounded-2xl px-4 py-2 text-sm font-black transition ${active ? 'bg-slate-950 text-white shadow-[0_4px_0_#2dd4bf]' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
            >
              <Icon className="h-4 w-4" /> {t.label}
            </button>
          );
        })}
      </div>
      <div key={tab} className="animate-fade-in">
        {tab === 'contacts' && <ContactsTab />}
        {tab === 'referrals' && <ReferralsTab />}
        {tab === 'outreach' && <OutreachTab />}
        {tab === 'tasks' && <TasksTab />}
      </div>
    </section>
  );
}

interface Contact {
  id: number;
  name: string;
  title: string;
  company_name?: string;
  location: string;
  email: string;
  profile_url: string;
  relationship_strength: number;
  tags: string[];
  notes: string;
}

const STRENGTH = ['Not connected', 'Cold contact', 'Acquaintance', 'Know them', 'Close', 'Strong ally'];

const BLANK = {
  name: '', title: '', company_name: '', location: '', email: '',
  profile_url: '', relationship_strength: 2, tags: [] as string[], notes: '',
};

function ContactsTab() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  function load() {
    setLoading(true);
    Network.contacts.list()
      .then((d) => setContacts((d.results ?? d) as Contact[]))
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }
  useEffect(load, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return contacts;
    return contacts.filter((c) =>
      [c.name, c.title, c.company_name, c.location, ...(c.tags ?? [])]
        .filter(Boolean).join(' ').toLowerCase().includes(q));
  }, [contacts, query]);

  async function save(payload: typeof BLANK, id?: number) {
    if (id) {
      const updated = await Network.contacts.patch(id, payload);
      setContacts((rows) => rows.map((r) => (r.id === id ? { ...r, ...updated } : r)));
      setEditingId(null);
    } else {
      const created = await Network.contacts.create(payload);
      setContacts((rows) => [created as Contact, ...rows]);
      setAdding(false);
    }
  }
  async function remove(id: number) {
    await Network.contacts.remove(id);
    setContacts((rows) => rows.filter((r) => r.id !== id));
  }

  const strong = contacts.filter((c) => c.relationship_strength >= 4).length;

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-end gap-2">
        <Link to="/network" className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-black text-slate-700 hover:bg-slate-50">
          <NetworkIcon className="h-4 w-4" /> Network graph
        </Link>
        <button onClick={() => { setAdding((v) => !v); setEditingId(null); }} className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-2 text-sm font-black text-white shadow-[0_4px_0_#2dd4bf] hover:bg-slate-800">
          <Plus className="h-4 w-4" /> Add contact
        </button>
      </div>

      <div className="grid grid-cols-3 gap-2.5 sm:gap-3">
        <Stat label="Contacts" value={contacts.length} />
        <Stat label="Strong allies" value={strong} />
        <Stat label="At companies" value={new Set(contacts.map((c) => c.company_name).filter(Boolean)).size} />
      </div>

      {adding && <ContactForm onCancel={() => setAdding(false)} onSave={(p) => save(p)} />}

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name, company, role or tag…"
          className="w-full rounded-2xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm focus:border-slate-400 focus:outline-none"
        />
      </div>

      {loading ? (
        <p className="text-sm font-semibold text-slate-400">Loading contacts…</p>
      ) : filtered.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-center">
          <Users className="mx-auto h-8 w-8 text-slate-300" />
          <p className="mt-2 text-sm font-bold text-slate-600">{contacts.length === 0 ? 'No connections yet' : 'No matches'}</p>
          <p className="text-sm text-slate-400">{contacts.length === 0 ? 'Add people you know to start tracking referral paths.' : 'Try a different search.'}</p>
        </div>
      ) : (
        <div className="grid animate-stagger grid-cols-2 gap-2.5 sm:gap-3 xl:grid-cols-3">
          {filtered.map((c) => (
            editingId === c.id ? (
              <ContactForm key={c.id} initial={c} onCancel={() => setEditingId(null)} onSave={(p) => save(p, c.id)} />
            ) : (
              <ContactCard key={c.id} c={c} onEdit={() => { setEditingId(c.id); setAdding(false); }} onRemove={() => remove(c.id)} />
            )
          ))}
        </div>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl bg-white p-3 shadow-sm sm:p-4">
      <div className="text-xl font-black tracking-tight text-slate-950 sm:text-3xl">{value}</div>
      <div className="mt-0.5 text-[10px] font-bold uppercase text-slate-500 sm:text-xs">{label}</div>
    </div>
  );
}

function ContactCard({ c, onEdit, onRemove }: { c: Contact; onEdit: () => void; onRemove: () => void }) {
  return (
    <div className="group flex flex-col rounded-2xl bg-white p-3 shadow-sm sm:p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2.5 sm:gap-3">
          <div className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-slate-100 text-sm font-black text-slate-700 sm:h-11 sm:w-11 sm:rounded-2xl">
            {c.name?.[0]?.toUpperCase() || '?'}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-black text-slate-900 sm:text-base">{c.name}</p>
            <p className="truncate text-[11px] font-semibold text-slate-500 sm:text-xs">
              {c.title}{c.company_name ? `${c.title ? ' · ' : ''}${c.company_name}` : ''}
            </p>
          </div>
        </div>
        <div className="flex flex-shrink-0 gap-1 opacity-100 transition sm:opacity-0 sm:group-hover:opacity-100">
          <button onClick={onEdit} className="grid h-8 w-8 place-items-center rounded-xl text-slate-400 hover:bg-slate-100" aria-label="Edit"><Pencil className="h-4 w-4" /></button>
          <button onClick={onRemove} className="grid h-8 w-8 place-items-center rounded-xl text-slate-400 hover:bg-red-50 hover:text-red-600" aria-label="Delete"><Trash2 className="h-4 w-4" /></button>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-black text-slate-600">{STRENGTH[c.relationship_strength] ?? 'Contact'}</span>
        {c.location && <span className="text-[11px] font-semibold text-slate-400">{c.location}</span>}
      </div>

      {c.tags?.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {c.tags.map((t) => <span key={t} className="rounded-full bg-teal-50 px-2 py-0.5 text-[11px] font-bold text-teal-700">{t}</span>)}
        </div>
      )}

      {c.notes && <p className="mt-2 line-clamp-2 text-xs font-semibold text-slate-500">{c.notes}</p>}

      <div className="mt-3 flex flex-wrap gap-3 pt-1">
        {c.email && <a href={`mailto:${c.email}`} className="inline-flex items-center gap-1 text-xs font-black text-slate-600 hover:text-slate-900"><Mail className="h-3.5 w-3.5" /> Email</a>}
        {c.profile_url && <a href={c.profile_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs font-black text-slate-600 hover:text-slate-900"><ExternalLink className="h-3.5 w-3.5" /> Profile</a>}
      </div>
    </div>
  );
}

function ContactForm({ initial, onSave, onCancel }: { initial?: Contact; onSave: (p: typeof BLANK) => void; onCancel: () => void }) {
  const [f, setF] = useState({ ...BLANK, ...(initial ? {
    name: initial.name, title: initial.title, company_name: initial.company_name ?? '',
    location: initial.location, email: initial.email, profile_url: initial.profile_url,
    relationship_strength: initial.relationship_strength, tags: initial.tags ?? [], notes: initial.notes,
  } : {}) });
  const [tagDraft, setTagDraft] = useState('');
  function set<K extends keyof typeof BLANK>(k: K, v: (typeof BLANK)[K]) { setF((s) => ({ ...s, [k]: v })); }

  return (
    <div className="col-span-2 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm xl:col-span-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <Input label="Name" value={f.name} onChange={(v) => set('name', v)} placeholder="Jane Doe" />
        <Input label="Role / title" value={f.title} onChange={(v) => set('title', v)} placeholder="Staff Engineer" />
        <Input label="Company" value={f.company_name} onChange={(v) => set('company_name', v)} placeholder="Stripe" icon={Building2} />
        <Input label="Location" value={f.location} onChange={(v) => set('location', v)} placeholder="Remote / SF" />
        <Input label="Email" value={f.email} onChange={(v) => set('email', v)} placeholder="jane@company.com" />
        <Input label="Profile URL (LinkedIn)" value={f.profile_url} onChange={(v) => set('profile_url', v)} placeholder="https://linkedin.com/in/…" />
        <label className="block">
          <span className="block text-xs font-bold uppercase text-slate-500">Relationship</span>
          <select value={f.relationship_strength} onChange={(e) => set('relationship_strength', Number(e.target.value))} className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm">
            {STRENGTH.map((label, i) => <option key={i} value={i}>{label}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="block text-xs font-bold uppercase text-slate-500">Tags</span>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {f.tags.map((t) => (
              <span key={t} className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">
                {t}<button onClick={() => set('tags', f.tags.filter((x) => x !== t))} className="text-slate-400 hover:text-red-600">×</button>
              </span>
            ))}
          </div>
          <input
            value={tagDraft}
            onChange={(e) => setTagDraft(e.target.value)}
            onKeyDown={(e) => { if ((e.key === 'Enter' || e.key === ',') && tagDraft.trim()) { e.preventDefault(); if (!f.tags.includes(tagDraft.trim())) set('tags', [...f.tags, tagDraft.trim()]); setTagDraft(''); } }}
            placeholder="e.g. referral, ex-colleague"
            className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm"
          />
        </label>
      </div>
      <label className="mt-3 block">
        <span className="block text-xs font-bold uppercase text-slate-500">Notes</span>
        <textarea value={f.notes} onChange={(e) => set('notes', e.target.value)} rows={2} className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm" placeholder="How you know them, last touchpoint…" />
      </label>
      <div className="mt-3 flex gap-2">
        <button onClick={() => f.name.trim() && onSave(f)} disabled={!f.name.trim()} className="rounded-2xl bg-slate-950 px-4 py-2 text-sm font-black text-white disabled:opacity-50">{initial ? 'Save' : 'Add contact'}</button>
        <button onClick={onCancel} className="rounded-2xl bg-slate-100 px-4 py-2 text-sm font-black text-slate-600">Cancel</button>
      </div>
    </div>
  );
}

function Input({ label, value, onChange, placeholder, icon: Icon }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; icon?: typeof Building2 }) {
  return (
    <label className="block">
      <span className="block text-xs font-bold uppercase text-slate-500">{label}</span>
      <div className="relative mt-1">
        {Icon && <Icon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />}
        <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={`w-full rounded-2xl border border-slate-200 py-2 pr-3 text-sm focus:border-slate-400 focus:outline-none ${Icon ? 'pl-9' : 'pl-3'}`} />
      </div>
    </label>
  );
}
