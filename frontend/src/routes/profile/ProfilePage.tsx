import { useEffect, useState, type ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { Briefcase, FileText, FolderGit2, GraduationCap, Plus, Save, Sparkles, Star, Trash2, User2 } from 'lucide-react';
import { Profile, Resumes } from '../../api/endpoints';
import { errorMessage } from '../../api/client';
import { ResumeImport } from '../../components/ResumeImport';
import { TargetsForm } from '../../components/TargetsForm';
import { Alert, Badge, Button, Card, ChipInput, EmptyState, Field, PageHeader, Spinner, inputCls, timeAgo } from '../../components/ui';
import type { ResumeUploadResult } from '../../lib/types';

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
  readiness?: { score: number; ready: boolean; missing: string[] };
}

interface ResumeRow {
  id: number;
  label: string;
  parse_status: 'pending' | 'done' | 'failed';
  parse_error: string;
  is_master: boolean;
  created_at: string;
}

type Notice = { kind: 'ok' | 'err' | 'info'; text: string } | null;

const EMPTY: ProfileData = {
  full_name: '', headline: '', summary: '', location: '', phone: '',
  website: '', linkedin: '', github: '',
  experiences: [], educations: [], skills: [], projects: [],
};

const TEXTAREA_CLS = `${inputCls} resize-y leading-relaxed`;

function normalise(d: Partial<ProfileData> | null | undefined): ProfileData {
  const p = d ?? {};
  return {
    ...EMPTY,
    ...p,
    skills: p.skills ?? [],
    experiences: p.experiences ?? [],
    educations: p.educations ?? [],
    projects: p.projects ?? [],
  };
}

function listOf<T>(d: unknown): T[] {
  if (Array.isArray(d)) return d as T[];
  const results = (d as { results?: unknown })?.results;
  return Array.isArray(results) ? (results as T[]) : [];
}

async function fetchProfile(): Promise<ProfileData> {
  return normalise(await Profile.get());
}

async function fetchResumes(): Promise<ResumeRow[]> {
  return listOf<ResumeRow>(await Resumes.list());
}

function formatDate(iso: string): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

