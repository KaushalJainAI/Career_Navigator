from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Callable

from django.conf import settings
from openai import OpenAI


_codex_lock = threading.Lock()


CLI_PROVIDERS = ('claude_cli', 'codex_cli', 'gemini_cli')


def _cli_installed(provider: str) -> bool:
    import shutil
    cmd = {
        'claude_cli': getattr(settings, 'CLAUDE_CLI_COMMAND', 'claude'),
        'codex_cli': getattr(settings, 'CODEX_CLI_COMMAND', 'codex'),
        'gemini_cli': getattr(settings, 'GEMINI_CLI_COMMAND', 'gemini'),
    }[provider]
    parts = shlex.split(cmd or '')
    return bool(parts) and shutil.which(parts[0]) is not None


def resolve_provider() -> str:
    """The provider actually in use ('' = none → deterministic mode)."""
    provider = getattr(settings, 'AI_PROVIDER', '').strip().lower()
    if provider == 'auto':
        for cand in CLI_PROVIDERS:
            if _cli_installed(cand):
                return cand
        return 'nvidia' if getattr(settings, 'NVIDIA_API_KEY', '').strip() else ''
    if provider == 'nvidia' and not getattr(settings, 'NVIDIA_API_KEY', '').strip():
        return ''
    return provider if provider in CLI_PROVIDERS + ('nvidia',) else ''


def _callable_for(provider: str):
    return {
        'claude_cli': claude_cli_complete,
        'codex_cli': codex_cli_complete,
        'gemini_cli': gemini_cli_complete,
        'nvidia': nvidia_complete,
    }.get(provider)


def get_configured_llm() -> Callable[[str], str] | None:
    provider = resolve_provider()
    fn = _callable_for(provider)
    if fn is None:
        return None
    fallback_provider = getattr(settings, 'AI_FALLBACK_PROVIDER', '').strip().lower()
    if provider in CLI_PROVIDERS and fallback_provider == 'nvidia' \
            and getattr(settings, 'NVIDIA_API_KEY', '').strip():
        return with_fallback(fn, nvidia_complete)
    if provider == 'codex_cli' and fallback_provider == 'nvidia':
        return with_fallback(fn, nvidia_complete)
    return fn


def configured_model_label() -> str:
    provider = resolve_provider()
    if provider == 'codex_cli':
        model = getattr(settings, 'CODEX_CLI_MODEL', '').strip()
        label = f'codex_cli:{model}' if model else 'codex_cli'
        if getattr(settings, 'AI_FALLBACK_PROVIDER', '').strip().lower() == 'nvidia':
            return f'{label},fallback:nvidia'
        return label
    if provider == 'claude_cli':
        model = getattr(settings, 'CLAUDE_CLI_MODEL', '').strip()
        return f'claude_cli:{model}' if model else 'claude_cli'
    if provider == 'gemini_cli':
        model = getattr(settings, 'GEMINI_CLI_MODEL', '').strip()
        return f'gemini_cli:{model}' if model else 'gemini_cli'
    if provider == 'nvidia':
        return f'nvidia:{getattr(settings, "NVIDIA_GUEST_MODEL", "")}'
    return ''


def ai_status() -> dict:
    provider = resolve_provider()
    return {
        'configured': getattr(settings, 'AI_PROVIDER', ''),
        'provider': provider,
        'label': configured_model_label(),
        'mode': 'ai' if provider else 'deterministic',
        'installed_clis': [p for p in CLI_PROVIDERS if _cli_installed(p)],
    }


def _run_cli(args: list[str], prompt: str, *, timeout: int) -> str:
    """Run a CLI with the prompt on stdin; '' on any failure (callers fall back)."""
    try:
        result = subprocess.run(args, input=prompt, text=True, capture_output=True, timeout=timeout,
                                check=False, cwd=str(settings.BASE_DIR), env=os.environ.copy())
    except (OSError, subprocess.TimeoutExpired):
        return ''
    if result.returncode != 0:
        return ''
    return (result.stdout or '').strip()


