# Fix all markdown files excluding directories from .gitignore
$ErrorActionPreference = "Continue"

# Function to parse .gitignore and extract directory patterns
function Get-GitignorePatterns {
    param (
        [string]$GitignorePath = ".gitignore"
    )

    if (-not (Test-Path $GitignorePath)) {
        return @()
    }

    $patterns = @()
    $gitignoreContent = Get-Content $GitignorePath

    foreach ($line in $gitignoreContent) {
        # Skip empty lines and comments
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) {
            continue
        }

        $line = $line.Trim()

        # Handle directory patterns (ending with /)
        if ($line.EndsWith('/')) {
            $pattern = $line.TrimEnd('/')
            # Convert to PowerShell wildcard pattern
            $patterns += "*\$pattern\*"
        }
        # Handle patterns that are clearly directories (common directory names)
        elseif ($line -match '^[^*?]+$' -and $line -notmatch '\.[a-zA-Z0-9]+$') {
            # This looks like a directory name without wildcards and no file extension
            $patterns += "*\$line\*"
        }
    }

    return $patterns
}

# Get patterns from .gitignore
$excludePatterns = Get-GitignorePatterns
# Always exclude .claude directory
$excludePatterns += '*\.claude\*'

# Get all markdown files
$files = Get-ChildItem -Path . -Recurse -Filter *.md | Where-Object {
    $filePath = $_.FullName
    $shouldExclude = $false

    foreach ($pattern in $excludePatterns) {
        if ($filePath -like $pattern) {
            $shouldExclude = $true
            break
        }
    }

    return -not $shouldExclude
}

$hasErrors = $false
$failedFiles = @()
$toolErrors = @()

foreach ($file in $files) {
    Write-Host "Fixing: $($file.FullName)"
    $output = & uv run pymarkdownlnt -d md013,md022,md031,md032,md036 fix $file.FullName 2>&1 | Out-String

    if ($LASTEXITCODE -ne 0) {
        # Check if it's a tool error (AttributeError, etc.) vs actual linting error
        if ($output -match "AttributeError|Unexpected Error") {
            $toolErrors += $file.FullName
            Write-Host "  Warning: Linter internal error, skipping this file" -ForegroundColor Yellow
        } else {
            $hasErrors = $true
            $failedFiles += $file.FullName
        }
    }
}

if ($toolErrors.Count -gt 0) {
    Write-Host "`nSkipped files (linter internal errors):" -ForegroundColor Yellow
    foreach ($toolError in $toolErrors) {
        Write-Host "  - $toolError" -ForegroundColor Yellow
    }
}

if ($hasErrors) {
    Write-Host "`nFailed files:" -ForegroundColor Red
    foreach ($failedFile in $failedFiles) {
        Write-Host "  - $failedFile" -ForegroundColor Red
    }
    exit 1
}
