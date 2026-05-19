import { Routes, Route, Link, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/useAuthStore';
import { Onboarding } from './routes/onboarding/Onboarding';
import { Dashboard } from './routes/dashboard/Dashboard';
import { JobsList } from './routes/jobs/JobsList';
import { JobDetail } from './routes/jobs/JobDetail';
import { ApplicationsKanban } from './routes/applications/ApplicationsKanban';
import { ResumesPage } from './routes/resumes/ResumesPage';
import { InterviewGrill } from './routes/interview/InterviewGrill';
import { Login } from './routes/auth/Login';
import { GoogleCallback } from './routes/auth/GoogleCallback';

function Nav() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  return (
    <nav className="bg-white border-b px-4 py-3 flex items-center gap-4 text-sm">
      <Link to="/" className="font-bold">Career Navigator</Link>
      <Link to="/jobs">Jobs</Link>
      <Link to="/applications">Applications</Link>
      <Link to="/resumes">Resumes</Link>
      <Link to="/interview">Interview Grill</Link>
      <div className="ml-auto flex items-center gap-3">
        {user ? (
          <>
            <span className="text-slate-500">{user.email}</span>
            <button className="text-red-600" onClick={logout}>Logout</button>
          </>
        ) : (
          <Link to="/login">Login</Link>
        )}
      </div>
    </nav>
  );
}

export default function App() {
  const user = useAuthStore((s) => s.user);
  return (
    <div className="min-h-screen">
      <Nav />
      <main className="p-6 max-w-6xl mx-auto">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/auth/google/callback" element={<GoogleCallback />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route
            path="/"
            element={user ? <Dashboard /> : <Navigate to="/login" replace />}
          />
          <Route path="/jobs" element={<JobsList />} />
          <Route path="/jobs/:id" element={<JobDetail />} />
          <Route path="/applications" element={<ApplicationsKanban />} />
          <Route path="/resumes" element={<ResumesPage />} />
          <Route path="/interview" element={<InterviewGrill />} />
        </Routes>
      </main>
    </div>
  );
}
