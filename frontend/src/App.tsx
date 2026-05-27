import { Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from './stores/useAuthStore';
import { Onboarding } from './routes/onboarding/Onboarding';
import { Dashboard } from './routes/dashboard/Dashboard';
import { JobsList } from './routes/jobs/JobsList';
import { JobDetail } from './routes/jobs/JobDetail';
import { ApplicationsKanban } from './routes/applications/ApplicationsKanban';
import { ResumesPage } from './routes/resumes/ResumesPage';
import { InterviewGrill } from './routes/interview/InterviewGrill';
import { Login } from './routes/auth/Login';
import { ResetPassword } from './routes/auth/ResetPassword';
import { GoogleCallback } from './routes/auth/GoogleCallback';
import { ApiTokensPage } from './routes/settings/ApiTokens';
import { NetworkGraphPage } from './routes/network/NetworkGraph';
import { Briefcase, LayoutDashboard, Send, FileText, Mic2, LogOut, Compass, Bell } from 'lucide-react';
import { useEffect, useState, type ReactNode } from 'react';
import { Notifications } from './api/endpoints';

function AppNavigation() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const location = useLocation();

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Discover Jobs', path: '/jobs', icon: Compass },
    { name: 'Applications', path: '/applications', icon: Send },
    { name: 'Resumes', path: '/resumes', icon: FileText },
    { name: 'Interview Prep', path: '/interview', icon: Mic2 },
  ];

  if (!user) return null;

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3 font-black text-slate-900">
            <div className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-2xl bg-slate-950 text-white shadow-[4px_4px_0_#2dd4bf]">
              <Briefcase className="h-5 w-5" />
            </div>
            <span className="truncate">Career Navigator</span>
          </div>

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

          <div className="ml-auto flex min-w-0 items-center gap-2">
            <NotificationCenter />
            <div className="hidden min-w-0 items-center gap-3 rounded-2xl bg-slate-100 px-3 py-2 sm:flex">
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-amber-300 text-sm font-black text-slate-950">
                {user.email?.[0].toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="max-w-40 truncate text-sm font-bold text-slate-900">{user.email}</p>
                <p className="truncate text-xs font-semibold text-slate-500">Job Seeker Tier</p>
              </div>
            </div>
            <button
              onClick={logout}
              className="grid h-11 w-11 place-items-center rounded-2xl text-slate-500 hover:bg-red-50 hover:text-red-600"
              aria-label="Logout"
              title="Logout"
            >
              <LogOut className="h-5 w-5" />
            </button>
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

function NotificationCenter() {
  const [alerts, setAlerts] = useState<Array<{ id: number; read: boolean; job_title?: string; company_name?: string; channel: string }>>([]);

  useEffect(() => {
    Notifications.alerts().then((data) => setAlerts(data.results || data)).catch(() => undefined);
  }, []);

  const unread = alerts.filter((alert) => !alert.read).length;

  async function markRead(id: number) {
    await Notifications.markRead(id);
    setAlerts((items) => items.map((item) => (item.id === id ? { ...item, read: true } : item)));
  }

  return (
    <button
      onClick={() => alerts[0] && markRead(alerts[0].id)}
      className="relative grid h-11 w-11 place-items-center rounded-2xl bg-slate-100 text-slate-600 hover:bg-slate-200"
      aria-label={`${unread} unread alerts`}
      title={alerts[0] ? `${alerts[0].job_title || 'New job match'} - ${alerts[0].company_name || alerts[0].channel}` : 'No alerts yet'}
    >
      <Bell className="h-5 w-5" />
      {unread > 0 && (
        <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-teal-300 px-1 text-[10px] font-black text-slate-950">
          {unread}
        </span>
      )}
    </button>
  );
}

export default function App() {
  const user = useAuthStore((s) => s.user);
  const initialized = useAuthStore((s) => s.initialized);
  const refresh = useAuthStore((s) => s.refresh);

  useEffect(() => {
    refresh();
  }, [refresh]);
  
  return (
    <div className="min-h-screen bg-[#f7f4ee] flex flex-col md:flex-row">
      <AppNavigation />
      <main className="min-w-0 flex-1 pb-24 lg:pb-0">
        <div className="mx-auto w-full max-w-7xl p-4 sm:p-6">
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
            <Route path="/resumes" element={<ProtectedRoute initialized={initialized} user={user}><ResumesPage /></ProtectedRoute>} />
            <Route path="/interview" element={<ProtectedRoute initialized={initialized} user={user}><InterviewGrill /></ProtectedRoute>} />
            <Route path="/network" element={<ProtectedRoute initialized={initialized} user={user}><NetworkGraphPage /></ProtectedRoute>} />
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
