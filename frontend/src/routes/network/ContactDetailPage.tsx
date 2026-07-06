import { useEffect, useState, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft, Mail, Phone, ExternalLink, MapPin, Pencil, Trash2,
  Network as NetworkIcon, Handshake, MessageSquare, StickyNote, CalendarClock,
} from 'lucide-react';
import { Network } from '../../api/endpoints';

interface Contact {
  id: number;
  name: string;
  title: string;
  company: number | null;
  company_name?: string;
  email: string;
  phone: string;
  profile_url: string;
  location: string;
  relationship_strength: number;
  how_we_met: string;
  last_discussed: string;
  last_contacted_at: string | null;
  notes: string;
  tags: string[];
}

const STRENGTH = ["Haven't met", 'Just met', 'Acquaintance', 'Know them well', 'Close', 'Strong ally'];
const STRENGTH_TONE = [
  'bg-slate-100 text-slate-500', 'bg-slate-100 text-slate-600', 'bg-sky-100 text-sky-700',
  'bg-teal-100 text-teal-700', 'bg-emerald-100 text-emerald-700', 'bg-amber-100 text-amber-800',
];
const STRENGTH_CHOICES = [1, 2, 3, 4, 5];

function fmtDate(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso + 'T00:00:00').toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
}

export function ContactDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [c, setC] = useState<Contact | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    Network.contacts.get(Number(id))
      .then((d) => { if (alive) { setC(d as Contact); setNotFound(false); } })
      .catch(() => { if (alive) setNotFound(true); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [id]);

  async function remove() {
    if (!c || !window.confirm(`Remove ${c.name} from your connections?`)) return;
    await Network.contacts.remove(c.id);
    navigate('/connections');
  }

  if (loading) return <p className="text-sm font-semibold text-slate-400">Loading…</p>;
  if (notFound || !c) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <p className="text-sm font-bold text-slate-600">Contact not found</p>
        <Link to="/connections" className="mt-2 inline-block text-sm font-black text-teal-700">← Back to connections</Link>
      </div>
    );
  }

  return (
    <section className="space-y-5">
      <Link to="/connections" className="inline-flex items-center gap-1.5 text-sm font-black text-slate-500 hover:text-slate-800">
        <ArrowLeft className="h-4 w-4" /> Connections
      </Link>

      {/* Header */}
      <div className="rounded-3xl border border-slate-900/10 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 items-center gap-4">
            <div className="grid h-14 w-14 flex-shrink-0 place-items-center rounded-2xl bg-slate-100 text-xl font-black text-slate-700 sm:h-16 sm:w-16 sm:text-2xl">
              {c.name?.[0]?.toUpperCase() || '?'}
            </div>
            <div className="min-w-0">
              <h1 className="truncate text-xl font-black tracking-tight text-slate-950 sm:text-2xl">{c.name}</h1>
              <p className="mt-0.5 truncate text-sm font-semibold text-slate-500">
                {c.title}
                {c.company_name && (
                  c.company
                    ? <>{c.title ? ' · ' : ''}<Link to={`/companies/${c.company}`} className="font-black text-slate-700 hover:text-teal-700">{c.company_name}</Link></>
                    : `${c.title ? ' · ' : ''}${c.company_name}`
                )}
              </p>
              <span className={`mt-2 inline-block rounded-full px-2.5 py-0.5 text-[11px] font-black ${STRENGTH_TONE[c.relationship_strength] ?? STRENGTH_TONE[0]}`}>
                {STRENGTH[c.relationship_strength] ?? 'Contact'}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link to={`/network?root=contact:${c.id}`} className="inline-flex items-center gap-1.5 rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm font-black text-slate-700 hover:bg-slate-50">
              <NetworkIcon className="h-4 w-4" /> In graph
            </Link>
            <button onClick={() => setEditing(true)} className="inline-flex items-center gap-1.5 rounded-2xl bg-slate-950 px-3 py-2 text-sm font-black text-white hover:bg-slate-800">
              <Pencil className="h-4 w-4" /> Edit
            </button>
          </div>
        </div>

        {/* Quick contact chips */}
        <div className="mt-4 flex flex-wrap gap-2">
          {c.email && <Chip icon={Mail} href={`mailto:${c.email}`}>{c.email}</Chip>}
          {c.phone && <Chip icon={Phone} href={`tel:${c.phone}`}>{c.phone}</Chip>}
          {c.profile_url && <Chip icon={ExternalLink} href={c.profile_url} external>Profile</Chip>}
          {c.location && <Chip icon={MapPin}>{c.location}</Chip>}
          {!c.email && !c.phone && !c.profile_url && !c.location && (
            <span className="text-sm font-semibold text-slate-400">No contact details yet — <button onClick={() => setEditing(true)} className="font-black text-teal-700 hover:underline">add some</button>.</span>
          )}
        </div>
      </div>

      {editing ? (
        <EditForm c={c} onCancel={() => setEditing(false)} onSaved={(updated) => { setC(updated); setEditing(false); }} onDelete={remove} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <StorySection icon={Handshake} title="How you know each other" body={c.how_we_met}
            emptyPrompt="Where did you meet? A mutual friend, a conference, a past job?" onAdd={() => setEditing(true)} />
          <StorySection icon={MessageSquare} title="Last conversation" body={c.last_discussed}
            meta={c.last_contacted_at ? `Last spoke ${fmtDate(c.last_contacted_at)}` : undefined}
            emptyPrompt="What did you talk about last time? Note it so you can pick up where you left off." onAdd={() => setEditing(true)} />
          <StorySection icon={StickyNote} title="Private notes" body={c.notes}
            emptyPrompt="Anything else worth remembering about them." onAdd={() => setEditing(true)} />
          <div className="rounded-2xl border border-slate-900/10 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-black uppercase tracking-wide text-slate-500">Tags</h2>
            {c.tags?.length ? (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {c.tags.map((t) => <span key={t} className="rounded-full bg-teal-50 px-2.5 py-1 text-xs font-bold text-teal-700">{t}</span>)}
              </div>
            ) : <p className="mt-3 text-sm font-semibold text-slate-400">No tags yet.</p>}
          </div>
        </div>
      )}
    </section>
  );
}

