"""Copilot agent loop.

With an LLM (AIAAS-style): plan → act → observe, up to MAX_STEPS per turn.
Each step the model sees the tool catalogue, the recent conversation and a
`--- PRIOR STEPS ---` trajectory of this turn's tool calls + observations, and
answers with strict JSON:  {"tool_calls": [{"name": ..., "args": {...}}]}  or
{"reply": "..."}. Read/draft tools run immediately; a `confirm` tool pauses
the loop and the user approves the exact call in the UI (HITL_CONFIRM).

Without an LLM: a deterministic intent router maps everyday phrasing ("I got
an OA from Infosys on Friday", "tailor my résumé for Stripe") onto the same
tools, so the copilot is useful with zero API keys.
"""

from __future__ import annotations

import json
import re
import secrets
from datetime import date, datetime, timedelta
from typing import Callable

from django.utils import timezone

from .tools import CONFIRM, TOOLS, ToolError, schema

MAX_STEPS = 5
HISTORY = 10

SYSTEM_PROMPT = """You are Career Navigator's copilot: a practical job-search assistant for one candidate
(often a fresher handling campus placements and off-campus applications). You can drive the app with tools.
Rules:
- Use tools to look things up before answering; never invent jobs, companies, dates or numbers.
- Never claim skills or experience the candidate does not have. Tailoring only reorders real facts.
- You cannot submit applications or send messages to other people; you prepare drafts and the user acts.
- Tools marked risk=confirm change the user's records; call them when the user clearly asked, the user will approve.
- Keep replies short, specific, and end with the single most useful next step.
Respond ONLY with JSON: {"tool_calls": [{"name": "...", "args": {...}}]} to act, or {"reply": "..."} to answer."""


# ------------------------------------------------------------------ execution

def execute(user, name: str, args: dict) -> dict:
    tool = TOOLS.get(name)
    if tool is None:
        return {'ok': False, 'error': f'unknown tool {name}'}
    clean = {k: v for k, v in (args or {}).items() if k in tool.params and v not in (None, '')}
    try:
        return {'ok': True, 'result': tool.fn(user, **clean)}
    except ToolError as exc:
        return {'ok': False, 'error': str(exc)}
    except Exception as exc:  # noqa: BLE001 - surface, don't crash the chat
        return {'ok': False, 'error': f'{type(exc).__name__}: {exc}'[:300]}


def pending_for(name: str, args: dict) -> dict:
    tool = TOOLS[name]
    summary = tool.summary(args) or f'{name}({json.dumps(args)})'
    return {'id': secrets.token_hex(8), 'tool': name, 'args': args, 'summary': summary}


def _ui_from(observations: list[dict]) -> list[dict]:
    ui = []
    for o in observations:
        res = o.get('result') or {}
        if isinstance(res, dict):
            ui.extend(res.get('ui') or [])
    seen, out = set(), []
    for u in ui:
        key = (u.get('type'), u.get('to'))
        if key not in seen:
            seen.add(key)
            out.append(u)
    return out[:4]


# ------------------------------------------------------------------ LLM loop

