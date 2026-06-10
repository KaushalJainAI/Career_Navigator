# scripts/

One-shot EC2 bootstrap, daily redeploy, and Claude Code remote-launch.

## Status audit (as of this commit)

| Item | Status |
| --- | --- |
| GitHub remote | ✅ `https://github.com/KaushalJainAI/Career_Navigator.git` |
| `backend/config/settings/prod.py` | ✅ committed |
| `scripts/bootstrap-ec2.sh` | ✅ this commit |
| `scripts/bootstrap-ec2-from-laptop.ps1` | ✅ this commit |
| `scripts/deploy.sh` | ✅ (for re-deploys after initial bootstrap) |
| `scripts/claude-remote.ps1` | ✅ (for daily Claude Code use) |
| Cloudflare A record `career.kaushaljain.com` | ✅ (you set this up) |
| Cloudflare Origin Certificate | ❌ you must generate it (browser-only step) |
| EC2 box provisioned (Node, nginx, code, services) | ❌ run the bootstrap |
| Claude Code logged in | ❌ interactive `/login` (you do this) |

## The one command you need to run

From the repo root on your laptop:

```powershell
pwsh ./scripts/bootstrap-ec2-from-laptop.ps1
```

That:

1. Verifies your `my-key.pem` SSH key permissions.
2. Tests SSH to the EC2 box.
3. `scp`s `bootstrap-ec2.sh` to the box.
4. Runs it. The server-side script:
   - Installs Node 20, nginx, redis, sqlite, python3.11, git, tmux.
   - Clones (or pulls) the repo to `/opt/career-navigator`.
   - Generates a prod `.env` with auto-generated `SECRET_KEY` and `CREDENTIAL_ENCRYPTION_KEY`.
   - Creates the Python venv, installs deps, runs migrations, collects static.
   - Builds the frontend with `VITE_API_BASE=https://career.kaushaljain.com/api/v1`.
   - Writes three systemd units (`cn-backend`, `cn-asgi`, `cn-celery`), enables + starts them.
   - Writes the nginx config (HTTP-only if no cert; HTTPS if Cloudflare cert is uploaded).
   - Installs Claude Code globally.
   - Creates a detached tmux session named `claude` for remote control.
   - Prints a health-check panel: which services are up, status codes from local curl.

The whole thing is **idempotent**. Re-run it any time — each step prints `[OK]` if already done, `[DO]` if it's doing it now.

## Adding SSL (after the first run)

The first run will print `[!!] no Cloudflare Origin Cert ... — writing HTTP-only nginx`. To finish the SSL setup:

1. Open the Cloudflare dashboard → `kaushaljain.com` → **SSL/TLS → Origin Server → Create Certificate**.
2. Use the defaults (RSA 2048, hostnames `career.kaushaljain.com`, 15-year validity). Click Create.
3. Copy the **Origin Certificate** block to a local file `cloudflare-cert.pem`.
4. Copy the **Private Key** block (shown only once!) to a local file `cloudflare-key.pem`.
5. Re-run the bootstrap with the cert paths:

   ```powershell
   pwsh ./scripts/bootstrap-ec2-from-laptop.ps1 `
       -CertFile cloudflare-cert.pem `
       -KeyFile cloudflare-key.pem
   ```

6. In the Cloudflare dashboard → **SSL/TLS → Overview** → set mode to **Full (strict)**.
7. **SSL/TLS → Edge Certificates** → toggle **Always Use HTTPS** ON.
8. Delete `cloudflare-key.pem` from your laptop (the box has the only copy you need).

## Logging into Claude Code

Once the bootstrap is done (the tmux `claude` session is already created and Claude Code is installed):

```powershell
pwsh ./scripts/claude-remote.ps1
```

This SSHes in and attaches to the tmux session. Inside the Claude REPL:

```
/login
```

The CLI prints a URL + code. Open the URL in your **laptop's** browser, sign in to Claude.ai, paste the code, click Authorize. Done — Claude Code is live on the EC2 box.

Detach with **Ctrl+B then D**. Your session persists across SSH disconnects.

## Adding API keys (Google OAuth, Adzuna, etc.)

The bootstrap generates a `.env` with empty values for all API keys. Two ways to fill them in:

**Option A — edit on the box (quick + dirty):**

```bash
ssh -i my-key.pem ec2-user@ec2-13-207-61-191.ap-south-1.compute.amazonaws.com
nano /opt/career-navigator/backend/.env
sudo systemctl restart cn-backend cn-asgi cn-celery
```

**Option B — overrides file on your laptop (reproducible):**

Create `cn-env-overrides.txt` on your laptop:

```
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
```

Re-run the bootstrap with `-EnvOverrides cn-env-overrides.txt`. The script merges these into `.env` on the box, preserving the auto-generated `SECRET_KEY` and `CREDENTIAL_ENCRYPTION_KEY`.

## Future redeploys

After the first bootstrap, you don't need to re-run the bootstrap for code changes. SSH in and run the lighter deploy script:

```bash
ssh -i my-key.pem ec2-user@ec2-13-207-61-191.ap-south-1.compute.amazonaws.com
cd /opt/career-navigator && bash scripts/deploy.sh
```

It pulls the latest code, reinstalls deps, runs migrations, rebuilds the frontend, and restarts services.

## What I cannot script (you must do these in a browser)

- **Generate the Cloudflare Origin Certificate.** The private key is shown only once in the CF dashboard browser session — no API can fetch it after.
- **Click through the Cloudflare SSL mode toggle to Full (strict).**
- **Run `/login` inside Claude Code.** The OAuth code-paste step is interactive by design.
- **Open inbound ports 80 / 443 in the EC2 Security Group** (if they aren't already open). Done in the AWS Console.

Everything else, the scripts handle.
