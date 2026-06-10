# bootstrap-ec2-from-laptop.ps1
# Run from your LAPTOP. SSHes into the EC2 box, uploads optional cert/env-override
# files, then runs scripts/bootstrap-ec2.sh on the box.
#
# Usage from the repo root:
#   pwsh ./scripts/bootstrap-ec2-from-laptop.ps1
#
# Optional params:
#   -KeyPath      path to SSH private key   (default: ./my-key.pem)
#   -Host         ec2-user@<host>           (default: ec2-user@ec2-13-207-61-191.ap-south-1.compute.amazonaws.com)
#   -PublicHost   public hostname           (default: career.kaushaljain.com)
#   -CertFile     local Cloudflare cert PEM (optional; if present, HTTPS gets configured)
#   -KeyFile      local Cloudflare key PEM  (optional)
#   -EnvOverrides local file of KEY=value lines to merge into .env (optional)

param(
    [string]$KeyPath      = "$(Resolve-Path .)/my-key.pem",
    [string]$SshHost      = "ec2-user@ec2-13-207-61-191.ap-south-1.compute.amazonaws.com",
    [string]$PublicHost   = "career.kaushaljain.com",
    [string]$CertFile     = "",
    [string]$KeyFile      = "",
    [string]$EnvOverrides = ""
)

$ErrorActionPreference = 'Stop'

function Step($msg)  { Write-Host ">> $msg" -ForegroundColor Cyan }
function Ok($msg)    { Write-Host "OK $msg"   -ForegroundColor Green }
function Warn($msg)  { Write-Host "!! $msg"   -ForegroundColor Yellow }
function Die($msg)   { Write-Host "ER $msg"   -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------------------
# 1. Pre-flight checks
# ---------------------------------------------------------------------------
Step "Pre-flight"

if (-not (Test-Path $KeyPath)) {
    Die "SSH key not found at $KeyPath. Pass -KeyPath <path>."
}

# On Windows, OpenSSH will refuse keys with permissive ACLs. Tighten them.
try {
    icacls $KeyPath /inheritance:r | Out-Null
    icacls $KeyPath /grant:r "$($env:USERNAME):(R)" | Out-Null
} catch { Warn "could not tighten ACL on $KeyPath (continuing): $_" }

# Smoke-test SSH
Step "Testing SSH to $SshHost"
$probe = & ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes -i $KeyPath $SshHost 'echo PROBE_OK && uname -a' 2>&1
if ($LASTEXITCODE -ne 0 -or -not ($probe -match 'PROBE_OK')) {
    Die "SSH probe failed: $probe"
}
Ok "SSH works"

# ---------------------------------------------------------------------------
# 2. Upload bootstrap script + optional files
# ---------------------------------------------------------------------------
Step "Uploading bootstrap-ec2.sh"
$bootstrap = (Resolve-Path "./scripts/bootstrap-ec2.sh").Path
& scp -i $KeyPath $bootstrap "${SshHost}:/tmp/bootstrap-ec2.sh"
if ($LASTEXITCODE -ne 0) { Die "scp of bootstrap-ec2.sh failed" }

if ($CertFile -ne "" -and (Test-Path $CertFile)) {
    Step "Uploading Cloudflare cert"
    & scp -i $KeyPath $CertFile "${SshHost}:/tmp/cn-cf-cert.pem"
    if ($LASTEXITCODE -ne 0) { Die "scp of cert failed" }
} else {
    Warn "No -CertFile provided. Bootstrap will configure HTTP only. (Set up SSL later.)"
}

if ($KeyFile -ne "" -and (Test-Path $KeyFile)) {
    Step "Uploading Cloudflare private key"
    & scp -i $KeyPath $KeyFile "${SshHost}:/tmp/cn-cf-key.pem"
    if ($LASTEXITCODE -ne 0) { Die "scp of key failed" }
}

if ($EnvOverrides -ne "" -and (Test-Path $EnvOverrides)) {
    Step "Uploading .env overrides"
    & scp -i $KeyPath $EnvOverrides "${SshHost}:/tmp/cn-env-overrides.txt"
    if ($LASTEXITCODE -ne 0) { Die "scp of env overrides failed" }
}

# ---------------------------------------------------------------------------
# 3. Run the bootstrap script on the box
# ---------------------------------------------------------------------------
Step "Running bootstrap-ec2.sh on the box (this will take a few minutes the first time)"

$remoteCmd = @"
export PUBLIC_HOST='$PublicHost'
export API_BASE='https://$PublicHost/api/v1'
chmod +x /tmp/bootstrap-ec2.sh
bash /tmp/bootstrap-ec2.sh
"@

# Suppress PS 5.1's habit of turning native-command stderr into a terminating
# exception. We rely on $LASTEXITCODE instead.
$prevPref = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& ssh -o StrictHostKeyChecking=accept-new -i $KeyPath $SshHost $remoteCmd
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $prevPref

# ---------------------------------------------------------------------------
# 4. Summary
# ---------------------------------------------------------------------------
if ($exitCode -eq 0) {
    Ok "Bootstrap completed."
    Write-Host ""
    Write-Host "What you still need to do manually:" -ForegroundColor Cyan
    Write-Host "  1. If no Cloudflare cert was uploaded: generate one in the Cloudflare dashboard"
    Write-Host "     (SSL/TLS → Origin Server → Create Certificate), save the two PEM blocks"
    Write-Host "     locally, then re-run this script with:"
    Write-Host "        pwsh ./scripts/bootstrap-ec2-from-laptop.ps1 \"
    Write-Host "            -CertFile cloudflare-cert.pem -KeyFile cloudflare-key.pem"
    Write-Host ""
    Write-Host "  2. Log into Claude Code (interactive - only you can do this):"
    Write-Host "        pwsh ./scripts/claude-remote.ps1"
    Write-Host "     Then inside the tmux session: type  /login  and paste the code from your browser."
    Write-Host ""
    Write-Host "  3. In Cloudflare dashboard: SSL/TLS → Overview → set mode to Full (strict)"
    Write-Host "     once HTTPS is up."
    Write-Host ""
    Write-Host "App URL (after cert is in place): https://$PublicHost/" -ForegroundColor Green
} else {
    Die "Bootstrap exited with code $exitCode. Re-run after fixing the issue (it's idempotent)."
}