def _parse_llm(raw: str) -> dict | None:
    m = re.search(r'\{.*\}', raw or '', re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def llm_turn(user, message: str, history: list[dict], llm: Callable[[str], str]) -> dict:
    catalogue = json.dumps(schema(), ensure_ascii=False)
    convo = '\n'.join(f"{m['role'].upper()}: {m['content'][:800]}" for m in history[-HISTORY:])
    trajectory: list[dict] = []
    steps: list[dict] = []
    for _ in range(MAX_STEPS):
        prior = '\n'.join(f"STEP {i + 1}: {json.dumps(t, default=str)[:1500]}" for i, t in enumerate(trajectory))
        prompt = (f'{SYSTEM_PROMPT}\n\nTOOLS: {catalogue}\n\nCONVERSATION:\n{convo}\nUSER: {message}\n\n'
                  f'--- PRIOR STEPS ---\n{prior or "(none)"}\n--- END PRIOR STEPS ---\nToday is {date.today():%A %d %B %Y}.')
        data = _parse_llm(llm(prompt) or '')
        if data is None:
            return {} if not steps else {'reply': summarise_steps(steps), 'steps': steps, 'ui': _ui_from(steps)}
        if isinstance(data.get('reply'), str) and not data.get('tool_calls'):
            return {'reply': data['reply'].strip(), 'steps': steps, 'ui': _ui_from(steps)}
        calls = [c for c in data.get('tool_calls') or [] if isinstance(c, dict) and c.get('name') in TOOLS][:4]
        if not calls:
            return {} if not steps else {'reply': summarise_steps(steps), 'steps': steps, 'ui': _ui_from(steps)}
        for call in calls:
            args = call.get('args') if isinstance(call.get('args'), dict) else {}
            if TOOLS[call['name']].risk == CONFIRM:
                pending = pending_for(call['name'], args)
                return {'reply': f"I can do this — please confirm: {pending['summary']}",
                        'steps': steps, 'pending_action': pending, 'ui': _ui_from(steps)}
            obs = {'tool': call['name'], 'args': args, **execute(user, call['name'], args)}
            steps.append(obs)
            trajectory.append(obs)
    return {'reply': summarise_steps(steps), 'steps': steps, 'ui': _ui_from(steps)}


# ------------------------------------------------------------------ deterministic router

MONTHS = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}
WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']


def parse_when(text: str, now: datetime | None = None) -> datetime | None:
    """Find a date (and optional time) in free text. Returns aware datetime or None."""
    now = now or timezone.localtime()
    t = text.lower()
    d: date | None = None
    if m := re.search(r'\b(20\d\d)-(\d{1,2})-(\d{1,2})\b', t):
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    elif re.search(r'\btoday\b|\btonight\b', t):
        d = now.date()
    elif re.search(r'\btomorrow\b', t):
        d = now.date() + timedelta(days=1)
    elif m := re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b', t):
        d = date(now.year, MONTHS[m.group(2)], int(m.group(1)))
    elif m := re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\b', t):
        d = date(now.year, MONTHS[m.group(1)], int(m.group(2)))
    elif m := re.search(r'\b(?:in\s+)?(\d{1,2})\s+days?\b', t):
        d = now.date() + timedelta(days=int(m.group(1)))
    else:
        for i, wd in enumerate(WEEKDAYS):
            if re.search(rf'\b(?:on |this |next )?{wd}\b', t):
                delta = (i - now.weekday()) % 7 or 7
                d = now.date() + timedelta(days=delta)
                break
    if d is None:
        return None
    if d < now.date() - timedelta(days=60):
        d = d.replace(year=d.year + 1)
    hour, minute = 10, 0
    if m := re.search(r'\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', t):
        hour = int(m.group(1)) % 12 + (12 if m.group(3) == 'pm' else 0)
        minute = int(m.group(2) or 0)
    elif m := re.search(r'\bat\s+(\d{1,2}):(\d{2})\b', t):
        hour, minute = int(m.group(1)), int(m.group(2))
    return timezone.make_aware(datetime(d.year, d.month, d.day, hour, minute))


STATUS_PATTERNS = [
    (r'\b(got|received|have|cleared to|scheduled)\b.*\b(oa|online (assessment|test)|assessment|coding (test|round)|aptitude)\b|\b(oa|online assessment)\b.*\b(on|scheduled|tomorrow|today)\b', 'assessment'),
    (r'\b(offer|offered|selected|got the job)\b', 'offer'),
    (r'\b(rejected|rejection|didn\'?t (get|make)|not selected|turned down)\b', 'rejected'),
    (r'\b(hr round|final round|onsite|on-site|final interview)\b', 'onsite'),
    (r'\b(shortlisted|interview|technical round|got a call|phone screen)\b', 'phone'),
    (r'\b(withdr[ae]w|no longer interested)\b', 'withdrawn'),
    (r'\b(i )?(have )?(just )?applied\b|\bsubmitted (my|the) application\b', 'applied'),
]