function Chip({ icon: Icon, href, external, children }: { icon: typeof Mail; href?: string; external?: boolean; children: ReactNode }) {
  const cls = 'inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-black text-slate-700';
  const inner = <><Icon className="h-3.5 w-3.5 text-slate-400" /> {children}</>;
  if (!href) return <span className={cls}>{inner}</span>;
  return <a href={href} {...(external ? { target: '_blank', rel: 'noreferrer' } : {})} className={`${cls} hover:bg-slate-200`}>{inner}</a>;
}

function StorySection({ icon: Icon, title, body, meta, emptyPrompt, onAdd }: {
  icon: typeof Handshake; title: string; body: string; meta?: string; emptyPrompt: string; onAdd: () => void;
}) {
  return (
    <div className="rounded-2xl border border-slate-900/10 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <div className="grid h-8 w-8 place-items-center rounded-xl bg-slate-100 text-slate-600"><Icon className="h-4 w-4" /></div>
        <h2 className="text-sm font-black uppercase tracking-wide text-slate-500">{title}</h2>
      </div>
      {body ? (
        <>
          <p className="mt-3 whitespace-pre-wrap text-sm font-semibold leading-6 text-slate-700">{body}</p>
          {meta && <p className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-slate-400"><CalendarClock className="h-3.5 w-3.5" /> {meta}</p>}
        </>
      ) : (
        <button onClick={onAdd} className="mt-3 w-full rounded-xl border border-dashed border-slate-300 px-3 py-4 text-left text-sm font-semibold text-slate-400 transition hover:border-teal-300 hover:text-teal-700">
          {emptyPrompt}
        </button>
      )}
    </div>
  );
}

function EditForm({ c, onCancel, onSaved, onDelete }: {
  c: Contact; onCancel: () => void; onSaved: (c: Contact) => void; onDelete: () => void;
}) {
  const [f, setF] = useState({
    name: c.name, title: c.title, company_name: c.company_name ?? '',
    email: c.email, phone: c.phone, profile_url: c.profile_url, location: c.location,
    relationship_strength: c.relationship_strength,
    how_we_met: c.how_we_met, last_discussed: c.last_discussed,
    last_contacted_at: c.last_contacted_at ?? '', notes: c.notes,
    tags: c.tags ?? [] as string[],
  });
  const [tagDraft, setTagDraft] = useState('');
  const [saving, setSaving] = useState(false);
  function set<K extends keyof typeof f>(k: K, v: (typeof f)[K]) { setF((s) => ({ ...s, [k]: v })); }
  function addTag(raw: string) { const t = raw.trim().replace(/,$/, ''); if (t && !f.tags.includes(t)) set('tags', [...f.tags, t]); setTagDraft(''); }

  async function save() {
    if (!f.name.trim()) return;
    setSaving(true);
    const payload = { ...f, last_contacted_at: f.last_contacted_at || null };
    const updated = await Network.contacts.patch(c.id, payload);
    onSaved(updated as Contact);
  }

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-sm font-black text-slate-900">Edit contact</h2>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Field label="Name" required value={f.name} onChange={(v) => set('name', v)} />
        <Field label="Role / title" value={f.title} onChange={(v) => set('title', v)} placeholder="Staff Engineer" />
        <Field label="Company" value={f.company_name} onChange={(v) => set('company_name', v)} placeholder="Stripe" />
        <Field label="Location" value={f.location} onChange={(v) => set('location', v)} placeholder="SF / Remote" />
        <Field label="Email" type="email" value={f.email} onChange={(v) => set('email', v)} placeholder="jane@company.com" />
        <Field label="Phone" type="tel" value={f.phone} onChange={(v) => set('phone', v)} placeholder="+1 555 123 4567" />
        <Field label="LinkedIn / profile" value={f.profile_url} onChange={(v) => set('profile_url', v)} placeholder="linkedin.com/in/…" />
        <Field label="Last spoke on" type="date" value={f.last_contacted_at} onChange={(v) => set('last_contacted_at', v)} />
      </div>

      <div className="mt-4">
        <span className="block text-xs font-bold uppercase text-slate-500">How well you know them</span>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {STRENGTH_CHOICES.map((i) => (
            <button type="button" key={i} onClick={() => set('relationship_strength', i)}
              className={`rounded-full px-3 py-1.5 text-xs font-black transition ${f.relationship_strength === i ? 'bg-slate-950 text-white shadow-[0_3px_0_#2dd4bf]' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
              {STRENGTH[i]}
            </button>
          ))}
        </div>
      </div>

      <Area label="How you know each other" value={f.how_we_met} onChange={(v) => set('how_we_met', v)} placeholder="Where you met, who introduced you, how you're connected…" />
      <Area label="What you discussed last time" value={f.last_discussed} onChange={(v) => set('last_discussed', v)} placeholder="Topics, promises, follow-ups from your last conversation…" />
      <Area label="Private notes" value={f.notes} onChange={(v) => set('notes', v)} placeholder="Anything else worth remembering." />

      <div className="mt-4">
        <span className="block text-xs font-bold uppercase text-slate-500">Tags</span>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {f.tags.map((t) => (
            <span key={t} className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2.5 py-1 text-xs font-bold text-teal-700">
              {t}<button type="button" onClick={() => set('tags', f.tags.filter((x) => x !== t))} className="text-teal-400 hover:text-red-600">×</button>
            </span>
          ))}
          <input value={tagDraft} onChange={(e) => setTagDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addTag(tagDraft); } }}
            onBlur={() => addTag(tagDraft)} placeholder={f.tags.length ? 'Add another…' : 'e.g. referral, ex-colleague'}
            className="min-w-[8rem] flex-1 rounded-2xl border border-slate-200 px-3 py-1.5 text-sm focus:border-slate-400 focus:outline-none" />
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <button onClick={save} disabled={!f.name.trim() || saving} className="rounded-2xl bg-slate-950 px-4 py-2 text-sm font-black text-white shadow-[0_4px_0_#2dd4bf] disabled:opacity-50 disabled:shadow-none">{saving ? 'Saving…' : 'Save changes'}</button>
        <button onClick={onCancel} className="rounded-2xl bg-slate-100 px-4 py-2 text-sm font-black text-slate-600 hover:bg-slate-200">Cancel</button>
        <button onClick={onDelete} className="ml-auto inline-flex items-center gap-1.5 rounded-2xl bg-red-50 px-4 py-2 text-sm font-black text-red-600 hover:bg-red-100">
          <Trash2 className="h-4 w-4" /> Delete
        </button>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, placeholder, type = 'text', required = false }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string; required?: boolean;
}) {
  return (
    <label className="block">
      <span className="block text-xs font-bold uppercase text-slate-500">{label}{required && <span className="text-teal-600"> *</span>}</span>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none" />
    </label>
  );
}

function Area({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <label className="mt-4 block">
      <span className="block text-xs font-bold uppercase text-slate-500">{label}</span>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={3} placeholder={placeholder}
        className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none" />
    </label>
  );
}
