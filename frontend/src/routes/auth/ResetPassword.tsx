import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, KeyRound, Mail, ShieldCheck } from 'lucide-react';
import { useAuthStore } from '../../stores/useAuthStore';

type Step = 'email' | 'code' | 'password' | 'done';

export function ResetPassword() {
  const navigate = useNavigate();
  const { requestPasswordReset, verifyPasswordResetOtp, confirmPasswordReset, loading, error } = useAuthStore();

  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [notice, setNotice] = useState('');

  async function requestCode(e: React.FormEvent) {
    e.preventDefault();
    try {
      const detail = await requestPasswordReset(email);
      setNotice(detail);
      setStep('code');
    } catch { /* error surfaced by store */ }
  }

  async function verifyCode(e: React.FormEvent) {
    e.preventDefault();
    try {
      const token = await verifyPasswordResetOtp(email, code.trim());
      setResetToken(token);
      setNotice('');
      setStep('password');
    } catch { /* error surfaced by store */ }
  }

  async function setNewPassword(e: React.FormEvent) {
    e.preventDefault();
    try {
      const detail = await confirmPasswordReset(email, resetToken, password);
      setNotice(detail);
      setStep('done');
      setTimeout(() => navigate('/login'), 1200);
    } catch { /* error surfaced by store */ }
  }

  return (
    <div className="-m-6 grid min-h-screen place-items-center bg-[#f7f4ee] px-6">
      <div className="w-full max-w-md rounded-[2rem] border border-white/70 bg-white/90 p-7 shadow-2xl">
        <Link to="/login" className="mb-6 inline-flex items-center gap-2 text-sm font-bold text-slate-600 hover:text-slate-950">
          <ArrowLeft className="h-4 w-4" />
          Back to login
        </Link>

        <div className="grid h-14 w-14 place-items-center rounded-2xl bg-teal-100 text-teal-700">
          {step === 'email' ? <Mail className="h-7 w-7" /> : step === 'code' ? <ShieldCheck className="h-7 w-7" /> : <KeyRound className="h-7 w-7" />}
        </div>

        <div className="mt-5 flex items-center gap-2 text-[11px] font-black uppercase tracking-widest text-slate-400">
          <span className={step === 'email' ? 'text-teal-700' : ''}>1 Email</span>
          <span>·</span>
          <span className={step === 'code' ? 'text-teal-700' : ''}>2 Code</span>
          <span>·</span>
          <span className={step === 'password' || step === 'done' ? 'text-teal-700' : ''}>3 New password</span>
        </div>

        {step === 'email' && (
          <form onSubmit={requestCode}>
            <h1 className="mt-3 text-3xl font-black tracking-tight">Reset your password</h1>
            <p className="mt-2 text-sm text-slate-600">Enter your email and we&apos;ll send you a 6-digit code.</p>
            <input
              className="mt-6 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
              type="email" placeholder="you@example.com" value={email} required
              onChange={(e) => setEmail(e.target.value)}
            />
            <Actions loading={loading} label="Send code" />
          </form>
        )}

        {step === 'code' && (
          <form onSubmit={verifyCode}>
            <h1 className="mt-3 text-3xl font-black tracking-tight">Enter your code</h1>
            <p className="mt-2 text-sm text-slate-600">
              We sent a 6-digit code to <span className="font-bold">{email}</span>. It expires in 10 minutes.
            </p>
            <input
              className="mt-6 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-center text-2xl font-black tracking-[0.4em] outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
              inputMode="numeric" maxLength={6} placeholder="••••••" value={code} required
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            />
            <button type="button" className="mt-3 text-xs font-bold text-teal-700 hover:text-teal-900" onClick={() => setStep('email')}>
              Use a different email
            </button>
            <Actions loading={loading} label="Verify code" />
          </form>
        )}

        {step === 'password' && (
          <form onSubmit={setNewPassword}>
            <h1 className="mt-3 text-3xl font-black tracking-tight">Set a new password</h1>
            <p className="mt-2 text-sm text-slate-600">Choose a strong password (at least 8 characters).</p>
            <input
              className="mt-6 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
              type="password" minLength={8} placeholder="New password" value={password} required
              onChange={(e) => setPassword(e.target.value)}
            />
            <Actions loading={loading} label="Update password" />
          </form>
        )}

        {step === 'done' && (
          <>
            <h1 className="mt-3 text-3xl font-black tracking-tight">All set 🎉</h1>
            <p className="mt-2 text-sm text-slate-600">{notice || 'Password updated. Redirecting you to login…'}</p>
          </>
        )}

        {error && <div className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</div>}
        {notice && step === 'code' && (
          <div className="mt-4 rounded-2xl bg-teal-50 px-4 py-3 text-sm font-semibold text-teal-800">{notice}</div>
        )}
      </div>
    </div>
  );
}

function Actions({ loading, label }: { loading: boolean; label: string }) {
  return (
    <button className="mt-6 w-full rounded-2xl bg-slate-950 px-5 py-3 font-black text-white shadow-[0_10px_0_#14b8a6] disabled:opacity-60" disabled={loading}>
      {loading ? 'Working…' : label}
    </button>
  );
}
