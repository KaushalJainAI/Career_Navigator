import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Check, Copy } from 'lucide-react';
import { AI } from '../api/endpoints';
import { errorMessage } from '../api/client';
import { Alert, Badge, Card, Spinner } from './ui';

type Provider = '' | 'claude_cli' | 'codex_cli' | 'gemini_cli' | 'nvidia';

interface AiStatus {
  configured: string;
  provider: Provider;
  label: string;
  mode: 'ai' | 'deterministic';
  installed_clis: string[];
}

const FRIENDLY_NAME: Record<Exclude<Provider, ''>, string> = {
  claude_cli: 'Claude (your Claude subscription via Claude Code)',
  codex_cli: 'ChatGPT (your subscription via Codex CLI)',
  gemini_cli: 'Gemini (your Google account via Gemini CLI)',
  nvidia: 'NVIDIA NIM (API key)',
};

const CLI_ROWS: { id: string; name: string; login: string; loginHint: string }[] = [
  { id: 'claude_cli', name: 'Claude Code', login: 'claude', loginHint: 'Then type /login inside Claude Code.' },
  { id: 'codex_cli', name: 'Codex CLI', login: 'codex login', loginHint: 'Follow the browser sign-in prompt.' },
  { id: 'gemini_cli', name: 'Gemini CLI', login: 'gemini', loginHint: 'Then sign in with your Google account when prompted.' },
];

// Origin of the API server: VITE_API_URL without its /api/v1 suffix.
const API_ORIGIN = (() => {
  const raw = ((import.meta.env.VITE_API_URL as string | undefined) || '').trim();
  const base = raw.replace(/\/+$/, '').replace(/\/api\/v1$/, '');
  return base || 'http://localhost:8000';
})();

function CopyButton({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <button
      type="button"
      onClick={copy}
      aria-label={`Copy ${label}`}
      className="inline-flex shrink-0 items-center gap-1 rounded-xl border border-slate-200 bg-white px-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

function CodeLine({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex items-stretch gap-2">
      <pre className="min-w-0 flex-1 overflow-x-auto rounded-xl bg-slate-950 px-3 py-2 font-mono text-xs leading-relaxed text-slate-100">
        <code>{value}</code>
      </pre>
      <CopyButton value={value} label={label} />
    </div>
  );
}

function ModeBadge({ status }: { status: AiStatus }) {
  if (status.mode === 'deterministic') {
    return (
      <div className="space-y-2">
        <Badge tone="slate">Built-in (no AI model)</Badge>
        <p className="text-sm text-slate-600">
          Everything works without AI: matching, tailoring, cover letters and the assistant use deterministic rules that never invent facts.
          Connecting a model makes the assistant conversational and polishes wording, and it is still verified so nothing is made up.
        </p>
      </div>
    );
  }
  const name = status.provider ? FRIENDLY_NAME[status.provider] : (status.label || 'Unknown model');
  return (
    <div className="space-y-2">
      <Badge tone="teal">{name}</Badge>
      {status.label && <p className="break-all font-mono text-xs text-slate-500">{status.label}</p>}
    </div>
  );
}

function SubscriptionSection({ installed }: { installed: string[] }) {
  return (
    <section className="space-y-3">
      <div>
        <h3 className="text-sm font-semibold text-slate-900">Use your own subscription</h3>
        <p className="mt-1 text-sm text-slate-500">
          The platform can run its AI through a CLI you are already logged into on the machine running the backend.
          No API key needed.
        </p>
      </div>

      <ul className="space-y-3">
        {CLI_ROWS.map((row) => {
          const isInstalled = installed.includes(row.id);
          return (
            <li key={row.id} className="min-w-0 space-y-2 rounded-xl border border-slate-200 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm font-semibold text-slate-900">{row.name}</span>
                {isInstalled ? <Badge tone="green">Detected</Badge> : <Badge tone="slate">Not found</Badge>}
              </div>

              <div className="space-y-1">
                <span className="block text-xs font-medium text-slate-500">Log in (run in a terminal)</span>
                <CodeLine value={row.login} label={`${row.name} login command`} />
                <p className="text-xs text-slate-500">{row.loginHint}</p>
              </div>

              <div className="space-y-1">
                <span className="block text-xs font-medium text-slate-500">Set in backend/.env</span>
                <CodeLine value={`AI_PROVIDER=${row.id}`} label={`${row.name} env setting`} />
              </div>
            </li>
          );
        })}
      </ul>

      <div className="space-y-1 rounded-xl border border-slate-200 p-3">
        <span className="block text-xs font-medium text-slate-500">Or let the backend pick whichever CLI is installed</span>
        <CodeLine value="AI_PROVIDER=auto" label="auto provider env setting" />
        <p className="text-xs text-slate-500">Restart the backend after changing backend/.env.</p>
      </div>
    </section>
  );
}

function PluginSection() {
  const steps: { title: string; body: ReactNode }[] = [
    {
      title: 'Create an API token',
      body: (
        <p className="text-sm text-slate-600">
          Make a token on the{' '}
          <Link to="/settings/api-tokens" className="font-semibold text-teal-700 underline underline-offset-2 hover:text-teal-800">
            API tokens page
          </Link>
          . Copy it once, it is shown only at creation.
        </p>
      ),
    },
    {
      title: 'Export the URL and token in your shell',
      body: (
        <div className="space-y-2">
          <CodeLine value={`export CAREER_NAVIGATOR_URL=${API_ORIGIN}`} label="server URL export command" />
          <CodeLine value="export CAREER_NAVIGATOR_TOKEN=<your token>" label="token export command" />
        </div>
      ),
    },
    {
      title: 'Install the plugin in Claude Code',
      body: (
        <div className="space-y-2">
          <CodeLine value="/plugin marketplace add KaushalJainAI/Career_Navigator" label="marketplace add command" />
          <CodeLine value="/plugin install career-navigator@career-navigator" label="plugin install command" />
        </div>
      ),
    },
    {
      title: 'Try it',
      body: (
        <div className="space-y-2">
          <CodeLine value="/career-navigator:today" label="today command" />
          <p className="text-xs text-slate-500">Shows what to do next in your search, using your Claude subscription.</p>
        </div>
      ),
    },
  ];

  return (
    <section className="space-y-3">
      <div>
        <h3 className="text-sm font-semibold text-slate-900">Use Career Navigator from Claude Code</h3>
        <p className="mt-1 text-sm text-slate-500">
          The plugin lets you manage your job search from Claude Code, with your Claude subscription doing the thinking.
        </p>
      </div>
      <ol className="space-y-4">
        {steps.map((s, i) => (
          <li key={s.title} className="flex min-w-0 gap-3">
            <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-bold text-slate-700">
              {i + 1}
            </span>
            <div className="min-w-0 flex-1 space-y-2">
              <p className="text-sm font-semibold text-slate-900">{s.title}</p>
              {s.body}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function AiEngineCard() {
  const [status, setStatus] = useState<AiStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    AI.status()
      .then((data: AiStatus) => {
        if (!cancelled) setStatus({ ...data, installed_clis: data.installed_clis ?? [] });
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(errorMessage(e, 'Could not load AI engine status.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  return (
    <Card className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-bold tracking-tight text-slate-950">AI engine</h2>

        {loading && <Spinner label="Checking AI engine…" />}
        {!loading && error && <Alert tone="red">{error}</Alert>}
        {!loading && !error && status && <ModeBadge status={status} />}
      </div>

      {!loading && (
        <>
          <SubscriptionSection installed={status?.installed_clis ?? []} />
          <hr className="border-slate-200" />
          <PluginSection />
        </>
      )}
    </Card>
  );
}
