# Install Gradle to %USERPROFILE%\Gradle and add to PATH for current session.
# Run: powershell -ExecutionPolicy Bypass -File scripts\install_gradle.ps1

$ErrorActionPreference = "Stop"
$gradleVersion = "8.2"
$gradleUrl = "https://services.gradle.org/distributions/gradle-$gradleVersion-bin.zip"
$destDir = Join-Path $env:USERPROFILE "Gradle"
$zipPath = Join-Path $env:TEMP "gradle-$gradleVersion-bin.zip"
$extractPath = Join-Path $destDir "gradle-$gradleVersion"

if (Get-Command gradle -ErrorAction SilentlyContinue) {
    Write-Host "Gradle already in PATH"
    gradle -v
    exit 0
}

if (Test-Path (Join-Path $extractPath "bin\gradle.bat")) {
    Write-Host "Gradle already installed at $extractPath"
    $env:PATH = "$extractPath\bin;$env:PATH"
    gradle -v
    exit 0
}

Write-Host "Downloading Gradle $gradleVersion..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $gradleUrl -OutFile $zipPath -UseBasicParsing

Write-Host "Extracting to $destDir"
New-Item -ItemType Directory -Path $destDir -Force | Out-Null
Expand-Archive -Path $zipPath -DestinationPath $destDir -Force
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

$env:PATH = "$extractPath\bin;$env:PATH"
Write-Host "Gradle installed at $extractPath"
Write-Host "Add to PATH permanently: $extractPath\bin"
& "$extractPath\bin\gradle.bat" -v
