import { useEffect, useState, type FormEvent } from 'react';
import { Check, Plus } from 'lucide-react';
import { Profile } from '../api/endpoints';
import { errorMessage } from '../api/client';
import type { Preference } from '../lib/types';
import { Alert, Button, ChipInput, Field, Spinner, inputCls } from './ui';

const ROLE_SUGGESTIONS = [
  'Software Engineer', 'SDE Intern', 'Graduate Engineer Trainee', 'Data Analyst', 'Frontend Developer', 'Backend Developer',
];
const LOCATION_SUGGESTIONS = ['Bengaluru', 'Hyderabad', 'Pune', 'Remote'];
const SENIORITY_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'Any level' },
  { value: 'intern', label: 'Intern' },
  { value: 'entry', label: 'Entry level (0–1 yrs)' },
  { value: 'mid', label: 'Mid' },
  { value: 'senior', label: 'Senior' },
];

const DEFAULT_PREF: Preference = {
  target_titles: [], locations: [], remote: false, salary_min: null, seniority: '', keywords: [],
  exclude_companies: [], work_auth: '', stealth_mode: false, watch_companies: [], weekly_goal: 5,
};

export function TargetsForm({ onSaved, compact }: { onSaved?: () => void; compact?: boolean }) {
  const [form, setForm] = useState<Preference | null>(null);
  const [savedSnapshot, setSavedSnapshot] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [justSaved, setJustSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Profile.get()
      .then((d: { preference?: Partial<Preference> | null }) => {
        if (cancelled) return;
        // Spread the loaded preference over the defaults so fields this form does not edit
        // (keywords, salary_min, work_auth, stealth_mode, ...) survive the PATCH untouched.
        const pref = { ...DEFAULT_PREF, ...(d.preference ?? {}) } as Preference;
        setForm(pref);
        setSavedSnapshot(JSON.stringify(pref));
      })
      .catch((e) => { if (!cancelled) setLoadError(errorMessage(e, 'Could not load your job preferences.')); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) return <Spinner label="Loading your job targets…" />;
  if (loadError || !form) return <Alert tone="red">{loadError || 'Could not load your job preferences.'}</Alert>;

  const goalValid = Number.isInteger(form.weekly_goal) && form.weekly_goal >= 1 && form.weekly_goal <= 50;
  const dirty = JSON.stringify(form) !== savedSnapshot;

  function update(patch: Partial<Preference>) {
    setForm((f) => (f ? { ...f, ...patch } : f));
    setJustSaved(false);
    setSaveError('');
  }

  function addTo(key: 'target_titles' | 'locations', value: string) {
    const current = form![key];
    if (!current.includes(value)) update({ [key]: [...current, value] } as Partial<Preference>);
  }

  async function save(e?: FormEvent) {
    e?.preventDefault();
    if (!form) return;
    if (form.target_titles.length === 0) {
      setSaveError('Add at least one role you want, for example Software Engineer.');
      return;
    }
    if (!goalValid) {
      setSaveError('Weekly goal must be a whole number from 1 to 50.');
      return;
    }
    setSaving(true);
    setSaveError('');
    try {
      const res = await Profile.patch({ preference: form });
      const pref = { ...DEFAULT_PREF, ...(res?.preference ?? form) } as Preference;
      setForm(pref);
      setSavedSnapshot(JSON.stringify(pref));
      setJustSaved(true);
      onSaved?.();
    } catch (err) {
      setSaveError(errorMessage(err, 'Could not save your job targets. Please try again.'));
    } finally {
      setSaving(false);
    }
  }

  const roleChips = ROLE_SUGGESTIONS.filter((s) => !form.target_titles.includes(s));
  const locationChips = LOCATION_SUGGESTIONS.filter((s) => !form.locations.includes(s));

  return (
    <form onSubmit={save} className={compact ? 'space-y-5' : 'space-y-6'}>
      <div className="space-y-2">
        <ChipInput
          label="Roles you want *"
          value={form.target_titles}
          onChange={(v) => update({ target_titles: v })}
          placeholder="Type a role and press Enter"
        />
        <SuggestionRow label="Quick add" items={roleChips} onPick={(v) => addTo('target_titles', v)} />
      </div>

      <div className="space-y-2">
        <ChipInput
          label="Locations"
          value={form.locations}
          onChange={(v) => update({ locations: v })}
          placeholder="Type a city and press Enter"
        />
        <SuggestionRow label="Quick add" items={locationChips} onPick={(v) => addTo('locations', v)} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Level">
          <select
            value={form.seniority}
            onChange={(e) => update({ seniority: e.target.value })}
            className={inputCls}
          >
            {SENIORITY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </Field>

        <Field
          label="Applications per week"
          hint="Your weekly target on the Today page (1–50)."
        >
          <input
            type="number"
            inputMode="numeric"
            min={1}
            max={50}
            value={Number.isNaN(form.weekly_goal) ? '' : form.weekly_goal}
            onChange={(e) => update({ weekly_goal: e.target.value === '' ? NaN : Number(e.target.value) })}
            className={inputCls}
          />
        </Field>
      </div>

      <label className="flex items-center gap-2.5 text-sm font-medium text-slate-800">
        <input
          type="checkbox"
          checked={form.remote}
          onChange={(e) => update({ remote: e.target.checked })}
          className="h-4 w-4 rounded border-slate-300 text-slate-950 focus:ring-slate-400"
        />
        Open to remote
      </label>

      <div className="space-y-2">
        <ChipInput
          label="Companies to hide"
          value={form.exclude_companies}
          onChange={(v) => update({ exclude_companies: v })}
          placeholder="e.g. your current employer, then press Enter"
        />
        <p className="text-xs text-slate-500">Jobs from these companies will not show in your feed.</p>
      </div>

      <div className="space-y-2">
        <ChipInput
          label="Company job boards to follow"
          value={form.watch_companies}
          onChange={(v) => update({ watch_companies: v })}
          placeholder="greenhouse:stripe or lever:mistral"
        />
        <p className="text-xs text-slate-500">
          Follow a company's public job board: greenhouse:stripe or lever:mistral.
        </p>
      </div>

      {saveError && <Alert tone="red">{saveError}</Alert>}
      {justSaved && !dirty && <Alert tone="green">Saved. Your job feed and daily plan use these from now on.</Alert>}

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" loading={saving}>
          {!saving && justSaved && !dirty && <Check className="h-4 w-4" aria-hidden="true" />}
          {saving ? 'Saving…' : 'Save job targets'}
        </Button>
        {dirty && !saving && <span className="text-xs text-slate-500">You have unsaved changes.</span>}
      </div>
    </form>
  );
}

function SuggestionRow({ label, items, onPick }: { label: string; items: string[]; onPick: (v: string) => void }) {
  if (items.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="mr-1 text-xs text-slate-500">{label}:</span>
      {items.map((item) => (
        <button
          key={item}
          type="button"
          onClick={() => onPick(item)}
          className="inline-flex items-center gap-1 rounded-full border border-dashed border-slate-300 px-2.5 py-0.5 text-xs font-medium text-slate-700 hover:border-teal-500 hover:bg-teal-50 hover:text-teal-800"
        >
          <Plus className="h-3 w-3" aria-hidden="true" /> {item}
        </button>
      ))}
    </div>
  );
}
