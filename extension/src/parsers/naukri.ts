import type { ParsedPosting, PostingParser } from '../lib/types';
import { firstNonEmpty, text } from '../lib/dom';

/** naukri.com job page parser. URL shape:
 *  https://www.naukri.com/job-listings-<slug>-<id> */
export const naukriParser: PostingParser = {
  id: 'naukri',
  detect(url) {
    return /naukri\.com\/(job-listings-|jobs\/)/i.test(url);
  },
  parse(doc, url): ParsedPosting | null {
    const idMatch = url.match(/-(\d{6,})(?:\?|$)/) || url.match(/jobs\/(\d+)/);
    const jobId = idMatch ? idMatch[1] : '';
    if (!jobId) return null;
    const title = text(doc, 'h1.styles_jd-header-title__rZwM1, h1');
    if (!title) return null;
    const companyName = firstNonEmpty(
      text(doc, '.styles_jd-header-comp-name__MvqAI a'),
      text(doc, '.styles_jd-header-comp-name__MvqAI'),
      text(doc, '.jd-header-comp-name'),
    );
    const location = firstNonEmpty(
      text(doc, '.styles_jhc__location__W_pVs'),
      text(doc, '.location'),
    );
    const description = firstNonEmpty(
      text(doc, '.styles_JDC__dang-inner-html__h0K4t'),
      text(doc, '.job-desc'),
      text(doc, '.jd-desc'),
    );
    return {
      parser: 'naukri',
      external_id: jobId,
      title,
      description,
      location,
      remote: /remote|work\s+from\s+home/i.test(`${title} ${location} ${description}`),
      apply_url: url,
      company: { name: companyName, ats_type: 'other' },
      raw: { url },
    };
  },
};
