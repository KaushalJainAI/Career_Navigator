import { Fragment, type ReactNode } from 'react';

/** Minimal, safe rendering of assistant text: **bold**, `code`, and line breaks.
 *  Never uses innerHTML, so model output cannot inject markup. */
function inline(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**') && p.length > 4) return <strong key={i} className="font-semibold">{p.slice(2, -2)}</strong>;
    if (p.startsWith('`') && p.endsWith('`') && p.length > 2) return <code key={i} className="rounded bg-slate-100 px-1 text-[0.85em]">{p.slice(1, -1)}</code>;
    return <Fragment key={i}>{p.replace(/(^|\s)\*([^*\s][^*]*)\*(?=\s|[.,;:!?]|$)/g, '$1$2')}</Fragment>;
  });
}

export function RichText({ text }: { text: string }) {
  const lines = text.split('\n');
  return (
    <div className="space-y-1 break-words text-sm leading-relaxed text-slate-900">
      {lines.map((raw, i) => {
        const line = raw.replace(/^#{1,4}\s+/, '');
        if (!line.trim()) return <div key={i} className="h-1.5" />;
        const bullet = line.match(/^\s*(?:[-*•]|\d+[.)])\s+(.*)$/);
        if (bullet) {
          const num = line.match(/^\s*(\d+)[.)]/);
          return (
            <div key={i} className="flex gap-2 pl-1">
              <span className="shrink-0 text-slate-400">{num ? `${num[1]}.` : '•'}</span>
              <span className="min-w-0">{inline(bullet[1])}</span>
            </div>
          );
        }
        return <p key={i}>{inline(line)}</p>;
      })}
    </div>
  );
}
