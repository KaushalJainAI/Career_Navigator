"""Parse tests for the newly added portal scrapers.

Each fixture is a representative slice of the portal's result markup that matches
the scraper's `# LIVE-SELECTOR` xpaths, so these lock in the canonical output
shape. The live selectors still need verifying against real pages.
"""

from portals.registry import PORTALS, get_scraper
from portals.scrapers.cutshort import CutshortScraper
from portals.scrapers.foundit import FounditScraper
from portals.scrapers.glassdoor import GlassdoorScraper
from portals.scrapers.hirect import HirectScraper
from portals.scrapers.indeed import IndeedScraper
from portals.scrapers.instahyre import InstahyreScraper
from portals.scrapers.internshala import InternshalaScraper
from portals.scrapers.shine import ShineScraper
from portals.scrapers.timesjobs import TimesJobsScraper
from portals.scrapers.wellfound import WellfoundScraper


def test_instahyre_parse_list():
    html = """
    <div class="opening-card">
      <a href="/job/482913/backend-engineer-acme">Backend Engineer</a>
      <div class="opening-title">Backend Engineer</div>
      <div class="company-name">Acme Labs</div>
      <div class="location">Bengaluru</div>
    </div>
    """
    p = InstahyreScraper.parse_list(html, 'https://www.instahyre.com')[0]
    assert p['external_id'] == '482913'
    assert p['title'] == 'Backend Engineer'
    assert p['company']['name'] == 'Acme Labs'
    assert p['apply_url'] == 'https://www.instahyre.com/job/482913/backend-engineer-acme'


def test_wellfound_parse_list():
    html = """
    <div class="styles_component__x1">
      <a href="/jobs/1234567-senior-platform-engineer">Senior Platform Engineer</a>
      <span class="company">Rocket</span>
      <span class="location">Remote</span>
    </div>
    """
    p = WellfoundScraper.parse_list(html, 'https://wellfound.com')[0]
    assert p['external_id'] == '1234567'
    assert p['title'] == 'Senior Platform Engineer'
    assert p['remote'] is True


def test_shine_parse_list():
    html = """
    <div class="jobCard">
      <a href="/jobs/senior-python-developer-acme/9988776">x</a>
      <span class="jobTitle">Senior Python Developer</span>
      <span class="companyName">Acme Labs</span>
      <span class="jobLoc">Pune</span>
    </div>
    """
    p = ShineScraper.parse_list(html, 'https://www.shine.com')[0]
    assert p['external_id'] == '9988776'
    assert p['title'] == 'Senior Python Developer'
    assert p['company']['name'] == 'Acme Labs'


def test_indeed_parse_list():
    html = """
    <div class="job_seen_beacon" data-jk="a1b2c3d4e5">
      <h2 class="jobTitle"><span>Data Engineer</span></h2>
      <span data-testid="company-name">Globex</span>
      <div data-testid="text-location">Remote</div>
    </div>
    """
    p = IndeedScraper.parse_list(html, 'https://www.indeed.com')[0]
    assert p['external_id'] == 'a1b2c3d4e5'
    assert p['title'] == 'Data Engineer'
    assert p['company']['name'] == 'Globex'
    assert p['apply_url'] == 'https://www.indeed.com/viewjob?jk=a1b2c3d4e5'
    assert p['remote'] is True


def test_timesjobs_parse_list():
    html = """
    <li class="clearfix job-bx">
      <header><h2><a href="https://www.timesjobs.com/job-detail/dev-acme-jobid-7654321">Software Developer</a></h2></header>
      <h3 class="joblist-comp-name">Acme Labs</h3>
      <ul class="top-jd-dtl"><li><span>Mumbai</span></li></ul>
    </li>
    """
    p = TimesJobsScraper.parse_list(html, 'https://www.timesjobs.com')[0]
    assert p['external_id'] == '7654321'
    assert p['title'] == 'Software Developer'
    assert p['company']['name'] == 'Acme Labs'


def test_foundit_parse_list():
    html = """
    <div class="srpResultCardContainer srpResultCard">
      <a href="/job/frontend-engineer-globex-334455">x</a>
      <div class="jobTitle">Frontend Engineer</div>
      <div class="companyName">Globex</div>
      <div class="jobLocation">Hyderabad</div>
    </div>
    """
    p = FounditScraper.parse_list(html, 'https://www.foundit.in')[0]
    assert p['external_id'] == '334455'
    assert p['title'] == 'Frontend Engineer'
    assert p['company']['name'] == 'Globex'


def test_cutshort_parse_list():
    html = """
    <div class="job-card">
      <a href="/job/Ab3Cd9Ef2/react-developer">x</a>
      <div class="job-title">React Developer</div>
      <div class="company">Startup Inc</div>
      <div class="location">Remote</div>
    </div>
    """
    p = CutshortScraper.parse_list(html, 'https://cutshort.io')[0]
    assert p['external_id'] == 'Ab3Cd9Ef2'
    assert p['title'] == 'React Developer'
    assert p['remote'] is True


def test_hirect_parse_list():
    html = """
    <div class="job-item">
      <a href="/job/55667788">x</a>
      <div class="job-title">Android Developer</div>
      <div class="company">Chatty Co</div>
      <div class="city">Delhi</div>
    </div>
    """
    p = HirectScraper.parse_list(html, 'https://www.hirect.in')[0]
    assert p['external_id'] == '55667788'
    assert p['title'] == 'Android Developer'
    assert p['company']['name'] == 'Chatty Co'


def test_internshala_parse_list():
    html = """
    <div class="individual_internship">
      <a class="job-title-href" href="/job/detail/python-developer-job-in-bangalore-98765">Python Developer</a>
      <div class="company-name">Acme Labs</div>
      <div class="locations">Bangalore</div>
    </div>
    """
    p = InternshalaScraper.parse_list(html, 'https://internshala.com')[0]
    assert p['external_id'] == '98765'
    assert p['title'] == 'Python Developer'
    assert p['company']['name'] == 'Acme Labs'


def test_glassdoor_parse_list():
    html = """
    <li class="JobsList_jobListItem__wjTHv" data-jobid="1009876543">
      <a class="JobCard_jobTitle__abc" href="/job-listing/data-scientist-acme-JV_123.htm">Data Scientist</a>
      <div class="EmployerProfile_employerName__x">Acme Labs</div>
      <div class="JobCard_location__y">San Francisco / Remote</div>
    </li>
    """
    p = GlassdoorScraper.parse_list(html, 'https://www.glassdoor.com')[0]
    assert p['external_id'] == '1009876543'
    assert p['title'] == 'Data Scientist'
    assert p['company']['name'] == 'Acme Labs'
    assert p['remote'] is True


def test_every_registered_portal_resolves_to_a_scraper():
    # PortalListView surfaces the whole registry; each must have a working scraper.
    for name in PORTALS:
        cls = get_scraper(name)
        assert cls is not None, f'no scraper wired for {name!r}'
        assert callable(cls.parse_list)


def test_empty_html_is_safe_for_all():
    for cls in (InstahyreScraper, WellfoundScraper, ShineScraper, IndeedScraper,
                TimesJobsScraper, FounditScraper, CutshortScraper, HirectScraper,
                InternshalaScraper, GlassdoorScraper):
        assert cls.parse_list('', 'https://example.com') == []