def _known_companies(user) -> list[tuple[str, int | None, int | None]]:
    """(name, application_id, job_id) for companies the user deals with."""
    from applications.models import Application
    out = [(a.job.company.name, a.id, a.job_id) for a in
           Application.objects.filter(user=user).select_related('job__company').order_by('-updated_at')[:200]]
    return out


def _match_company(user, text: str, *, include_jobs: bool = False):
    low = text.lower()
    best = None
    for name, app_id, job_id in _known_companies(user):
        n = name.lower()
        if n and re.search(r'(?<![a-z0-9])' + re.escape(n) + r'(?![a-z0-9])', low):
            if best is None or len(n) > len(best[0]):
                best = (name, app_id, job_id)
    if best or not include_jobs:
        return best
    from jobs.views import visible_jobs
    m = re.search(r'\b(?:for|at|with|to)\s+(?:the\s+)?([A-Z][\w&.\- ]{1,40}?)(?:\s+(?:role|job|position|internship)|[?.!,]|$)', text)
    if m:
        name = m.group(1).strip()
        j = visible_jobs(user).filter(company__name__iexact=name).order_by('-created_at').first() or \
            visible_jobs(user).filter(company__name__icontains=name).order_by('-created_at').first()
        if j:
            return (j.company.name, None, j.pk)
        return (name, None, None)
    return None


def _split_list(s: str) -> list[str]:
    return [x.strip(' .') for x in re.split(r',|\band\b|/|;', s) if x.strip(' .')]


HELP = ("Here's what I can do — just ask in plain words:\n"
        "• \"What should I do today?\"\n"
        "• \"Find new jobs\" or \"Show my best matches\" / \"remote backend roles\"\n"
        "• \"Tailor my résumé for Stripe\" · \"Write a cover letter for Infosys\"\n"
        "• \"I applied to Zoho\" · \"I got an OA from TCS on Friday at 10am\" · \"Rejected by Wipro\"\n"
        "• \"Deadline for Amazon is 14 Nov\" · \"Show my applications\"\n"
        "• \"Add skills React, Docker\" · \"My target roles are SDE Intern and Data Analyst\"\n"
        "• \"Add contact Riya Shah, SDE at Google, my senior\" · \"Who do I know at Google?\"\n"
        "• \"Help me prepare for the Amazon HR round\"")


