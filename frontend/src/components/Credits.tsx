import { Link } from 'react-router-dom';
import { Coins, ArrowUpRight } from 'lucide-react';
import { useBillingStore } from '../stores/useBillingStore';

export interface CreditShortfall {
  cost: number;
  balance: number;
  shortfall: number;
}

/** Detect the backend's HTTP 402 insufficient-credits response. */
export function insufficientCredits(err: unknown): CreditShortfall | null {
  const res = (err as { response?: { status?: number; data?: { code?: string; cost?: number; balance?: number; shortfall?: number } } })?.response;
  if (res?.status === 402 && res.data?.code === 'insufficient_credits') {
    return { cost: res.data.cost ?? 0, balance: res.data.balance ?? 0, shortfall: res.data.shortfall ?? 0 };
  }
  return null;
}

/** Friendly "you're short on credits" banner with a top-up link. */
export function CreditWall({ info }: { info: CreditShortfall }) {
  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm">
      <p className="font-black text-amber-800">Not enough credits</p>
      <p className="mt-1 font-semibold text-amber-700">
        This action costs {info.cost} credits and you have {info.balance}. Add {info.shortfall || info.cost - info.balance} more to continue.
      </p>
      <Link to="/settings/billing" className="mt-3 inline-flex items-center gap-1 rounded-xl bg-slate-950 px-3 py-2 text-xs font-black text-white hover:bg-slate-800">
        Top up credits <ArrowUpRight className="h-3.5 w-3.5" />
      </Link>
    </div>
  );
}

/** A small "N credits" pill shown next to a paid action, so cost is visible
 *  before the user clicks. */
export function CreditCost({ cost, className = '' }: { cost: number; className?: string }) {
  if (!cost) return null;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-black text-amber-700 ${className}`}
      title={`Costs ${cost} credits`}
    >
      <Coins className="h-3 w-3" />
      {cost}
    </span>
  );
}

/** Header balance chip, links to the billing page. */
export function CreditBalancePill() {
  const balance = useBillingStore((s) => s.balance);
  const loaded = useBillingStore((s) => s.loaded);
  if (!loaded || balance === null) return null;
  const low = balance < 10;
  return (
    <Link
      to="/settings/billing"
      title="Credits — click to top up"
      className={`hidden items-center gap-1.5 rounded-2xl px-3 py-2 text-sm font-black transition sm:inline-flex ${
        low ? 'bg-amber-100 text-amber-700 hover:bg-amber-200' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
      }`}
    >
      <Coins className="h-4 w-4" />
      {balance}
    </Link>
  );
}
