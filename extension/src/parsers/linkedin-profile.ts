import type { ParsedExperience, ParsedProfile, ProfileParser } from '../lib/types';
import { all, firstNonEmpty, text } from '../lib/dom';

/** Parses linkedin.com/in/<handle> pages.
 *  LinkedIn's DOM changes often; the selectors below are a best-effort that we
 *  fall back to text-only when a structured selector misses. */
export const linkedinProfileParser: ProfileParser = {
  detect(url) {
    return /linkedin\.com\/in\//i.test(url);
  },
  parse(doc, url): ParsedProfile | null {
    const name = firstNonEmpty(
      text(doc, 'h1.text-heading-xlarge'),
      text(doc, 'h1.top-card-layout__title'),
      text(doc, 'h1'),
    );
    if (!name) return null;
    const headline = firstNonEmpty(
      text(doc, '.text-body-medium.break-words'),
      text(doc, '.top-card-layout__headline'),
    );
    const location = firstNonEmpty(
      text(doc, '.text-body-small.inline.t-black--light.break-words'),
      text(doc, '.top-card__subline-item'),
    );

    const experiences: ParsedExperience[] = [];
    // Experience section: each <li> within #experience or section[id*=experience]
    const expSection =
      doc.querySelector('section[id*=experience]') ||
      doc.querySelector('#experience')?.parentElement ||
      doc.querySelector('[data-section="experience"]');
    if (expSection) {
      for (const li of all(expSection, 'li')) {
        const role = firstNonEmpty(
          text(li, 'span[aria-hidden=true]'),
          text(li, '.t-bold'),
        );
        const companyEl = li.querySelector('.t-14.t-normal, .pv-entity__secondary-title');
        const companyName = (companyEl?.textContent || '').trim().split('·')[0].trim();
        const dateRange = firstNonEmpty(
          text(li, '.pv-entity__date-range, .t-14.t-normal.t-black--light'),
        );
        if (!role || !companyName) continue;
        const isCurrent = /present/i.test(dateRange);
        const dates = parseDateRange(dateRange);
        experiences.push({
          company_name: companyName,
          title: role,
          started_at: dates.start,
          ended_at: dates.end,
          is_current: isCurrent,
          raw: { date_range: dateRange },
        });
      }
    }

    return {
      profile_url: url.split('?')[0],
      name,
      headline,
      location,
      experiences,
      raw: { url },
    };
  },
};

function parseDateRange(s: string): { start: string | null; end: string | null } {
  if (!s) return { start: null, end: null };
  // Common shapes: "Jan 2022 - Present", "2020 - 2023", "Jan 2022 - Mar 2024"
  const [startRaw, endRaw] = s.split(/[-–]/).map((p) => p.trim());
  return {
    start: parseLooseDate(startRaw),
    end: /present/i.test(endRaw || '') ? null : parseLooseDate(endRaw || ''),
  };
}

function parseLooseDate(s: string): string | null {
  if (!s) return null;
  const yearMatch = s.match(/(\d{4})/);
  if (!yearMatch) return null;
  const year = yearMatch[1];
  const monthMatch = s.match(/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/i);
  const monthMap: Record<string, string> = {
    jan: '01', feb: '02', mar: '03', apr: '04', may: '05', jun: '06',
    jul: '07', aug: '08', sep: '09', oct: '10', nov: '11', dec: '12',
  };
  const month = monthMatch ? monthMap[monthMatch[1].toLowerCase()] : '01';
  return `${year}-${month}-01`;
}
