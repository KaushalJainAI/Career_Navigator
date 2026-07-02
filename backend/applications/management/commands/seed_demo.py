"""Seed realistic demo data for the application tracker.

Creates demo companies + job postings, a spread of applications across every
pipeline stage (back-dated, with status-change events so the analytics funnel
lights up), plus follow-ups, todos and goals — so the tracker can be evaluated
with real-looking content.

    python manage.py seed_demo --email you@example.com
    python manage.py seed_demo --email you@example.com --clear   # wipe & reseed

All demo jobs hang off a single Source named "demo-seed", so --clear can remove
everything it created without touching real data.
"""
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from applications.models import Application, ApplicationEvent, Goal, Todo
from jobs.models import Company, JobPosting, Source
from networking.models import (
    ActionQueueItem,
    Contact,
    OutreachMessage,
    ReferralOpportunity,
)
from notifications.models import Alert, Subscription

SOURCE_NAME = 'demo-seed'
DEMO_SUB_NAME = 'Demo alerts'

# (company, event_type, hours_ago) — richer interaction events for the activity feed.
EXTRA_EVENTS = [
    ('Stripe', 'tailored_resume_generated', 30 * 24),
    ('Stripe', 'cover_letter_generated', 30 * 24),
    ('Vercel', 'tailored_resume_generated', 19 * 24),
    ('Notion', 'autonomous_prepared', 5 * 24),
    ('Retool', 'tailored_resume_generated', 40),
]

# (contact_name, company_for_job, score, status, reason, next_action)
REFERRALS = [
    ('Priya Sharma', 'Stripe', 88, 'referred',
     'Worked with you directly — strong backend overlap.', 'Thank Priya and share your resume link'),
    ('Alex Chen', 'Vercel', 72, 'contacted',
     'Same stack; offered an intro to the hiring manager.', 'Follow up on the intro offer'),
    ('Maya Patel', 'Notion', 64, 'suggested',
     'Director in the org — can flag your application internally.', 'Ask Maya for a referral'),
    ('Ravi Kumar', 'Datadog', 55, 'suggested',
     'On the platform team; can vouch for you.', 'Reach out to Ravi'),
]

# (contact_name, subject, body, status, hours_ago_sent_or_None)
OUTREACH = [
    ('Alex Chen', 'Quick question about the Vercel role',
     'Hi Alex,\n\nSaw the Full Stack Engineer opening at Vercel and your name came up. Would you be open to a quick pointer on whether the team is actively hiring?\n\nHappy to send a short resume summary. Thanks either way!',
     'drafted', None),
    ('Maya Patel', 'Referral for the Notion backend role',
     'Hi Maya,\n\nThanks again for offering to help. I just applied for the Backend Engineer role at Notion — would you be comfortable flagging my application internally?\n\nResume link attached. Really appreciate it!',
     'sent', 26),
]

# (action_type, title, priority, due_in_days, contact_name)
ACTIONS = [
    ('send_outreach', 'Send the drafted message to Alex Chen', 80, 0, 'Alex Chen'),
    ('follow_up', 'Follow up with Priya on the Stripe referral', 75, 1, 'Priya Sharma'),
    ('ask_referral', 'Ask Maya Patel for a Notion referral', 60, 2, 'Maya Patel'),
    ('reconnect', 'Reconnect with Tom Baker as a reference', 40, 5, 'Tom Baker'),
]

# (company, hours_ago, read) — job-match notifications for the bell.
ALERTS = [
    ('Anthropic', 3, False),
    ('Linear', 20, False),
    ('Supabase', 30, False),
    ('Notion', 52, True),
    ('Vercel', 96, True),
]

