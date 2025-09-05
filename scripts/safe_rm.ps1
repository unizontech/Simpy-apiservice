param([Parameter(Mandatory=$true)][string[]]$Paths)
$trash = Join-Path -Path (git rev-parse --show-toplevel) -ChildPath ".trash/$(Get-Date -Format yyyyMMdd-HHmmss)"
New-Item -ItemType Directory -Force -Path $trash | Out-Null
foreach ($p in $Paths) {
  if (Test-Path $p) { Move-Item -Path $p -Destination $trash -Force }
}
Write-Host "Moved to trash:" $trash