# Fix all markdown files excluding .claude/ directory
$ErrorActionPreference = "Stop"

$files = Get-ChildItem -Path . -Recurse -Filter *.md | Where-Object { $_.FullName -notlike '*\.claude\*' }
$hasErrors = $false

foreach ($file in $files) {
    Write-Host "Fixing: $($file.FullName)"
    & pymarkdownlnt.exe -d md013,md036 fix $file.FullName
    if ($LASTEXITCODE -ne 0) {
        $hasErrors = $true
    }
}

if ($hasErrors) {
    exit 1
}
