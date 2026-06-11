import { ShieldAlert, ShieldCheck, ShieldQuestion } from 'lucide-react';

export type GhostBand = 'low' | 'medium' | 'high';

export function bandFor(score: number): GhostBand {
  if (score >= 60) return 'high';
  if (score >= 30) return 'medium';
  return 'low';
}

const STYLES: Record<GhostBand, { label: string; className: string; Icon: typeof ShieldCheck }> = {
  low: {
    label: 'Likely live',
    className: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    Icon: ShieldCheck,
  },
  medium: {
    label: 'Verify role',
    className: 'bg-amber-50 text-amber-800 border-amber-100',
    Icon: ShieldQuestion,
  },
  high: {
    label: 'Ghost-job risk',
    className: 'bg-red-50 text-red-700 border-red-100',
    Icon: ShieldAlert,
  },
};

interface Props {
  score: number;
  band?: GhostBand;
  reasons?: string[];
  showScore?: boolean;
}

/** Ghost-Job Shield indicator. `band` wins if provided (server-computed);
 *  otherwise it's derived from the score so the thresholds stay in one place. */
export function GhostRiskBadge({ score, band, reasons = [], showScore = false }: Props) {
  const resolved = band ?? bandFor(score);
  const { label, className, Icon } = STYLES[resolved];
  const title = reasons.length ? reasons.join('\n') : label;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-bold ${className}`}
      title={title}
      data-testid="ghost-risk-badge"
      data-band={resolved}
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
      {showScore && <span className="opacity-70">· {score}</span>}
    </span>
  );
}
