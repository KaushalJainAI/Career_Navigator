import { useEffect, useState } from 'react';
import { Coins, Infinity as InfinityIcon, Gift, ShieldCheck } from 'lucide-react';
import { Billing } from '../../api/endpoints';
import { useBillingStore } from '../../stores/useBillingStore';

interface LedgerRow {
  id: number;
  delta: number;
  reason: string;
  created_at: string;
}

interface PricingItem {
  reason: string;
  label: string;
  cost: number;
  blurb: string;
}

const REASON_LABELS: Record<string, string> = {
  signup_bonus: 'Welcome bonus',
  top_up: 'Top-up',
  tailor_resume: 'Tailored resume',
  cover_letter: 'Cover letter',
  mock_interview: 'Interview grill',
  autonomous_apply: 'Autonomous apply',
  refund: 'Refund',
};

export function BillingPage() {
  const [balance, setBalance] = useState(0);
  const [spent, setSpent] = useState(0);
  const [signupBonus, setSignupBonus] = useState(0);
  const [pricing, setPricing] = useState<PricingItem[]>([]);
  const [latest, setLatest] = useState<LedgerRow[]>([]);
  const [amount, setAmount] = useState(250);
  const [status, setStatus] = useState('');
  const refreshStore = useBillingStore((s) => s.refresh);

  async function refresh() {
    const data = await Billing.summary();
    setBalance(data.balance);
    setSpent(data.spent_total ?? 0);
    setSignupBonus(data.signup_bonus ?? 0);
    setPricing(data.pricing ?? []);
    setLatest(data.latest ?? []);
    refreshStore();
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
        <h1 className="text-2xl font-black tracking-tight text-slate-950">Billing &amp; credits</h1>
        <p className="mt-1 text-sm font-semibold text-slate-500">
          Simple, honest pricing — reading and matching jobs is always free; AI actions spend a few credits.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-3xl bg-slate-950 p-5 text-white shadow-sm">
          <p className="inline-flex items-center gap-2 text-sm font-black uppercase text-teal-300"><Coins className="h-4 w-4" /> Balance</p>
          <div className="mt-2 text-5xl font-black">{balance}</div>
          <p className="mt-1 text-sm font-semibold text-slate-400">credits available</p>
        </div>
        <div className="rounded-3xl bg-white p-5 shadow-sm">
          <p className="text-sm font-black uppercase text-slate-500">Spent so far</p>
          <div className="mt-2 text-4xl font-black text-slate-950">{spent}</div>
          <p className="mt-1 text-sm font-semibold text-slate-500">credits used on AI actions</p>
        </div>
        <div className="rounded-3xl bg-white p-5 shadow-sm">
          <p className="inline-flex items-center gap-2 text-sm font-black uppercase text-slate-500"><Gift className="h-4 w-4" /> Welcome bonus</p>
          <div className="mt-2 text-4xl font-black text-slate-950">{signupBonus}</div>
          <p className="mt-1 text-sm font-semibold text-slate-500">credits, granted on sign-up</p>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        <Trust icon={InfinityIcon} title="Credits never expire" body="They roll over indefinitely — use them whenever your search picks up." />
        <Trust icon={ShieldCheck} title="No surprise charges" body="No subscription and no card on file. You only ever spend what you top up." />
        <Trust icon={Coins} title="You see costs upfront" body="Every paid action shows its credit cost before you click." />
      </section>

      <section className="rounded-3xl bg-white p-5 shadow-sm">
        <h2 className="text-sm font-black uppercase text-slate-500">What actions cost</h2>
        <ul className="mt-3 divide-y divide-slate-100">
          {pricing.map((item) => (
            <li key={item.reason} className="flex items-start justify-between gap-4 py-3">
              <div>
                <p className="font-black text-slate-900">{item.label}</p>
                <p className="text-sm text-slate-500">{item.blurb}</p>
              </div>
              <span className="mt-0.5 inline-flex flex-shrink-0 items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-sm font-black text-amber-700">
                <Coins className="h-3.5 w-3.5" />{item.cost}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-3xl bg-white p-5 shadow-sm">
        <h2 className="text-sm font-black uppercase text-slate-500">Add credits</h2>
        <p className="mt-1 text-sm font-semibold text-slate-400">Stripe checkout is coming; for now credits are added directly.</p>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <label>
            <span className="block text-xs font-bold uppercase text-slate-500">Amount</span>
            <input className="mt-1 w-40 rounded-2xl border border-slate-200 px-3 py-2 text-sm" type="number" value={amount} onChange={(e) => setAmount(Number(e.target.value))} />
          </label>
          <button onClick={topUp} className="rounded-2xl bg-slate-950 px-4 py-2 text-sm font-black text-white shadow-[0_4px_0_#2dd4bf] hover:bg-slate-800">Add credits</button>
          {status && <span className="text-sm font-semibold text-slate-600">{status}</span>}
        </div>
      </section>

      <section className="rounded-3xl bg-white p-5 shadow-sm">
        <h2 className="text-sm font-black uppercase text-slate-500">Recent activity</h2>
        {latest.length === 0 ? (
          <p className="mt-3 text-sm text-slate-400">No ledger entries yet.</p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-100">
            {latest.map((row) => (
              <li key={row.id} className="flex items-center justify-between py-3 text-sm">
                <span className="font-bold text-slate-800">{REASON_LABELS[row.reason] ?? row.reason}</span>
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

function Trust({ icon: Icon, title, body }: { icon: typeof Coins; title: string; body: string }) {
  return (
    <div className="rounded-3xl bg-white p-4 shadow-sm">
      <Icon className="h-5 w-5 text-teal-600" />
      <p className="mt-2 text-sm font-black text-slate-900">{title}</p>
      <p className="mt-1 text-xs font-semibold text-slate-500">{body}</p>
    </div>
  );
}
