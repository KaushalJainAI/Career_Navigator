import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Loader2, Plus, Send } from 'lucide-react';
import { Copilot } from '../../api/endpoints';
import { errorMessage } from '../../api/client';
import type { CopilotPending, CopilotSession, CopilotTurn, CopilotUi } from '../../lib/types';
import { Alert, Badge, Button, Spinner } from '../ui';

type Step = CopilotTurn['steps'][number];

interface ChatMessage {
  key: string;
  role: 'user' | 'assistant';
  content: string;
  steps: Step[];
  ui: CopilotUi[];
  pending: CopilotPending | null;
}

const TOOL_LABELS: Record<string, string> = {
  search_jobs: 'Searched jobs',
  find_new_jobs: 'Searched job boards',
  tailor_resume: 'Tailored résumé',
  draft_cover_letter: 'Drafted cover letter',
  update_application: 'Updated application',
  update_skills: 'Updated skills',
  update_targets: 'Updated targets',
  add_contact: 'Added contact',
  list_applications: 'Checked pipeline',
  get_overview: "Checked today's plan",
  list_contacts: 'Checked contacts',
  draft_referral_message: 'Drafted referral',
  start_practice: 'Prepared practice',
  get_profile: 'Read profile',
  save_job: 'Saved job',
  add_job: 'Added job',
  get_job: 'Read job',
  navigate: 'Opened page',
};

const PAGE_CHIPS = ['What should I do today?', 'Show my applications', 'Find new jobs'];

const INTRO_CHIPS: { label: string; text: string; fill: boolean }[] = [
  { label: 'What should I do today?', text: 'What should I do today?', fill: false },
  { label: 'Show my best matches', text: 'Show my best matches', fill: false },
  { label: 'Find new jobs', text: 'Find new jobs', fill: false },
  { label: 'Show my applications', text: 'Show my applications', fill: false },
  { label: 'I got an OA from <company> tomorrow at 10am', text: 'I got an OA from <company> tomorrow at 10am', fill: true },
  { label: 'Help me prepare for an HR round', text: 'Help me prepare for an HR round', fill: false },
];

const MAX_INPUT_PX = 132; // roughly five lines of text

function stepLabel(tool: string): string {
  return TOOL_LABELS[tool] ?? tool.replace(/_/g, ' ');
}

function fromTurn(turn: Pick<CopilotTurn, 'reply' | 'steps' | 'ui' | 'pending_action'>, key: string): ChatMessage {
  return {
    key,
    role: 'assistant',
    content: turn.reply,
    steps: turn.steps ?? [],
    ui: turn.ui ?? [],
    pending: turn.pending_action ?? null,
  };
}

function fromSession(s: CopilotSession): ChatMessage[] {
  const msgs: ChatMessage[] = s.messages.map((m) => {
    const meta = m.meta ?? [];
    return {
      key: `r-${m.id}`,
      role: m.role,
      content: m.content,
      steps: m.role === 'assistant' ? meta.flatMap((x) => x.steps ?? []) : [],
      ui: m.role === 'assistant' ? meta.flatMap((x) => x.ui ?? []) : [],
      pending: null,
    };
  });
  // Only the newest assistant message can hold an open approval.
  const lastAssistant = msgs.map((m) => m.role).lastIndexOf('assistant');
  if (lastAssistant >= 0) {
    const metaPending = s.messages[lastAssistant].meta?.find((x) => x.pending_action)?.pending_action ?? null;
    msgs[lastAssistant].pending = s.pending_action ?? metaPending;
  }
  return msgs;
}

function StepLine({ steps }: { steps: Step[] }) {
  if (!steps.length) return null;
  return (
    <p className="mt-2 text-[11px] text-slate-400">
      Used: {steps.map((s, i) => (
        <span key={`${s.tool}-${i}`}>
          {i > 0 && ', '}
          {s.ok ? (
            stepLabel(s.tool)
          ) : (
            <span className="text-red-600">
              {stepLabel(s.tool)} failed{s.error ? `: ${s.error}` : ''}
            </span>
          )}
        </span>
      ))}
    </p>
  );
}