def route(user, message: str) -> list[tuple[str, dict]] | str:
    """Map a message to tool calls, or return a direct reply."""
    text = message.strip()
    low = text.lower()
    if not low or re.fullmatch(r'(hi|hello|hey|help|\?|what can you do\??)[!. ]*', low):
        return HELP

    # contacts
    if m := re.match(r'(?:please\s+)?(?:add|save|new)\s+(?:a\s+)?contact[:\s]+(.+)', text, re.IGNORECASE):
        rest = m.group(1)
        parts = [p.strip() for p in rest.split(',')]
        name = parts[0]
        args: dict = {'name': name}
        title_company = ' '.join(parts[1:2]) if len(parts) > 1 else ''
        if mm := re.search(r'^(.*?)\s+at\s+(.+)$', title_company or rest[len(name):].strip()):
            args['title'], args['company'] = mm.group(1).strip(), mm.group(2).strip()
        elif mm := re.search(r'\bat\s+([A-Z][\w&.\- ]+)', rest):
            args['company'] = mm.group(1).strip()
        if email := re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', rest):
            args['email'] = email.group(0)
        if len(parts) > 2:
            args['notes'] = ', '.join(p for p in parts[2:] if '@' not in p)
        return [('add_contact', args)]
    if re.search(r'\b(who do i know|contacts?|referral|refer me|connections?)\b', low):
        comp = _match_company(user, text, include_jobs=True)
        if re.search(r'\b(draft|write|message|ask)\b', low) and comp:
            from networking.models import Contact
            c = Contact.objects.filter(user=user, company__name__iexact=comp[0]).order_by('-relationship_strength').first()
            if c:
                return [('draft_referral_message', {'contact_id': c.id, 'job_id': comp[2]})]
        return [('list_contacts', {'company': comp[0] if comp else ''})]

    # profile edits
    if m := re.search(r'\b(?:add|i (?:know|have|can use))\s+(?:the\s+)?(?:skills?|experience with)?\s*[:\-]?\s*(.+)', text, re.IGNORECASE):
        if re.search(r'\bskills?\b|\bi (know|can use)\b|\bexperience with\b', low):
            return [('update_skills', {'add': _split_list(m.group(1))})]
    if m := re.search(r'\bremove\s+(?:the\s+)?skills?\s*[:\-]?\s*(.+)', text, re.IGNORECASE):
        return [('update_skills', {'remove': _split_list(m.group(1))})]
    if m := re.search(r'\b(?:target(?:ing)?|looking for|i want (?:to work as|roles? (?:as|like))|my (?:target )?roles? (?:are|is))\s*(?:roles?)?\s*[:\-]?\s*(?:as\s+)?(.+)', text, re.IGNORECASE):
        if not re.search(r'\bjobs?\b\s*$', low):
            return [('update_targets', {'roles': _split_list(m.group(1))})]
    if m := re.search(r'\bweekly goal\b.*?(\d+)|\b(\d+)\s+applications? (?:a|per) week\b', low):
        return [('update_targets', {'weekly_goal': int(m.group(1) or m.group(2))})]

    # tailoring
    if re.search(r'\b(tailor|customi[sz]e|optimi[sz]e)\b.*\b(resume|résumé|cv)\b|\b(resume|résumé|cv)\b.*\bfor\b', low):
        comp = _match_company(user, text, include_jobs=True)
        if not comp or (comp[1] is None and comp[2] is None):
            return 'Which job? Tell me the company (e.g. "tailor my résumé for Stripe") — it needs to be in your Jobs or Pipeline.'
        return [('tailor_resume', {'application_id': comp[1], 'job_id': comp[2] if comp[1] is None else None})]
    if re.search(r'\bcover letter\b', low):
        comp = _match_company(user, text, include_jobs=True)
        if not comp or (comp[1] is None and comp[2] is None):
            return 'Which job should the cover letter be for? Name the company.'
        return [('draft_cover_letter', {'application_id': comp[1], 'job_id': comp[2] if comp[1] is None else None})]

    # practice
    if re.search(r'\b(prepare|prep|practi[cs]e|mock|rehearse)\b', low):
        comp = _match_company(user, text)
        stage = 'hr' if re.search(r'\bhr\b', low) else 'cs_fundamentals' if re.search(r'\b(cs|dbms|os|oops?|fundamentals|technical basics)\b', low) \
            else 'behavioral' if 'behavio' in low else 'tech_phone'
        if comp and comp[1]:
            return [('start_practice', {'application_id': comp[1], 'stage': stage})]
        return [('navigate', {'path': '/practice'})]

    # application updates
    comp = _match_company(user, text)
    if comp and comp[1]:
        when = parse_when(text)
        for pattern, status in STATUS_PATTERNS:
            if re.search(pattern, low):
                args = {'application_id': comp[1], 'status': status}
                if when and status in ('assessment', 'phone', 'onsite'):
                    args['next_round_at'] = when.isoformat()
                return [('update_application', args)]
        if re.search(r'\bdeadline|last date|apply by|closes\b', low) and when:
            return [('update_application', {'application_id': comp[1], 'deadline': when.date().isoformat()})]
        if m := re.search(r'\bnote[:\s]+(.+)', text, re.IGNORECASE):
            return [('update_application', {'application_id': comp[1], 'notes': m.group(1)})]
        if re.search(r'\b(status|where am i|update)\b', low):
            return [('list_applications', {'company': comp[0]})]

    # discovery
    if re.search(r'\b(find|search|look for|fetch|refresh|get)\b.*\b(new|more|fresh|latest)\b.*\b(jobs?|roles?|openings?|internships?)\b|\brefresh jobs\b', low):
        return [('find_new_jobs', {})]
    if re.search(r'\b(jobs?|roles?|openings?|matches|internships?|positions?)\b', low) and \
            not re.search(r'\b(applications?|pipeline)\b', low):
        args = {'min_fit': 70 if re.search(r'\bstrong\b', low) else 0,
                'remote': bool(re.search(r'\bremote\b', low)), 'limit': 5}
        q = re.sub(r'\b(show|me|my|find|the|best|top|strong|matches|match|jobs?|roles?|openings?|remote|for|some|any|good|'
                   r'please|internships?|positions?|recommend(ed)?|what|are|there|in)\b', ' ', low)
        q = re.sub(r'[^\w+#. -]', ' ', q).strip()
        if 'intern' in low:
            q = (q + ' intern').strip()
        args['query'] = re.sub(r'\s+', ' ', q)[:60]
        return [('search_jobs', args)]

    if re.search(r'\b(applications?|pipeline|applied to|status)\b', low):
        status = next((s for s in ['saved', 'applied', 'assessment', 'offer', 'rejected'] if s in low), '')
        if 'interview' in low:
            status = 'phone'
        return [('list_applications', {'status': status})]
    if re.search(r'\b(profile|my skills|about me|what do you know)\b', low):
        return [('get_profile', {})]
    if re.search(r'\b(today|next|plan|what should i|todo|to-do|overview|deadlines?|follow ?ups?)\b', low):
        return [('get_overview', {})]
    if comp and comp[1]:
        return [('list_applications', {'company': comp[0]})]
    return "I'm not sure what you'd like me to do.\n\n" + HELP


