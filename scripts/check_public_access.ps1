# Проверка доступности приложения снаружи (https://ar.neuroimagen.ru)
# Запуск: .\scripts\check_public_access.ps1

Write-Host "=== Проверка доступа к https://ar.neuroimagen.ru ===" -ForegroundColor Cyan
Write-Host ""

# 1. Порт 8000 слушается?
Write-Host "1. Слушается ли порт 8000 на этом ПК?" -ForegroundColor Yellow
$listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    $listeners | ForEach-Object { Write-Host "   OK: $($_.LocalAddress):$($_.LocalPort) (State: $($_.State))" -ForegroundColor Green }
} else {
    Write-Host "   НЕТ. Запустите сервер: python -m app.main" -ForegroundColor Red
}
Write-Host ""

# 2. Локальные IPv4 (для проброса в роутере)
Write-Host "2. Локальный IP этого ПК (указать в роутере в пробросе портов):" -ForegroundColor Yellow
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\.' } | ForEach-Object {
    Write-Host "   $($_.IPAddress)  ($($_.InterfaceAlias))" -ForegroundColor Green
}
Write-Host ""

# 3. Правило файрвола для 8000 (при пробросе 443→8000 трафик приходит на ПК на порт 8000!)
Write-Host "3. Правило брандмауэра для входящего TCP 8000:" -ForegroundColor Yellow
$found = $false
Get-NetFirewallRule -Direction Inbound -Enabled True -ErrorAction SilentlyContinue | ForEach-Object {
    $port = ($_ | Get-NetFirewallPortFilter -ErrorAction SilentlyContinue).LocalPort
    if ($port -eq 8000) { $found = $true }
}
if ($found) {
    Write-Host "   Есть правило для порта 8000" -ForegroundColor Green
} else {
    Write-Host "   Правило не найдено. Выполните (от админа): New-NetFirewallRule -DisplayName 'ARV HTTPS 8000' -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow" -ForegroundColor Red
}
Write-Host ""

# 4. Локальный запрос
Write-Host "4. Локальный запрос к приложению (127.0.0.1:8000):" -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest -Uri "https://127.0.0.1:8000/api/health/status" -SkipCertificateCheck -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
    Write-Host "   OK: $($r.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "   Ошибка: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Убедитесь, что сервер запущен (python -m app.main)" -ForegroundColor Red
}
Write-Host ""

Write-Host "--- Что проверить в роутере ---" -ForegroundColor Cyan
Write-Host "Проброс портов: внешний 443 (или 8000) -> IP этого ПК (см. выше) -> порт 8000"
Write-Host "DNS: ar.neuroimagen.ru должен указывать на ваш внешний IP (проверьте у провайдера или в панели домена)"
Write-Host ""
