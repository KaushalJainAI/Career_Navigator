# Development server workflow

How code actually gets written on this project: not locally, on the EC2 box.

## The loop

Coding happens **on the remote EC2 machine** (`testing.kaushaljain.com`), not on this laptop. This laptop is used to review, test, and merge — never to author features directly.

1. **Vibe-code on the remote box.** SSH in (`pwsh ./scripts/claude-remote.ps1` attaches to the `claude` tmux session at `/opt/career-navigator`) and write/iterate on the feature there.
2. **Test it there.** The remote box is also the live target for `testing.kaushaljain.com` — use `switch careernavigator --build` (see [deployment.md](deployment.md)) to serve the change and click through it against the real domain.
3. **Commit and push from the remote box**, on the **`agent`** branch. The remote working tree is the source of truth for what's "shipped to testing" — see the note in [deployment.md](deployment.md) that testing deploys straight from the working tree, not a git checkout.
4. **Pull down to this laptop.** Fetch `agent` locally to review the diff and re-run it here.
5. **Review + test locally.** Read the diff, run the relevant backend/frontend tests locally (see [development.md](development.md) and [testing.md](testing.md)), sanity-check edge cases the remote session may have rushed past.
6. **Merge `agent` → `main` locally** once the review is clean.

## Why this shape

- The remote box already has the live `.env`, real API keys, Redis, and Celery wired up — testing against `testing.kaushaljain.com` there is testing against the real deployment target, not a local approximation.
- Keeping authorship on `agent` and merges on `main` means `main` only ever receives code that's been through a second, calmer pass on the laptop — the remote loop is fast/exploratory, the local pass is the quality gate.

## Practical notes

- SSH key: `my-key.pem` in the repo root. Host: `ec2-user@ec2-13-207-61-191.ap-south-1.compute.amazonaws.com`.
- If SSH times out from this laptop, it's a connectivity issue (instance stopped, Security Group not allowing the current IP, or local network) — not a key problem. Verify the instance is running and the Security Group allows port 22 from the current IP before retrying.
- Pulling `agent` locally after a remote push is a normal `git fetch origin agent && git checkout agent` (or merge into whatever local branch is being reviewed from) — nothing special beyond normal git.
- Never merge `agent` → `main` without having actually run the tests locally first; the remote session's own "it worked" isn't the review.
