import { Routes, Route, Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from './stores/useAuthStore';
import { Onboarding } from './routes/onboarding/Onboarding';
import { Dashboard } from './routes/dashboard/Dashboard';
import { JobsList } from './routes/jobs/JobsList';
import { JobDetail } from './routes/jobs/JobDetail';
import { ApplicationsKanban } from './routes/applications/ApplicationsKanban';
import { ConnectionsPage } from './routes/network/ConnectionsPage';
import { InterviewGrill } from './routes/interview/InterviewGrill';
import { Login } from './routes/auth/Login';
import { ResetPassword } from './routes/auth/ResetPassword';
import { GoogleCallback } from './routes/auth/GoogleCallback';
import { ApiTokensPage } from './routes/settings/ApiTokens';
import { BillingPage } from './routes/settings/BillingPage';
import { SettingsPage } from './routes/settings/SettingsPage';
import { ProfilePage } from './routes/profile/ProfilePage';
import { NetworkGraphPage } from './routes/network/NetworkGraph';
import { CompaniesPage } from './routes/companies/CompaniesPage';
import { CompanyDetailPage } from './routes/companies/CompanyDetailPage';
import { Briefcase, LayoutDashboard, Send, Users, Mic2, Compass, Bell, Settings, Sun, Moon, TrendingUp, FileText, Activity, LayoutGrid, Coins, KeyRound, Network as NetworkIcon, Sparkles, Building2 } from 'lucide-react';
import { useThemeStore, resolveTheme } from './lib/theme';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Notifications } from './api/endpoints';
import { CreditBalancePill } from './components/Credits';
import { useBillingStore } from './stores/useBillingStore';

