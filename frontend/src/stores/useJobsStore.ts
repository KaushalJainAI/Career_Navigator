import { create } from 'zustand';
import { Jobs } from '../api/endpoints';

interface Job {
  id: number;
  title: string;
  company: { name: string; domain: string };
  location: string;
  remote: boolean;
  apply_url: string;
  ghost_risk?: number;
  ghost_band?: 'low' | 'medium' | 'high';
}

interface JobsState {
  jobs: Job[];
  loading: boolean;
  fetch: (params?: Record<string, string | number | boolean>) => Promise<void>;
}

export const useJobsStore = create<JobsState>((set) => ({
  jobs: [],
  loading: false,
  fetch: async (params = {}) => {
    set({ loading: true });
    try {
      const data = await Jobs.list(params);
      set({ jobs: data.results ?? data, loading: false });
    } catch {
      set({ loading: false });
    }
  },
}));
