# Accept Android SDK licenses so that gradle assembleDebug can run.
# Run from repo root: powershell -ExecutionPolicy Bypass -File scripts\android_accept_licenses.ps1

$ErrorActionPreference = "Stop"
$sdkRoot = "$env:LOCALAPPDATA\Android\Sdk"
$licensesDir = Join-Path $sdkRoot "licenses"

# Create license files so Gradle can install Platform 34 and Build-Tools 34
if (-not (Test-Path $sdkRoot)) {
    Write-Host "Android SDK not found at $sdkRoot"
    exit 1
}
New-Item -ItemType Directory -Path $licensesDir -Force | Out-Null

$licenseContent = @"
8933bad161af4178b1185d1a37fbf41ea5269c55
"@
$previewContent = @"
84831b9409646a918e30573bab4c9c91346d8abd
"@

Set-Content -Path (Join-Path $licensesDir "android-sdk-license") -Value $licenseContent -Encoding ASCII
Set-Content -Path (Join-Path $licensesDir "android-sdk-preview-license") -Value $previewContent -Encoding ASCII
Write-Host "License files created in $licensesDir"
Write-Host "Run again: cd android; .\gradlew.bat assembleDebug"