function AppNavigation() {
  const user = useAuthStore((s) => s.user);
  const refreshBalance = useBillingStore((s) => s.refresh);
  const pathname = useLocation().pathname;
  // Keep the balance chip fresh as the user moves between pages (spends happen elsewhere).
  useEffect(() => { if (user) refreshBalance(); }, [user, pathname, refreshBalance]);
  const location = useLocation();

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Discover Jobs', path: '/jobs', icon: Compass },
    { name: 'Applications', path: '/applications', icon: Send },
    { name: 'Connections', path: '/connections', icon: Users },
    { name: 'Interview Prep', path: '/interview', icon: Mic2 },
  ];

  if (!user) return null;

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3 sm:px-6">
          <Link to="/" className="flex flex-shrink-0 items-center gap-3 font-black text-slate-900">
            <div className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-2xl bg-slate-950 text-white shadow-[4px_4px_0_#2dd4bf]">
              <Briefcase className="h-5 w-5" />
            </div>
            <span className="hidden whitespace-nowrap sm:inline">Career Navigator</span>
          </Link>

          <nav className="hidden flex-1 items-center justify-center gap-1 lg:flex">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
              return (
                <Link
                  key={item.name}
                  to={item.path}
                  className={`inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-sm font-black transition ${
                    isActive
                      ? 'bg-slate-950 text-white shadow-[0_4px_0_#2dd4bf]'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? 'text-teal-300' : 'text-slate-400'}`} />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto flex flex-shrink-0 items-center gap-2">
            <CreditBalancePill />
            <NotificationCenter />
            <Link
              to="/profile"
              className={`grid h-11 w-11 flex-shrink-0 place-items-center rounded-2xl transition ${
                location.pathname.startsWith('/profile') ? 'ring-2 ring-slate-950 ring-offset-2' : 'hover:opacity-80'
              }`}
              aria-label="Your profile"
              title={`${user.email} · ${user.cn_profile?.tier ?? 'Free'} Tier`}
            >
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-amber-300 text-sm font-black text-slate-950">
                {user.email?.[0].toUpperCase()}
              </span>
            </Link>
            <MoreMenu email={user.email} tier={user.cn_profile?.tier ?? 'Free'} />
          </div>
        </div>
      </header>

      <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/95 px-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-2 shadow-[0_-10px_30px_rgba(15,23,42,0.08)] backdrop-blur lg:hidden">
        <div className="mx-auto grid max-w-lg grid-cols-5 gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
            return (
              <Link
                key={item.name}
                to={item.path}
                className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-2xl px-1 text-[11px] font-black leading-tight transition ${
                  isActive ? 'bg-slate-950 text-white' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <Icon className={`h-5 w-5 ${isActive ? 'text-teal-300' : 'text-slate-400'}`} />
                <span className="max-w-full truncate">{item.name.replace('Discover ', '').replace('Interview ', '')}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}

const MORE_LINKS: { to: string; label: string; desc: string; icon: typeof Coins }[] = [
  { to: '/companies', label: 'Companies', desc: 'Connections, careers & opportunities', icon: Building2 },
  { to: '/network', label: 'Network graph', desc: 'Explore & build your connections', icon: NetworkIcon },
  { to: '/settings/billing', label: 'Billing & credits', desc: 'Balance, pricing and top-ups', icon: Coins },
  { to: '/settings/api-tokens', label: 'Browser extension', desc: 'API tokens for the extension', icon: KeyRound },
  { to: '/onboarding', label: 'Onboarding chat', desc: 'Build your profile by chatting', icon: Sparkles },
  { to: '/settings', label: 'Settings', desc: 'Account, notifications, appearance', icon: Settings },
];

function MoreMenu({ email, tier }: { email?: string; tier?: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const isDark = resolveTheme(theme) === 'dark';

  useEffect(() => {
    function onDoc(e: MouseEvent) { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); }
    function onEsc(e: KeyboardEvent) { if (e.key === 'Escape') setOpen(false); }
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onEsc);
    return () => { document.removeEventListener('mousedown', onDoc); document.removeEventListener('keydown', onEsc); };
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="grid h-11 w-11 place-items-center rounded-2xl bg-slate-100 text-slate-600 hover:bg-slate-200"
        aria-label="More pages"
        aria-expanded={open}
        title="More"
      >
        <LayoutGrid className="h-5 w-5" />
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-2 w-72 max-w-[calc(100vw-2rem)] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl animate-fade-up">
          <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
            <div className="min-w-0 flex-1">
              {email ? <p className="truncate text-sm font-black text-slate-900">{email}</p> : <p className="text-sm font-black text-slate-900">More</p>}
              {email && <p className="text-xs font-semibold capitalize text-slate-500">{tier ?? 'Free'} Tier</p>}
            </div>
            <button
              onClick={() => setTheme(isDark ? 'light' : 'dark')}
              className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-600 hover:bg-slate-200"
              aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              title={isDark ? 'Light mode' : 'Dark mode'}
            >
              {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </div>
          {MORE_LINKS.map((l) => {
            const Icon = l.icon;
            return (
              <Link
                key={l.to}
                to={l.to}
                onClick={() => setOpen(false)}
                className="flex items-start gap-3 border-b border-slate-50 px-4 py-3 transition hover:bg-slate-50"
              >
                <span className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-600">
                  <Icon className="h-4 w-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-bold text-slate-800">{l.label}</p>
                  <p className="text-xs font-semibold text-slate-500">{l.desc}</p>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

type ActivityKind = 'alert' | 'status' | 'material' | 'apply' | 'activity';

interface ActivityItem {
  key: string;
  kind: ActivityKind;
  title: string;
  subtitle?: string;
  url?: string;
  at?: string;
  read: boolean;
  alert_id?: number;
}

const KIND_ICON: Record<ActivityKind, typeof Bell> = {
  alert: Briefcase,
  status: TrendingUp,
  material: FileText,
  apply: Send,
  activity: Activity,
};

const KIND_TONE: Record<ActivityKind, string> = {
  alert: 'bg-teal-100 text-teal-700',
  status: 'bg-sky-100 text-sky-700',
  material: 'bg-violet-100 text-violet-700',
  apply: 'bg-amber-100 text-amber-700',
  activity: 'bg-slate-100 text-slate-600',
};

function timeAgo(iso?: string): string {
  if (!iso) return '';
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return 'just now';
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return d === 1 ? 'yesterday' : `${d}d ago`;
}

function NotificationCenter() {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const load = () =>
    Notifications.activity()
      .then((data) => { setItems(data.items ?? []); setUnread(data.unread ?? 0); })
      .catch(() => undefined);
  useEffect(() => { load(); }, []);

  useEffect(() => {
    function onDoc(e: MouseEvent) { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); }
    function onEsc(e: KeyboardEvent) { if (e.key === 'Escape') setOpen(false); }
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onEsc);
    return () => { document.removeEventListener('mousedown', onDoc); document.removeEventListener('keydown', onEsc); };
  }, []);

  function toggle() { const next = !open; setOpen(next); if (next) load(); }

  async function markRead(alertId: number) {
    await Notifications.markRead(alertId).catch(() => undefined);
    setItems((rows) => rows.map((it) => (it.alert_id === alertId ? { ...it, read: true } : it)));
    setUnread((u) => Math.max(0, u - 1));
  }
  async function markAll() {
    const unreadAlerts = items.filter((it) => it.alert_id && !it.read);
    await Promise.all(unreadAlerts.map((it) => Notifications.markRead(it.alert_id!).catch(() => undefined)));
    setItems((rows) => rows.map((it) => ({ ...it, read: true })));
    setUnread(0);
  }
  function openItem(it: ActivityItem) {
    if (it.kind === 'alert' && it.alert_id && !it.read) markRead(it.alert_id);
    setOpen(false);
    if (it.url) navigate(it.url);
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={toggle}
        className="relative grid h-11 w-11 place-items-center rounded-2xl bg-slate-100 text-slate-600 hover:bg-slate-200"
        aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}
        aria-expanded={open}
      >
        <Bell className="h-5 w-5" />
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-teal-300 px-1 text-[10px] font-black text-slate-950">
            {unread}
          </span>
        )}
      </button>

      {open && (
        <div className="fixed left-1/2 top-16 z-50 max-h-[calc(100vh-5rem)] w-[calc(100vw-1.5rem)] -translate-x-1/2 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl animate-fade-in sm:absolute sm:left-auto sm:right-0 sm:top-auto sm:mt-2 sm:max-h-none sm:w-80 sm:translate-x-0">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <p className="text-sm font-black text-slate-900">Recent activity</p>
            {unread > 0 && (
              <button onClick={markAll} className="text-xs font-black text-teal-700 hover:underline">Mark all read</button>
            )}
          </div>
          <div className="max-h-96 overflow-y-auto">
            {items.length === 0 ? (
              <div className="px-4 py-10 text-center">
                <Bell className="mx-auto h-6 w-6 text-slate-300" />
                <p className="mt-2 text-sm font-bold text-slate-600">You&apos;re all caught up</p>
                <p className="text-xs text-slate-400">Job matches and application activity show up here.</p>
              </div>
            ) : (
              items.map((it) => {
                const Icon = KIND_ICON[it.kind] ?? Activity;
                return (
                  <button
                    key={it.key}
                    onClick={() => openItem(it)}
                    className={`flex w-full items-start gap-3 border-b border-slate-50 px-4 py-3 text-left transition hover:bg-slate-50 ${it.read ? '' : 'bg-teal-50/50'}`}
                  >
                    <span className={`grid h-8 w-8 flex-shrink-0 place-items-center rounded-xl ${KIND_TONE[it.kind]}`}>
                      <Icon className="h-4 w-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-bold text-slate-800">{it.title}</p>
                      <p className="truncate text-xs font-semibold text-slate-500">
                        {[it.subtitle, timeAgo(it.at)].filter(Boolean).join(' · ')}
                      </p>
                    </div>
                    {!it.read && <span className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-teal-500" />}
                  </button>
                );
              })
            )}
          </div>
          <Link
            to="/applications"
            onClick={() => setOpen(false)}
            className="block border-t border-slate-100 px-4 py-2.5 text-center text-xs font-black text-slate-600 hover:bg-slate-50"
          >
            View applications
          </Link>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const user = useAuthStore((s) => s.user);
  const initialized = useAuthStore((s) => s.initialized);
  const refresh = useAuthStore((s) => s.refresh);
  const location = useLocation();

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="flex min-h-screen flex-col bg-[#f7f4ee]">
      <AppNavigation />
      <main className="min-w-0 flex-1 pb-24 lg:pb-0">
        {/* Keyed by path so each navigation re-triggers the entrance animation. */}
        <div key={location.pathname} className="mx-auto w-full max-w-7xl p-4 animate-fade-up sm:p-6">
          <Routes>
            <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/auth/google/callback" element={<GoogleCallback />} />
            <Route path="/onboarding" element={<ProtectedRoute initialized={initialized} user={user}><Onboarding /></ProtectedRoute>} />
            <Route
              path="/"
              element={<ProtectedRoute initialized={initialized} user={user}><Dashboard /></ProtectedRoute>}
            />
            <Route path="/jobs" element={<ProtectedRoute initialized={initialized} user={user}><JobsList /></ProtectedRoute>} />
            <Route path="/jobs/:id" element={<ProtectedRoute initialized={initialized} user={user}><JobDetail /></ProtectedRoute>} />
            <Route path="/applications" element={<ProtectedRoute initialized={initialized} user={user}><ApplicationsKanban /></ProtectedRoute>} />
            <Route path="/connections" element={<ProtectedRoute initialized={initialized} user={user}><ConnectionsPage /></ProtectedRoute>} />
            <Route path="/interview" element={<ProtectedRoute initialized={initialized} user={user}><InterviewGrill /></ProtectedRoute>} />
            <Route path="/network" element={<ProtectedRoute initialized={initialized} user={user}><NetworkGraphPage /></ProtectedRoute>} />
            <Route path="/companies" element={<ProtectedRoute initialized={initialized} user={user}><CompaniesPage /></ProtectedRoute>} />
            <Route path="/companies/:id" element={<ProtectedRoute initialized={initialized} user={user}><CompanyDetailPage /></ProtectedRoute>} />
            <Route path="/profile" element={<ProtectedRoute initialized={initialized} user={user}><ProfilePage /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute initialized={initialized} user={user}><SettingsPage /></ProtectedRoute>} />
            <Route path="/settings/billing" element={<ProtectedRoute initialized={initialized} user={user}><BillingPage /></ProtectedRoute>} />
            <Route path="/settings/api-tokens" element={<ProtectedRoute initialized={initialized} user={user}><ApiTokensPage /></ProtectedRoute>} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

function ProtectedRoute({ initialized, user, children }: { initialized: boolean; user: unknown; children: ReactNode }) {
  if (!initialized) {
    return <div className="rounded-2xl bg-white p-4 text-sm font-semibold text-slate-500 shadow-sm">Loading...</div>;
  }
  return user ? children : <Navigate to="/login" replace />;
}
