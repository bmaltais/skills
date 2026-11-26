param([Parameter(Mandatory)][string]$Org, [string]$Root = "$HOME\org-secret-scan-$Org")
$env:GIT_CONFIG_COUNT = '1'; $env:GIT_CONFIG_KEY_0 = 'safe.directory'; $env:GIT_CONFIG_VALUE_0 = '*'
$repos = Get-Content (Join-Path $Root 'repos.json') -Raw | ConvertFrom-Json
$sha = [System.Security.Cryptography.SHA256]::Create()
function Get-Sid([string]$s) { ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s))) -replace '-', '').Substring(0, 10).ToLower() }
function Get-Shape([string]$s) {
    $c = ''; if ($s -cmatch '[a-z]') { $c += 'a' }; if ($s -cmatch '[A-Z]') { $c += 'A' }; if ($s -match '\d') { $c += '9' }; if ($s -match '[^A-Za-z0-9]') { $c += '#' }
    "len=$($s.Length) chars=$c"
}
$all = foreach ($r in $repos) {
    $f = Join-Path $Root "reports\$($r.name).json"
    if (-not (Test-Path $f)) { continue }
    $arr = Get-Content $f -Raw | ConvertFrom-Json
    $mirror = Join-Path $Root "mirrors\$($r.name).git"
    foreach ($i in $arr) {
        if (-not $i.RuleID) { continue }
        $headContent = git -C $mirror show "$($r.default_branch):$($i.File)" 2>$null | Out-String
        $ctx = if ($i.Secret) { $i.Match.Replace($i.Secret, '[REDACTED]') } else { $i.Match }
        if ($ctx.Length -gt 140) { $ctx = $ctx.Substring(0, 140) + '...' }
        [pscustomobject]@{
            repo = $r.name; rule = $i.RuleID; file = $i.File; line = $i.StartLine; commit = $i.Commit.Substring(0, 12); date = $i.Date
            sid = Get-Sid $i.Secret; shape = Get-Shape $i.Secret; entropy = [math]::Round($i.Entropy, 2)
            atHead = [bool]($headContent -and $i.Secret -and $headContent.Contains($i.Secret)); context = $ctx -replace '\s+', ' '
        }
    }
}
$all | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $Root 'findings-redacted.json') -Encoding UTF8
$o = @("TOTAL raw: $(@($all).Count)")
$o += $all | Group-Object repo | ForEach-Object { "$($_.Name): $($_.Count)" }
$o += "`n=== Unique (repo, rule, file, sid) ==="
$o += $all | Group-Object repo, rule, file, sid | ForEach-Object {
    $g = $_.Group; $first = $g | Sort-Object date | Select-Object -First 1
    [pscustomobject]@{ repo = $first.repo; rule = $first.rule; file = $first.file; line = $first.line; n = $g.Count; commit = $first.commit
        date = $first.date.Substring(0, 10); sid = $first.sid; shape = $first.shape; ent = $first.entropy; head = ($g.atHead -contains $true); ctx = $first.context }
} | Sort-Object repo, rule, file | Format-List | Out-String -Width 300
$o | Set-Content (Join-Path $Root 'analysis.txt') -Encoding UTF8
