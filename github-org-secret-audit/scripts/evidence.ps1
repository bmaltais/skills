param([Parameter(Mandatory)][string]$Org, [string]$Root = "$HOME\org-secret-scan-$Org", [Parameter(Mandatory)][string]$Report)
# Injects Appendix A (values still on default branches) and B (every commit/file/line) with GitHub permalinks.
# Secret values are held in memory only to locate lines; the HTML contains paths, key names and sids only.
$orgUrl = "https://github.com/$Org"
$env:GIT_CONFIG_COUNT = '1'; $env:GIT_CONFIG_KEY_0 = 'safe.directory'; $env:GIT_CONFIG_VALUE_0 = '*'
$repos = Get-Content (Join-Path $Root 'repos.json') -Raw | ConvertFrom-Json
$sha256 = [Security.Cryptography.SHA256]::Create()
function Get-Sid([string]$v) { ([BitConverter]::ToString($sha256.ComputeHash([Text.Encoding]::UTF8.GetBytes($v))) -replace '-', '').Substring(0, 10).ToLower() }
function ConvertTo-UrlPath([string]$p) { ($p -split '/' | ForEach-Object { [Uri]::EscapeDataString($_) }) -join '/' }
# Deliberately not 'H': that alias (Get-History) shadows functions
function HtmlEnc([string]$s) { [System.Net.WebUtility]::HtmlEncode($s) }
function Get-Mirror([string]$n) { Join-Path $Root "mirrors\$n.git" }
function Get-Candidates([string]$line) {
    foreach ($mt in [regex]::Matches($line, '["'']([^"'']{4,})["'']')) { $mt.Groups[1].Value }
    foreach ($mt in [regex]::Matches($line, '[:=]\s*([^"''\s;,]{4,})')) { $mt.Groups[1].Value }
    foreach ($mt in [regex]::Matches($line, '[^"''\s=:;,]{4,}')) { $mt.Value }
}
function New-Row($repo, $source, $sid, $key, $sha, $date, $file, $line, $fp) {
    [pscustomobject]@{ repo = $repo; source = $source; sid = $sid; key = $key; commit = $sha; date = $date; file = $file; line = [int]$line; fp = $fp
        url = "$orgUrl/$repo/blob/$sha/$(ConvertTo-UrlPath $file)#L$line" }
}

$rows = New-Object System.Collections.Generic.List[object]
$values = @{}

# 1. Scanner matches (exact commit/file/line from Gitleaks)
foreach ($r in $repos) {
    $f = Join-Path $Root "reports\$($r.name).json"
    if (-not (Test-Path $f)) { continue }
    $arr = Get-Content $f -Raw | ConvertFrom-Json
    foreach ($i in $arr) {
        if (-not $i.RuleID) { continue }
        $fp = ''
        if ($i.RuleID -eq 'slack-webhook-url' -and $i.Secret -match 'T0{8}/B0{8}/X{24}') { $fp = 'placeholder webhook' }
        elseif ($i.Match -match 'index_key') { $fp = 'Terraform for_each key' }
        elseif ($i.Secret -match '^0{8}-0{4}-0{4}-0{4}-0{12}$') { $fp = 'all-zero GUID placeholder' }
        $key = ([regex]::Match($i.Match, '^[^:=]*')).Value -replace '[^A-Za-z0-9_.-]', ''
        $sid = Get-Sid $i.Secret
        if (-not $fp) { $values["$($r.name)|$sid"] = $i.Secret }
        $rows.Add((New-Row $r.name "gitleaks: $($i.RuleID)" $sid $key $i.Commit $i.Date.Substring(0, 10) $i.File $i.StartLine $fp))
    }
}

# 2. Manual-review literals, resolved to the exact line by hash
$current = $null
foreach ($l in (Get-Content (Join-Path $Root 'manual-review.txt'))) {
    if ($l -match '^##### (\S+)') { $current = $Matches[1]; continue }
    if ($l -notmatch '^\s+LIT (.+?)\s*\| key=(\S+) \| len=\d+ \| sid=(\w+) \| commit=(\w+)') { continue }
    $file = $Matches[1].Trim(); $key = $Matches[2]; $sid = $Matches[3]; $short = $Matches[4]
    $m = Get-Mirror $current
    $sha = (git -C $m rev-parse $short).Trim()
    $date = (git -C $m show -s --format=%ad --date=short $sha).Trim()
    $lines = @(git -C $m show "$($sha):$file" 2>$null)
    for ($n = 0; $n -lt $lines.Count; $n++) {
        if ($lines[$n] -notmatch [regex]::Escape($key)) { continue }
        foreach ($c in (Get-Candidates $lines[$n])) {
            if ((Get-Sid $c) -eq $sid) {
                $values["$current|$sid"] = $c
                $rows.Add((New-Row $current 'manual review' $sid $key $sha $date $file ($n + 1) ''))
                break
            }
        }
    }
}

