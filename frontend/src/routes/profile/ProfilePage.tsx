import { useEffect, useState } from 'react';
import { Profile, Resumes } from '../../api/endpoints';
import { Plus, Trash2, Save, User2, Briefcase, GraduationCap, FolderGit2, Sparkles, Target, FileText, UploadCloud, Award, Languages as LanguagesIcon } from 'lucide-react';

interface Experience {
  company: string;
  title: string;
  location?: string;
  start_date?: string | null;
  end_date?: string | null;
  is_current?: boolean;
  bullets?: string[];
}
interface Education {
  institution: string;
  degree?: string;
  field_of_study?: string;
  start_date?: string | null;
  end_date?: string | null;
  gpa?: string;
}
interface SkillRow { name: string; proficiency?: string; years?: number | null }
interface ProjectRow { name: string; description?: string; url?: string; tech_stack?: string[] }
interface CertificationRow { name: string; issuer?: string; issue_date?: string; credential_url?: string }
interface LanguageRow { name: string; proficiency?: string }
interface PreferenceData {
  target_titles: string[];
  locations: string[];
  keywords: string[];
  remote: boolean;
  salary_min: number | null;
  seniority: string;
  work_auth: string;
}

interface ProfileData {
  full_name: string;
  headline: string;
  summary: string;
  location: string;
  phone: string;
  website: string;
  linkedin: string;
  github: string;
  experiences: Experience[];
  educations: Education[];
  skills: SkillRow[];
  projects: ProjectRow[];
  certifications: CertificationRow[];
  languages: LanguageRow[];
  preference: PreferenceData;
  readiness?: { score: number; ready: boolean; missing: string[] };
}

const EMPTY_PREF: PreferenceData = {
  target_titles: [], locations: [], keywords: [], remote: true,
  salary_min: null, seniority: '', work_auth: '',
};

const EMPTY: ProfileData = {
  full_name: '', headline: '', summary: '', location: '', phone: '',
  website: '', linkedin: '', github: '',
  experiences: [], educations: [], skills: [], projects: [],
  certifications: [], languages: [],
  preference: EMPTY_PREF,
};

