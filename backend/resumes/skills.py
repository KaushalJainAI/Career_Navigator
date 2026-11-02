"""Skill taxonomy + extraction.

One canonical name per skill with the aliases people actually write
("postgres", "k8s", "ML"...). Used for resumes *and* job descriptions so both
sides of a match speak the same vocabulary. Deterministic and dependency-free.
"""

from __future__ import annotations

import re
from functools import lru_cache

# canonical -> aliases (lower-case). The canonical name is always matched too.
SKILLS: dict[str, list[str]] = {
    # --- Languages ---
    'Python': [], 'Java': [], 'JavaScript': ['js', 'ecmascript'], 'TypeScript': ['ts'],
    'Go': ['golang'], 'Rust': [], 'C++': ['cpp'], 'C#': ['csharp', 'c sharp'], 'C': [],
    'Ruby': [], 'PHP': [], 'Kotlin': [], 'Swift': [], 'Scala': [], 'R': [],
    'Elixir': [], 'Haskell': [], 'Dart': [], 'Objective-C': [], 'Perl': [],
    'Bash': ['shell scripting', 'shell'], 'SQL': [], 'MATLAB': [], 'Solidity': [],
    'HTML': ['html5'], 'CSS': ['css3'],
    # --- Frontend ---
    'React': ['react.js', 'reactjs'], 'Next.js': ['nextjs'], 'Vue': ['vue.js', 'vuejs'],
    'Angular': ['angularjs'], 'Svelte': [], 'Redux': [], 'Tailwind CSS': ['tailwind'],
    'React Native': [], 'Flutter': [], 'Webpack': [], 'Vite': [], 'SASS': ['scss'],
    # --- Backend / frameworks ---
    'Node.js': ['node', 'nodejs'], 'Express': ['express.js', 'expressjs'], 'NestJS': [],
    'Django': [], 'Flask': [], 'FastAPI': [], 'Spring': ['spring boot', 'springboot'],
    'Ruby on Rails': ['rails'], 'Laravel': [], '.NET': ['dotnet', 'asp.net'],
    'GraphQL': [], 'REST': ['rest api', 'rest apis', 'restful'], 'gRPC': [],
    'Microservices': ['microservice'], 'Celery': [], 'RabbitMQ': [], 'Kafka': ['apache kafka'],
    'WebSockets': ['websocket'],
    # --- Data stores ---
    'PostgreSQL': ['postgres'], 'MySQL': [], 'MongoDB': ['mongo'], 'Redis': [],
    'Elasticsearch': ['elastic search', 'opensearch'], 'DynamoDB': [], 'Cassandra': [],
    'SQLite': [], 'Snowflake': [], 'BigQuery': [], 'Redshift': [], 'ClickHouse': [],
    # --- Cloud / infra ---
    'AWS': ['amazon web services'], 'GCP': ['google cloud', 'google cloud platform'],
    'Azure': ['microsoft azure'], 'Docker': ['containers'], 'Kubernetes': ['k8s'],
    'Terraform': [], 'Ansible': [], 'CI/CD': ['ci cd', 'continuous integration', 'continuous delivery'],
    'GitHub Actions': [], 'Jenkins': [], 'Linux': [], 'Nginx': [], 'Serverless': ['lambda'],
    'Prometheus': [], 'Grafana': [], 'Datadog': [], 'Observability': ['monitoring'],
    'Git': [], 'Distributed Systems': ['distributed system'], 'System Design': [],
    'Security': ['application security', 'appsec', 'cybersecurity'], 'Networking': ['tcp/ip'],
    # --- Data / ML ---
    'Machine Learning': ['ml'], 'Deep Learning': [], 'NLP': ['natural language processing'],
    'Computer Vision': [], 'LLM': ['llms', 'large language models', 'large language model'],
    'Generative AI': ['genai', 'gen ai'], 'RAG': ['retrieval augmented generation'],
    'PyTorch': [], 'TensorFlow': [], 'Keras': [], 'scikit-learn': ['sklearn', 'scikit learn'],
    'Pandas': [], 'NumPy': [], 'Spark': ['apache spark', 'pyspark'], 'Airflow': ['apache airflow'],
    'dbt': [], 'ETL': ['elt', 'data pipelines', 'data pipeline'], 'Data Analysis': ['data analytics'],
    'Statistics': ['statistical analysis'], 'A/B Testing': ['ab testing', 'a/b tests', 'experimentation'],
    'Tableau': [], 'Power BI': ['powerbi'], 'Looker': [], 'Excel': ['microsoft excel', 'spreadsheets'],
    'LangChain': [], 'Hugging Face': ['huggingface', 'transformers'], 'MLOps': [],
    'Data Engineering': [], 'Data Science': [],
    # --- Testing / practices ---
    'Unit Testing': ['tdd', 'test driven development'], 'Pytest': [], 'Jest': [],
    'Cypress': [], 'Playwright': [], 'Selenium': [], 'Agile': ['scrum', 'kanban'],
    'Code Review': ['code reviews'], 'API Design': [],
    # --- Product / design / business ---
    'Product Management': ['product manager', 'product strategy'], 'Roadmapping': ['roadmap', 'roadmaps'],
    'User Research': ['customer research', 'user interviews'], 'Figma': [], 'Sketch': [],
    'UX Design': ['ux', 'user experience'], 'UI Design': ['ui design', 'visual design'],
    'Prototyping': [], 'Design Systems': ['design system'], 'Wireframing': ['wireframes'],
    'SEO': ['search engine optimization'], 'Content Marketing': [], 'Growth Marketing': ['growth'],
    'Google Analytics': [], 'Salesforce': [], 'HubSpot': [], 'Jira': [], 'Confluence': [],
    'Stakeholder Management': ['stakeholders'], 'Project Management': ['program management'],
    'Leadership': ['team lead', 'tech lead', 'people management', 'mentoring', 'mentorship'],
    'Communication': ['written communication', 'presentation skills'],
    'Financial Modeling': ['financial modelling'], 'Sales': ['business development'],
    'Customer Success': [], 'Copywriting': [], 'Operations': [],
}

