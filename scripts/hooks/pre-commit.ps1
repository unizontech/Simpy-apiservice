#!/usr/bin/env pwsh
$limit = 5  # .md削除が6件以上ならブロック
$deleted = git diff --cached --name-status | Where-Object { $_ -match '^D\s+.*\.md' }
if ($deleted.Count -ge $limit -and -not (Test-Path 'docs/deletion_approval.yaml')) {
  Write-Error "Too many docs deletions ($($deleted.Count)). Create docs/deletion_approval.yaml to proceed."
  exit 1
}
exit 0