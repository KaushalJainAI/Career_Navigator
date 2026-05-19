import { create } from 'zustand';
import { Applications } from '../api/endpoints';

interface Application {
  id: number;
  job: number;
  status: string;
  tier_used: string;
}

interface AppState {
  applications: Application[];
  fetch: () => Promise<void>;
  create: (jobId: number, tier?: string) => Promise<Application>;
  setStatus: (id: number, status: string) => Promise<void>;
}

export const useApplicationsStore = create<AppState>((set, get) => ({
  applications: [],
  fetch: async () => {
    const data = await Applications.list();
    set({ applications: data.results ?? data });
  },
  create: async (jobId, tier) => {
    const app = await Applications.create(jobId, tier);
    set({ applications: [app, ...get().applications] });
    return app;
  },
  setStatus: async (id, status) => {
    await Applications.patch(id, { status });
    set({
      applications: get().applications.map((a) =>
        a.id === id ? { ...a, status } : a,
      ),
    });
  },
}));
