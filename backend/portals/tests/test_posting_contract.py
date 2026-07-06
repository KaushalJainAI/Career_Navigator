"""Contract test: every portal scraper's output must translate cleanly into the
internal JobPosting shape.

`make_posting` guarantees the *keys*; this guards the *values* each scraper is
responsible for — a non-empty external_id + title (else upsert_postings drops the
row), a resolved company name, an absolute apply_url, and correctly-typed
salary/remote fields. One representative fixture per portal, so a future scraper
that regresses the mapping fails here instead of silently ingesting junk.
"""

import pytest

from portals.registry import PORTALS, get_scraper

# Canonical keys emitted by ingestion.adapters.base.make_posting and consumed by
# ingestion.services.upsert_postings.
CANONICAL_KEYS = {
    'external_id', 'title', 'description', 'location', 'remote',
    'salary_min', 'salary_max', 'salary_currency', 'apply_url',
    'posted_at', 'company', 'raw',
}

# One fixture per portal, matching that scraper's LIVE-SELECTOR xpaths.
FIXTURES = {
    'linkedin': """
      <ul class="jobs-search__results-list"><li>
        <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/backend-engineer-3812345678">Backend Engineer</a>
        <h3 class="base-search-card__title">Backend Engineer</h3>
        <h4 class="base-search-card__subtitle">Acme Labs</h4>
        <span class="job-search-card__location">Bengaluru, India</span>
      </li></ul>""",
    'naukri': """
      <div class="srp-jobtuple-wrapper">
        <a class="title" href="https://www.naukri.com/job-listings-python-dev-acme-1234567">Python Dev</a>
        <a class="comp-name">Acme Labs</a><span class="locWdth">Pune</span>
      </div>""",
    'unstop': """
      <div class="single_profile">
        <a href="/jobs/data-analyst-acme-987654"><h2 class="opp_title">Data Analyst</h2></a>
        <div class="org_name">Acme</div><div class="location">Remote</div>
      </div>""",
    'ycombinator': """
      <div class="job-listing">
        <a href="/jobs/45678" class="job-name">Founding Engineer</a>
        <div class="company-name">Rocket</div><div class="job-location">SF / Remote</div>
      </div>""",
    'instahyre': """
      <div class="opening-card">
        <a href="/job/482913/backend-engineer">Backend Engineer</a>
        <div class="opening-title">Backend Engineer</div>
        <div class="company-name">Acme Labs</div><div class="location">Bengaluru</div>
      </div>""",
    'wellfound': """
      <div class="styles_component__x1">
        <a href="/jobs/1234567-senior-platform-engineer">Senior Platform Engineer</a>
        <span class="company">Rocket</span><span class="location">Remote</span>
      </div>""",
    'shine': """
      <div class="jobCard">
        <a href="/jobs/senior-python-developer/9988776">x</a>
        <span class="jobTitle">Senior Python Developer</span>
        <span class="companyName">Acme Labs</span><span class="jobLoc">Pune</span>
      </div>""",
    'indeed': """
      <div class="job_seen_beacon" data-jk="a1b2c3d4e5">
        <h2 class="jobTitle"><span>Data Engineer</span></h2>
        <span data-testid="company-name">Globex</span>
        <div data-testid="text-location">Remote</div>
      </div>""",
    'timesjobs': """
      <li class="clearfix job-bx">
        <header><h2><a href="https://www.timesjobs.com/job-detail/dev-jobid-7654321">Software Developer</a></h2></header>
        <h3 class="joblist-comp-name">Acme Labs</h3>
        <ul class="top-jd-dtl"><li><span>Mumbai</span></li></ul>
      </li>""",
    'foundit': """
      <div class="srpResultCardContainer srpResultCard">
        <a href="/job/frontend-engineer-334455">x</a>
        <div class="jobTitle">Frontend Engineer</div>
        <div class="companyName">Globex</div><div class="jobLocation">Hyderabad</div>
      </div>""",
    'cutshort': """
      <div class="job-card">
        <a href="/job/Ab3Cd9Ef2/react-developer">x</a>
        <div class="job-title">React Developer</div>
        <div class="company">Startup Inc</div><div class="location">Remote</div>
      </div>""",
    'hirect': """
      <div class="job-item">
        <a href="/job/55667788">x</a>
        <div class="job-title">Android Developer</div>
        <div class="company">Chatty Co</div><div class="city">Delhi</div>
      </div>""",
    'internshala': """
      <div class="individual_internship">
        <a class="job-title-href" href="/job/detail/python-developer-in-bangalore-98765">Python Developer</a>
        <div class="company-name">Acme Labs</div><div class="locations">Bangalore</div>
      </div>""",
    'glassdoor': """
      <li class="JobsList_jobListItem__wjTHv" data-jobid="1009876543">
        <a class="JobCard_jobTitle__abc" href="/job-listing/data-scientist-JV_123.htm">Data Scientist</a>
        <div class="EmployerProfile_employerName__x">Acme Labs</div>
        <div class="JobCard_location__y">SF / Remote</div>
      </li>""",
}


def _assert_canonical(p: dict, portal: str):
    assert set(p) == CANONICAL_KEYS, f'{portal}: unexpected key set {set(p) ^ CANONICAL_KEYS}'
    # Required — else upsert_postings silently drops the row.
    assert isinstance(p['external_id'], str) and p['external_id'], f'{portal}: empty external_id'
    assert isinstance(p['title'], str) and p['title'], f'{portal}: empty title'
    # Types the model / ghost-risk / UI depend on.
    assert isinstance(p['remote'], bool)
    assert p['salary_min'] is None or isinstance(p['salary_min'], int)
    assert p['salary_max'] is None or isinstance(p['salary_max'], int)
    assert isinstance(p['salary_currency'], str)
    assert isinstance(p['location'], str)
    assert isinstance(p['description'], str)
    assert isinstance(p['raw'], dict)
    # apply_url must be absolute — the detail page does new URL(apply_url).
    assert isinstance(p['apply_url'], str) and p['apply_url'].startswith('http'), \
        f'{portal}: non-absolute apply_url {p["apply_url"]!r}'
    company = p['company']
    assert isinstance(company, dict)
    assert isinstance(company['name'], str) and company['name'], f'{portal}: empty company name'
    assert isinstance(company['domain'], str)
    assert isinstance(company['ats_type'], str)


def test_every_portal_has_a_contract_fixture():
    # If a portal is added to the registry, it must get a fixture here too.
    assert set(FIXTURES) == set(PORTALS), \
        f'fixture/registry mismatch: {set(FIXTURES) ^ set(PORTALS)}'


@pytest.mark.parametrize('portal', sorted(FIXTURES))
def test_scraper_output_matches_internal_contract(portal):
    scraper = get_scraper(portal)
    postings = scraper.parse_list(FIXTURES[portal], PORTALS[portal].login_url.rsplit('/', 1)[0])
    assert postings, f'{portal}: fixture produced no postings'
    for p in postings:
        _assert_canonical(p, portal)