# Very short / ambiguous names that should only match in a case-sensitive way
# (e.g. "Go", "R", "C") to avoid matching ordinary English words.
_CASE_SENSITIVE = {'Go', 'R', 'C', 'Swift', 'Rust', 'Spring', 'Express', 'Excel', 'Growth',
                   'Sales', 'Operations', 'Security', 'Networking', 'Leadership',
                   'Communication', 'Agile', 'Git', 'Shell'}
# Aliases that are too ambiguous to use at all for extraction from free text.
_SKIP_ALIASES = {'ts', 'js', 'ml', 'ux', 'node', 'shell', 'growth', 'containers', 'lambda',
                 'monitoring', 'roadmap', 'stakeholders', 'mongo', 'rails', 'kanban'}
_SAFE_SHORT_ALIASES = {'ml', 'ux', 'js', 'ts', 'node'}  # matched case-sensitively upper-case


def _pattern(term: str) -> str:
    return r'(?<![A-Za-z0-9+#.])' + re.escape(term) + r'(?![A-Za-z0-9+#]|\.[A-Za-z])'


@lru_cache(maxsize=1)
def _compiled() -> list[tuple[str, re.Pattern]]:
    out: list[tuple[str, re.Pattern]] = []
    for canonical, aliases in SKILLS.items():
        terms = [canonical] + [a for a in aliases if a not in _SKIP_ALIASES]
        parts = []
        for term in terms:
            parts.append(_pattern(term))
        flags = 0 if canonical in _CASE_SENSITIVE else re.IGNORECASE
        out.append((canonical, re.compile('|'.join(parts), flags)))
        # Safe short aliases only when written in capitals (ML, UX, JS, TS, Node).
        short = [a for a in aliases if a in _SAFE_SHORT_ALIASES]
        for a in short:
            variant = 'Node' if a == 'node' else a.upper()
            out.append((canonical, re.compile(_pattern(variant))))
    return out


_LOWER_INDEX = {name.lower(): name for name in SKILLS}
for _name, _aliases in SKILLS.items():
    for _a in _aliases:
        _LOWER_INDEX.setdefault(_a.lower(), _name)


def canonical_skill(name: str) -> str:
    """Map a free-form skill name onto its canonical spelling (or keep it)."""
    cleaned = (name or '').strip()
    return _LOWER_INDEX.get(cleaned.lower(), cleaned)


def extract_skills(text: str) -> list[str]:
    """All canonical skills mentioned in `text`, in order of first appearance."""
    if not text:
        return []
    hits: dict[str, int] = {}
    for canonical, pattern in _compiled():
        m = pattern.search(text)
        if m and (canonical not in hits or m.start() < hits[canonical]):
            hits[canonical] = m.start()
    # "C" is only trustworthy in a list context such as "C, C++" or "C/C++".
    if 'C' in hits and not re.search(r'(?:^|[\s,(/])C(?:\s*[,/)]|\s+and\s)', text):
        hits.pop('C')
    return [name for name, _ in sorted(hits.items(), key=lambda kv: kv[1])]


def skill_counts(text: str) -> dict[str, int]:
    """How often each canonical skill appears — used to weight JD requirements."""
    counts: dict[str, int] = {}
    if not text:
        return counts
    for canonical, pattern in _compiled():
        n = len(pattern.findall(text))
        if n:
            counts[canonical] = counts.get(canonical, 0) + n
    if 'C' in counts and not re.search(r'(?:^|[\s,(/])C(?:\s*[,/)]|\s+and\s)', text):
        counts.pop('C')
    return counts
