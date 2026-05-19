import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../../stores/useAuthStore';

export function GoogleCallback() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const loginWithGoogle = useAuthStore((s) => s.loginWithGoogle);
  const [error, setError] = useState<string | null>(null);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    const code = params.get('code');
    const oauthErr = params.get('error');
    if (oauthErr) {
      setError(oauthErr);
      return;
    }
    if (!code) {
      setError('Missing authorization code.');
      return;
    }
    const redirectUri =
      (import.meta.env.VITE_GOOGLE_REDIRECT_URI as string)
      || `${window.location.origin}/auth/google/callback`;
    loginWithGoogle(code, redirectUri)
      .then(() => navigate('/'))
      .catch((e) => setError((e as Error).message));
  }, [params, loginWithGoogle, navigate]);

  return (
    <section className="max-w-sm mx-auto bg-white p-6 rounded shadow mt-12 text-center">
      {error ? (
        <>
          <h2 className="font-semibold text-red-600">Google sign-in failed</h2>
          <p className="text-sm text-slate-500 mt-2">{error}</p>
        </>
      ) : (
        <p>Signing you in…</p>
      )}
    </section>
  );
}
