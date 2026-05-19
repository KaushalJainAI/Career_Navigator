import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/useAuthStore';
import { buildGoogleAuthUrl } from '../../api/endpoints';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const { login, register, error, loading } = useAuthStore();
  const navigate = useNavigate();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (mode === 'login') await login(email, password);
    else await register(email, password);
    navigate('/');
  }

  return (
    <form onSubmit={onSubmit} className="max-w-sm mx-auto bg-white p-6 rounded shadow space-y-3">
      <h2 className="text-lg font-semibold">{mode === 'login' ? 'Log in' : 'Sign up'}</h2>
      <input className="w-full border p-2 rounded" type="email" placeholder="Email"
             value={email} onChange={(e) => setEmail(e.target.value)} />
      <input className="w-full border p-2 rounded" type="password" placeholder="Password"
             value={password} onChange={(e) => setPassword(e.target.value)} />
      {error && <div className="text-red-600 text-sm">{error}</div>}
      <button className="w-full bg-indigo-600 text-white py-2 rounded" disabled={loading}>
        {loading ? '…' : mode === 'login' ? 'Log in' : 'Create account'}
      </button>
      <button type="button" className="text-sm text-slate-500"
              onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
        {mode === 'login' ? 'Need an account?' : 'Have an account?'}
      </button>
      <div className="flex items-center gap-2 my-2 text-xs text-slate-400">
        <span className="flex-1 h-px bg-slate-200" /> or <span className="flex-1 h-px bg-slate-200" />
      </div>
      <button
        type="button"
        className="w-full border border-slate-300 py-2 rounded hover:bg-slate-50"
        onClick={() => { window.location.href = buildGoogleAuthUrl(); }}
      >
        Continue with Google
      </button>
    </form>
  );
}