export function ProfilePage() {
  const [data, setData] = useState<ProfileData>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);

  useEffect(() => {
    Profile.get()
      .then((d) => setData({ ...EMPTY, ...d, skills: d.skills ?? [], experiences: d.experiences ?? [], educations: d.educations ?? [], projects: d.projects ?? [], certifications: d.certifications ?? [], languages: d.languages ?? [], preference: { ...EMPTY_PREF, ...(d.preference ?? {}) } }))
      .catch(() => setStatus({ kind: 'err', text: 'Could not load your profile.' }))
      .finally(() => setLoading(false));
  }, []);

  function set<K extends keyof ProfileData>(key: K, value: ProfileData[K]) {
    setData((d) => ({ ...d, [key]: value }));
  }

  function setPref<K extends keyof PreferenceData>(key: K, value: PreferenceData[K]) {
    setData((d) => ({ ...d, preference: { ...d.preference, [key]: value } }));
  }

  async function save() {
    setSaving(true);
    setStatus(null);
    try {
      const saved = await Profile.patch({
        full_name: data.full_name,
        headline: data.headline,
        summary: data.summary,
        location: data.location,
        phone: data.phone,
        website: data.website,
        linkedin: data.linkedin,
        github: data.github,
        experiences: data.experiences,
        educations: data.educations,
        skills: data.skills,
        projects: data.projects,
        certifications: data.certifications,
        languages: data.languages,
        preference: data.preference,
      });
      setData({ ...EMPTY, ...saved, skills: saved.skills ?? [], experiences: saved.experiences ?? [], educations: saved.educations ?? [], projects: saved.projects ?? [], certifications: saved.certifications ?? [], languages: saved.languages ?? [], preference: { ...EMPTY_PREF, ...(saved.preference ?? {}) } });
      setStatus({ kind: 'ok', text: 'Profile saved.' });
    } catch {
      setStatus({ kind: 'err', text: 'Save failed. Check the highlighted fields and try again.' });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="rounded-2xl bg-white p-4 text-sm font-semibold text-slate-500 shadow-sm">Loading your profile…</div>;
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-slate-950">Your profile</h1>
          <p className="mt-1 text-sm font-semibold text-slate-500">
            This powers resume tailoring, match scoring and the interview agent.
          </p>
        </div>
        <button
          onClick={save}
          disabled={saving}
          className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-2 text-sm font-black text-white shadow-[0_4px_0_#2dd4bf] hover:bg-slate-800 disabled:opacity-60"
        >
          <Save className="h-4 w-4" /> {saving ? 'Saving…' : 'Save changes'}
        </button>
      </header>

      {status && (
        <p className={`rounded-2xl p-3 text-sm font-semibold ${status.kind === 'ok' ? 'bg-teal-50 text-teal-700' : 'bg-red-50 text-red-700'}`}>
          {status.text}
        </p>
      )}

      {data.readiness && (
        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-black uppercase tracking-wide text-slate-500">Profile readiness</h2>
              <p className="mt-1 text-sm font-semibold text-slate-600">
                {data.readiness.ready ? 'Ready for matching and tailoring.' : 'Add the missing pieces to improve matching.'}
              </p>
            </div>
            <div className="text-3xl font-black text-slate-950">{Math.round(data.readiness.score * 100)}%</div>
          </div>
          {data.readiness.missing.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {data.readiness.missing.map((item) => (
                <span key={item} className="rounded-full bg-amber-100 px-3 py-1 text-xs font-black text-amber-900">{item}</span>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Personal info */}
      <Card icon={User2} title="Personal information">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Full name" value={data.full_name} onChange={(v) => set('full_name', v)} />
          <Field label="Headline" value={data.headline} onChange={(v) => set('headline', v)} placeholder="Senior Backend Engineer" />
          <Field label="Location" value={data.location} onChange={(v) => set('location', v)} placeholder="Bengaluru, IN" />
          <Field label="Phone" value={data.phone} onChange={(v) => set('phone', v)} />
          <Field label="Website" value={data.website} onChange={(v) => set('website', v)} placeholder="https://" />
          <Field label="LinkedIn" value={data.linkedin} onChange={(v) => set('linkedin', v)} placeholder="https://linkedin.com/in/…" />
          <Field label="GitHub" value={data.github} onChange={(v) => set('github', v)} placeholder="https://github.com/…" />
        </div>
        <div className="mt-4">
          <Label>Summary</Label>
          <textarea
            value={data.summary}
            onChange={(e) => set('summary', e.target.value)}
            rows={4}
            className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
            placeholder="A short professional summary…"
          />
        </div>
      </Card>

      {/* Skills */}
      <Card icon={Sparkles} title="Skills">
        <TagInput
          values={data.skills.map((s) => s.name)}
          onChange={(names) => set('skills', names.map((name) => {
            const existing = data.skills.find((s) => s.name === name);
            return existing ?? { name };
          }))}
          placeholder="Type a skill and press Enter"
        />
      </Card>

      {/* Job search preferences */}
      <Card icon={Target} title="Job search preferences">
        <p className="mb-3 text-sm text-slate-500">Drives which roles get matched and surfaced to you.</p>
        <div className="space-y-4">
          <div>
            <Label>Target titles</Label>
            <TagInput values={data.preference.target_titles} onChange={(v) => setPref('target_titles', v)} placeholder="e.g. Backend Engineer" />
          </div>
          <div>
            <Label>Preferred locations</Label>
            <TagInput values={data.preference.locations} onChange={(v) => setPref('locations', v)} placeholder="e.g. Remote, Bengaluru" />
          </div>
          <div>
            <Label>Keywords to match on</Label>
            <TagInput values={data.preference.keywords} onChange={(v) => setPref('keywords', v)} placeholder="Skills / tech" />
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Minimum salary" type="number" value={data.preference.salary_min?.toString() ?? ''} onChange={(v) => setPref('salary_min', v ? Number(v) : null)} />
            <Field label="Seniority" value={data.preference.seniority} onChange={(v) => setPref('seniority', v)} placeholder="e.g. senior" />
            <Field label="Work authorization" value={data.preference.work_auth} onChange={(v) => setPref('work_auth', v)} placeholder="e.g. Citizen, H1B" />
          </div>
          <label className="inline-flex items-center gap-2 text-sm font-semibold text-slate-700">
            <input type="checkbox" checked={data.preference.remote} onChange={(e) => setPref('remote', e.target.checked)} />
            Open to remote roles
          </label>
        </div>
      </Card>

      {/* Resumes */}
      <ResumesSection />

      {/* Experience */}
      <Card icon={Briefcase} title="Experience" onAdd={() => set('experiences', [...data.experiences, { company: '', title: '', bullets: [] }])}>
        {data.experiences.length === 0 && <Empty text="No experience added yet." />}
        <div className="space-y-4">
          {data.experiences.map((exp, i) => (
            <RowCard key={i} onRemove={() => set('experiences', data.experiences.filter((_, j) => j !== i))}>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Title" value={exp.title} onChange={(v) => updateItem('experiences', i, { title: v })} />
                <Field label="Company" value={exp.company} onChange={(v) => updateItem('experiences', i, { company: v })} />
                <Field label="Location" value={exp.location ?? ''} onChange={(v) => updateItem('experiences', i, { location: v })} />
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Start" type="date" value={exp.start_date ?? ''} onChange={(v) => updateItem('experiences', i, { start_date: v || null })} />
                  <Field label="End" type="date" value={exp.end_date ?? ''} onChange={(v) => updateItem('experiences', i, { end_date: v || null })} />
                </div>
              </div>
              <label className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-slate-700">
                <input type="checkbox" checked={!!exp.is_current} onChange={(e) => updateItem('experiences', i, { is_current: e.target.checked })} />
                I currently work here
              </label>
              <div className="mt-3">
                <Label>Highlights (one per line)</Label>
                <textarea
                  value={(exp.bullets ?? []).join('\n')}
                  onChange={(e) => updateItem('experiences', i, { bullets: splitLines(e.target.value) })}
                  rows={3}
                  className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
                />
              </div>
            </RowCard>
          ))}
        </div>
      </Card>

      {/* Education */}
      <Card icon={GraduationCap} title="Education" onAdd={() => set('educations', [...data.educations, { institution: '' }])}>
        {data.educations.length === 0 && <Empty text="No education added yet." />}
        <div className="space-y-4">
          {data.educations.map((ed, i) => (
            <RowCard key={i} onRemove={() => set('educations', data.educations.filter((_, j) => j !== i))}>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Institution" value={ed.institution} onChange={(v) => updateItem('educations', i, { institution: v })} />
                <Field label="Degree" value={ed.degree ?? ''} onChange={(v) => updateItem('educations', i, { degree: v })} />
                <Field label="Field of study" value={ed.field_of_study ?? ''} onChange={(v) => updateItem('educations', i, { field_of_study: v })} />
                <Field label="GPA" value={ed.gpa ?? ''} onChange={(v) => updateItem('educations', i, { gpa: v })} />
                <Field label="Start" type="date" value={ed.start_date ?? ''} onChange={(v) => updateItem('educations', i, { start_date: v || null })} />
                <Field label="End" type="date" value={ed.end_date ?? ''} onChange={(v) => updateItem('educations', i, { end_date: v || null })} />
              </div>
            </RowCard>
          ))}
        </div>
      </Card>

      {/* Projects */}
      <Card icon={FolderGit2} title="Projects" onAdd={() => set('projects', [...data.projects, { name: '', tech_stack: [] }])}>
        {data.projects.length === 0 && <Empty text="No projects added yet." />}
        <div className="space-y-4">
          {data.projects.map((p, i) => (
            <RowCard key={i} onRemove={() => set('projects', data.projects.filter((_, j) => j !== i))}>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Name" value={p.name} onChange={(v) => updateItem('projects', i, { name: v })} />
                <Field label="URL" value={p.url ?? ''} onChange={(v) => updateItem('projects', i, { url: v })} placeholder="https://" />
              </div>
              <div className="mt-3">
                <Label>Description</Label>
                <textarea
                  value={p.description ?? ''}
                  onChange={(e) => updateItem('projects', i, { description: e.target.value })}
                  rows={2}
                  className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
                />
              </div>
              <div className="mt-3">
                <Label>Tech stack</Label>
                <TagInput
                  values={p.tech_stack ?? []}
                  onChange={(vals) => updateItem('projects', i, { tech_stack: vals })}
                  placeholder="Add a technology"
                />
              </div>
            </RowCard>
          ))}
        </div>
      </Card>

      {/* Certifications */}
      <Card icon={Award} title="Certifications" onAdd={() => set('certifications', [...data.certifications, { name: '' }])}>
        {data.certifications.length === 0 && <Empty text="No certifications added yet." />}
        <div className="space-y-4">
          {data.certifications.map((c, i) => (
            <RowCard key={i} onRemove={() => set('certifications', data.certifications.filter((_, j) => j !== i))}>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Name" value={c.name} onChange={(v) => updateItem('certifications', i, { name: v })} placeholder="AWS Solutions Architect" />
                <Field label="Issuer" value={c.issuer ?? ''} onChange={(v) => updateItem('certifications', i, { issuer: v })} placeholder="Amazon Web Services" />
                <Field label="Issued" value={c.issue_date ?? ''} onChange={(v) => updateItem('certifications', i, { issue_date: v })} placeholder="Mar 2024" />
                <Field label="Credential URL" value={c.credential_url ?? ''} onChange={(v) => updateItem('certifications', i, { credential_url: v })} placeholder="https://" />
              </div>
            </RowCard>
          ))}
        </div>
      </Card>

      {/* Languages */}
      <Card icon={LanguagesIcon} title="Languages" onAdd={() => set('languages', [...data.languages, { name: '', proficiency: 'Professional' }])}>
        {data.languages.length === 0 && <Empty text="No languages added yet." />}
        <div className="space-y-3">
          {data.languages.map((l, i) => (
            <div key={i} className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 p-3">
              <div className="min-w-40 flex-1">
                <Label>Language</Label>
                <input value={l.name} onChange={(e) => updateItem('languages', i, { name: e.target.value })} placeholder="English" className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none" />
              </div>
              <div>
                <Label>Proficiency</Label>
                <select value={l.proficiency ?? 'Professional'} onChange={(e) => updateItem('languages', i, { proficiency: e.target.value })} className="mt-1 rounded-2xl border border-slate-200 px-3 py-2 text-sm">
                  {['Native', 'Fluent', 'Professional', 'Conversational', 'Basic'].map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <button onClick={() => set('languages', data.languages.filter((_, j) => j !== i))} className="grid h-9 w-9 place-items-center rounded-xl text-slate-400 hover:bg-red-50 hover:text-red-600" aria-label="Remove language">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );

  function updateItem<K extends 'experiences' | 'educations' | 'projects' | 'certifications' | 'languages'>(key: K, index: number, patch: Partial<ProfileData[K][number]>) {
    setData((d) => ({
      ...d,
      [key]: (d[key] as ProfileData[K]).map((item, i) => (i === index ? { ...item, ...patch } : item)),
    }));
  }
}

function splitLines(value: string): string[] {
  return value.split('\n').map((l) => l.trim()).filter(Boolean);
}

interface ResumeRow {
  id: number;
  label: string;
  parse_status: string;
  is_master: boolean;
  created_at: string;
}

function ResumesSection() {
  const [items, setItems] = useState<ResumeRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const refresh = () => Resumes.list().then((d) => setItems(d.results ?? d)).catch(() => undefined);
  useEffect(() => { refresh(); }, []);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files?.[0]) return;
    setBusy(true); setErr('');
    try {
      await Resumes.upload(e.target.files[0]);
      await refresh();
    } catch {
      setErr('Upload failed. Use a PDF or DOCX under a few MB.');
    } finally {
      setBusy(false);
      e.target.value = '';
    }
  }
  async function remove(id: number) {
    await Resumes.remove(id);
    setItems((rows) => rows.filter((r) => r.id !== id));
  }

  return (
    <Card icon={FileText} title="Resumes">
      <p className="mb-3 text-sm text-slate-500">
        Upload your master resume — it powers match scoring and one-click tailoring for each job.
      </p>
      <label className="flex cursor-pointer items-center gap-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm font-bold text-slate-700 hover:bg-slate-100">
        <UploadCloud className="h-5 w-5 text-slate-400" />
        <span>{busy ? 'Uploading…' : 'Upload PDF or DOCX'}</span>
        <input className="hidden" type="file" accept=".pdf,.docx" onChange={onUpload} disabled={busy} />
      </label>
      {err && <p className="mt-2 text-sm font-semibold text-red-600">{err}</p>}
      {items.length > 0 && (
        <ul className="mt-3 space-y-2">
          {items.map((r) => (
            <li key={r.id} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 p-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-black text-slate-900">{r.label}</p>
                <p className="mt-0.5 text-xs font-semibold text-slate-500">
                  {r.parse_status === 'done' ? 'Parsed' : r.parse_status}
                  {r.is_master && <span className="ml-2 rounded-full bg-teal-100 px-2 py-0.5 text-[11px] font-black text-teal-700">Master</span>}
                </p>
              </div>
              <button onClick={() => remove(r.id)} className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-xl text-slate-400 hover:bg-red-50 hover:text-red-600" aria-label="Delete resume">
                <Trash2 className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function Card({ icon: Icon, title, children, onAdd }: { icon: typeof User2; title: string; children: React.ReactNode; onAdd?: () => void }) {
  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="inline-flex items-center gap-2 text-sm font-black uppercase tracking-wide text-slate-500">
          <Icon className="h-4 w-4 text-slate-400" /> {title}
        </h2>
        {onAdd && (
          <button onClick={onAdd} className="inline-flex items-center gap-1 rounded-xl border border-slate-200 px-3 py-1 text-sm font-bold text-slate-700 hover:bg-slate-50">
            <Plus className="h-4 w-4" /> Add
          </button>
        )}
      </div>
      {children}
    </section>
  );
}

function RowCard({ children, onRemove }: { children: React.ReactNode; onRemove: () => void }) {
  return (
    <div className="relative rounded-2xl border border-slate-200 p-4">
      <button onClick={onRemove} className="absolute right-3 top-3 grid h-8 w-8 place-items-center rounded-xl text-slate-400 hover:bg-red-50 hover:text-red-600" aria-label="Remove">
        <Trash2 className="h-4 w-4" />
      </button>
      {children}
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return <span className="block text-xs font-bold uppercase text-slate-500">{children}</span>;
}

function Field({ label, value, onChange, type = 'text', placeholder }: { label: string; value: string; onChange: (v: string) => void; type?: string; placeholder?: string }) {
  return (
    <label className="block">
      <Label>{label}</Label>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
      />
    </label>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="text-sm text-slate-400">{text}</p>;
}

function TagInput({ values, onChange, placeholder }: { values: string[]; onChange: (v: string[]) => void; placeholder?: string }) {
  const [draft, setDraft] = useState('');
  function commit() {
    const v = draft.trim();
    if (v && !values.includes(v)) onChange([...values, v]);
    setDraft('');
  }
  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {values.map((v) => (
          <span key={v} className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 text-sm font-bold text-slate-800">
            {v}
            <button onClick={() => onChange(values.filter((x) => x !== v))} className="text-slate-400 hover:text-red-600" aria-label={`Remove ${v}`}>×</button>
          </span>
        ))}
      </div>
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); commit(); } }}
        onBlur={commit}
        placeholder={placeholder}
        className="mt-2 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm focus:border-slate-400 focus:outline-none"
      />
    </div>
  );
}
