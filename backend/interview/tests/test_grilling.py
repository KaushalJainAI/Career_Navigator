from interview.grilling import (
    evaluate_answer,
    generate_question_bank,
    research,
    summarise_session,
)


def test_research_invokes_llm_and_returns_notes():
    captured = {}

    def llm(prompt, **_):
        captured['prompt'] = prompt
        return 'NOTES'

    out = research('Acme', 'Senior Engineer', 'tech_phone', llm=llm)
    assert out['company'] == 'Acme'
    assert out['notes'] == 'NOTES'
    assert 'Acme' in captured['prompt']


def test_generate_question_bank_seed_fallback():
    bank = generate_question_bank('Engineer', 'behavioral', count=3)
    assert len(bank) == 3
    assert all('prompt' in q for q in bank)


def test_generate_question_bank_with_llm():
    def llm(prompt, **_):
        return 'Q1?\nQ2?\nQ3?'

    bank = generate_question_bank('Engineer', 'behavioral', llm=llm, count=3)
    assert [q['prompt'] for q in bank] == ['Q1?', 'Q2?', 'Q3?']


def test_evaluate_answer_heuristic_weak():
    out = evaluate_answer({'prompt': 'q'}, 'short')
    assert out['score'] < 0.5
    assert out['drill_focus']


def test_evaluate_answer_heuristic_strong():
    answer = (
        'I led a migration that reduced p99 latency by 40 percent. The result was 30% lower '
        'infra cost and we shipped on time. Specifically, we cut three database queries.'
    ) * 2
    out = evaluate_answer({'prompt': 'q'}, answer)
    assert out['score'] > 0.5


def test_summarise_session_aggregates_scores_and_gaps():
    turns = [
        {'score': 0.4, 'drill_focus': 'add a clear situation→task→action→result arc'},
        {'score': 0.8, 'drill_focus': None},
    ]
    data = summarise_session(turns)
    assert data['overall_score'] == 0.6
    assert 'add a clear situation→task→action→result arc' in data['gaps']
    assert data['study_plan']
