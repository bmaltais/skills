param([Parameter(Mandatory)][string]$Org, [string]$Root = "$HOME\org-secret-scan-$Org")
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force $Root | Out-Null
$headers = @{ 'User-Agent' = 'org-secret-audit'; 'Accept' = 'application/vnd.github+json' }
# Token is optional and supplied by the user via environment; never printed
if ($env:GITHUB_TOKEN) { $headers['Authorization'] = "Bearer $env:GITHUB_TOKEN" }
$all = @(); $page = 1
do {
    $batch = Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/orgs/$Org/repos?type=all&per_page=100&page=$page"
    $all += $batch; $page++
} while (@($batch).Count -eq 100)
$repos = $all | Select-Object name, full_name, private, visibility, archived, fork, default_branch, clone_url, size, pushed_at
$repos | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $Root 'repos.json') -Encoding UTF8
"total=$(@($repos).Count) private=$(@($repos | Where-Object private).Count) archived=$(@($repos | Where-Object archived).Count) forks=$(@($repos | Where-Object fork).Count) authenticated=$([bool]$env:GITHUB_TOKEN)" |
    Set-Content (Join-Path $Root 'inventory-status.txt') -Encoding UTF8
