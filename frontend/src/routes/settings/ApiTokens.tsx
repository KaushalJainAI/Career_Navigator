import { useEffect, useState } from 'react';
import { ApiTokens } from '../../api/endpoints';

type TokenRow = {
  id: number;
  name: string;
  last_used_at: string | null;
  created_at: string;
};

export function ApiTokensPage() {
  const [tokens, setTokens] = useState<TokenRow[]>([]);
  const [name, setName] = useState('Browser extension');
  const [newToken, setNewToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    ApiTokens.list()
      .then((data) => setTokens(data.results ?? data))
      .catch(() => setError('Could not load API tokens.'));
  }, []);

  async function handleCreate() {
    setError(null);
    setNewToken(null);
    try {
      const created = await ApiTokens.create(name);
      setNewToken(created.token);
      setTokens((rows) => [
        { id: created.id, name: created.name, last_used_at: null, created_at: created.created_at },
        ...rows,
      ]);
    } catch {
      setError('Could not create token. Check that you are signed in.');
    }
  }

  async function handleRevoke(id: number) {
    await ApiTokens.revoke(id);
    setTokens((rows) => rows.filter((r) => r.id !== id));
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-black text-slate-900">Browser extension tokens</h1>
        <p className="mt-1 text-sm text-slate-600">
          Long-lived API tokens for the Career Navigator browser extension. The
          cleartext token is shown once on creation — copy it immediately.
        </p>
      </header>

      <section className="rounded-3xl bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex-1 min-w-60">
            <span className="block text-xs font-bold uppercase text-slate-500">Name</span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm"
              placeholder="e.g. Chrome on laptop"
            />
          </label>
          <button
            onClick={handleCreate}
            className="rounded-2xl bg-slate-950 px-4 py-2 text-sm font-black text-white hover:bg-slate-800"
          >
            Create token
          </button>
        </div>

        {newToken && (
          <div className="mt-4 rounded-2xl border-2 border-teal-400 bg-teal-50 p-4">
            <p className="text-xs font-black uppercase text-teal-700">
              Copy this token — it will not be shown again
            </p>
            <pre className="mt-2 overflow-x-auto rounded-xl bg-white p-3 text-xs font-mono">
              {newToken}
            </pre>
          </div>
        )}

        {error && (
          <p className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>
        )}
      </section>

      <section className="rounded-3xl bg-white p-5 shadow-sm">
        <h2 className="text-sm font-black uppercase text-slate-500">Active tokens</h2>
        {tokens.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">No tokens yet.</p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-100">
            {tokens.map((t) => (
              <li key={t.id} className="flex items-center justify-between py-3">
                <div>
                  <p className="font-bold text-slate-900">{t.name}</p>
                  <p className="text-xs text-slate-500">
                    Created {new Date(t.created_at).toLocaleString()} •{' '}
                    {t.last_used_at
                      ? `Last used ${new Date(t.last_used_at).toLocaleString()}`
                      : 'Never used'}
                  </p>
                </div>
                <button
                  onClick={() => handleRevoke(t.id)}
                  className="rounded-xl border border-red-200 px-3 py-1 text-sm font-bold text-red-600 hover:bg-red-50"
                >
                  Revoke
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
