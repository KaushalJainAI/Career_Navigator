import type { ParsedPosting, PostingParser } from '../lib/types';
import { pathSegment, text } from '../lib/dom';

export const leverParser: PostingParser = {
  id: 'lever',
  detect(url) {
    return /jobs\.lever\.co\//i.test(url);
  },
  parse(doc, url): ParsedPosting | null {
    // jobs.lever.co/<company>/<posting-id>
    const company = pathSegment(url, 0);
    const postingId = pathSegment(url, 1);
    if (!postingId) return null;
    const title = text(doc, '.posting-headline h2, h2');
    if (!title) return null;
    const location = text(doc, '.posting-headline .sort-by-time, .location');
    const description = text(doc, '.posting-page, .content, .section.page-centered');
    return {
      parser: 'lever',
      external_id: postingId,
      title,
      description,
      location,
      remote: /remote/i.test(location),
      apply_url: `${url}/apply`,
      company: {
        name: company.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        ats_type: 'lever',
      },
      raw: { url },
    };
  },
};
