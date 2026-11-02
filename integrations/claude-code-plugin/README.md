# Career Navigator — Claude Code plugin

Use your own Claude subscription to drive your Career Navigator account from Claude Code: ranked jobs, truthful résumé tailoring, application tracking (assessments, interview rounds, deadlines), referrals and interview prep.

## Install

1. In Career Navigator, open **Settings → API tokens** and create a token.
2. Export the connection details (add them to your shell profile):
   ```bash
   export CAREER_NAVIGATOR_URL=http://localhost:8000
   export CAREER_NAVIGATOR_TOKEN=<your token>
   ```
3. In Claude Code:
   ```
   /plugin marketplace add KaushalJainAI/Career_Navigator
   /plugin install career-navigator@career-navigator
   ```
4. Try `/career-navigator:today`, `/career-navigator:apply Stripe`, `/career-navigator:prep Infosys hr`, or just ask: *"I got an OA from TCS on Friday at 10am"*.

The MCP server (`mcp/server.py`) is plain Python 3 with no dependencies, so it also works in any other MCP host (Claude Desktop, Codex, Gemini CLI) — point the host at `python3 mcp/server.py` with the same two environment variables.

## Safety

- Tools never submit applications or message anyone. You do that.
- Tools that change your records are marked, so Claude Code asks for permission before each one.
- Everything runs against your own backend with your token. Revoke the token in Settings at any time.
