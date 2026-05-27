import { create } from 'zustand';
import { Interview } from '../api/endpoints';

interface Question {
  id: number;
  prompt: string;
  category: string;
  difficulty: string;
}

interface Turn {
  id: number;
  user_answer: string;
  score: number | null;
  feedback: string;
}

interface InterviewState {
  sessionId: number | null;
  questions: Question[];
  turns: Turn[];
  currentIndex: number;
  loading: boolean;
  start: (payload: { role: string; stage: string; difficulty?: string }) => Promise<void>;
  answer: (text: string) => Promise<Turn>;
  generateReport: () => Promise<unknown>;
}

export const useInterviewStore = create<InterviewState>((set, get) => ({
  sessionId: null,
  questions: [],
  turns: [],
  currentIndex: 0,
  loading: false,
  start: async (payload) => {
    set({ loading: true });
    try {
      const session = await Interview.start(payload);
      set({
        sessionId: session.id,
        questions: session.questions ?? [],
        turns: [],
        currentIndex: 0,
        loading: false,
      });
    } catch {
      set({ loading: false });
    }
  },
  answer: async (text) => {
    const id = get().sessionId;
    if (!id) throw new Error('No session');
    const turn = await Interview.answer(id, text);
    set({ turns: [...get().turns, turn], currentIndex: get().currentIndex + 1 });
    return turn;
  },
  generateReport: async () => {
    const id = get().sessionId;
    if (!id) throw new Error('No session');
    return Interview.report(id);
  },
}));
