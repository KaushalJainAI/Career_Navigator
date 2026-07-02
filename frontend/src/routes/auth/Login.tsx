import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Globe2, Lock, Mail, Sparkles, Target } from 'lucide-react';
import { buildGoogleAuthUrl } from '../../api/endpoints';
import { useAuthStore } from '../../stores/useAuthStore';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [notice, setNotice] = useState('');
  const { login, register, requestPasswordReset, error, loading } = useAuthStore();
  const navigate = useNavigate();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (mode === 'login') await login(email, password);
      else await register(email, password);
      navigate('/');
    } catch {
      return;
    }
  }

  async function onForgotPassword() {
    if (!email) {
      setNotice('Enter your email first and we will send the reset link.');
      return;
    }
    try {
      const message = await requestPasswordReset(email);
      setNotice(message);
    } catch {
      return;
    }
  }

  return (
    <div className="auth-stage -m-4 min-h-screen overflow-hidden bg-[#f7f4ee] text-slate-950 sm:-m-6">
      <div className="pointer-events-none absolute inset-0">
        <div className="career-orbit career-orbit-one" />
        <div className="career-orbit career-orbit-two" />
        <div className="career-ribbon" />
      </div>
      <main className="relative grid min-h-screen grid-cols-1 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="flex flex-col justify-between px-4 py-6 sm:px-10 lg:px-14">
          <div className="flex items-center gap-3 font-black tracking-tight">
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-slate-950 text-white shadow-[6px_6px_0_#2dd4bf]">
              <Target className="h-5 w-5" />
            </div>
            Career Navigator
          </div>

          <div className="max-w-2xl py-8 sm:py-12">
            <div className="mb-5 inline-flex max-w-full items-center gap-2 rounded-full border border-slate-900/10 bg-white/70 px-3 py-1 text-sm font-semibold text-slate-700 shadow-sm">
              <Sparkles className="h-4 w-4 text-amber-500" />
              <span className="truncate">Your next role deserves momentum</span>
            </div>
            <h1 className="max-w-xl text-4xl font-black leading-tight tracking-tight text-slate-950 sm:text-6xl sm:leading-[0.98]">
              Turn job search chaos into a daily win streak.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-slate-700 sm:mt-6 sm:text-lg sm:leading-8">
              Track matches, tailor resumes, prepare interviews, and get alerts before the good opportunities go cold.
            </p>
            <div className="mt-8 grid max-w-xl gap-3 sm:grid-cols-3">
              {['Matched roles', 'Smart reminders', 'Interview reps'].map((item) => (
                <div key={item} className="flex items-center gap-2 rounded-2xl bg-white/75 px-4 py-3 text-sm font-bold shadow-sm">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="hidden max-w-xl rounded-[2rem] border border-slate-900/10 bg-slate-950 p-5 text-white shadow-2xl sm:block">
            <div className="mb-3 text-sm text-teal-200">Today&apos;s nudge</div>
            <div className="text-2xl font-black">Apply to three strong-fit roles before lunch.</div>
            <div className="mt-4 h-2 rounded-full bg-white/10">
              <div className="h-2 w-2/3 rounded-full bg-teal-300" />
            </div>
          </div>
        </section>

        <section className="flex items-center justify-center px-4 pb-8 sm:px-6 lg:py-10">
          <form onSubmit={onSubmit} className="relative w-full max-w-md rounded-[1.5rem] border border-white/70 bg-white/85 p-5 shadow-[0_30px_90px_rgba(15,23,42,0.18)] backdrop-blur-xl sm:rounded-[2rem] sm:p-7">
            <div className="absolute -right-2 -top-4 grid h-14 w-14 rotate-6 place-items-center rounded-[1.25rem] bg-amber-300 text-sm font-black shadow-xl sm:-right-5 sm:-top-5 sm:h-20 sm:w-20 sm:rounded-[1.5rem] sm:text-base">
              Hired
            </div>
            <h2 className="pr-12 text-2xl font-black tracking-tight sm:pr-0 sm:text-3xl">{mode === 'login' ? 'Welcome back' : 'Create your launchpad'}</h2>
            <p className="mt-2 text-sm text-slate-600">Keep your pipeline warm and your confidence warmer.</p>

            <label className="mt-7 block text-sm font-bold text-slate-700" htmlFor="email">Email</label>
            <div className="mt-2 flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 focus-within:border-teal-500 focus-within:ring-4 focus-within:ring-teal-100">
              <Mail className="h-5 w-5 text-slate-400" />
              <input id="email" className="w-full bg-transparent outline-none" type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>

            <label className="mt-4 block text-sm font-bold text-slate-700" htmlFor="password">Password</label>
            <div className="mt-2 flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 focus-within:border-teal-500 focus-within:ring-4 focus-within:ring-teal-100">
              <Lock className="h-5 w-5 text-slate-400" />
              <input id="password" className="w-full bg-transparent outline-none" type="password" placeholder="At least 8 characters" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>

            {error && <div className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</div>}
            {notice && <div className="mt-4 rounded-2xl bg-teal-50 px-4 py-3 text-sm font-semibold text-teal-800">{notice}</div>}

            <button className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-950 px-5 py-3 font-black text-white shadow-[0_12px_0_#14b8a6] transition hover:-translate-y-0.5 disabled:opacity-60" disabled={loading}>
              {loading ? 'Working...' : mode === 'login' ? 'Log in and move' : 'Create account'}
              <ArrowRight className="h-5 w-5" />
            </button>

            <div className="mt-5 flex flex-col gap-3 text-sm font-bold min-[380px]:flex-row min-[380px]:items-center min-[380px]:justify-between">
              <button type="button" className="text-slate-600 hover:text-slate-950" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
                {mode === 'login' ? 'Need an account?' : 'Have an account?'}
              </button>
              <button type="button" className="text-teal-700 hover:text-teal-900" onClick={onForgotPassword}>
                Forgot password?
              </button>
            </div>

            <div className="my-6 flex items-center gap-3 text-xs font-bold uppercase tracking-[0.2em] text-slate-400">
              <span className="h-px flex-1 bg-slate-200" /> or <span className="h-px flex-1 bg-slate-200" />
            </div>
            <button type="button" className="flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-5 py-3 font-black text-slate-800 hover:bg-slate-50" onClick={() => { window.location.href = buildGoogleAuthUrl(); }}>
              <Globe2 className="h-5 w-5" />
              Continue with Google
            </button>
            <Link className="mt-5 block text-center text-xs font-semibold text-slate-500" to="/reset-password">
              Already have a reset link?
            </Link>
          </form>
        </section>
      </main>
    </div>
  );
}
