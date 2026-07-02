import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ExternalLink, Users, Briefcase, Send, Sparkles, Check, Pencil, Network as NetworkIcon } from 'lucide-react';
import { Network } from '../../api/endpoints';

interface Detail {
  id: number;
  name: string;
  domain: string;
  careers_url: string;
  ats_type: string;
  description: string;
  counts: { contacts: number; jobs: number; applications: number };
  contacts: { id: number; name: string; title: string; relationship_strength: number; profile_url: string }[];
  jobs: { id: number; title: string; location: string; remote: boolean; apply_url: string }[];
  applications: { id: number; status: string; job_id: number; job_title: string; next_action: string; follow_up_on: string | null }[];
  warm_intros: { contact_id: number; name: string; title: string; score: number; hop: number; reason: string }[];
}

const STATUS_TONE: Record<string, string> = {
  queued: 'bg-slate-100 text-slate-600',
  applied: 'bg-sky-100 text-sky-700',
  phone_screen: 'bg-indigo-100 text-indigo-700',
  interviewing: 'bg-amber-100 text-amber-700',
  offer: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-rose-100 text-rose-700',
  withdrawn: 'bg-slate-100 text-slate-500',
};

export function CompanyDetailPage() {
  const { id } = useParams();
  const [d, setD] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [careersUrl, setCareersUrl] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!id) return;
    Network.companies.get(Number(id))
      .then((data) => { setD(data); setCareersUrl(data.careers_url ?? ''); })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, [id]);

  async function saveCareers() {
    if (!id) return;
    setSaving(true);
    try {
      const data = await Network.companies.patch(Number(id), { careers_url: careersUrl });
      setD(data);
      setEditing(false);
    } finally { setSaving(false); }
  }

  if (loading) return <p className="text-sm font-semibold text-slate-400">Loading company…</p>;
  if (!d) return <p className="text-sm font-bold text-slate-600">Company not found.</p>;

  return (
    <div className="space-y-4 sm:space-y-6">
      <Link to="/companies" className="inline-flex items-center gap-1.5 text-sm font-black text-slate-500 hover:text-slate-900">
        <ArrowLeft className="h-4 w-4" /> All companies
      </Link>

      {/* Header */}
      <div className="rounded-2xl border border-slate-900/10 bg-white p-4 shadow-sm sm:rounded-3xl sm:p-6">
        <div className="flex items-start gap-3 sm:gap-4">
          <div className="grid h-12 w-12 flex-shrink-0 place-items-center rounded-2xl bg-slate-100 text-xl font-black text-slate-700 sm:h-16 sm:w-16 sm:text-3xl">
            {d.name[0] ?? '?'}
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-xl font-black tracking-tight text-slate-950 sm:text-2xl">{d.name}</h1>
            {d.domain && <p className="truncate text-xs font-semibold text-slate-400 sm:text-sm">{d.domain}</p>}
            <div className="mt-3 flex flex-wrap gap-1.5 text-[11px] font-black sm:text-xs">
              <Chip icon={Users} label={`${d.counts.contacts} contacts`} tone="bg-rose-50 text-rose-700" />
              <Chip icon={Briefcase} label={`${d.counts.jobs} jobs`} tone="bg-sky-50 text-sky-700" />
              <Chip icon={Send} label={`${d.counts.applications} applications`} tone="bg-emerald-50 text-emerald-700" />
            </div>
          </div>
          <Link
            to={`/network?root=company:${d.id}`}
            className="hidden flex-shrink-0 items-center gap-1.5 rounded-2xl bg-slate-100 px-3 py-2 text-xs font-black text-slate-600 hover:bg-slate-200 sm:inline-flex"
          >
            <NetworkIcon className="h-4 w-4" /> View in graph
          </Link>
        </div>

        {/* Careers page — editable */}
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
          <span className="text-xs font-black uppercase text-slate-400">Careers page</span>
          {editing ? (
            <>
              <input
                value={careersUrl}
                onChange={(e) => setCareersUrl(e.target.value)}
                placeholder="https://company.com/careers"
                className="min-w-48 flex-1 rounded-xl border border-slate-200 px-3 py-1.5 text-sm"
              />
              <button onClick={saveCareers} disabled={saving} className="inline-flex items-center gap-1 rounded-xl bg-teal-600 px-3 py-1.5 text-xs font-black text-white disabled:opacity-50">
                <Check className="h-3.5 w-3.5" /> {saving ? 'Saving…' : 'Save'}
              </button>
            </>
          ) : d.careers_url ? (
            <>
              <a href={d.careers_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm font-black text-teal-700 hover:underline">
                {d.careers_url.replace(/^https?:\/\//, '')} <ExternalLink className="h-3.5 w-3.5" />
              </a>
              <button onClick={() => setEditing(true)} className="text-slate-400 hover:text-slate-700"><Pencil className="h-3.5 w-3.5" /></button>
            </>
          ) : (
            <button onClick={() => setEditing(true)} className="inline-flex items-center gap-1 text-sm font-black text-slate-500 hover:text-slate-900">
              <Pencil className="h-3.5 w-3.5" /> Add careers URL
            </button>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Connections */}
        <Section title="Connections" icon={Users} count={d.contacts.length}>
          {d.contacts.length === 0 ? (
            <Empty text="No contacts here yet." />
          ) : (
            <ul className="space-y-2">
              {d.contacts.map((c) => (
                <li key={c.id} className="flex items-center gap-2.5 rounded-xl bg-slate-50 p-2.5">
                  <span className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-lg bg-white text-sm font-black text-slate-600">{c.name[0]}</span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-black text-slate-900">{c.name}</p>
                    {c.title && <p className="truncate text-xs font-semibold text-slate-500">{c.title}</p>}
                  </div>
                  <span className="flex-shrink-0 text-[11px] font-black text-amber-600">{'★'.repeat(Math.min(c.relationship_strength, 5)) || '—'}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>

        {/* Warm intros */}
        <Section title="Warm intros" icon={Sparkles} count={d.warm_intros.length}>
          {d.warm_intros.length === 0 ? (
            <Empty text="No warm intro paths found." />
          ) : (
            <ul className="space-y-2">
              {d.warm_intros.map((w) => (
                <li key={w.contact_id} className="rounded-xl bg-slate-50 p-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm font-black text-slate-900">{w.name}</p>
                    <span className="flex-shrink-0 rounded-full bg-teal-100 px-2 py-0.5 text-[11px] font-black text-teal-700">{w.score}</span>
                  </div>
                  <p className="truncate text-xs font-semibold text-slate-500">{w.reason || w.title}</p>
                </li>
              ))}
            </ul>
          )}
        </Section>

        {/* Opportunities */}
        <Section title="Open opportunities" icon={Briefcase} count={d.jobs.length}>
          {d.jobs.length === 0 ? (
            <Empty text="No open roles tracked." />
          ) : (
            <ul className="space-y-2">
              {d.jobs.map((j) => (
                <li key={j.id}>
                  <Link to={`/jobs/${j.id}`} className="block rounded-xl bg-slate-50 p-2.5 hover:bg-teal-50">
                    <p className="truncate text-sm font-black text-slate-900">{j.title}</p>
                    <p className="truncate text-xs font-semibold text-slate-500">{j.remote ? 'Remote' : j.location || '—'}</p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Section>

        {/* Applications */}
        <Section title="Your applications" icon={Send} count={d.applications.length}>
          {d.applications.length === 0 ? (
            <Empty text="You haven't applied here yet." />
          ) : (
            <ul className="space-y-2">
              {d.applications.map((a) => (
                <li key={a.id}>
                  <Link to={`/jobs/${a.job_id}`} className="block rounded-xl bg-slate-50 p-2.5 hover:bg-teal-50">
                    <div className="flex items-center justify-between gap-2">
                      <p className="truncate text-sm font-black text-slate-900">{a.job_title}</p>
                      <span className={`flex-shrink-0 rounded-full px-2 py-0.5 text-[11px] font-black capitalize ${STATUS_TONE[a.status] ?? 'bg-slate-100 text-slate-600'}`}>
                        {a.status.replace('_', ' ')}
                      </span>
                    </div>
                    {a.next_action && <p className="truncate text-xs font-semibold text-slate-500">Next: {a.next_action}</p>}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>
    </div>
  );
}

function Section({ title, icon: Icon, count, children }: { title: string; icon: typeof Users; count: number; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-900/10 bg-white p-4 shadow-sm sm:rounded-3xl sm:p-5">
      <div className="mb-3 flex items-center gap-2">
        <Icon className="h-4 w-4 text-slate-400" />
        <h2 className="text-sm font-black uppercase tracking-wide text-slate-500">{title}</h2>
        <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-black text-slate-500">{count}</span>
      </div>
      {children}
    </section>
  );
}

function Chip({ icon: Icon, label, tone }: { icon: typeof Users; label: string; tone: string }) {
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 ${tone}`}><Icon className="h-3 w-3" /> {label}</span>;
}

function Empty({ text }: { text: string }) {
  return <p className="rounded-xl bg-slate-50 px-3 py-4 text-center text-xs font-semibold text-slate-400">{text}</p>;
}