def rule_turn(user, message: str) -> dict:
    plan = route(user, message)
    if isinstance(plan, str):
        return {'reply': plan, 'steps': [], 'ui': []}
    steps = []
    for name, args in plan:
        args = {k: v for k, v in args.items() if v not in (None, '')}
        if TOOLS[name].risk == CONFIRM:
            pending = pending_for(name, args)
            return {'reply': f"Shall I go ahead? {pending['summary']}", 'steps': steps, 'pending_action': pending, 'ui': []}
        steps.append({'tool': name, 'args': args, **execute(user, name, args)})
    return {'reply': summarise_steps(steps), 'steps': steps, 'ui': _ui_from(steps)}


# ------------------------------------------------------------------ replies

def _fmt_dt(iso: str | None) -> str:
    if not iso:
        return ''
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return iso
    return dt.strftime('%a %d %b') + (dt.strftime(', %I:%M %p').replace(' 0', ' ') if 'T' in iso else '')


def describe(step: dict) -> str:
    name, res = step['tool'], step.get('result')
    if not step.get('ok'):
        return f"I couldn't do that: {step.get('error')}"
    if name == 'get_overview':
        lines = [f"• {s['title']} — {s['detail']}" for s in res['steps'][:6]]
        st = res['stats']
        head = f"This week: {res['week']['applied']}/{res['week']['goal']} applications. " \
               f"{st['applied']} applied in total, {st['interviewing']} in assessment/interviews, {st['offers']} offers."
        return head + ('\n\nNext steps:\n' + '\n'.join(lines) if lines else '\n\nYou are all caught up.')
    if name == 'search_jobs':
        if not res['has_profile']:
            return 'Add your résumé first so I can rank jobs for you.'
        if not res['jobs']:
            return 'No matching jobs yet. Say "find new jobs" to search company boards, or add one you found.'
        lines = [f"• {j['title']} at {j['company']} — fit {j['fit']}/100"
                 + (f" (missing {', '.join(j['missing'][:2])})" if j.get('missing') else '') for j in res['jobs']]
        return f"Top {len(lines)} of {res['total']} jobs for you:\n" + '\n'.join(lines)
    if name == 'find_new_jobs':
        ok = [s for s in res['sources'] if s['ok']]
        return f"Searched {len(res['sources'])} sources ({len(ok)} reachable) and found {res['new_jobs']} new jobs."
    if name == 'get_job':
        return f"{res['title']} at {res['company']}: fit {res['fit']}/100 ({res['verdict']}). " + '; '.join(res['reasons'][:4])
    if name == 'list_applications':
        if not res['applications']:
            return 'No applications found.'
        lines = [f"• {a['company']} — {a['title']}: {a['status']}"
                 + (f", next round {_fmt_dt(a['next_round_at'])}" if a['next_round_at'] else '')
                 + (f", deadline {a['deadline']}" if a['deadline'] else '') for a in res['applications'][:10]]
        return f"{res['count']} application(s):\n" + '\n'.join(lines)
    if name == 'list_contacts':
        if not res['contacts']:
            return 'No contacts saved there yet. Add one with: "add contact Riya Shah, SDE at Google, college senior".'
        return 'Your contacts:\n' + '\n'.join(f"• {c['name']}" + (f", {c['title']}" if c['title'] else '')
                                             + (f" at {c['company']}" if c['company'] else '') for c in res['contacts'][:10])
    if name == 'get_profile':
        return (f"{res['name'] or 'You'} — {res['headline'] or 'no headline yet'}.\n"
                f"Skills: {', '.join(res['skills'][:15]) or 'none yet'}.\n"
                f"Education: {'; '.join(res['education']) or 'not added'}.\n"
                f"Targets: {', '.join(res['targets']['roles']) or 'not set'}.")
    if name == 'save_job':
        return f"Saved {res['title']} at {res['company']} to your pipeline."
    if name == 'add_job':
        return f"Added {res['title']} at {res['company']} and saved it to your pipeline."
    if name == 'tailor_resume':
        cov = f"covers {res['keyword_coverage']}% of the skills they ask for" if res['keyword_coverage'] is not None else 'is ready'
        gaps = f" Gaps to address honestly: {', '.join(res['missing_skills'])}." if res['missing_skills'] else ''
        return f"Tailored your résumé for {res['title']} at {res['company']} — it {cov}.{gaps} Review and download it from the job page."
    if name == 'draft_cover_letter':
        return 'Here is a draft cover letter (edit it on the job page):\n\n' + res['letter']
    if name == 'draft_referral_message':
        return f"Draft referral request to {res['to']} — copy and send it yourself:\n\n{res['draft']}"
    if name == 'start_practice':
        return f"Ready to practise for {res['company']} ({res['stage'].replace('_', ' ')}). Open the practice room to begin."
    if name == 'update_application':
        extra = []
        if res.get('next_round_at'):
            extra.append(f"next round {_fmt_dt(res['next_round_at'])}")
        if res.get('deadline'):
            extra.append(f"deadline {res['deadline']}")
        return f"Updated {res['company']}: status {res['status']}" + (f", {', '.join(extra)}" if extra else '') + '.'
    if name == 'update_targets':
        return f"Targets saved: {', '.join(res['roles']) or 'no roles'}; locations {', '.join(res['locations']) or 'any'}; " \
               f"weekly goal {res['weekly_goal']}."
    if name == 'update_skills':
        bits = []
        if res['added']:
            bits.append(f"added {', '.join(res['added'])}")
        if res['removed']:
            bits.append(f"removed {', '.join(res['removed'])}")
        return ('Skills ' + ' and '.join(bits) + '.') if bits else 'Those skills were already on your profile.'
    if name == 'add_contact':
        return f"Saved {res['name']} as a contact."
    if name == 'navigate':
        return 'Opening that page.'
    return json.dumps(res, default=str)[:600]


def summarise_steps(steps: list[dict]) -> str:
    return '\n\n'.join(describe(s) for s in steps) or 'Done.'
