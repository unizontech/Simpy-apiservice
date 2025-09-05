param(
  [string]$Pattern = "*"  # 例: "ja", "docs-ja", "simpy_*"
)

$repo = git rev-parse --show-toplevel
$latest = Get-ChildItem "$repo\.trash" -Directory | Sort-Object Name -Descending | Select-Object -First 1
if (-not $latest) { Write-Error "No .trash found"; exit 1 }

$manifest = Join-Path $latest.FullName "manifest.json"
if (-not (Test-Path $manifest)) { Write-Error "Manifest not found: $manifest"; exit 1 }

$entries = Get-Content $manifest -Raw | ConvertFrom-Json
foreach ($e in $entries) {
  $name = Split-Path $e.to -Leaf
  if ($name -like $Pattern) {
    $target = Join-Path $repo (Split-Path $e.from -Parent)
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    Move-Item -LiteralPath $e.to -Destination $target -Force
    Write-Host "Restored: $name -> $target"
  }
}