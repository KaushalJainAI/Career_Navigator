import type { ParsedPosting, PostingParser } from '../lib/types';
import { firstNonEmpty, pathSegment, text } from '../lib/dom';

/** unstop.com job / internship / competition page parser.
 *  URL shape: https://unstop.com/jobs/<slug>-<id> or /internships/<slug>-<id>. */
export const unstopParser: PostingParser = {
  id: 'unstop',
  detect(url) {
    return /unstop\.com\/(jobs|internships|hackathons|competitions)\//i.test(url);
  },
  parse(doc, url): ParsedPosting | null {
    // Trailing -<digits> in slug; fall back to last path segment.
    const slug = pathSegment(url, 1);
    const idMatch = slug.match(/-(\d+)$/);
    const jobId = idMatch ? idMatch[1] : slug;
    if (!jobId) return null;
    const title = firstNonEmpty(
      text(doc, 'h1.opp_title, h1'),
      text(doc, '.competition-title'),
    );
    if (!title) return null;
    const companyName = firstNonEmpty(
      text(doc, '.un_org_name'),
      text(doc, '.organisation-name'),
      text(doc, '[data-test="organisation-name"]'),
    );
    const location = firstNonEmpty(
      text(doc, '.un_location'),
      text(doc, '.location-name'),
    );
    const description = firstNonEmpty(
      text(doc, '#opportunity_detail, .opportunity-detail'),
      text(doc, '.about-section'),
    );
    return {
      parser: 'unstop',
      external_id: jobId,
      title,
      description,
      location,
      remote: /remote|work\s+from\s+home|wfh/i.test(`${location} ${description}`),
      apply_url: url,
      company: { name: companyName, ats_type: 'other' },
      raw: { url, slug },
    };
  },
};
