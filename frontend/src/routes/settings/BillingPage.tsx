import { useEffect, useState } from 'react';
import { Billing } from '../../api/endpoints';

interface LedgerRow {
  id: number;
  delta: number;
  reason: string;
  created_at: string;
}

export function BillingPage() {
  const [balance, setBalance] = useState(0);
  const [latest, setLatest] = useState<LedgerRow[]>([]);
  const [amount, setAmount] = useState(250);
  const [status, setStatus] = useState('');

  async function refresh() {
    const data = await Billing.summary();
    setBalance(data.balance);
    setLatest(data.latest ?? []);
  }

  useEffect(() => { refresh().catch(() => setStatus('Could not load billing.')); }, []);

  async function topUp() {
    setStatus('');
    try {
      await Billing.topUp(amount);
      await refresh();
      setStatus('Credits added.');
    } catch {
      setStatus('Could not add credits.');
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-black tracking-tight text-slate-950">Billing & credits</h1>
        <p className="mt-1 text-sm font-semibold text-slate-500">Stripe checkout is not enabled yet; credits are tracked in the ledger.</p>
      </header>

      <section className="rounded-3xl bg-white p-5 shadow-sm">
        <p className="text-sm font-black uppercase text-slate-500">Current balance</p>
        <div className="mt-2 text-5xl font-black text-slate-950">{balance}</div>
        <p className="mt-1 text-sm font-semibold text-slate-500">credits</p>
      </section>

      <section className="rounded-3xl bg-white p-5 shadow-sm">
        <h2 className="text-sm font-black uppercase text-slate-500">Manual top-up</h2>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <label>
            <span className="block text-xs font-bold uppercase text-slate-500">Amount</span>
            <input className="mt-1 w-40 rounded-2xl border border-slate-200 px-3 py-2 text-sm" type="number" value={amount} onChange={(e) => setAmount(Number(e.target.value))} />
          </label>
          <button onClick={topUp} className="rounded-2xl bg-slate-950 px-4 py-2 text-sm font-black text-white">Add credits</button>
          {status && <span className="text-sm font-semibold text-slate-600">{status}</span>}
        </div>
      </section>

      <section className="rounded-3xl bg-white p-5 shadow-sm">
        <h2 className="text-sm font-black uppercase text-slate-500">Recent ledger</h2>
        {latest.length === 0 ? (
          <p className="mt-3 text-sm text-slate-400">No ledger entries yet.</p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-100">
            {latest.map((row) => (
              <li key={row.id} className="flex items-center justify-between py-3 text-sm">
                <span className="font-bold text-slate-800">{row.reason}</span>
                <span className={row.delta >= 0 ? 'font-black text-teal-700' : 'font-black text-red-600'}>
                  {row.delta >= 0 ? '+' : ''}{row.delta}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
