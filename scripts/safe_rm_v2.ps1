param([Parameter(Mandatory=$true)][string[]]$Paths)

$repo = git rev-parse --show-toplevel
$stamp = Get-Date -Format yyyyMMdd-HHmmss
$trash = Join-Path $repo ".trash\$stamp"
$manifest = Join-Path $trash "manifest.json"

# 保護リストチェック
$protectedFile = Join-Path $repo "scripts\protected_paths.txt"
$protected = (Test-Path $protectedFile) ? (Get-Content $protectedFile | ? {$_ -and -not $_.StartsWith("#")}) : @()

foreach ($p in $Paths) {
  foreach ($guard in $protected) {
    if ($p -like "$guard*") {
      Write-Error "PROTECTED path matched: $p (guard: $guard)"; exit 2
    }
  }
}

New-Item -ItemType Directory -Force -Path $trash | Out-Null
$entries = @()

foreach ($p in $Paths) {
  $abs = Resolve-Path $p -ErrorAction SilentlyContinue
  if (-not $abs) { Write-Warning "Skip (not found): $p"; continue }
  $name = Split-Path $abs -Leaf
  $dest = Join-Path $trash $name
  Move-Item -LiteralPath $abs -Destination $dest -Force
  $entries += [pscustomobject]@{ original = (Resolve-Path -Relative $dest "..\..\$name").Path; from = $p; to = $dest }
}

$entries | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $manifest
Write-Host "Moved to trash: $trash"
Write-Host "Manifest: $manifest"