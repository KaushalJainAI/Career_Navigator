from tailoring.generators import draft_cover_letter, tailor_resume


def test_tailor_resume_uses_injected_llm():
    captured = {}

    def llm(prompt, **_):
        captured['prompt'] = prompt
        return 'TAILORED'

    out = tailor_resume({'summary': 'engineer'}, 'Senior', 'JD', llm=llm)
    assert out['content']['raw_text'] == 'TAILORED'
    assert 'JD' in captured['prompt']


def test_draft_cover_letter_uses_injected_llm():
    out = draft_cover_letter({}, 'Senior', 'Acme', 'JD', llm=lambda p, **_: 'LETTER')
    assert out == 'LETTER'
