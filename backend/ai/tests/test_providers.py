from pathlib import Path
from subprocess import CompletedProcess

from ai.providers import (
    codex_cli_complete,
    configured_model_label,
    get_configured_llm,
    nvidia_complete,
    with_fallback,
)


def test_get_configured_llm_returns_none_by_default(settings):
    settings.AI_PROVIDER = ''
    assert get_configured_llm() is None


def test_get_configured_llm_returns_codex_callable(settings):
    settings.AI_PROVIDER = 'codex_cli'
    settings.AI_FALLBACK_PROVIDER = ''
    assert get_configured_llm() is codex_cli_complete


def test_get_configured_llm_returns_nvidia_callable(settings):
    settings.AI_PROVIDER = 'nvidia'
    assert get_configured_llm() is nvidia_complete


def test_configured_model_label_includes_codex_model(settings):
    settings.AI_PROVIDER = 'codex_cli'
    settings.AI_FALLBACK_PROVIDER = ''
    settings.CODEX_CLI_MODEL = 'gpt-5-codex'
    assert configured_model_label() == 'codex_cli:gpt-5-codex'


def test_configured_model_label_includes_fallback(settings):
    settings.AI_PROVIDER = 'codex_cli'
    settings.AI_FALLBACK_PROVIDER = 'nvidia'
    settings.CODEX_CLI_MODEL = ''
    assert configured_model_label() == 'codex_cli,fallback:nvidia'


def test_with_fallback_uses_secondary_when_primary_empty():
    calls = []

    def primary(prompt, **_):
        calls.append(('primary', prompt))
        return ''

    def fallback(prompt, **_):
        calls.append(('fallback', prompt))
        return 'fallback answer'

    assert with_fallback(primary, fallback)('prompt') == 'fallback answer'
    assert calls == [('primary', 'prompt'), ('fallback', 'prompt')]


def test_with_fallback_keeps_primary_answer():
    def primary(prompt, **_):
        return f'primary {prompt}'

    def fallback(prompt, **_):
        return f'fallback {prompt}'

    assert with_fallback(primary, fallback)('answer') == 'primary answer'


def test_codex_cli_complete_reads_output_file(settings, monkeypatch, tmp_path):
    captured = {}
    settings.CODEX_CLI_COMMAND = 'codex'
    settings.CODEX_CLI_MODEL = 'gpt-5-codex'
    settings.CODEX_CLI_SANDBOX = 'read-only'
    settings.CODEX_CLI_TIMEOUT_SECONDS = 5
    settings.CODEX_CLI_WORKDIR = str(tmp_path)

    def fake_run(args, cwd, input, text, capture_output, timeout, check, env):
        captured.update(
            {
                'args': args,
                'cwd': cwd,
                'input': input,
                'text': text,
                'capture_output': capture_output,
                'timeout': timeout,
                'check': check,
                'quiet': env.get('CODEX_QUIET_MODE'),
            }
        )
        output_path = Path(args[args.index('--output-last-message') + 1])
        output_path.write_text('Codex answer', encoding='utf-8')
        return CompletedProcess(args=args, returncode=0, stdout='ignored', stderr='')

    monkeypatch.setattr('ai.providers.subprocess.run', fake_run)

    assert codex_cli_complete('Prompt text') == 'Codex answer'
    assert captured['args'][:2] == ['codex', 'exec']
    assert captured['args'][-2:] == ['--model', 'gpt-5-codex']
    assert captured['input'] == 'Prompt text'
    assert captured['cwd'] == str(tmp_path.resolve())
    assert captured['timeout'] == 5
    assert captured['quiet'] == '1'


def test_codex_cli_complete_falls_back_to_stdout(settings, monkeypatch, tmp_path):
    settings.CODEX_CLI_COMMAND = 'codex'
    settings.CODEX_CLI_MODEL = ''
    settings.CODEX_CLI_WORKDIR = str(tmp_path)

    def fake_run(args, **_):
        return CompletedProcess(args=args, returncode=0, stdout='stdout answer', stderr='')

    monkeypatch.setattr('ai.providers.subprocess.run', fake_run)

    assert codex_cli_complete('Prompt text') == 'stdout answer'


def test_codex_cli_complete_returns_empty_string_on_missing_command(settings, monkeypatch, tmp_path):
    settings.CODEX_CLI_COMMAND = 'missing-codex'
    settings.CODEX_CLI_WORKDIR = str(tmp_path)

    def fake_run(*_, **__):
        raise FileNotFoundError

    monkeypatch.setattr('ai.providers.subprocess.run', fake_run)

    assert codex_cli_complete('Prompt text') == ''


def test_nvidia_complete_returns_empty_without_key(settings):
    settings.NVIDIA_API_KEY = ''
    assert nvidia_complete('Prompt text') == ''