# (company, domain, title, location, remote, smin, smax, status, applied_days_ago,
#  tier, ghost_risk, first_response_days_after_apply, next_action, follow_up_in_days, notes)
JOBS = [
    ('Stripe', 'stripe.com', 'Senior Backend Engineer', 'Remote (US)', True, 180000, 240000,
     'offer', 34, 'assist', 8, 12, 'Negotiate offer — ask about equity refresh', 1,
     'Offer received! 4 rounds done. Comp looks strong, clarifying equity.'),
    ('Vercel', 'vercel.com', 'Full Stack Engineer', 'Remote', True, 160000, 210000,
     'onsite', 21, 'autofill', 5, 9, 'Prep system design for onsite loop', 3,
     'Onsite scheduled next week. 3 technical + 1 behavioural.'),
    ('Datadog', 'datadoghq.com', 'Platform Engineer', 'New York, NY', False, 170000, 220000,
     'phone', 12, 'assist', 15, 6, 'Send thank-you note to recruiter', 0,
     'Recruiter screen went well. Waiting on tech phone screen slot.'),
    ('Notion', 'notion.so', 'Backend Engineer', 'SF / Remote', True, 165000, 215000,
     'applied', 6, 'autonomous', 20, None, 'Ask ex-colleague for a referral', 2,
     'Applied via careers page. Trying to line up a warm intro.'),
    ('Linear', 'linear.app', 'Product Engineer', 'Remote', True, 150000, 200000,
     'applied', 4, 'assist', 10, None, 'Follow up if no reply by end of week', 4,
     'Small team, high bar. Tailored resume emphasised product sense.'),
    ('Ramp', 'ramp.com', 'Software Engineer', 'New York, NY', False, 170000, 225000,
     'phone', 15, 'autofill', 12, 7, 'Confirm availability for tech screen', -1,
     'Passed recruiter chat. Overdue on scheduling — chase this.'),
    ('Anthropic', 'anthropic.com', 'Software Engineer, Product', 'Remote', True, 200000, 300000,
     'applied', 3, 'assist', 5, None, 'Review take-home requirements', 5,
     'Dream role. Take-home assignment pending.'),
    ('Figma', 'figma.com', 'Infrastructure Engineer', 'San Francisco, CA', False, 175000, 230000,
     'ready', 1, 'assist', 18, None, 'Submit application', 1,
     'Materials tailored and ready to send.'),
    ('Retool', 'retool.com', 'Full Stack Engineer', 'Remote', True, 155000, 205000,
     'tailored', 2, 'assist', 22, None, 'Generate cover letter, then apply', 2,
     'Resume tailored. Cover letter next.'),
    ('Supabase', 'supabase.com', 'Backend Engineer (Postgres)', 'Remote', True, 150000, 195000,
     'saved', 0, '', 8, None, 'Review JD and decide whether to apply', 3,
     'Saved from discovery. Strong Postgres match.'),
    ('Airtable', 'airtable.com', 'Backend Engineer', 'Remote', True, 160000, 210000,
     'rejected', 40, 'autofill', 35, None, '', None,
     'Rejected after tech screen. High ghost-risk posting — noted for pattern.'),
    ('Render', 'render.com', 'Platform Engineer', 'Remote', True, 150000, 190000,
     'withdrawn', 28, 'assist', 25, None, '', None,
     'Withdrew — location/timezone mismatch.'),
]

TODOS = [
    ('Follow up with Stripe recruiter about offer timeline', 'Stripe', 1, False),
    ('Prepare a system-design story for the Vercel onsite', 'Vercel', 3, False),
    ('Send a thank-you note to the Datadog interviewer', 'Datadog', 0, False),
    ('Ask ex-colleague for a referral at Notion', 'Notion', 2, False),
    ('Update LinkedIn headline and "open to work"', None, None, False),
    ('Review the Anthropic take-home requirements', 'Anthropic', 5, True),
]

GOALS = [
    ('Apply to 15 roles this week', Goal.Metric.APPLICATIONS, 15, Goal.Period.WEEK, 0),
    ('Land 3 interviews this month', Goal.Metric.INTERVIEWS, 3, Goal.Period.MONTH, 0),
    ('Get an offer', Goal.Metric.OFFERS, 1, Goal.Period.ALL, 0),
    ('Reach out to 10 contacts', Goal.Metric.CUSTOM, 10, Goal.Period.WEEK, 4),
]

