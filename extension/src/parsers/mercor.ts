import type { ParsedPosting, PostingParser } from '../lib/types';
import { firstNonEmpty, pathSegment, text } from '../lib/dom';

/** mercor.com job/role page parser.
 *  URL shapes vary; we look for /jobs/<id> or /roles/<id>. */
export const mercorParser: PostingParser = {
  id: 'mercor',
  detect(url) {
    return /mercor\.com\/(jobs|roles|opportunities)\//i.test(url);
  },
  parse(doc, url): ParsedPosting | null {
    const id = pathSegment(url, 1);
    if (!id) return null;
    const title = firstNonEmpty(
      text(doc, 'h1[data-test="role-title"]'),
      text(doc, 'h1'),
    );
    if (!title) return null;
    const companyName = firstNonEmpty(
      text(doc, '[data-test="company-name"]'),
      text(doc, '.company-name'),
      'Mercor',
    );
    const location = firstNonEmpty(
      text(doc, '[data-test="role-location"]'),
      text(doc, '.role-location'),
      'Remote',
    );
    const description = firstNonEmpty(
      text(doc, '[data-test="role-description"]'),
      text(doc, '.role-description'),
      text(doc, 'main'),
    );
    return {
      parser: 'mercor',
      external_id: id,
      title,
      description,
      location,
      remote: /remote/i.test(`${location} ${description}`),
      apply_url: url,
      company: { name: companyName, domain: 'mercor.com', ats_type: 'other' },
      raw: { url },
    };
  },
};
