import pytest

from portals.drivers import FakeBrowserDriver
from portals.scrapers.base import NeedsLoginError, PortalQuery
from portals.scrapers.linkedin import LinkedInScraper
from portals.scrapers.naukri import NaukriScraper
from portals.scrapers.unstop import UnstopScraper
from portals.scrapers.ycombinator import YCombinatorScraper

LINKEDIN_HTML = """
<ul class="jobs-search__results-list">
  <li>
    <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/backend-engineer-at-acme-3812345678?refId=x">Backend Engineer</a>
    <h3 class="base-search-card__title">Backend Engineer</h3>
    <h4 class="base-search-card__subtitle">Acme Labs</h4>
    <span class="job-search-card__location">Bengaluru, Karnataka, India</span>
  </li>
  <li>
    <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/3899999999">Remote Platform Engineer</a>
    <h3 class="base-search-card__title">Remote Platform Engineer</h3>
    <h4 class="base-search-card__subtitle">Globex</h4>
    <span class="job-search-card__location">Remote</span>
  </li>
</ul>
"""

NAUKRI_HTML = """
<div class="srp-jobtuple-wrapper">
  <a class="title" href="https://www.naukri.com/job-listings-senior-python-developer-acme-bengaluru-1234567">Senior Python Developer</a>
  <a class="comp-name">Acme Labs</a>
  <span class="locWdth">Bengaluru</span>
</div>
"""

UNSTOP_HTML = """
<div class="single_profile">
  <a href="/jobs/data-analyst-internship-acme-987654"><h2 class="opp_title">Data Analyst Internship</h2></a>
  <div class="org_name">Acme</div>
  <div class="location">Remote</div>
</div>
"""

YC_HTML = """
<div class="job-listing">
  <a href="/jobs/45678" class="job-name">Founding Engineer</a>
  <div class="company-name">Rocket Startup</div>
  <div class="job-location">San Francisco / Remote</div>
</div>
"""


def test_linkedin_parse_list_extracts_cards():
    postings = LinkedInScraper.parse_list(LINKEDIN_HTML, 'https://www.linkedin.com')
    assert [p['external_id'] for p in postings] == ['3812345678', '3899999999']
    first = postings[0]
    assert first['title'] == 'Backend Engineer'
    assert first['company']['name'] == 'Acme Labs'
    assert 'Bengaluru' in first['location']
    assert first['apply_url'] == 'https://www.linkedin.com/jobs/view/backend-engineer-at-acme-3812345678'
    assert postings[1]['remote'] is True  # "Remote" location


def test_naukri_parse_list():
    postings = NaukriScraper.parse_list(NAUKRI_HTML, 'https://www.naukri.com')
    assert len(postings) == 1
    assert postings[0]['external_id'] == '1234567'
    assert postings[0]['title'] == 'Senior Python Developer'
    assert postings[0]['company']['name'] == 'Acme Labs'


def test_unstop_parse_list():
    postings = UnstopScraper.parse_list(UNSTOP_HTML, 'https://unstop.com')
    assert postings[0]['external_id'] == '987654'
    assert postings[0]['title'] == 'Data Analyst Internship'
    assert postings[0]['remote'] is True
    assert postings[0]['apply_url'] == 'https://unstop.com/jobs/data-analyst-internship-acme-987654'


def test_ycombinator_parse_list():
    postings = YCombinatorScraper.parse_list(YC_HTML, 'https://www.workatastartup.com')
    assert postings[0]['external_id'] == '45678'
    assert postings[0]['title'] == 'Founding Engineer'
    assert postings[0]['company']['name'] == 'Rocket Startup'
    assert postings[0]['remote'] is True


def test_parse_list_empty_html_is_safe():
    assert LinkedInScraper.parse_list('', 'https://www.linkedin.com') == []


def test_scrape_raises_needs_login_on_login_wall():
    driver = FakeBrowserDriver(default_html='<html><body>Join now to see who you know. Sign in to continue.</body></html>')
    scraper = LinkedInScraper(driver)
    with pytest.raises(NeedsLoginError):
        scraper.scrape(PortalQuery(keywords='python'))


def test_scrape_drives_driver_and_returns_postings():
    driver = FakeBrowserDriver(pages={'/jobs/search': LINKEDIN_HTML})
    scraper = LinkedInScraper(driver)
    postings = scraper.scrape(PortalQuery(keywords='python', location='India', max_results=1))
    assert len(postings) == 1  # max_results honoured
    assert driver.visited and 'keywords=python' in driver.visited[0]