# (name, title, company, location, email, profile_url, strength, tags, notes)
CONTACTS = [
    ('Maya Patel', 'Director of Engineering', 'Notion', 'Remote', 'maya@notion.example',
     'https://linkedin.com/in/mayapatel', 5, ['mentor', 'strong'],
     'Long-time mentor and strong advocate — happy to refer.'),
    ('Priya Sharma', 'Engineering Manager', 'Stripe', 'Remote', 'priya@stripe.example',
     'https://linkedin.com/in/priyasharma', 4, ['referral', 'ex-colleague'],
     'Worked together at a prior startup. Can refer for backend roles.'),
    ('Alex Chen', 'Staff Engineer', 'Vercel', 'San Francisco, CA', '',
     'https://linkedin.com/in/alexchen', 3, ['warm-intro'],
     'Met at a conference — offered to intro me to the hiring manager.'),
    ('Sam Rivera', 'Founding Engineer', 'Linear', 'Remote', '',
     'https://linkedin.com/in/samrivera', 3, ['ex-colleague'],
     'Old teammate, now early at Linear.'),
    ('Jordan Lee', 'Technical Recruiter', 'Datadog', 'New York, NY', 'jordan@datadog.example',
     '', 2, ['recruiter'],
     'Reached out about the platform engineering role.'),
    ('Nina White', 'Staff Engineer', 'Ramp', 'New York, NY', '',
     'https://linkedin.com/in/ninawhite', 4, ['referral', 'friend'],
     'Close friend — offered to submit a referral.'),
    ('Tom Baker', 'Engineering Manager', 'Airtable', 'Remote', '',
     'https://linkedin.com/in/tombaker', 3, ['ex-colleague'],
     'Managed me two roles ago; good reference.'),
    ('Aisha Khan', 'Product Manager', 'Notion', 'Remote', '',
     'https://linkedin.com/in/aishakhan', 3, ['mutual'],
     'Mutual connection via Maya; can intro to the team.'),
    ('David Park', 'Technical Recruiter', 'Anthropic', 'Remote', 'david@anthropic.example',
     '', 2, ['recruiter'],
     'Reached out about the product engineering role.'),
    ('Carlos Mendez', 'Co-founder & CTO', 'Supabase', 'Remote', 'carlos@supabase.example',
     '', 2, ['founder', 'warm-intro'],
     'Met at a hackathon — said to ping when applying.'),
    ('Elena Ortiz', 'Recruiting Lead', 'Figma', 'San Francisco, CA', 'elena@figma.example',
     '', 2, ['recruiter'],
     'Sourced me for the infrastructure role.'),
    ('Ravi Kumar', 'Senior Engineer', 'Datadog', 'Remote', '',
     'https://linkedin.com/in/ravikumar', 3, ['warm-intro'],
     'Can put in a word with the platform team.'),
    ('Sara Lindqvist', 'Design Lead', '', 'Remote', '',
     'https://linkedin.com/in/saralind', 1, ['cold-outreach'],
     'Cold outreach target — no reply yet.'),
]