$uniq = @($rows | Group-Object repo, commit, file, line, sid | ForEach-Object { $_.Group[0] })
$uniq | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $Root 'evidence.json') -Encoding UTF8

# 3. Locations still on the default branch today
$head = New-Object System.Collections.Generic.List[object]
foreach ($k in $values.Keys) {
    $repo, $sid = $k.Split('|')
    $r = $repos | Where-Object name -eq $repo
    $m = Get-Mirror $repo
    $hs = (git -C $m rev-parse $r.default_branch).Trim()
    foreach ($g in (git -C $m grep -n -F -e $values[$k] $hs 2>$null)) {
        $p = $g.Substring($hs.Length + 1) -split ':', 3
        $head.Add([pscustomobject]@{ repo = $repo; sid = $sid; branch = $r.default_branch; file = $p[0]; line = [int]$p[1]; url = "$orgUrl/$repo/blob/$hs/$(ConvertTo-UrlPath $p[0])#L$($p[1])" })
    }
}
$values = $null
$head = @($head | Sort-Object repo, sid, file, line)
$head | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $Root 'evidence-head.json') -Encoding UTF8

# 4. Appendix HTML
$sb = New-Object System.Text.StringBuilder
$nScan = @($uniq | Where-Object source -like 'gitleaks*').Count; $nMan = @($uniq | Where-Object source -eq 'manual review').Count
[void]$sb.AppendLine('    <section id="evidence">')
[void]$sb.AppendLine('      <h2>Appendix A - Values still present on the default branch</h2>')
[void]$sb.AppendLine("      <p>$($head.Count) locations where a flagged credential is still present at the current default-branch commit. Each link is a permalink to the exact file and line. Clean these up first after rotation.</p>")
[void]$sb.AppendLine('      <div class="inventory"><table><thead><tr><th>Repository</th><th>Branch</th><th>File : line (link)</th><th>sid</th></tr></thead><tbody>')
foreach ($x in $head) { [void]$sb.AppendLine("<tr><td>$(HtmlEnc $x.repo)</td><td><code>$(HtmlEnc $x.branch)</code></td><td><a href=""$(HtmlEnc $x.url)"">$(HtmlEnc $x.file):$($x.line)</a></td><td><code>$($x.sid)</code></td></tr>") }
[void]$sb.AppendLine('      </tbody></table></div>')
[void]$sb.AppendLine('      <h2 style="margin-top:28px">Appendix B - Evidence index: every commit, file and line</h2>')
[void]$sb.AppendLine("      <p>$($uniq.Count) locations in history ($nScan scanner matches, $nMan manual-review locations). <strong>Commit</strong> opens the commit diff; <strong>File : line</strong> opens the file at that commit scrolled to the line holding the secret. The <em>sid</em> column groups occurrences of the same value. False positives are kept but labelled.</p>")
foreach ($grp in ($uniq | Group-Object repo | Sort-Object Name)) {
    [void]$sb.AppendLine("      <h3>$(HtmlEnc $grp.Name) <span class=""meta"">($($grp.Count) locations)</span></h3>")
    [void]$sb.AppendLine('      <div class="inventory"><table><thead><tr><th>Date</th><th>Commit</th><th>File : line (link)</th><th>Key</th><th>sid</th><th>Source</th><th>Note</th></tr></thead><tbody>')
    foreach ($x in ($grp.Group | Sort-Object date, file, line)) {
        $note = if ($x.fp) { 'False positive: ' + (HtmlEnc $x.fp) } else { '' }
        [void]$sb.AppendLine("<tr><td>$($x.date)</td><td><a href=""$orgUrl/$($x.repo)/commit/$($x.commit)""><code>$($x.commit.Substring(0, 12))</code></a></td><td><a href=""$(HtmlEnc $x.url)"">$(HtmlEnc $x.file):$($x.line)</a></td><td><code>$(HtmlEnc $x.key)</code></td><td><code>$($x.sid)</code></td><td>$(HtmlEnc $x.source)</td><td>$note</td></tr>")
    }
    [void]$sb.AppendLine('      </tbody></table></div>')
}
[void]$sb.AppendLine('    </section>')

# Idempotent: replace any previous appendix, insert before the repository inventory
$html = [IO.File]::ReadAllText($Report)
$html = [regex]::Replace($html, '(?s)\s*<section id="evidence">.*?</section>', '')
$anchor = [regex]::Match($html, '\s*<section>\s*<h2>Repository inventory</h2>')
if (-not $anchor.Success) { throw 'Repository inventory section not found in report' }
$html = $html.Insert($anchor.Index, "`r`n" + $sb.ToString().TrimEnd())
[IO.File]::WriteAllText($Report, $html, (New-Object Text.UTF8Encoding $false))
"rows=$($uniq.Count) scanner=$nScan manual=$nMan head=$($head.Count) emptyFile=$(@($uniq | Where-Object { -not $_.file }).Count) finished=$(Get-Date -Format s)" |
    Set-Content (Join-Path $Root 'evidence-status.txt') -Encoding UTF8
