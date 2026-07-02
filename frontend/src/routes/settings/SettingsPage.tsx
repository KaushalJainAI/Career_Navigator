import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Account, Notifications } from '../../api/endpoints';
import { useAuthStore } from '../../stores/useAuthStore';
import { Auth } from '../../api/endpoints';
import { UserCog, KeyRound, EyeOff, ChevronRight, Save, Bell, BellRing, Monitor, Moon, Sun, LogOut } from 'lucide-react';
import { disablePush, enablePush, isSubscribed, permissionState, pushSupported } from '../../lib/push';
import { useThemeStore, type Theme } from '../../lib/theme';

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-black tracking-tight text-slate-950">Settings</h1>
        <p className="mt-1 text-sm font-semibold text-slate-500">Your account, notifications, privacy and appearance. Career details live on your <a href="/profile" className="font-black text-slate-900 underline">profile</a>.</p>
      </header>
      <AppearanceSection />
      <AccountSection />
      <PasswordSection />
      <PushNotificationsSection />
      <AlertSubscriptionsSection />
      <PrivacySection />
      <LinksSection />
      <SignOutSection />
    </div>
  );
}

function PushNotificationsSection() {
  const [supported] = useState(pushSupported());
  const [subscribed, setSubscribed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<Status>(null);

  useEffect(() => { isSubscribed().then(setSubscribed).catch(() => undefined); }, []);

  async function turnOn() {
    setBusy(true);
    setStatus(null);
    const result = await enablePush();
    if (result.ok) {
      setSubscribed(true);
      setStatus({ kind: 'ok', text: 'Browser notifications are on — we\'ll ping this device on new matches.' });
    } else {
      const messages: Record<string, string> = {
        unsupported: 'This browser does not support push notifications.',
        denied: 'Notifications are blocked. Enable them in your browser site settings and retry.',
        'server-disabled': 'Push is not configured on the server yet.',
        error: 'Could not enable notifications. Please try again.',
      };
      setStatus({ kind: 'err', text: messages[result.reason] ?? 'Could not enable notifications.' });
    }
    setBusy(false);
  }

  async function turnOff() {
    setBusy(true);
    setStatus(null);
    await disablePush();
    setSubscribed(false);
    setStatus({ kind: 'ok', text: 'Browser notifications turned off for this device.' });
    setBusy(false);
  }

  const blocked = supported && permissionState() === 'denied';

  return (
    <Card icon={BellRing} title="Browser notifications">
      <p className="mb-3 text-sm text-slate-500">
        Get a desktop/phone notification the moment a job matches one of your alerts — even when
        Career Navigator isn't open. Works per-device.
      </p>
      {!supported ? (
        <p className="text-sm font-semibold text-amber-600">This browser doesn't support push notifications.</p>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-black ${subscribed ? 'bg-teal-50 text-teal-700' : 'bg-slate-100 text-slate-600'}`}>
            <span className={`h-2 w-2 rounded-full ${subscribed ? 'bg-teal-500' : 'bg-slate-400'}`} />
            {subscribed ? 'Enabled on this device' : 'Off'}
          </span>
          {subscribed ? (
            <button onClick={turnOff} disabled={busy} className="rounded-2xl border border-slate-200 px-4 py-2 text-sm font-black text-slate-700 hover:bg-slate-50 disabled:opacity-60">
              {busy ? 'Working…' : 'Turn off'}
            </button>
          ) : (
            <button onClick={turnOn} disabled={busy || blocked} className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-2 text-sm font-black text-white shadow-[0_4px_0_#2dd4bf] hover:bg-slate-800 disabled:opacity-60">
              <BellRing className="h-4 w-4" /> {busy ? 'Enabling…' : 'Enable notifications'}
            </button>
          )}
          {status && (
            <span className={`text-sm font-semibold ${status.kind === 'ok' ? 'text-teal-600' : 'text-red-600'}`}>{status.text}</span>
          )}
        </div>
      )}
      {blocked && (
        <p className="mt-2 text-xs font-semibold text-amber-600">
          Notifications are blocked for this site — allow them in your browser's address-bar site settings, then reload.
        </p>
      )}
    </Card>
  );
}

interface AlertSubscription {
  id: number;
  name: string;
  filter_json: { keywords?: string[]; location?: string; remote?: boolean };
  channels: string[];
  enabled: boolean;
}

const CHANNEL_OPTIONS: { key: string; label: string }[] = [
  { key: 'in_app', label: 'In-app' },
  { key: 'webpush', label: 'Browser push' },
  { key: 'email', label: 'Email' },
];

function AlertSubscriptionsSection() {
  const [items, setItems] = useState<AlertSubscription[]>([]);
  const [name, setName] = useState('Remote backend roles');
  const [keywords, setKeywords] = useState<string[]>([]);
  const [location, setLocation] = useState('');
  const [remote, setRemote] = useState(true);
  const [channels, setChannels] = useState<string[]>(['in_app']);
  const [status, setStatus] = useState<Status>(null);
  const [saving, setSaving] = useState(false);

  function toggleChannel(key: string) {
    setChannels((c) => (c.includes(key) ? c.filter((x) => x !== key) : [...c, key]));
  }

  useEffect(() => {
    Notifications.subscriptions()
      .then((data) => setItems(data.results ?? data))
      .catch(() => setStatus({ kind: 'err', text: 'Could not load alert subscriptions.' }));
  }, []);

  async function create() {
    setSaving(true);
    setStatus(null);
    try {
      const created = await Notifications.createSubscription({
        name,
        filter_json: { keywords, location, remote },
        channels: channels.length ? channels : ['in_app'],
        enabled: true,
      });
      setItems((rows) => [created, ...rows]);
      setStatus({ kind: 'ok', text: 'Alert subscription created.' });
    } catch {
      setStatus({ kind: 'err', text: 'Could not create subscription.' });
    } finally {
      setSaving(false);
    }
  }

  async function toggle(item: AlertSubscription) {
    const updated = await Notifications.patchSubscription(item.id, { enabled: !item.enabled });
    setItems((rows) => rows.map((row) => row.id === item.id ? updated : row));
  }

  async function remove(id: number) {
    await Notifications.deleteSubscription(id);
    setItems((rows) => rows.filter((row) => row.id !== id));
  }

  return (
    <Card icon={Bell} title="Alert subscriptions">
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="space-y-3">
          <Field label="Name" value={name} onChange={setName} />
          <div>
            <Label>Keywords</Label>
            <TagInput values={keywords} onChange={setKeywords} placeholder="e.g. Python" />
          </div>
          <Field label="Location" value={location} onChange={setLocation} placeholder="Remote, Bengaluru" />
          <div>
            <Label>Deliver via</Label>
            <div className="mt-1 flex flex-wrap gap-2">
              {CHANNEL_OPTIONS.map((opt) => (
                <button
                  key={opt.key}
                  type="button"
                  onClick={() => toggleChannel(opt.key)}
                  className={`rounded-full px-3 py-1 text-xs font-black transition ${channels.includes(opt.key) ? 'bg-slate-950 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <p className="mt-1 text-xs text-slate-400">Browser push needs notifications enabled above.</p>
          </div>
          <label className="inline-flex items-center gap-2 text-sm font-semibold text-slate-700">
            <input type="checkbox" checked={remote} onChange={(e) => setRemote(e.target.checked)} />
            Remote only
          </label>
          <SaveBar onSave={create} saving={saving} status={status} label="Create alert" />
        </div>
        <div>
          {items.length === 0 ? (
            <p className="text-sm text-slate-400">No alert subscriptions yet.</p>
          ) : (
            <ul className="space-y-2">
              {items.map((item) => (
                <li key={item.id} className="rounded-2xl border border-slate-200 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-bold text-slate-900">{item.name}</p>
                      <p className="text-xs text-slate-500">
                        {(item.filter_json.keywords ?? []).join(', ') || 'Any keyword'} {item.filter_json.location ? `- ${item.filter_json.location}` : ''}
                      </p>
                    </div>
                    <button onClick={() => toggle(item)} className="rounded-xl bg-slate-100 px-3 py-1 text-xs font-black text-slate-700">
                      {item.enabled ? 'Enabled' : 'Paused'}
                    </button>
                  </div>
                  <button onClick={() => remove(item.id)} className="mt-2 text-xs font-bold text-red-600">Delete</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Card>
  );
}

function AccountSection() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const [firstName, setFirstName] = useState(user?.first_name ?? '');
  const [lastName, setLastName] = useState(user?.last_name ?? '');
  const [status, setStatus] = useState<Status>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setFirstName(user?.first_name ?? '');
    setLastName(user?.last_name ?? '');
  }, [user?.first_name, user?.last_name]);

  async function save() {
    setSaving(true);
    setStatus(null);
    try {
      await Account.update({ first_name: firstName, last_name: lastName });
      const me = await Auth.me();
      setUser(me);
      setStatus({ kind: 'ok', text: 'Account updated.' });
    } catch {
      setStatus({ kind: 'err', text: 'Could not update account.' });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card icon={UserCog} title="Account">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="First name" value={firstName} onChange={setFirstName} />
        <Field label="Last name" value={lastName} onChange={setLastName} />
        <label className="block sm:col-span-2">
          <Label>Email</Label>
          <input
            value={user?.email ?? ''}
            disabled
            className="mt-1 w-full cursor-not-allowed rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500"
          />
          <span className="mt-1 block text-xs text-slate-400">Email is tied to sign-in and can't be changed here.</span>
        </label>
      </div>
      <SaveBar onSave={save} saving={saving} status={status} />
    </Card>
  );
}

function PasswordSection() {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [status, setStatus] = useState<Status>(null);
  const [saving, setSaving] = useState(false);

  async function save() {
    setStatus(null);
    if (next !== confirm) {
      setStatus({ kind: 'err', text: 'New passwords do not match.' });
      return;
    }
    setSaving(true);
    try {
      await Account.changePassword(current, next);
      setCurrent(''); setNext(''); setConfirm('');
      setStatus({ kind: 'ok', text: 'Password changed.' });
    } catch (e) {
      const detail = (e as { response?: { data?: Record<string, unknown> } })?.response?.data;
      const msg = (detail?.current_password as string[])?.[0]
        || (detail?.new_password as string[])?.[0]
        || 'Could not change password.';
      setStatus({ kind: 'err', text: msg });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card icon={KeyRound} title="Password">
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Current password" type="password" value={current} onChange={setCurrent} />
        <Field label="New password" type="password" value={next} onChange={setNext} />
        <Field label="Confirm new password" type="password" value={confirm} onChange={setConfirm} />
      </div>
      <SaveBar onSave={save} saving={saving} status={status} label="Update password" />
    </Card>
  );
}

function SignOutSection() {
  const logout = useAuthStore((s) => s.logout);
  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="inline-flex items-center gap-2 text-sm font-black uppercase tracking-wide text-slate-500">
            <LogOut className="h-4 w-4 text-slate-400" /> Session
          </h2>
          <p className="mt-1 text-sm font-semibold text-slate-500">Sign out of Career Navigator on this device.</p>
        </div>
        <button
          onClick={logout}
          className="inline-flex items-center gap-2 rounded-2xl bg-red-50 px-4 py-2 text-sm font-black text-red-600 hover:bg-red-100"
        >
          <LogOut className="h-4 w-4" /> Sign out
        </button>
      </div>
    </section>
  );
}

function AppearanceSection() {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const options: { value: Theme; label: string; icon: typeof Sun }[] = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'system', label: 'System', icon: Monitor },
  ];
  return (
    <Card icon={Moon} title="Appearance">
      <p className="mb-3 text-sm text-slate-500">Choose how Career Navigator looks. “System” follows your device setting.</p>
      <div className="inline-flex flex-wrap gap-2">
        {options.map((o) => {
          const Icon = o.icon;
          const active = theme === o.value;
          return (
            <button
              key={o.value}
              onClick={() => setTheme(o.value)}
              className={`inline-flex items-center gap-2 rounded-2xl px-4 py-2 text-sm font-black transition ${active ? 'bg-slate-950 text-white shadow-[0_4px_0_#2dd4bf]' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
            >
              <Icon className="h-4 w-4" /> {o.label}
            </button>
          );
        })}
      </div>
    </Card>
  );
}

function PrivacySection() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const [domains, setDomains] = useState<string[]>(user?.cn_profile?.stealth_domains ?? []);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<Status>(null);

  useEffect(() => { setDomains(user?.cn_profile?.stealth_domains ?? []); }, [user?.cn_profile?.stealth_domains]);

  async function save() {
    setSaving(true);
    setStatus(null);
    try {
      await Account.update({ stealth_domains: domains });
      const me = await Auth.me();
      setUser(me);
      setStatus({ kind: 'ok', text: 'Stealth list saved.' });
    } catch {
      setStatus({ kind: 'err', text: 'Could not save stealth list.' });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card icon={EyeOff} title="Privacy & stealth">
      <p className="mb-3 text-sm text-slate-500">
        Jobs from these company domains are never ingested, matched or shown to you — useful for hiding your search from your current employer.
      </p>
      <Label>Blocked company domains</Label>
      <TagInput values={domains} onChange={setDomains} placeholder="e.g. currentemployer.com" />
      <SaveBar onSave={save} saving={saving} status={status} label="Save stealth list" />
    </Card>
  );
}

function LinksSection() {
  return (
    <Card icon={KeyRound} title="More">
      <Link to="/settings/api-tokens" className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 text-sm font-bold text-slate-800 hover:bg-slate-50">
        Browser extension API tokens
        <ChevronRight className="h-4 w-4 text-slate-400" />
      </Link>
      <Link to="/settings/billing" className="mt-2 flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 text-sm font-bold text-slate-800 hover:bg-slate-50">
        Billing and credits
        <ChevronRight className="h-4 w-4 text-slate-400" />
      </Link>
    </Card>
  );
}

// ---- shared bits ----

type Status = { kind: 'ok' | 'err'; text: string } | null;

function Card({ icon: Icon, title, children }: { icon: typeof UserCog; title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-3xl bg-white p-5 shadow-sm">
      <h2 className="mb-4 inline-flex items-center gap-2 text-sm font-black uppercase tracking-wide text-slate-500">
        <Icon className="h-4 w-4 text-slate-400" /> {title}
      </h2>
      {children}
    </section>
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

function SaveBar({ onSave, saving, status, label = 'Save changes' }: { onSave: () => void; saving: boolean; status: Status; label?: string }) {
  return (
    <div className="mt-4 flex flex-wrap items-center gap-3">
      <button
        onClick={onSave}
        disabled={saving}
        className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-2 text-sm font-black text-white shadow-[0_4px_0_#2dd4bf] hover:bg-slate-800 disabled:opacity-60"
      >
        <Save className="h-4 w-4" /> {saving ? 'Saving…' : label}
      </button>
      {status && (
        <span className={`text-sm font-semibold ${status.kind === 'ok' ? 'text-teal-600' : 'text-red-600'}`}>{status.text}</span>
      )}
    </div>
  );
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
