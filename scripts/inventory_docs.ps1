$paths = @("docs","README.md")
$files = git ls-files | ? { $_ -match '(^docs/.*\.md$|^README\.md$)' }
$cnt = $files.Count
$lines = 0; foreach($f in $files){ $lines += (Get-Content $f -ErrorAction SilentlyContinue | Measure-Object -Line).Lines }
[pscustomobject]@{ files=$cnt; lines=$lines } | Format-List
$files | Sort-Object | ForEach-Object { $_ }