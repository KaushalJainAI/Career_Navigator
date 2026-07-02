import { create } from 'zustand';
import { Billing } from '../api/endpoints';

interface PricingItem {
  reason: string;
  label: string;
  cost: number;
  blurb: string;
}

interface BillingState {
  balance: number | null;
  pricing: PricingItem[];
  costByReason: Record<string, number>;
  loaded: boolean;
  refresh: () => Promise<void>;
}

/** Shared credit balance + price list, so the header pill and every paid-action
 *  button stay in sync. Call refresh() after any action that spends credits. */
export const useBillingStore = create<BillingState>((set) => ({
  balance: null,
  pricing: [],
  costByReason: {},
  loaded: false,
  refresh: async () => {
    try {
      const data = await Billing.summary();
      const pricing: PricingItem[] = data.pricing ?? [];
      const costByReason: Record<string, number> = {};
      pricing.forEach((p) => { costByReason[p.reason] = p.cost; });
      set({ balance: data.balance, pricing, costByReason, loaded: true });
    } catch {
      set({ loaded: true });
    }
  },
}));
