# Registrator Ofisi Tizimini Docker orqali ishga tushirish skripti
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Registrator Ofisi Murojaatlar Tizimi (Docker Launcher)  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Docker yo'lini PATH ga qo'shish
$dockerPath = "C:\Users\Veon Admin\AppData\Local\Programs\DockerDesktop\resources\bin"
if (Test-Path $dockerPath) {
    $env:PATH = "$dockerPath;$env:PATH"
    Write-Host "[OK] Docker CLI yo'li ulandi: $dockerPath" -ForegroundColor Green
}

# Docker daemon holatini tekshirish
try {
    & docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[DIQQAT] Docker Desktop ishga tushmagan ko'rinadi." -ForegroundColor Yellow
        Write-Host "Docker Desktop dasturini ishga tushiring va bir necha soniyadan so'ng qayta urinib ko'ring." -ForegroundColor Yellow
        Write-Host "Docker Desktop ishga tushirilmoqda..." -ForegroundColor Cyan
        Start-Process "C:\Users\Veon Admin\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe" -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 5
    }
} catch {
    Write-Host "[XATO] Docker komandasi topilmadi." -ForegroundColor Red
}

# Docker Compose orqali konteynerni yig'ish va ishga tushirish
Write-Host "`nKonteyner yig'ilmoqda va ishga tushirilmoqda (docker compose up -d --build)..." -ForegroundColor Cyan
& docker compose up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[MUVAFFAQIYAT] Tizim Docker konteynerida muvaffaqiyatli ishga tushdi!" -ForegroundColor Green
    Write-Host "Swagger API hujjatlari: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "Salomatlik tekshiruvi:  http://localhost:8000/health" -ForegroundColor Cyan
} else {
    Write-Host "`n[OGOHLANTIRISH] Docker Desktop to'liq yuklangach, ushbu skriptni qayta ishga tushiring:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\run_docker.ps1" -ForegroundColor White
}