export function ProfilePage() {
  const [data, setData] = useState<ProfileData>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  const [resumes, setResumes] = useState<ResumeRow[]>([]);
  const [resumeBusy, setResumeBusy] = useState<number | null>(null);
  const [resumeNotice, setResumeNotice] = useState<Notice>(null);
  const [showImport, setShowImport] = useState(false);
  const [targetsKey, setTargetsKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchProfile(), fetchResumes()])
      .then(([p, r]) => {
        if (cancelled) return;
        setData(p);
        setResumes(r);
      })
      .catch(() => { if (!cancelled) setNotice({ kind: 'err', text: 'Could not load your profile.' }); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  async function refreshProfile() {
    setData(await fetchProfile());
    setDirty(false);
  }

  async function refreshResumes() {
    setResumes(await fetchResumes());
  }

  function set<K extends keyof ProfileData>(key: K, value: ProfileData[K]) {
    setData((d) => ({ ...d, [key]: value }));
    setDirty(true);
  }

  function updateItem<K extends 'experiences' | 'educations' | 'projects'>(key: K, index: number, patch: Partial<ProfileData[K][number]>) {
    setData((d) => ({
      ...d,
      [key]: (d[key] as ProfileData[K]).map((item, i) => (i === index ? { ...item, ...patch } : item)),
    }));
    setDirty(true);
  }

  async function save() {
    setSaving(true);
    setNotice(null);
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
      });
      setData(normalise(saved));
      setDirty(false);
      setNotice({ kind: 'ok', text: 'Profile saved.' });
    } catch (e) {
      setNotice({ kind: 'err', text: errorMessage(e, 'Save failed. Check the highlighted fields and try again.') });
    } finally {
      setSaving(false);
    }
  }

  async function runResumeAction(id: number, action: () => Promise<unknown>, okText: string, reloadProfile: boolean) {
    setResumeBusy(id);
    setResumeNotice(null);
    try {
      await action();
      await refreshResumes();
      if (reloadProfile) {
        if (dirty) {
          setResumeNotice({ kind: 'info', text: `${okText} Your unsaved edits are still on the page. Save them, then refresh to see the imported details.` });
        } else {
          await refreshProfile();
          setResumeNotice({ kind: 'ok', text: okText });
        }
      } else {
        setResumeNotice({ kind: 'ok', text: okText });
      }
    } catch (e) {
      setResumeNotice({ kind: 'err', text: errorMessage(e, 'That did not work. Please try again.') });
    } finally {
      setResumeBusy(null);
    }
  }

  function useAsMaster(r: ResumeRow) {
    void runResumeAction(r.id, () => Resumes.makeMaster(r.id, false), `"${r.label}" is now your master résumé.`, true);
  }

  function reimport(r: ResumeRow) {
    const warning = `Re-import "${r.label}" into your profile?\n\nThis replaces your experiences, education and projects with the ones from this résumé.`
      + (dirty ? '\n\nYour unsaved profile edits will be lost.' : '');
    if (!window.confirm(warning)) return;
    void runResumeAction(
      r.id,
      () => Resumes.makeMaster(r.id, true),
      'Profile re-imported from this résumé.',
      true,
    );
  }

  function remove(r: ResumeRow) {
    if (!window.confirm(`Delete "${r.label}"? This cannot be undone.`)) return;
    void runResumeAction(r.id, () => Resumes.remove(r.id), 'Résumé deleted.', false);
  }

  function toggleImport() {
    setShowImport((v) => !v);
  }

  async function onImported(_r: ResumeUploadResult) {
    setTargetsKey((k) => k + 1);
    try {
      await refreshResumes();
      if (!dirty) await refreshProfile();
    } catch {
      setResumeNotice({ kind: 'err', text: 'Your résumé was added, but the page could not refresh. Reload to see it.' });
    }
  }

  if (loading) return <Spinner label="Loading your profile…" />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Your profile"
        subtitle="This powers résumé tailoring, match scoring and the interview practice."
        actions={
          <Button onClick={save} loading={saving}>
            <Save className="h-4 w-4" aria-hidden="true" /> {saving ? 'Saving…' : 'Save changes'}
          </Button>
        }
      />

      {notice && <Alert tone={notice.kind === 'ok' ? 'green' : notice.kind === 'err' ? 'red' : 'slate'}>{notice.text}</Alert>}
      {dirty && !saving && <p className="-mt-4 text-xs text-slate-500">You have unsaved changes.</p>}

      {/* Résumés */}
      <Section
        icon={FileText}
        title="Résumés"
        hint="The master résumé is used for tailoring. Re-import one to refill your profile from it."
        action={
          <Button variant="secondary" onClick={toggleImport}>
            {showImport ? 'Hide' : <><Plus className="h-4 w-4" aria-hidden="true" /> Add another résumé</>}
          </Button>
        }
      >
        {resumeNotice && <div className="mb-4"><Alert tone={resumeNotice.kind === 'ok' ? 'green' : resumeNotice.kind === 'err' ? 'red' : 'slate'}>{resumeNotice.text}</Alert></div>}

        {resumes.length === 0 && !showImport && (
          <EmptyState
            icon={<FileText className="h-5 w-5" aria-hidden="true" />}
            title="No résumé yet"
            action={<Button onClick={() => setShowImport(true)}>Add your résumé</Button>}
          >
            Upload a PDF, DOCX or TXT file, or paste the text. Your profile fills in from it.
          </EmptyState>
        )}

        {resumes.length > 0 && (
          <ul className="space-y-3">
            {resumes.map((r) => {
              const busy = resumeBusy === r.id;
              const anyBusy = resumeBusy !== null;
              return (
                <li key={r.id} className="flex flex-col gap-3 rounded-2xl border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate font-semibold text-slate-950">{r.label}</p>
                      {r.is_master && <Badge tone="teal"><Star className="h-3 w-3" aria-hidden="true" /> Master</Badge>}
                      <ParseBadge status={r.parse_status} />
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      Added {formatDate(r.created_at)}{r.created_at ? ` · ${timeAgo(r.created_at)}` : ''}
                    </p>
                    {r.parse_status === 'failed' && r.parse_error && (
                      <p className="mt-1 text-xs text-red-700">{r.parse_error}</p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {r.parse_status === 'done' && !r.is_master && (
                      <Button variant="secondary" onClick={() => useAsMaster(r)} loading={busy} disabled={anyBusy && !busy}>
                        Use as master
                      </Button>
                    )}
                    {r.parse_status === 'done' && (
                      <Button variant="secondary" onClick={() => reimport(r)} loading={busy} disabled={anyBusy && !busy}>
                        Re-import into profile
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      onClick={() => remove(r)}
                      disabled={anyBusy}
                      aria-label={`Delete ${r.label}`}
                      className="text-slate-500 hover:bg-red-50 hover:text-red-600"
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        {showImport && (
          <div className="mt-5 border-t border-slate-100 pt-5">
            <ResumeImport onDone={onImported} />
          </div>
        )}
      </Section>

      {/* Job targets */}
      <Section
        icon={Star}
        title="Job targets"
        hint="The roles and places your job feed searches for."
      >
        <TargetsForm key={targetsKey} compact />
      </Section>

      {data.readiness && (
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-slate-950">Profile readiness</h2>
              <p className="mt-1 text-sm text-slate-600">
                {data.readiness.ready ? 'Ready for matching and tailoring.' : 'Add the missing pieces to improve matching.'}
              </p>
            </div>
            <div className="text-3xl font-bold text-slate-950">{Math.round(data.readiness.score * 100)}%</div>
          </div>
          {data.readiness.missing.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {data.readiness.missing.map((item) => <Badge key={item} tone="amber">{item}</Badge>)}
            </div>
          )}
        </Card>
      )}

      {/* Personal info */}
      <Section icon={User2} title="Personal information">
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Full name" value={data.full_name} onChange={(v) => set('full_name', v)} />
          <TextField label="Headline" value={data.headline} onChange={(v) => set('headline', v)} placeholder="Final-year B.Tech, Computer Science" />
          <TextField label="Location" value={data.location} onChange={(v) => set('location', v)} placeholder="Bengaluru, IN" />
          <TextField label="Phone" type="tel" value={data.phone} onChange={(v) => set('phone', v)} />
          <TextField label="Website" type="url" value={data.website} onChange={(v) => set('website', v)} placeholder="https://" />
          <TextField label="LinkedIn" type="url" value={data.linkedin} onChange={(v) => set('linkedin', v)} placeholder="https://linkedin.com/in/…" />
          <TextField label="GitHub" type="url" value={data.github} onChange={(v) => set('github', v)} placeholder="https://github.com/…" />
        </div>
        <div className="mt-4">
          <TextAreaField label="Summary" value={data.summary} onChange={(v) => set('summary', v)} rows={4} placeholder="A short summary of who you are and what you are looking for." />
        </div>
      </Section>

      {/* Skills */}
      <Section icon={Sparkles} title="Skills" hint="Press Enter after each skill.">
        <ChipInput
          value={data.skills.map((s) => s.name)}
          onChange={(names) => set('skills', names.map((name) => data.skills.find((s) => s.name === name) ?? { name }))}
          placeholder="Type a skill, for example Python"
        />
      </Section>

      {/* Experience */}
      <Section
        icon={Briefcase}
        title="Experience"
        hint="Internships and jobs. Leave empty if you have none yet."
        action={<AddButton onClick={() => set('experiences', [...data.experiences, { company: '', title: '', bullets: [] }])} />}
      >
        {data.experiences.length === 0 && <Empty text="No experience added yet." />}
        <div className="space-y-4">
          {data.experiences.map((exp, i) => (
            <RowCard key={i} label="experience" onRemove={() => set('experiences', data.experiences.filter((_, j) => j !== i))}>
              <div className="grid gap-4 sm:grid-cols-2">
                <TextField label="Title" value={exp.title} onChange={(v) => updateItem('experiences', i, { title: v })} placeholder="Software Engineer Intern" />
                <TextField label="Company" value={exp.company} onChange={(v) => updateItem('experiences', i, { company: v })} />
                <TextField label="Location" value={exp.location ?? ''} onChange={(v) => updateItem('experiences', i, { location: v })} />
                <div className="grid grid-cols-2 gap-3">
                  <TextField label="Start" type="date" value={exp.start_date ?? ''} onChange={(v) => updateItem('experiences', i, { start_date: v || null })} />
                  <TextField label="End" type="date" value={exp.end_date ?? ''} onChange={(v) => updateItem('experiences', i, { end_date: v || null })} />
                </div>
              </div>
              <label className="mt-4 inline-flex items-center gap-2.5 text-sm font-medium text-slate-800">
                <input
                  type="checkbox"
                  checked={!!exp.is_current}
                  onChange={(e) => updateItem('experiences', i, { is_current: e.target.checked })}
                  className="h-4 w-4 rounded border-slate-300"
                />
                I currently work here
              </label>
              <div className="mt-4">
                <TextAreaField
                  label="Highlights"
                  hint="One achievement per line. Start with a verb and add a number where you can."
                  value={(exp.bullets ?? []).join('\n')}
                  onChange={(v) => updateItem('experiences', i, { bullets: splitLines(v) })}
                  rows={4}
                />
              </div>
            </RowCard>
          ))}
        </div>
      </Section>

      {/* Education */}
      <Section
        icon={GraduationCap}
        title="Education"
        action={<AddButton onClick={() => set('educations', [...data.educations, { institution: '' }])} />}
      >
        {data.educations.length === 0 && <Empty text="No education added yet." />}
        <div className="space-y-4">
          {data.educations.map((ed, i) => (
            <RowCard key={i} label="education" onRemove={() => set('educations', data.educations.filter((_, j) => j !== i))}>
              <div className="grid gap-4 sm:grid-cols-2">
                <TextField label="Institution" value={ed.institution} onChange={(v) => updateItem('educations', i, { institution: v })} placeholder="College or university" />
                <TextField label="Degree" value={ed.degree ?? ''} onChange={(v) => updateItem('educations', i, { degree: v })} placeholder="B.Tech" />
                <TextField label="Field of study" value={ed.field_of_study ?? ''} onChange={(v) => updateItem('educations', i, { field_of_study: v })} placeholder="Computer Science" />
                <TextField label="GPA / CGPA" value={ed.gpa ?? ''} onChange={(v) => updateItem('educations', i, { gpa: v })} placeholder="8.4 / 10" />
                <TextField label="Start" type="date" value={ed.start_date ?? ''} onChange={(v) => updateItem('educations', i, { start_date: v || null })} />
                <TextField label="End" type="date" value={ed.end_date ?? ''} onChange={(v) => updateItem('educations', i, { end_date: v || null })} />
              </div>
            </RowCard>
          ))}
        </div>
      </Section>

      {/* Projects */}
      <Section
        icon={FolderGit2}
        title="Projects"
        hint="Projects count a lot when you have no work experience. Add the main ones."
        action={<AddButton onClick={() => set('projects', [...data.projects, { name: '', tech_stack: [] }])} />}
      >
        {data.projects.length === 0 && <Empty text="No projects added yet." />}
        <div className="space-y-4">
          {data.projects.map((p, i) => (
            <RowCard key={i} label="project" onRemove={() => set('projects', data.projects.filter((_, j) => j !== i))}>
              <div className="grid gap-4 sm:grid-cols-2">
                <TextField label="Name" value={p.name} onChange={(v) => updateItem('projects', i, { name: v })} />
                <TextField label="URL" type="url" value={p.url ?? ''} onChange={(v) => updateItem('projects', i, { url: v })} placeholder="https://" />
              </div>
              <div className="mt-4">
                <TextAreaField label="Description" value={p.description ?? ''} onChange={(v) => updateItem('projects', i, { description: v })} rows={3} />
              </div>
              <div className="mt-4">
                <ChipInput
                  label="Tech stack"
                  value={p.tech_stack ?? []}
                  onChange={(vals) => updateItem('projects', i, { tech_stack: vals })}
                  placeholder="Type a technology and press Enter"
                />
              </div>
            </RowCard>
          ))}
        </div>
      </Section>

      <div className="flex justify-end">
        <Button onClick={save} loading={saving}>
          <Save className="h-4 w-4" aria-hidden="true" /> {saving ? 'Saving…' : 'Save changes'}
        </Button>
      </div>
    </div>
  );
}

function splitLines(value: string): string[] {
  return value.split('\n').map((l) => l.trim()).filter(Boolean);
}

function Section({ icon: Icon, title, hint, action, children }: {
  icon?: LucideIcon; title: string; hint?: string; action?: ReactNode; children: ReactNode;
}) {
  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-base font-semibold text-slate-950">
            {Icon && <Icon className="h-4 w-4 text-slate-400" aria-hidden="true" />}
            {title}
          </h2>
          {hint && <p className="mt-1 text-sm text-slate-500">{hint}</p>}
        </div>
        {action}
      </div>
      {children}
    </Card>
  );
}

function AddButton({ onClick }: { onClick: () => void }) {
  return (
    <Button variant="secondary" onClick={onClick}>
      <Plus className="h-4 w-4" aria-hidden="true" /> Add
    </Button>
  );
}

function RowCard({ children, onRemove, label }: { children: ReactNode; onRemove: () => void; label: string }) {
  return (
    <div className="relative rounded-2xl border border-slate-200 p-4 pr-14 sm:p-5">
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove this ${label}`}
        className="absolute right-3 top-3 grid h-9 w-9 place-items-center rounded-xl text-slate-400 hover:bg-red-50 hover:text-red-600"
      >
        <Trash2 className="h-4 w-4" aria-hidden="true" />
      </button>
      {children}
    </div>
  );
}

function ParseBadge({ status }: { status: ResumeRow['parse_status'] }) {
  if (status === 'done') return <Badge tone="green">Read</Badge>;
  if (status === 'failed') return <Badge tone="red">Could not read</Badge>;
  return <Badge tone="amber">Reading…</Badge>;
}

function TextField({ label, value, onChange, type = 'text', placeholder }: {
  label: string; value: string; onChange: (v: string) => void; type?: string; placeholder?: string;
}) {
  return (
    <Field label={label}>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className={inputCls}
      />
    </Field>
  );
}

function TextAreaField({ label, value, onChange, rows = 3, placeholder, hint }: {
  label: string; value: string; onChange: (v: string) => void; rows?: number; placeholder?: string; hint?: string;
}) {
  return (
    <Field label={label} hint={hint}>
      <textarea
        value={value}
        rows={rows}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className={TEXTAREA_CLS}
      />
    </Field>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="text-sm text-slate-500">{text}</p>;
}
