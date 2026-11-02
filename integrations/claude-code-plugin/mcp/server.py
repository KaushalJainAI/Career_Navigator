#!/usr/bin/env python3
"""Career Navigator MCP server (stdio, zero dependencies).

Exposes the Career Navigator copilot tools to any MCP host — Claude Code,
Claude Desktop, Codex, Gemini CLI — so you can manage your job search with the
AI subscription you already pay for. All work happens on your Career Navigator
backend with the same safety rules as the in-app copilot: tools never submit
applications or message anyone, and tools that change your records are marked
so the host asks for your permission first.

Config (environment):
  CAREER_NAVIGATOR_URL    e.g. http://localhost:8000   (no trailing /api/v1)
  CAREER_NAVIGATOR_TOKEN  an API token from Settings → API tokens
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

PROTOCOL_VERSION = '2025-06-18'
BASE = os.environ.get('CAREER_NAVIGATOR_URL', 'http://localhost:8000').rstrip('/') + '/api/v1'
TOKEN = os.environ.get('CAREER_NAVIGATOR_TOKEN', '').strip()


def api(method: str, path: str, body: dict | None = None, timeout: int = 180) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={
        'Authorization': f'Token {TOKEN}', 'Content-Type': 'application/json', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b'{}')
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b'{}')
        except ValueError:
            return exc.code, {'detail': f'HTTP {exc.code}'}
    except (urllib.error.URLError, TimeoutError) as exc:
        return 0, {'detail': f'Cannot reach Career Navigator at {BASE}: {exc}'}


def list_tools() -> list[dict]:
    status, data = api('GET', '/agent/copilot/tools/')
    if status != 200:
        return []
    out = []
    for t in data.get('tools', []):
        desc = t['description']
        if t.get('risk') == 'confirm':
            desc += ' (Changes your Career Navigator records — confirm with the user first.)'
        out.append({'name': t['name'], 'description': desc, 'inputSchema': t['input_schema'],
                    'annotations': {'readOnlyHint': t.get('risk') == 'read',
                                    'destructiveHint': False}})
    out.append({'name': 'ask_copilot', 'description': 'Send a plain-language request to the in-app copilot '
                '(same as typing in the Assistant page). Use when no single tool fits.',
                'inputSchema': {'type': 'object', 'properties': {'message': {'type': 'string'}}, 'required': ['message']},
                'annotations': {'readOnlyHint': False}})
    return out


def call_tool(name: str, args: dict) -> dict:
    if not TOKEN:
        return {'content': [{'type': 'text', 'text': 'Set CAREER_NAVIGATOR_TOKEN (create one in Career Navigator → Settings → API tokens).'}], 'isError': True}
    if name == 'ask_copilot':
        status, data = api('POST', '/agent/copilot/', {'message': args.get('message', '')})
        text = data.get('reply') or data.get('detail', '')
        if data.get('pending_action'):
            text += f"\n\n(Waiting for approval in the app: {data['pending_action']['summary']})"
        return {'content': [{'type': 'text', 'text': text}], 'isError': status != 200}
    # The MCP host shows the user a permission prompt before every tool call,
    # which is our confirmation for write tools.
    status, data = api('POST', f'/agent/copilot/tools/{name}/', {'args': args, 'confirmed': True})
    if status != 200:
        return {'content': [{'type': 'text', 'text': data.get('detail', f'Error {status}')}], 'isError': True}
    text = data.get('text', '')
    payload = json.dumps(data.get('result'), ensure_ascii=False, default=str)
    return {'content': [{'type': 'text', 'text': f'{text}\n\nData: {payload[:6000]}'}], 'isError': False}


def handle(msg: dict) -> dict | None:
    method, mid = msg.get('method'), msg.get('id')
    if method == 'initialize':
        result = {'protocolVersion': msg.get('params', {}).get('protocolVersion', PROTOCOL_VERSION),
                  'capabilities': {'tools': {}},
                  'serverInfo': {'name': 'career-navigator', 'version': '0.1.0'},
                  'instructions': 'Career Navigator job-search tools. Start with get_overview. Never claim the user '
                                  'applied or sent anything unless they say so.'}
    elif method == 'tools/list':
        result = {'tools': list_tools()}
    elif method == 'tools/call':
        p = msg.get('params', {})
        result = call_tool(p.get('name', ''), p.get('arguments') or {})
    elif method == 'ping':
        result = {}
    elif mid is None:
        return None  # notification (e.g. notifications/initialized)
    else:
        return {'jsonrpc': '2.0', 'id': mid, 'error': {'code': -32601, 'message': f'Unknown method {method}'}}
    return {'jsonrpc': '2.0', 'id': mid, 'result': result}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        reply = handle(msg)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + '\n')
            sys.stdout.flush()


if __name__ == '__main__':
    main()
