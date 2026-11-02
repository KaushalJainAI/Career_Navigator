// Shared UI kit. Every page uses these so the app looks like one product.
import { useEffect, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Loader2, X } from 'lucide-react';
import type { Verdict } from '../lib/types';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
const VARIANTS: Record<Variant, string> = {
  primary: 'bg-slate-950 text-white hover:bg-slate-800 shadow-sm',
  secondary: 'bg-white text-slate-900 border border-slate-200 hover:bg-slate-50',
  ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
  danger: 'bg-red-600 text-white hover:bg-red-700',
};

export function Button({ variant = 'primary', loading, children, className = '', disabled, ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${VARIANTS[variant]} ${className}`}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>{children}</div>;
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

type Tone = 'slate' | 'green' | 'amber' | 'red' | 'teal' | 'blue';
const TONES: Record<Tone, string> = {
  slate: 'bg-slate-100 text-slate-700',
  green: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200',
  amber: 'bg-amber-50 text-amber-800 ring-1 ring-amber-200',
  red: 'bg-red-50 text-red-700 ring-1 ring-red-200',
  teal: 'bg-teal-50 text-teal-700 ring-1 ring-teal-200',
  blue: 'bg-sky-50 text-sky-700 ring-1 ring-sky-200',
};
export function Badge({ children, tone = 'slate', className = '' }: { children: ReactNode; tone?: Tone; className?: string }) {
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${TONES[tone]} ${className}`}>{children}</span>;
}

export const VERDICT_LABEL: Record<Verdict, string> = { strong: 'Strong fit', good: 'Good fit', stretch: 'Stretch', weak: 'Weak fit' };
const VERDICT_COLOR: Record<Verdict, string> = { strong: '#059669', good: '#0d9488', stretch: '#d97706', weak: '#94a3b8' };

/** Circular fit score 0..100. */
export function FitRing({ fit, verdict, size = 56 }: { fit: number | null; verdict: Verdict | null; size?: number }) {
  if (fit == null || verdict == null) {
    return <div style={{ width: size, height: size }} className="grid place-items-center rounded-full bg-slate-100 text-xs text-slate-400">—</div>;
  }
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} title={`${VERDICT_LABEL[verdict]} · ${fit}/100`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#e2e8f0" strokeWidth={6} fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={VERDICT_COLOR[verdict]} strokeWidth={6} fill="none"
          strokeDasharray={c} strokeDashoffset={c * (1 - fit / 100)} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-sm font-bold text-slate-900">{fit}</div>
    </div>
  );
}

export function VerdictBadge({ verdict }: { verdict: Verdict | null }) {
  if (!verdict) return null;
  const tone: Tone = verdict === 'strong' ? 'green' : verdict === 'good' ? 'teal' : verdict === 'stretch' ? 'amber' : 'slate';
  return <Badge tone={tone}>{VERDICT_LABEL[verdict]}</Badge>;
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-8 text-sm text-slate-500">
      <Loader2 className="h-4 w-4 animate-spin" /> {label ?? 'Loading…'}
    </div>
  );
}

export function EmptyState({ icon, title, children, action }: { icon?: ReactNode; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-12 text-center">
      {icon && <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-full bg-slate-100 text-slate-500">{icon}</div>}
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      {children && <div className="mx-auto mt-1 max-w-md text-sm text-slate-500">{children}</div>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

export function Alert({ tone = 'slate', children }: { tone?: 'slate' | 'red' | 'amber' | 'green'; children: ReactNode }) {
  const cls = { slate: 'bg-slate-50 text-slate-700 border-slate-200', red: 'bg-red-50 text-red-700 border-red-200',
    amber: 'bg-amber-50 text-amber-800 border-amber-200', green: 'bg-emerald-50 text-emerald-700 border-emerald-200' }[tone];
  return <div className={`rounded-xl border px-4 py-3 text-sm ${cls}`}>{children}</div>;
}

export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <div role="dialog" aria-label={title} onClick={(e) => e.stopPropagation()}
        className={`max-h-[92vh] w-full overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl ${wide ? 'sm:max-w-3xl' : 'sm:max-w-lg'}`}>
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"><X className="h-5 w-5" /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

/** Text input that turns Enter/comma into removable chips. */
export function ChipInput({ value, onChange, placeholder, label }: { value: string[]; onChange: (v: string[]) => void; placeholder?: string; label?: string }) {
  function add(raw: string) {
    const items = raw.split(',').map((s) => s.trim()).filter(Boolean);
    if (!items.length) return;
    onChange(Array.from(new Set([...value, ...items])));
  }
  return (
    <label className="block">
      {label && <span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>}
      <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-2 py-2 focus-within:border-slate-400">
        {value.map((v) => (
          <span key={v} className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2 py-1 text-sm text-slate-800">
            {v}
            <button type="button" aria-label={`Remove ${v}`} onClick={() => onChange(value.filter((x) => x !== v))} className="text-slate-400 hover:text-slate-700"><X className="h-3.5 w-3.5" /></button>
          </span>
        ))}
        <input
          className="min-w-[8rem] flex-1 border-0 bg-transparent px-1 py-0.5 text-sm outline-none"
          placeholder={placeholder}
          onKeyDown={(e) => {
            const el = e.currentTarget;
            if ((e.key === 'Enter' || e.key === ',') && el.value.trim()) { e.preventDefault(); add(el.value); el.value = ''; }
            if (e.key === 'Backspace' && !el.value && value.length) onChange(value.slice(0, -1));
          }}
          onBlur={(e) => { if (e.currentTarget.value.trim()) { add(e.currentTarget.value); e.currentTarget.value = ''; } }}
        />
      </div>
    </label>
  );
}

export const inputCls = 'w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400';

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

export function ReasonList({ reasons }: { reasons: { kind: string; title: string; detail: string }[] }) {
  const dot = (k: string) => (k === 'positive' ? 'bg-emerald-500' : k === 'negative' ? 'bg-red-500' : 'bg-slate-400');
  return (
    <ul className="space-y-2">
      {reasons.map((r, i) => (
        <li key={i} className="flex gap-2.5 text-sm">
          <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dot(r.kind)}`} />
          <span><span className="font-medium text-slate-900">{r.title}</span>{r.detail && <span className="text-slate-500"> — {r.detail}</span>}</span>
        </li>
      ))}
    </ul>
  );
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return '';
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  return `${months} month${months > 1 ? 's' : ''} ago`;
}

export function salaryLabel(min: number | null, max: number | null, cur: string): string {
  if (!min && !max) return '';
  const f = (n: number) => (n >= 1000 ? `${Math.round(n / 1000)}k` : String(n));
  const c = cur ? `${cur} ` : '';
  if (min && max) return `${c}${f(min)}–${f(max)}`;
  return `${c}${f((min || max) as number)}`;
}
