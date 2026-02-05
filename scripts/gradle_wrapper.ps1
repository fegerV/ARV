# Generate Gradle Wrapper in android/ without using the daemon (avoids "Could not connect to Gradle daemon").
# Run from repo root: powershell -ExecutionPolicy Bypass -File scripts\gradle_wrapper.ps1

$ErrorActionPreference = "Stop"
$gradlePath = Join-Path $env:USERPROFILE "Gradle\gradle-8.2\bin\gradle.bat"
$androidDir = Join-Path $PSScriptRoot "..\android"

if (-not (Test-Path $gradlePath)) {
    Write-Host "Gradle not found at $gradlePath. Run scripts\install_gradle.ps1 first."
    exit 1
}

Push-Location $androidDir
try {
    $env:GRADLE_OPTS = "-Dorg.gradle.daemon=false"
    & $gradlePath wrapper --no-daemon
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Done. You can now run: cd android; .\gradlew.bat assembleDebug"
} finally {
    Pop-Location
}
