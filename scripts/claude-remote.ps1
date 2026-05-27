# claude-remote.ps1
# One-command launcher: SSH into the EC2 box and attach to (or create) a tmux
# session running Claude Code in /opt/career-navigator. Run from your laptop:
#
#   pwsh ./scripts/claude-remote.ps1
#
# Detach without killing the session: Ctrl+B then D.
# Kill the session entirely (from inside): exit, or tmux kill-session -t claude.

param(
    [string]$KeyPath = "$(Resolve-Path .)/my-key.pem",
    [string]$Host    = "ec2-user@ec2-13-207-61-191.ap-south-1.compute.amazonaws.com",
    [string]$Session = "claude",
    [string]$Workdir = "/opt/career-navigator"
)

if (-not (Test-Path $KeyPath)) {
    Write-Error "SSH key not found at $KeyPath. Pass -KeyPath <path>."
    exit 1
}

# Build the remote command. `tmux attach || tmux new ...` is the standard idiom:
# attach if a session named $Session exists, otherwise create one running claude
# in the project working directory.
$remote = "tmux attach -t $Session 2>/dev/null || tmux new -s $Session 'cd $Workdir && claude'"

Write-Host "Connecting to $Host (session: $Session) ..." -ForegroundColor Cyan
ssh -t -i $KeyPath $Host $remote
