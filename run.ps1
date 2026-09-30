$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$distRoot = Join-Path $projectRoot 'dist'
$appRoot = Join-Path $distRoot 'EmploymentPortalSearch'
$executable = Join-Path $appRoot 'EmploymentPortalSearch.exe'
$installing = Join-Path $distRoot '.portable-installing'

if ((Test-Path -LiteralPath $executable) -and -not (Test-Path -LiteralPath $installing)) {
    Start-Process -FilePath $executable -WorkingDirectory $appRoot
    exit 0
}

Write-Host 'First launch: downloading the Windows portable app from GitHub Releases.'
Write-Host 'The archive is large. Keep this window open until the download and extraction finish.'

$repository = 'songhaotian694-oss/portal-search-app'
$archiveName = 'EmploymentPortalSearch-windows-x64.zip'
$checksumName = "$archiveName.sha256"
$headers = @{ 'User-Agent' = 'EmploymentPortalSearch-Portable-Launcher'; 'Accept' = 'application/vnd.github+json' }
$release = Invoke-RestMethod -Uri "https://api.github.com/repos/$repository/releases/latest" -Headers $headers
$archiveAsset = $release.assets | Where-Object { $_.name -eq $archiveName } | Select-Object -First 1
$checksumAsset = $release.assets | Where-Object { $_.name -eq $checksumName } | Select-Object -First 1
if (-not $archiveAsset -or -not $checksumAsset) {
    throw 'The latest GitHub release does not contain a complete Windows portable package.'
}

New-Item -ItemType Directory -Path $distRoot -Force | Out-Null
$archive = Join-Path $distRoot $archiveName
$partial = "$archive.partial"
try {
    Invoke-WebRequest -Uri $archiveAsset.browser_download_url -Headers $headers -OutFile $partial -UseBasicParsing
    $expected = ([string](Invoke-WebRequest -Uri $checksumAsset.browser_download_url -Headers $headers -UseBasicParsing).Content).Trim()
    if ($expected -notmatch '^[0-9a-fA-F]{64}$') {
        throw 'The release checksum is invalid.'
    }
    $actual = (Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash
    if ($actual -ne $expected) {
        throw 'The downloaded archive failed its SHA-256 integrity check.'
    }
    Move-Item -LiteralPath $partial -Destination $archive -Force
    New-Item -ItemType File -Path $installing -Force | Out-Null
    Expand-Archive -LiteralPath $archive -DestinationPath $distRoot -Force
    if (-not (Test-Path -LiteralPath $executable)) {
        throw 'The portable package is missing EmploymentPortalSearch.exe.'
    }
    Remove-Item -LiteralPath $installing -Force
    Write-Host 'The app is ready. Starting the login screen...'
} finally {
    Remove-Item -LiteralPath $partial, $archive -Force -ErrorAction SilentlyContinue
}

Start-Process -FilePath $executable -WorkingDirectory $appRoot
