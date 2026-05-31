param(
    [string]$CommitMessage = "",
    [switch]$SkipVercel,
    [switch]$SkipHuggingFace
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [string]$Label,
        [scriptblock]$Script
    )

    Write-Host "`n[$Label]" -ForegroundColor Cyan
    & $Script
}

function Test-GitClean {
    $status = git status --short
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read git status."
    }
    return [string]::IsNullOrWhiteSpace($status)
}

function Get-CurrentBranch {
    $branch = git branch --show-current
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($branch)) {
        throw "Unable to determine the current branch."
    }
    return $branch.Trim()
}

if (-not (Test-GitClean)) {
    if ([string]::IsNullOrWhiteSpace($CommitMessage)) {
        throw "Working tree has changes. Commit them first or rerun with -CommitMessage 'your message'."
    }

    Invoke-Checked -Label "Commit" -Script {
        git add index.py portfolio/trading/deploy.py requirements.txt pyproject.toml README.md pyaudioop.py
        if ($LASTEXITCODE -ne 0) { throw "git add failed." }
        git commit -m $CommitMessage
        if ($LASTEXITCODE -ne 0) { throw "git commit failed." }
    }
}

$branch = Get-CurrentBranch

if (-not $SkipHuggingFace) {
    Invoke-Checked -Label "Hugging Face" -Script {
        git push space HEAD:$branch
        if ($LASTEXITCODE -ne 0) { throw "Hugging Face push failed." }
    }
}

if (-not $SkipVercel) {
    Invoke-Checked -Label "Vercel" -Script {
        vercel deploy --prod --yes
        if ($LASTEXITCODE -ne 0) { throw "Vercel deploy failed." }
    }
}

Write-Host "`nDeploy complete." -ForegroundColor Green
