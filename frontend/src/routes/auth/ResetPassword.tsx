import { useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, KeyRound } from 'lucide-react';
import { useAuthStore } from '../../stores/useAuthStore';

export function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const { confirmPasswordReset, loading, error } = useAuthStore();
  const uid = useMemo(() => params.get('uid') || '', [params]);
  const token = useMemo(() => params.get('token') || '', [params]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const detail = await confirmPasswordReset(uid, token, password);
      setMessage(detail);
      setTimeout(() => navigate('/login'), 900);
    } catch {
      return;
    }
  }

  return (
    <div className="-m-6 grid min-h-screen place-items-center bg-[#f7f4ee] px-6">
      <form onSubmit={onSubmit} className="w-full max-w-md rounded-[2rem] border border-white/70 bg-white/90 p-7 shadow-2xl">
        <Link to="/login" className="mb-6 inline-flex items-center gap-2 text-sm font-bold text-slate-600 hover:text-slate-950">
          <ArrowLeft className="h-4 w-4" />
          Back to login
        </Link>
        <div className="grid h-14 w-14 place-items-center rounded-2xl bg-teal-100 text-teal-700">
          <KeyRound className="h-7 w-7" />
        </div>
        <h1 className="mt-5 text-3xl font-black tracking-tight">Set a new password</h1>
        <p className="mt-2 text-sm text-slate-600">Choose a strong password and get back to your job search plan.</p>
        <input
          className="mt-6 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
          type="password"
          minLength={8}
          placeholder="New password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <div className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</div>}
        {message && <div className="mt-4 rounded-2xl bg-teal-50 px-4 py-3 text-sm font-semibold text-teal-800">{message}</div>}
        <button className="mt-6 w-full rounded-2xl bg-slate-950 px-5 py-3 font-black text-white shadow-[0_10px_0_#14b8a6]" disabled={loading || !uid || !token}>
          {loading ? 'Updating...' : 'Update password'}
        </button>
      </form>
    </div>
  );
}
