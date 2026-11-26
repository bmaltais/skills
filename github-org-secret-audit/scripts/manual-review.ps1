param([Parameter(Mandatory)][string]$Org, [string]$Root = "$HOME\org-secret-scan-$Org")
# Output never contains secret values: only names, shapes, counts and truncated SHA-256 ids (sid)
$env:GIT_CONFIG_COUNT = '1'; $env:GIT_CONFIG_KEY_0 = 'safe.directory'; $env:GIT_CONFIG_VALUE_0 = '*'
$repos = Get-Content (Join-Path $Root 'repos.json') -Raw | ConvertFrom-Json
$sha = [Security.Cryptography.SHA256]::Create()
function Get-Sid([string]$v) { ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($v))) -replace '-', '').Substring(0, 10).ToLower() }
function Get-Shape([string]$s) { $c = ''; if ($s -cmatch '[a-z]') { $c += 'a' }; if ($s -cmatch '[A-Z]') { $c += 'A' }; if ($s -match '\d') { $c += '9' }; if ($s -match '[^A-Za-z0-9]') { $c += '#' }; "len=$($s.Length)/$c" }
$o = New-Object System.Collections.Generic.List[string]

$filePat = '(\.tfstate(\.backup)?|tfstate\.backup(\.old)?|\.pfx|\.p12|\.pem|\.key|id_rsa[^/]*|id_ed25519[^/]*|kubeconfig[^/]*|\.env|private\.env|\.publishsettings|credentials[^/]*|\.kdbx|\.jks|\.keystore|\.npmrc|\.pypirc|\.netrc)$'
$pwPat = '(?i)(password|passwd|pwd|secret|client_secret|apppassword|access_key|account_key|sas_token|connection_?string|api_?key|subscription_key|search_service_key_\w+|token)\s*[:=]\s*["'']([^"''$\{\}<>\s]{6,})["'']'
$hdrPat = '(?i)(Ocp-Apim-Subscription-Key|x-api-key|x-functions-key|api-key)\s*:\s*([A-Za-z0-9._-]{16,})'
$placeholder = '(?i)^(changeme|password|secret|x{4,}|\*+|example|placeholder|your|<|none|null|true|false|var\.|local\.|data\.|module\.|dependency\.|random_|get_env)'

foreach ($r in $repos) {
    $m = Join-Path $Root "mirrors\$($r.name).git"
    if (-not (Test-Path $m)) { continue }
    $tips = @(git -C $m for-each-ref --format='%(refname)')
    $o.Add("##### $($r.name)  refs=$($tips.Count)")

    # Sensitive file types anywhere in history
    foreach ($p in (git -C $m log --all --name-only --format= 2>$null | Sort-Object -Unique | Where-Object { $_ -match $filePat })) {
        $head = [bool](git -C $m ls-tree -r --name-only $r.default_branch -- $p 2>$null)
        $first = git -C $m log --all --format='%h %ad' --date=short -- $p 2>$null | Select-Object -Last 1
        $o.Add("  FILE $p | atDefaultHead=$head | firstCommit=$first")
        if ($p -match '\.env$|private\.env$') {
            $c = git -C $m log --all --format=%h -1 -- $p
            $vars = foreach ($l in (git -C $m show "$($c):$p" 2>$null)) { if ($l -match '^\s*(export\s+)?([A-Za-z_]\w*)\s*=\s*(.*)$') { $v = $Matches[3].Trim('"', "'", ' '); "$($Matches[2])[$(if ($v) { Get-Shape $v } else { 'empty' })]" } }
            $o.Add("    ENVVARS @$c : $($vars -join ' ')")
        }
        if ($p -match 'tfstate') {
            $c = git -C $m log --all --format=%h --diff-filter=AM -1 -- $p
            $txt = (git -C $m show "$($c):$p" 2>$null) -join "`n"
            $types = [regex]::Matches($txt, '"type"\s*:\s*"([a-z0-9_]+)"') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
            $sens = [regex]::Matches($txt, '"([a-z_]*(key|password|secret|connection_string|sas|token)[a-z_]*)"\s*:\s*"([^"]{8,})"') | ForEach-Object { $_.Groups[1].Value } | Group-Object | ForEach-Object { "$($_.Name)x$($_.Count)" }
            $emails = [regex]::Matches($txt, '[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[a-z]{2,})') | ForEach-Object { $_.Groups[1].Value.ToLower() } | Group-Object | ForEach-Object { "$($_.Name)x$($_.Count)" }
            $o.Add("    STATE @$c types=$($types -join ',')")
            $o.Add("    STATE sensitiveAttrs=$($sens -join ', ') emailDomains=$($emails -join ' ')")
        }
    }

    # Literals the default rules miss, from every added line in history
    $seen = @{}; $vals = @{}; $c = $null; $f = $null
    git -C $m log --all -p -U0 --no-ext-diff --no-textconv --format='@@C %h' 2>$null | ForEach-Object {
        if ($_ -like '@@C *') { $c = $_.Substring(4); return }
        if ($_ -like '+++ b/*') { $f = $_.Substring(6); return }
        if (-not $_.StartsWith('+')) { return }
        foreach ($mt in @([regex]::Matches($_, $pwPat)) + @([regex]::Matches($_, $hdrPat))) {
            $v = $mt.Groups[2].Value
            if ($v -match $placeholder) { continue }
            $vals[$v] = $mt.Groups[1].Value
            $k = "$f|$($mt.Groups[1].Value)|$v"
            if ($seen.ContainsKey($k)) { continue }; $seen[$k] = 1
            $o.Add("  LIT $f | key=$($mt.Groups[1].Value) | len=$($v.Length) | sid=$(Get-Sid $v) | commit=$c")
        }
    }
    # Where each literal still lives
    foreach ($v in $vals.Keys) {
        $headFiles = @(git -C $m grep -l -F -e $v $r.default_branch 2>$null)
        $refCount = @(git -C $m grep -l -F -e $v @tips 2>$null | ForEach-Object { $_.Split(':')[0] } | Sort-Object -Unique).Count
        $o.Add("  VAL key=$($vals[$v]) sid=$(Get-Sid $v) $(Get-Shape $v) headFiles=$($headFiles.Count) refTips=$refCount/$($tips.Count)")
    }
    $vals = $null

    # Org-wide indicators (counts only)
    $hist = (git -C $m log --all -p --no-ext-diff --no-textconv --format= 2>$null) -join "`n"
    $em = @([regex]::Matches($hist, '[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.(gc\.ca|canada\.ca|onmicrosoft\.com|gov|mil)') | ForEach-Object { $_.Value.ToLower() } | Sort-Object -Unique).Count
    $subs = @([regex]::Matches($hist, '/subscriptions/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}') | ForEach-Object { $_.Value } | Sort-Object -Unique).Count
    $pk = [regex]::Matches($hist, '-----BEGIN (RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----').Count
    $sas = [regex]::Matches($hist, 'sig=[A-Za-z0-9%]{20,}').Count
    $hist = $null
    $o.Add("  ORG govEmails=$em subscriptionIds=$subs privateKeyBlocks=$pk sasSig=$sas")
    $o | Set-Content (Join-Path $Root 'manual-review.txt') -Encoding UTF8
}
$o.Add("done $(Get-Date -Format s)")
$o | Set-Content (Join-Path $Root 'manual-review.txt') -Encoding UTF8
