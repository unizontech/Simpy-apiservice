#!/usr/bin/env pwsh
$limit = 10
$base = (git rev-parse '@{push}' 2>$null)
if (-not $base) { 
  # No upstream branch yet, allow push
  exit 0 
}
$deleted = git diff --name-status "$base"..HEAD | Where-Object { $_ -match '^D\s+.*\.md' }
if ($deleted.Count -ge $limit -and -not (Test-Path 'docs/deletion_approval.yaml')) {
  Write-Error "Pushing large docs deletions without approval file. Push blocked."
  exit 1
}
exit 0