# Проверка доступности сервера ARV (health и порт)
$base = "http://localhost:8000"
$health = "$base/api/health/status"

Write-Host "=== Проверка сервера ARV ===" -ForegroundColor Cyan
Write-Host ""

# 1. Health endpoint
try {
    $r = Invoke-WebRequest -Uri $health -UseBasicParsing -TimeoutSec 5
    Write-Host "[OK] Сервер отвечает: HTTP $($r.StatusCode)" -ForegroundColor Green
    $json = $r.Content | ConvertFrom-Json
    if ($json.checks.database) { Write-Host "  DB: $($json.checks.database)" }
    if ($json.checks.system) {
        Write-Host "  CPU: $($json.checks.system.cpu_percent)% | RAM: $($json.checks.system.memory_percent)%"
    }
} catch {
    Write-Host "[FAIL] Сервер недоступен: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Убедитесь, что запущен: uvicorn app.main:app --host 0.0.0.0 --port 8000" -ForegroundColor Yellow
    exit 1
}

# 2. Главная страница
try {
    $r2 = Invoke-WebRequest -Uri $base -UseBasicParsing -TimeoutSec 3 -MaximumRedirection 0 -ErrorAction SilentlyContinue
} catch {
    if ($_.Exception.Response.StatusCode -eq 302 -or $_.Exception.Response.StatusCode -eq 200) {
        Write-Host "[OK] Главная страница доступна" -ForegroundColor Green
    } else {
        Write-Host "[?] Главная: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Полезные URL:" -ForegroundColor Cyan
Write-Host "  Health:  $health"
Write-Host "  Docs:    $base/docs"
Write-Host "  AR view: $base/view/<unique_id>"
