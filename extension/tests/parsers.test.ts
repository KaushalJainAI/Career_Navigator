import { describe, expect, it } from 'vitest';
import { greenhouseParser } from '../src/parsers/greenhouse';
import { leverParser } from '../src/parsers/lever';
import { linkedinJobParser } from '../src/parsers/linkedin-job';
import { linkedinProfileParser } from '../src/parsers/linkedin-profile';
import { mercorParser } from '../src/parsers/mercor';
import { naukriParser } from '../src/parsers/naukri';
import { pickParser } from '../src/parsers/index';
import { unstopParser } from '../src/parsers/unstop';

function htmlDoc(body: string): Document {
  return new DOMParser().parseFromString(`<!doctype html><html><body>${body}</body></html>`, 'text/html');
}

describe('detect()', () => {
  it('routes URLs to the right parser', () => {
    expect(pickParser('https://www.linkedin.com/jobs/view/12345')?.id).toBe('linkedin');
    expect(pickParser('https://boards.greenhouse.io/acme/jobs/9876')?.id).toBe('greenhouse');
    expect(pickParser('https://jobs.lever.co/acme/abc-123')?.id).toBe('lever');
    expect(pickParser('https://www.naukri.com/job-listings-backend-engineer-acme-bengaluru-1-3-years-123456')?.id).toBe('naukri');
    expect(pickParser('https://unstop.com/jobs/devops-engineer-acme-789')?.id).toBe('unstop');
    expect(pickParser('https://www.mercor.com/jobs/abc-123')?.id).toBe('mercor');
    expect(pickParser('https://example.com/foo')).toBeNull();
  });
});

describe('linkedin job parser', () => {
  it('extracts external_id from /jobs/view/<id>', () => {
    const doc = htmlDoc(`
      <div class="job-details-jobs-unified-top-card__job-title">Backend Engineer</div>
      <div class="job-details-jobs-unified-top-card__company-name">Acme</div>
    `);
    const out = linkedinJobParser.parse(doc, 'https://www.linkedin.com/jobs/view/12345');
    expect(out?.external_id).toBe('12345');
    expect(out?.title).toBe('Backend Engineer');
    expect(out?.company.name).toBe('Acme');
  });

  it('returns null if no title is found', () => {
    const doc = htmlDoc('<div></div>');
    const out = linkedinJobParser.parse(doc, 'https://www.linkedin.com/jobs/view/123');
    expect(out).toBeNull();
  });
});

describe('greenhouse parser', () => {
  it('extracts company slug and job id', () => {
    const doc = htmlDoc('<h1 class="app-title">Senior Engineer</h1>');
    const out = greenhouseParser.parse(doc, 'https://boards.greenhouse.io/acme/jobs/9876');
    expect(out?.external_id).toBe('acme/9876');
    expect(out?.title).toBe('Senior Engineer');
    expect(out?.company.name).toBe('Acme');
    expect(out?.company.ats_type).toBe('greenhouse');
  });
});

describe('lever parser', () => {
  it('uses posting id from URL', () => {
    const doc = htmlDoc('<h2>DevOps Engineer</h2>');
    const out = leverParser.parse(doc, 'https://jobs.lever.co/acme/abc-123');
    expect(out?.external_id).toBe('abc-123');
    expect(out?.title).toBe('DevOps Engineer');
    expect(out?.apply_url).toContain('/apply');
  });
});

describe('naukri parser', () => {
  it('extracts numeric id from slug', () => {
    const doc = htmlDoc('<h1>Backend Engineer at Acme</h1>');
    const url = 'https://www.naukri.com/job-listings-backend-engineer-acme-bengaluru-1-3-years-123456';
    const out = naukriParser.parse(doc, url);
    expect(out?.external_id).toBe('123456');
    expect(out?.title).toContain('Backend Engineer');
  });
});

describe('unstop parser', () => {
  it('extracts trailing id from slug', () => {
    const doc = htmlDoc('<h1 class="opp_title">Devops Engineer</h1>');
    const out = unstopParser.parse(doc, 'https://unstop.com/jobs/devops-engineer-acme-789');
    expect(out?.external_id).toBe('789');
    expect(out?.title).toBe('Devops Engineer');
  });
});

describe('mercor parser', () => {
  it('extracts id and defaults company', () => {
    const doc = htmlDoc('<h1>AI Engineer</h1>');
    const out = mercorParser.parse(doc, 'https://www.mercor.com/jobs/role-abc');
    expect(out?.external_id).toBe('role-abc');
    expect(out?.title).toBe('AI Engineer');
    expect(out?.company.domain).toBe('mercor.com');
  });
});

describe('linkedin profile parser', () => {
  it('extracts name and headline', () => {
    const doc = htmlDoc(`
      <h1 class="text-heading-xlarge">Alice Doe</h1>
      <div class="text-body-medium break-words">Engineering Manager at Acme</div>
    `);
    const out = linkedinProfileParser.parse(doc, 'https://www.linkedin.com/in/alice');
    expect(out?.name).toBe('Alice Doe');
    expect(out?.headline).toContain('Engineering Manager');
    expect(out?.profile_url).toBe('https://www.linkedin.com/in/alice');
  });

  it('returns null if no name is found', () => {
    const doc = htmlDoc('<div></div>');
    const out = linkedinProfileParser.parse(doc, 'https://www.linkedin.com/in/x');
    expect(out).toBeNull();
  });
});
