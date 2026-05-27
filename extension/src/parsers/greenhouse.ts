import type { ParsedPosting, PostingParser } from '../lib/types';
import { hostname, pathSegment, text } from '../lib/dom';

export const greenhouseParser: PostingParser = {
  id: 'greenhouse',
  detect(url) {
    return /\.greenhouse\.io\//i.test(url);
  },
  parse(doc, url): ParsedPosting | null {
    // URL shapes: boards.greenhouse.io/<co>/jobs/<id> OR job-boards.greenhouse.io/<co>/jobs/<id>
    const host = hostname(url);
    const company = pathSegment(url, 0);
    let jobId = '';
    const parts = new URL(url).pathname.split('/').filter(Boolean);
    const ix = parts.indexOf('jobs');
    if (ix >= 0 && parts[ix + 1]) jobId = parts[ix + 1];
    if (!jobId) return null;
    const title = text(doc, 'h1.app-title, h1');
    if (!title) return null;
    const location = text(doc, '.location, .body__location');
    const description = text(doc, '#content, #app_body, .content');
    return {
      parser: 'greenhouse',
      external_id: `${company}/${jobId}`,
      title,
      description,
      location,
      remote: /remote/i.test(location),
      apply_url: url,
      company: {
        name: company.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        domain: host,
        ats_type: 'greenhouse',
      },
      raw: { url },
    };
  },
};
