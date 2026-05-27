import type { ParsedPosting, PostingParser } from '../lib/types';
import { attr, pathSegment, text } from '../lib/dom';

export const linkedinJobParser: PostingParser = {
  id: 'linkedin',
  detect(url) {
    return /linkedin\.com\/jobs\/(view|collections)/i.test(url);
  },
  parse(doc, url): ParsedPosting | null {
    // jobId is part of the URL on /jobs/view/{id}, or query param currentJobId.
    let jobId = pathSegment(url, 2); // /jobs/view/<id>
    if (!/^\d+$/.test(jobId)) {
      const m = new URL(url).searchParams.get('currentJobId') || '';
      jobId = m || jobId;
    }
    if (!jobId) return null;
    const title = text(doc, '.job-details-jobs-unified-top-card__job-title')
      || text(doc, 'h1.t-24, h1');
    if (!title) return null;
    const companyName = text(doc, '.job-details-jobs-unified-top-card__company-name')
      || text(doc, '[data-test-id="job-details-company-name"]');
    const location = text(doc, '.job-details-jobs-unified-top-card__primary-description-container > div > span');
    const description = text(doc, '.jobs-description__content, .description__text');
    const applyUrl = attr(doc, 'a[data-control-name="jobdetails_topcard_inapply"]', 'href') || url;
    return {
      parser: 'linkedin',
      external_id: jobId,
      title,
      description,
      location,
      remote: /remote/i.test(location),
      apply_url: applyUrl,
      company: { name: companyName, ats_type: 'other' },
      raw: { url },
    };
  },
};