function UiLinks({ ui }: { ui: CopilotUi[] }) {
  if (!ui.length) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {ui.map((u, i) => (
        <Link
          key={`${u.to}-${i}`}
          to={u.to}
          className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-teal-700 hover:bg-slate-50"
        >
          {u.label || (u.type === 'navigate' ? 'Open page' : 'Open')}
        </Link>
      ))}
    </div>
  );
}

function PendingCard({ pending, busy, approving, onApprove, onCancel }: {
  pending: CopilotPending; busy: boolean; approving: boolean; onApprove: () => void; onCancel: () => void;
}) {
  return (
    <div className="mt-3 rounded-xl border border-amber-300 bg-amber-50 p-3">
      <p className="text-sm font-semibold text-amber-900">Confirm this change</p>
      <p className="mt-1 whitespace-pre-line text-sm text-amber-900/90">{pending.summary}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button onClick={onApprove} loading={approving} disabled={busy && !approving}>Approve</Button>
        <Button variant="secondary" onClick={onCancel} disabled={busy}>Cancel</Button>
      </div>
    </div>
  );
}

export function CopilotChat({ variant }: { variant: 'panel' | 'page' }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [mode, setMode] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [approvingKey, setApprovingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const keySeq = useRef(0);
  const nextKey = () => `m-${++keySeq.current}`;

  const busy = sending || approvingKey !== null;

  // Restore the latest conversation on mount.
  useEffect(() => {
    let cancelled = false;
    Copilot.latest()
      .then((s: CopilotSession) => {
        if (cancelled) return;
        setSessionId(s.id);
        setMessages(fromSession(s));
      })
      .catch((e: unknown) => {
        if (!cancelled) setLoadError(errorMessage(e, 'Could not load your earlier conversation.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  // Keep the newest message in view.
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, busy]);

  // Auto-grow the composer up to about five lines.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_INPUT_PX)}px`;
    el.style.overflowY = el.scrollHeight > MAX_INPUT_PX ? 'auto' : 'hidden';
  }, [input]);

  function followNavigation(ui: CopilotUi[]) {
    const target = [...ui].reverse().find((u) => u.type === 'navigate');
    if (target) navigate(target.to);
  }

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    const userKey = nextKey();
    setError(null);
    setInput('');
    setMessages((prev) => [...prev, { key: userKey, role: 'user', content: message, steps: [], ui: [], pending: null }]);
    setSending(true);
    try {
      const turn: CopilotTurn = await Copilot.send(message, sessionId);
      setSessionId(turn.session_id);
      setMode(turn.mode);
      // The backend replaces any open approval with this turn's own result.
      setMessages((prev) => [...prev.map((m) => ({ ...m, pending: null })), fromTurn(turn, nextKey())]);
      followNavigation(turn.ui ?? []);
    } catch (e) {
      setMessages((prev) => prev.filter((m) => m.key !== userKey));
      setInput((cur) => cur || message);
      setError(errorMessage(e, "I couldn't reach the copilot. Please try again."));
    } finally {
      setSending(false);
    }
  }

  async function decide(key: string, pending: CopilotPending, approve: boolean) {
    if (sessionId == null || busy) return;
    setError(null);
    setApprovingKey(key);
    try {
      const turn: CopilotTurn = await Copilot.approve(sessionId, pending.id, approve);
      setSessionId(turn.session_id);
      setMode(turn.mode);
      setMessages((prev) => [
        ...prev.map((m) => (m.key === key ? { ...m, pending: null } : m)),
        fromTurn(turn, nextKey()),
      ]);
      followNavigation(turn.ui ?? []);
    } catch (e) {
      setError(errorMessage(e, 'That change could not be completed. Please try again.'));
    } finally {
      setApprovingKey(null);
    }
  }

  function newChat() {
    if (busy) return;
    setMessages([]);
    setSessionId(null);
    setMode(null);
    setInput('');
    setError(null);
    inputRef.current?.focus();
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      void send(input);
    }
  }

  const modeBadge = mode == null ? null : mode === 'rules' ? (
    <span title="Runs without an AI model. Connect a model in Settings for free-form chat.">
      <Badge tone="slate">Rules mode</Badge>
    </span>
  ) : (
    <Badge tone="teal">AI: {mode}</Badge>
  );

  const shell = variant === 'page' ? 'h-[calc(100vh-10rem)] lg:h-[calc(100vh-6rem)]' : 'h-full';

  return (
    <section className={`flex min-h-0 flex-col bg-[#fbfaf7] ${shell}`}>
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="text-base font-semibold text-slate-950">Copilot</h2>
          {modeBadge}
        </div>
        <button
          type="button"
          onClick={newChat}
          disabled={busy}
          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-950 disabled:opacity-50"
        >
          <Plus className="h-4 w-4" /> New chat
        </button>
      </div>

      <div ref={listRef} role="log" aria-live="polite" className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {loadError && <Alert tone="red">{loadError}</Alert>}
        {loading && <Spinner label="Loading your conversation…" />}

        {!loading && messages.length === 0 && (
          <div className="space-y-4">
            <div className="max-w-[90%] rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 text-sm leading-relaxed text-slate-800 shadow-sm">
              Hi! I'm your job-search copilot. I can find and rank jobs, tailor your résumé, track applications, remember deadlines and prep you for interviews. Try:
            </div>
            <div className="flex flex-wrap gap-2">
              {INTRO_CHIPS.map((c) => (
                <button
                  key={c.label}
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    if (c.fill) {
                      setInput(c.text);
                      inputRef.current?.focus();
                    } else {
                      void send(c.text);
                    }
                  }}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-left text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) => {
          if (m.role === 'user') {
            return (
              <div key={m.key} className="flex justify-end">
                <div className="max-w-[85%] whitespace-pre-line rounded-2xl rounded-br-md bg-slate-950 px-4 py-2.5 text-sm leading-relaxed text-white">
                  {m.content}
                </div>
              </div>
            );
          }
          const p = m.pending;
          return (
            <div key={m.key} className="flex justify-start">
              <div className="max-w-[90%] rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 shadow-sm">
                <div className="whitespace-pre-line text-sm leading-relaxed text-slate-900">{m.content}</div>
                <StepLine steps={m.steps} />
                <UiLinks ui={m.ui} />
                {p && (
                  <PendingCard
                    pending={p}
                    busy={busy}
                    approving={approvingKey === m.key}
                    onApprove={() => void decide(m.key, p, true)}
                    onCancel={() => void decide(m.key, p, false)}
                  />
                )}
              </div>
            </div>
          );
        })}

        {busy && (
          <div className="flex justify-start">
            <div className="flex items-start gap-2 rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm">
              <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-teal-600" />
              <div>
                <div>Working…</div>
                <div className="text-xs text-slate-400">Searching can take up to a minute.</div>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="space-y-2 border-t border-slate-200 bg-white p-3">
        {error && <Alert tone="red">{error}</Alert>}
        {variant === 'page' && (
          <div className="flex flex-wrap gap-1.5">
            {PAGE_CHIPS.map((c) => (
              <button
                key={c}
                type="button"
                disabled={busy}
                onClick={() => void send(c)}
                className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50"
              >
                {c}
              </button>
            ))}
          </div>
        )}
        <div className="flex items-end gap-2">
          <label className="min-w-0 flex-1">
            <span className="sr-only">Message the copilot</span>
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Ask in plain words, e.g. I got an OA from TCS on Friday 10am"
              className="block max-h-[132px] min-h-[40px] w-full resize-none rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm leading-5 outline-none focus:border-slate-400"
            />
          </label>
          <button
            type="button"
            aria-label="Send message"
            disabled={busy || !input.trim()}
            onClick={() => void send(input)}
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-slate-950 text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </section>
  );
}