def claude_cli_complete(prompt: str, **_: object) -> str:
    """Claude Code in print mode, using the operator's Claude subscription login.
    Tools are disabled: the platform only needs text back."""
    cmd = shlex.split(getattr(settings, 'CLAUDE_CLI_COMMAND', 'claude')) or ['claude']
    args = [*cmd, '-p', '--output-format', 'text', '--tools', '']
    model = getattr(settings, 'CLAUDE_CLI_MODEL', '').strip()
    if model:
        args += ['--model', model]
    with _codex_lock:
        return _run_cli(args, prompt, timeout=int(getattr(settings, 'CLI_TIMEOUT_SECONDS', 120)))


def gemini_cli_complete(prompt: str, **_: object) -> str:
    """Gemini CLI in non-interactive mode (prompt on stdin), using the operator's Google login."""
    cmd = shlex.split(getattr(settings, 'GEMINI_CLI_COMMAND', 'gemini')) or ['gemini']
    args = [*cmd]
    model = getattr(settings, 'GEMINI_CLI_MODEL', '').strip()
    if model:
        args += ['-m', model]
    with _codex_lock:
        return _run_cli(args, prompt, timeout=int(getattr(settings, 'CLI_TIMEOUT_SECONDS', 120)))


def with_fallback(primary: Callable[[str], str], fallback: Callable[[str], str]) -> Callable[[str], str]:
    def _complete(prompt: str, **kwargs: object) -> str:
        primary_out = primary(prompt, **kwargs)
        if primary_out:
            return primary_out
        return fallback(prompt, **kwargs)

    return _complete


def codex_cli_complete(prompt: str, **_: object) -> str:
    """Call the locally authenticated Codex CLI.

    This uses the official `codex exec` path, so the developer must run
    `codex login` or `codex login --device-auth` on the machine first.
    """

    command = shlex.split(getattr(settings, 'CODEX_CLI_COMMAND', 'codex'))
    if not command:
        command = ['codex']

    timeout = int(getattr(settings, 'CODEX_CLI_TIMEOUT_SECONDS', 120))
    cwd = Path(getattr(settings, 'CODEX_CLI_WORKDIR', settings.BASE_DIR)).resolve()
    sandbox = getattr(settings, 'CODEX_CLI_SANDBOX', 'read-only')
    model = getattr(settings, 'CODEX_CLI_MODEL', '').strip()

    output_path = ''
    try:
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as handle:
            output_path = handle.name

        args = [*command, 'exec', '--sandbox', sandbox, '--output-last-message', output_path]
        if model:
            args.extend(['--model', model])

        env = os.environ.copy()
        env.setdefault('CODEX_QUIET_MODE', '1')

        # Codex credentials are local-user state; serialize calls to avoid
        # overlapping interactive refreshes or rate-limit bursts.
        with _codex_lock:
            result = subprocess.run(
                args,
                cwd=str(cwd),
                input=prompt,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
                env=env,
            )

        output = Path(output_path).read_text(encoding='utf-8', errors='ignore').strip()
        if output:
            return output
        return (result.stdout or '').strip()
    except (OSError, subprocess.TimeoutExpired):
        return ''
    finally:
        if output_path:
            try:
                Path(output_path).unlink(missing_ok=True)
            except OSError:
                pass


def nvidia_complete(prompt: str, **_: object) -> str:
    api_key = getattr(settings, 'NVIDIA_API_KEY', '').strip()
    if not api_key:
        return ''

    timeout = int(getattr(settings, 'NVIDIA_TIMEOUT_SECONDS', 120))
    max_tokens = int(getattr(settings, 'NVIDIA_MAX_TOKENS', 2048))
    model = getattr(settings, 'NVIDIA_GUEST_MODEL', 'nvidia/llama-3.3-nemotron-super-49b-v1')

    try:
        client = OpenAI(
            api_key=api_key,
            base_url='https://integrate.api.nvidia.com/v1',
            timeout=timeout,
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    'role': 'system',
                    'content': 'You are an AI assistant inside Career Navigator. Return only the requested content.',
                },
                {'role': 'user', 'content': prompt},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        return (response.choices[0].message.content or '').strip()
    except Exception:  # noqa: BLE001
        return ''
