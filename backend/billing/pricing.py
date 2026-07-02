"""Credit pricing for paid actions.

Career Navigator uses a simple, honest credit model (no Stripe yet): every user
gets a welcome bonus, and the AI-heavy actions cost a fixed number of credits.
Credits are *rolling* — they never expire. Reading, matching, ghost-risk scoring,
Kanban tracking and alerts are always free.

The keys here match ``billing.models.CreditLedger.REASONS`` so a spend is fully
auditable in the ledger.
"""

# One-time welcome grant issued the moment an account is created.
SIGNUP_BONUS = 100

# Credits deducted per paid action.
PRICING = {
    'tailor_resume': 5,
    'cover_letter': 3,
    'mock_interview': 8,
    'autonomous_apply': 10,
}

# Human-facing catalogue used by the pricing endpoint and the in-app UI, so the
# cost and value of each paid action is visible *before* the user spends.
CATALOG = [
    {
        'reason': 'tailor_resume',
        'label': 'Tailored resume',
        'cost': PRICING['tailor_resume'],
        'blurb': 'AI rewrites your resume for one specific job, then a truthfulness '
                 'pass makes sure every claim still matches your profile.',
    },
    {
        'reason': 'cover_letter',
        'label': 'Cover letter',
        'cost': PRICING['cover_letter'],
        'blurb': 'A tailored cover letter drafted from your profile and the job description.',
    },
    {
        'reason': 'mock_interview',
        'label': 'Interview grill session',
        'cost': PRICING['mock_interview'],
        'blurb': 'A company-researched question bank plus a live grilling round scored '
                 'against a STAR rubric, ending in a personalised study plan.',
    },
    {
        'reason': 'autonomous_apply',
        'label': 'Autonomous apply',
        'cost': PRICING['autonomous_apply'],
        'blurb': 'The agent prepares a complete application and pauses for your one-tap '
                 'approval before anything is submitted.',
    },
]


def cost_of(reason: str) -> int:
    """Credit cost of an action, or 0 if the action is free."""
    return PRICING.get(reason, 0)
