import { Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { useEffect, type ReactNode } from 'react';
import { Bot, Compass, KanbanSquare, LogOut, Mic2, Settings, Sun, UserRound, Briefcase } from 'lucide-react';
import { useAuthStore } from './stores/useAuthStore';
import { Login } from './routes/auth/Login';
import { ResetPassword } from './routes/auth/ResetPassword';
import { GoogleCallback } from './routes/auth/GoogleCallback';
import { ApiTokensPage } from './routes/settings/ApiTokens';
import { BillingPage } from './routes/settings/BillingPage';
import { SettingsPage } from './routes/settings/SettingsPage';
import { ProfilePage } from './routes/profile/ProfilePage';
import { NetworkGraphPage } from './routes/network/NetworkGraph';
import { TodayPage } from './routes/today/TodayPage';
import { SetupWizard } from './routes/setup/SetupWizard';
import { JobsPage } from './routes/jobs/JobsPage';
import { JobWorkspace } from './routes/jobs/JobWorkspace';
import { PipelinePage } from './routes/pipeline/PipelinePage';
import { PracticePage } from './routes/practice/PracticePage';
import { AssistantPage } from './routes/assistant/AssistantPage';
import { CopilotLauncher } from './components/copilot/CopilotLauncher';

const NAV = [
  { name: 'Today', path: '/', icon: Sun },
  { name: 'Jobs', path: '/jobs', icon: Compass },
  { name: 'Pipeline', path: '/pipeline', icon: KanbanSquare },
  { name: 'Practice', path: '/practice', icon: Mic2 },
  { name: 'Assistant', path: '/assistant', icon: Bot },
  { name: 'Profile', path: '/profile', icon: UserRound },
];

function isActive(pathname: string, path: string) {
  return path === '/' ? pathname === '/' : pathname.startsWith(path);
}

function Shell({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const { pathname } = useLocation();
  if (!user) return <>{children}</>;
  return (
    <div className="min-h-screen lg:flex">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-slate-200 bg-white/70 px-3 py-5 backdrop-blur lg:flex">
        <Link to="/" className="mb-6 flex items-center gap-2.5 px-2 font-bold text-slate-950">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-slate-950 text-teal-300"><Briefcase className="h-5 w-5" /></span>
          Career Navigator
        </Link>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map(({ name, path, icon: Icon }) => (
            <Link key={path} to={path}
              className={`flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition ${
                isActive(pathname, path) ? 'bg-slate-950 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'}`}>
              <Icon className={`h-4 w-4 ${isActive(pathname, path) ? 'text-teal-300' : 'text-slate-400'}`} />
              {name}
            </Link>
          ))}
        </nav>
        <div className="border-t border-slate-200 pt-3">
          <p className="truncate px-3 pb-2 text-xs text-slate-500" title={user.email}>{user.email}</p>
          <Link to="/settings" className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"><Settings className="h-4 w-4 text-slate-400" /> Settings</Link>
          <button onClick={logout} className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm text-slate-600 hover:bg-red-50 hover:text-red-600"><LogOut className="h-4 w-4 text-slate-400" /> Log out</button>
        </div>
      </aside>

      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
        <Link to="/" className="flex items-center gap-2 font-bold text-slate-950">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-slate-950 text-teal-300"><Briefcase className="h-4 w-4" /></span>
          Career Navigator
        </Link>
        <div className="flex items-center gap-1">
          <Link to="/settings" aria-label="Settings" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><Settings className="h-5 w-5" /></Link>
          <button onClick={logout} aria-label="Log out" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><LogOut className="h-5 w-5" /></button>
        </div>
      </header>

      <main className="min-w-0 flex-1 pb-24 lg:pb-10">
        <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</div>
      </main>

      {!pathname.startsWith('/assistant') && <CopilotLauncher />}

      <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/95 px-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur lg:hidden">
        <div className="mx-auto grid max-w-lg grid-cols-6 gap-1">
          {NAV.map(({ name, path, icon: Icon }) => (
            <Link key={path} to={path}
              className={`flex flex-col items-center gap-1 rounded-xl py-1.5 text-[11px] font-medium ${isActive(pathname, path) ? 'bg-slate-950 text-white' : 'text-slate-500'}`}>
              <Icon className="h-5 w-5" />{name}
            </Link>
          ))}
        </div>
      </nav>
    </div>
  );
}

function Protected({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const initialized = useAuthStore((s) => s.initialized);
  if (!initialized) return <div className="p-6 text-sm text-slate-500">{useAuthStore.getState().error ? 'Reconnecting to the server…' : 'Loading…'}</div>;
  return user ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  const user = useAuthStore((s) => s.user);
  const refresh = useAuthStore((s) => s.refresh);
  useEffect(() => { refresh(); }, [refresh]);

  const p = (el: ReactNode) => <Protected>{el}</Protected>;
  return (
    <div className="min-h-screen bg-[#f7f4ee]">
      <Shell>
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/auth/google/callback" element={<GoogleCallback />} />
          <Route path="/" element={p(<TodayPage />)} />
          <Route path="/setup" element={p(<SetupWizard />)} />
          <Route path="/jobs" element={p(<JobsPage />)} />
          <Route path="/jobs/:id" element={p(<JobWorkspace />)} />
          <Route path="/pipeline" element={p(<PipelinePage />)} />
          <Route path="/practice" element={p(<PracticePage />)} />
          <Route path="/assistant" element={p(<AssistantPage />)} />
          <Route path="/profile" element={p(<ProfilePage />)} />
          <Route path="/network" element={p(<NetworkGraphPage />)} />
          <Route path="/settings" element={p(<SettingsPage />)} />
          <Route path="/settings/billing" element={p(<BillingPage />)} />
          <Route path="/settings/api-tokens" element={p(<ApiTokensPage />)} />
          {/* old paths */}
          <Route path="/applications" element={<Navigate to="/pipeline" replace />} />
          <Route path="/interview" element={<Navigate to="/practice" replace />} />
          <Route path="/resumes" element={<Navigate to="/profile" replace />} />
          <Route path="/onboarding" element={<Navigate to="/setup" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Shell>
    </div>
  );
}
