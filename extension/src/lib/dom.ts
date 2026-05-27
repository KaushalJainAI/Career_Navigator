/** DOM helpers for selector-based scraping. Used by all parsers. */

export function text(doc: ParentNode, selector: string): string {
  const el = doc.querySelector(selector);
  return (el?.textContent || '').trim().replace(/\s+/g, ' ');
}

export function attr(doc: ParentNode, selector: string, name: string): string {
  const el = doc.querySelector(selector);
  return el?.getAttribute(name) || '';
}

export function all(doc: ParentNode, selector: string): Element[] {
  return Array.from(doc.querySelectorAll(selector));
}

export function firstNonEmpty(...values: string[]): string {
  for (const v of values) {
    if (v && v.trim()) return v.trim();
  }
  return '';
}

/** Extract a path segment from a URL by zero-based index from the path. */
export function pathSegment(url: string, index: number): string {
  try {
    const u = new URL(url);
    const parts = u.pathname.split('/').filter(Boolean);
    return parts[index] || '';
  } catch {
    return '';
  }
}

export function hostname(url: string): string {
  try {
    return new URL(url).hostname.toLowerCase();
  } catch {
    return '';
  }
}