class Command(BaseCommand):
    help = 'Seed demo applications, todos and goals for a user.'

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Target user email. If omitted, seeds every user.')
        parser.add_argument('--clear', action='store_true', help='Remove demo data first.')

    def handle(self, *args, **opts):
        User = get_user_model()
        users = User.objects.filter(email__iexact=opts['email']) if opts.get('email') else User.objects.all()
        if not users:
            self.stderr.write(self.style.ERROR('No matching users.'))
            return

        source, _ = Source.objects.get_or_create(name=SOURCE_NAME, defaults={'kind': 'web_search'})

        for user in users:
            if opts['clear']:
                self._clear(user, source)
            self._seed(user, source)
            self.stdout.write(self.style.SUCCESS(f'Seeded demo data for {user.email}'))

    def _clear(self, user, source):
        Application.objects.filter(user=user, job__source=source).delete()  # cascades events
        Todo.objects.filter(user=user).delete()
        Goal.objects.filter(user=user).delete()
        ReferralOpportunity.objects.filter(user=user).delete()
        OutreachMessage.objects.filter(user=user).delete()
        ActionQueueItem.objects.filter(user=user).delete()
        Contact.objects.filter(user=user).delete()  # cascades contact-linked rows
        Subscription.objects.filter(user=user, name=DEMO_SUB_NAME).delete()  # cascades its alerts

    def _seed(self, user, source):
        now = timezone.now()
        apps_by_company: dict[str, Application] = {}

        for (company_name, domain, title, location, remote, smin, smax, status, applied_days_ago,
             tier, ghost_risk, resp_days, next_action, follow_in, notes) in JOBS:
            company, _ = Company.objects.get_or_create(name=company_name, defaults={'domain': domain})
            job, _ = JobPosting.objects.get_or_create(
                source=source, external_id=f'demo-{company_name.lower()}-{title[:12].lower().replace(" ", "-")}',
                defaults={
                    'company': company, 'title': title,
                    'description': f'<p>{title} at {company_name}. Demo posting for the tracker.</p>',
                    'location': location, 'remote': remote,
                    'salary_min': smin, 'salary_max': smax, 'salary_currency': 'USD',
                    'apply_url': f'https://{domain}/careers', 'ghost_risk': ghost_risk,
                    'ghost_reasons': ['Elevated repost frequency'] if ghost_risk >= 30 else [],
                },
            )
            applied_at = now - timedelta(days=applied_days_ago)
            follow_up = (now.date() + timedelta(days=follow_in)) if follow_in is not None else None
            app, created = Application.objects.get_or_create(
                user=user, job=job,
                defaults={
                    'status': status, 'tier_used': tier, 'notes': notes,
                    'next_action': next_action, 'follow_up_on': follow_up,
                },
            )
            if not created:
                continue
            # Back-date created_at (auto_now_add ignores assignment on create).
            Application.objects.filter(pk=app.pk).update(created_at=applied_at, updated_at=applied_at)
            apps_by_company[company_name] = app
            self._add_events(app, applied_at, status, resp_days)

        self._seed_todos(user, apps_by_company)
        self._seed_goals(user)
        self._seed_contacts(user)
        self._seed_networking(user, apps_by_company)
        self._seed_alerts(user, apps_by_company)
        self._seed_extra_events(apps_by_company)

    def _add_events(self, app, applied_at, status, resp_days):
        """Emit status_changed events so the analytics funnel + response timing work."""
        progression = ['applied', 'phone', 'onsite', 'offer']
        if status not in progression and status not in ('rejected', 'withdrawn'):
            return
        # Build the chain up to the current peak stage.
        peak = 'offer' if status in ('rejected', 'withdrawn') and resp_days else status
        chain = []
        for stage in progression:
            chain.append(stage)
            if stage == status:
                break
        offsets = {'applied': 0, 'phone': resp_days or 5, 'onsite': (resp_days or 5) + 6,
                   'offer': (resp_days or 5) + 12}
        for stage in chain:
            ev = ApplicationEvent.objects.create(
                application=app, type='status_changed', payload={'status': stage})
            ApplicationEvent.objects.filter(pk=ev.pk).update(
                created_at=applied_at + timedelta(days=offsets.get(stage, 0)))

    def _seed_todos(self, user, apps_by_company):
        now = timezone.now()
        for title, company, due_in, done in TODOS:
            app = apps_by_company.get(company) if company else None
            Todo.objects.create(
                user=user, title=title, done=done, application=app,
                due_on=(now.date() + timedelta(days=due_in)) if due_in is not None else None,
            )

    def _seed_goals(self, user):
        for title, metric, target, period, manual in GOALS:
            Goal.objects.create(
                user=user, title=title, metric=metric, target=target,
                period=period, manual_progress=manual)

    def _seed_extra_events(self, apps_by_company):
        now = timezone.now()
        for company, event_type, hours_ago in EXTRA_EVENTS:
            app = apps_by_company.get(company)
            if app is None:
                continue
            ev = ApplicationEvent.objects.create(application=app, type=event_type, payload={})
            ApplicationEvent.objects.filter(pk=ev.pk).update(created_at=now - timedelta(hours=hours_ago))

    def _seed_networking(self, user, apps_by_company):
        now = timezone.now()
        contacts = {c.name: c for c in Contact.objects.filter(user=user)}

        for name, company, score, status, reason, next_action in REFERRALS:
            contact = contacts.get(name)
            app = apps_by_company.get(company)
            if not contact or not app:
                continue
            ReferralOpportunity.objects.get_or_create(
                user=user, job=app.job, contact=contact,
                defaults={'score': score, 'status': status, 'reason': reason, 'next_action': next_action},
            )

        for name, subject, body, status, hours_ago in OUTREACH:
            contact = contacts.get(name)
            if not contact:
                continue
            msg = OutreachMessage.objects.create(
                user=user, contact=contact, channel='email', subject=subject,
                draft_body=body, status=status,
                approved_body=body if status in ('sent', 'approved') else '',
            )
            if hours_ago is not None:
                OutreachMessage.objects.filter(pk=msg.pk).update(sent_at=now - timedelta(hours=hours_ago))

        for action_type, title, priority, due_in, name in ACTIONS:
            contact = contacts.get(name)
            ActionQueueItem.objects.create(
                user=user, action_type=action_type, title=title, priority=priority,
                due_at=now + timedelta(days=due_in), contact=contact, status='open',
            )

    def _seed_alerts(self, user, apps_by_company):
        now = timezone.now()
        sub, _ = Subscription.objects.get_or_create(
            user=user, name=DEMO_SUB_NAME,
            defaults={'filter_json': {}, 'channels': ['in_app'], 'enabled': True},
        )
        for company, hours_ago, read in ALERTS:
            app = apps_by_company.get(company)
            if app is None:
                continue
            alert, created = Alert.objects.get_or_create(
                user=user, job=app.job, subscription=sub, channel='in_app',
                defaults={'read': read},
            )
            if created:
                Alert.objects.filter(pk=alert.pk).update(
                    sent_at=now - timedelta(hours=hours_ago), read=read)

    def _seed_contacts(self, user):
        for name, title, company_name, location, email, url, strength, tags, notes in CONTACTS:
            company, _ = Company.objects.get_or_create(name=company_name)
            Contact.objects.get_or_create(
                user=user, name=name,
                defaults={
                    'title': title, 'company': company, 'location': location,
                    'email': email, 'profile_url': url, 'relationship_strength': strength,
                    'tags': tags, 'notes': notes,
                },
            )
