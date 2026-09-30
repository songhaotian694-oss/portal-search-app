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
$downloadBase = "https://github.com/$repository/releases/latest/download"
$headers = @{ 'User-Agent' = 'EmploymentPortalSearch-Portable-Launcher' }

New-Item -ItemType Directory -Path $distRoot -Force | Out-Null
$archive = Join-Path $distRoot $archiveName
$partial = "$archive.partial"
$checksumFile = Join-Path $distRoot $checksumName
try {
    Invoke-WebRequest -Uri "$downloadBase/$archiveName" -Headers $headers -OutFile $partial -UseBasicParsing
    Invoke-WebRequest -Uri "$downloadBase/$checksumName" -Headers $headers -OutFile $checksumFile -UseBasicParsing
    $expected = (Get-Content -LiteralPath $checksumFile -Raw -Encoding ASCII).Trim()
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
    Remove-Item -LiteralPath $partial, $archive, $checksumFile -Force -ErrorAction SilentlyContinue
}

Start-Process -FilePath $executable -WorkingDirectory $appRoot
