param([Parameter(Mandatory)][string]$Org, [string]$Root = "$HOME\org-secret-scan-$Org", [string]$Gitleaks)
# PS 5.1 turns native stderr into ErrorRecords; 'Stop' would abort on Gitleaks INF lines
$ErrorActionPreference = 'Continue'
if (-not $Gitleaks) {
    $Gitleaks = (Get-Command gitleaks -ErrorAction SilentlyContinue).Source
    if (-not $Gitleaks) { $Gitleaks = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gitleaks.Gitleaks_*\gitleaks.exe" | Select-Object -First 1).FullName }
}
if (-not $Gitleaks) { throw 'gitleaks.exe not found' }
$mirrors = Join-Path $Root 'mirrors'; $reports = Join-Path $Root 'reports'
New-Item -ItemType Directory -Force $mirrors, $reports | Out-Null
$env:GIT_CONFIG_COUNT = '1'; $env:GIT_CONFIG_KEY_0 = 'safe.directory'; $env:GIT_CONFIG_VALUE_0 = '*'
$env:GIT_TERMINAL_PROMPT = '0'

$repos = Get-Content (Join-Path $Root 'repos.json') -Raw | ConvertFrom-Json
$results = foreach ($r in $repos) {
    $dest = Join-Path $mirrors "$($r.name).git"
    $row = [ordered]@{ name = $r.name; clone = 'ok'; commits = $null; scanExit = $null; scannedCommits = $null; matches = $null; error = $null }
    if (-not (Test-Path $dest)) {
        git clone --mirror --quiet $r.clone_url $dest 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { $row.clone = 'failed'; $row.error = "clone exit $LASTEXITCODE"; [pscustomobject]$row; continue }
    }
    $row.commits = [int](git -C $dest rev-list --all --count)
    $out = Join-Path $reports "$($r.name).json"; $log = Join-Path $reports "$($r.name).log"
    $glArgs = @('git', "`"$dest`"", '--log-opts="--all --full-history -m --root --no-ext-diff --no-textconv"',
        '--ignore-gitleaks-allow', '--no-color', '--no-banner', '--report-format', 'json', '--report-path', "`"$out`"", '--exit-code', '2')
    $p = Start-Process -FilePath $Gitleaks -ArgumentList $glArgs -NoNewWindow -Wait -PassThru -RedirectStandardError $log -RedirectStandardOutput "$log.out"
    $text = (Get-Content $log -Raw) + (Get-Content "$log.out" -Raw)
    $row.scanExit = $p.ExitCode
    if ($text -match '(\d+) commits scanned') { $row.scannedCommits = [int]$Matches[1] }
    if ($p.ExitCode -in 0, 2 -and (Test-Path $out)) { $arr = Get-Content $out -Raw | ConvertFrom-Json; $row.matches = @($arr).Count }
    else { $row.error = "gitleaks exit $($p.ExitCode)" }
    if ($text -match '(?m)^.*\s(ERR|WRN)\s(?!leaks found).*$') { $row.error = $Matches[0].Trim() }
    [pscustomobject]$row
}
$results | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $Root 'scan-summary.json') -Encoding UTF8
$ok = @($results | Where-Object { $_.scanExit -in 0, 2 -and $_.scannedCommits -ne $null })
"repos=$(@($results).Count) ok=$($ok.Count) failed=$(@($results).Count - $ok.Count) commits=$(($results | Measure-Object commits -Sum).Sum) scanned=$(($results | Measure-Object scannedCommits -Sum).Sum) rawMatches=$(($results | Measure-Object matches -Sum).Sum) finished=$(Get-Date -Format s)" |
    Set-Content (Join-Path $Root 'scan-status.txt') -Encoding UTF8
