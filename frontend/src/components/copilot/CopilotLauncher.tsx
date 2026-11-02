import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bot, Maximize2, X } from 'lucide-react';
import { CopilotChat } from './CopilotChat';

const STORAGE_KEY = 'cn_copilot_open';

function readOpen(): boolean {
  try {
    return window.sessionStorage.getItem(STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

function writeOpen(open: boolean) {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, open ? '1' : '0');
  } catch {
    /* storage unavailable (private mode, blocked): the panel still works */
  }
}

export function CopilotLauncher() {
  const [open, setOpen] = useState<boolean>(readOpen);

  useEffect(() => {
    writeOpen(open);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open copilot"
        className="fixed bottom-24 right-4 z-40 grid h-14 w-14 place-items-center rounded-full bg-slate-950 text-white shadow-lg transition hover:bg-slate-800 lg:bottom-6"
      >
        <Bot className="h-6 w-6" />
      </button>
    );
  }

  return (
    <div
      role="dialog"
      aria-label="Copilot"
      className="fixed inset-0 z-50 flex flex-col border-slate-200 bg-white shadow-xl lg:inset-y-0 lg:left-auto lg:right-0 lg:w-[420px] lg:border-l"
    >
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-2.5">
        <Link
          to="/assistant"
          onClick={() => setOpen(false)}
          className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-medium text-teal-700 hover:bg-teal-50"
        >
          <Maximize2 className="h-4 w-4" /> Open full screen
        </Link>
        <button
          type="button"
          onClick={() => setOpen(false)}
          aria-label="Close copilot"
          className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
      <div className="min-h-0 flex-1">
        <CopilotChat variant="panel" />
      </div>
    </div>
  );
}
