# ============================================================
#  GameMetrics S.A. - Inicio completo del sistema
#
#  Uso normal (primera vez incluye bootstrap comercio 04+05+06):
#    .\inicio.ps1
#
#  Forzar de nuevo tablas REALTIME + catálogo + promos (destructivo en 04):
#    .\inicio.ps1 -BootstrapCommerce
# ============================================================

param(
    [switch]$BootstrapCommerce
)

$BASE_URL = "http://localhost:4200"
$BOOTSTRAP_FILE = Join-Path $PSScriptRoot "etl\data\stage\commerce_bootstrapped.json"
$PHASE2_FILE    = Join-Path $PSScriptRoot "etl\data\stage\phase2_bootstrapped.json"
$PHASE3_FILE    = Join-Path $PSScriptRoot "etl\data\stage\phase3_bootstrapped.json"
$PHASE4_FILE    = Join-Path $PSScriptRoot "etl\data\stage\phase4_bootstrapped.json"
$PHASE5_FILE    = Join-Path $PSScriptRoot "etl\data\stage\phase5_bootstrapped.json"

function Write-Step($n, $msg) {
    Write-Host ""
    Write-Host "[$n] $msg" -ForegroundColor Cyan
}
function Write-OK($msg)   { Write-Host "    OK  $msg" -ForegroundColor Green }
function Write-Info($msg) { Write-Host "    ... $msg" -ForegroundColor Gray }
function Write-Fail($msg) { Write-Host "    ERR $msg" -ForegroundColor Red }
function Write-Warn($msg) { Write-Host "    !!  $msg" -ForegroundColor Yellow }

function Wait-URL($url, $label) {
    Write-Info "Esperando $label..."
    $intentos = 0
    while ($true) {
        try {
            $null = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            Write-OK "$label listo"
            return
        } catch {
            $intentos++
            if ($intentos % 5 -eq 0) { Write-Info "Aun esperando $label ($intentos intentos)..." }
            Start-Sleep -Seconds 3
        }
    }
}

function Start-ETLJob($endpoint, $jobKey, $label, $body = "{}") {
    Write-Info "Iniciando $label..."
    try {
        $null = Invoke-WebRequest -Uri "$BASE_URL/etl/$endpoint" -Method POST `
            -ContentType "application/json" -Body $body -UseBasicParsing -ErrorAction Stop
    } catch {
        Write-Fail "No se pudo iniciar $label : $_"
        exit 1
    }

    Start-Sleep -Seconds 2

    $dots = 0
    while ($true) {
        Start-Sleep -Seconds 5
        try {
            $r    = Invoke-WebRequest -Uri "$BASE_URL/etl/status" -UseBasicParsing -ErrorAction Stop
            $json = $r.Content | ConvertFrom-Json
            $st   = $json.$jobKey.status
            $msg  = $json.$jobKey.mensaje

            if ($st -eq "ok") {
                Write-OK "$label completado"
                return
            } elseif ($st -eq "error") {
                Write-Fail "$label fallo: $msg"
                exit 1
            } else {
                $dots++
                if ($dots % 4 -eq 0) { Write-Info "$label ejecutando... ($msg)" }
            }
        } catch {
            Write-Info "Esperando respuesta ETL..."
        }
    }
}

function Get-TargetSemana {
    try {
        $r = Invoke-WebRequest -Uri "$BASE_URL/etl/semanas-status" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        $semanas = ($r.Content | ConvertFrom-Json).semanas
        if ($semanas -and @($semanas).Count -gt 0) {
            return ($semanas | Measure-Object -Maximum).Maximum
        }
    } catch {
        Write-Info "No se pudo leer semanas cargadas, usando semana 1"
    }
    return 1
}

function Test-DatasetReady {
    $parquet = Join-Path $PSScriptRoot "etl\data\stage\videogames.parquet"
    if (Test-Path $parquet) { return $true }
    try {
        $r = Invoke-WebRequest -Uri "$BASE_URL/etl/semanas-status" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        $semanas = ($r.Content | ConvertFrom-Json).semanas
        return ($semanas -and @($semanas).Count -gt 0)
    } catch {
        return $false
    }
}

function Invoke-CommerceBootstrap {
    if ($BootstrapCommerce) {
        Write-Warn "BootstrapCommerce: el paso 04 BORRA y recrea tablas REALTIME"
        Write-Warn "(carrito, biblioteca y reseñas pueden perderse hasta que Kafka reindexe)"
    }

    Start-ETLJob "create-realtime-tables" "realtime" "Paso 04: Tablas REALTIME comercio"

    if (Test-DatasetReady) {
        $semana = Get-TargetSemana
        $catalogBody = "{`"semana`": $semana}"
        Start-ETLJob "reload-catalogo" "catalogo" "Paso 05: Catalogo comercial (semana $semana)" $catalogBody
    } else {
        Write-Warn "Dataset no cargado: se omite paso 05 (catalogo)"
        Write-Warn "Ejecuta en el Dashboard: 01 Cargar Semana, luego 05 Cargar catalogo"
        $semana = 1
    }

    Start-ETLJob "seed-promociones" "promociones" "Paso 06: Promociones"

    $dir = Split-Path $BOOTSTRAP_FILE -Parent
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    @{
        bootstrapped    = $true
        semana          = $semana
        catalog_loaded  = (Test-DatasetReady)
        at              = (Get-Date).ToString("o")
    } | ConvertTo-Json | Set-Content $BOOTSTRAP_FILE -Encoding UTF8
    Write-OK "Bootstrap comercio registrado ($BOOTSTRAP_FILE)"
}

# ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "   GameMetrics S.A.  -  Inicio del sistema " -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta

# PASO 1 - Detener Kafka y reiniciar ZooKeeper limpio
Write-Step 1 "Limpiando ZooKeeper y Kafka..."
docker stop kafka 2>$null
docker stop zookeeper 2>$null
Start-Sleep -Seconds 3
docker start zookeeper 2>$null

Write-Info "Esperando que ZooKeeper este listo..."
$zk = 0
while ($zk -lt 20) {
    Start-Sleep -Seconds 3
    $zk++
    $status = docker inspect --format="{{.State.Health.Status}}" zookeeper 2>$null
    if ($status -eq "healthy") {
        Write-OK "ZooKeeper listo"
        break
    }
    Write-Info "ZooKeeper iniciando... ($zk)"
}

Write-Info "Borrando nodo /brokers/ids/1 en ZooKeeper..."
docker exec zookeeper zkCli.sh -server localhost:2181 delete /brokers/ids/1 2>$null
Write-OK "Nodo broker limpiado (o no existia, esta bien)"
Start-Sleep -Seconds 2

# PASO 2 - Levantar Docker
Write-Step 2 "Levantando contenedores Docker..."
docker compose up -d
if ($LASTEXITCODE -ne 0) { Write-Fail "Error al levantar Docker"; exit 1 }
Write-OK "Contenedores iniciados"

# PASO 3 - Esperar servicios
Write-Step 3 "Esperando que el sistema este listo..."
Wait-URL "$BASE_URL" "Frontend"
Wait-URL "$BASE_URL/etl/status" "ETL API"
Wait-URL "$BASE_URL/api/games/count" "Backend"

# PASO 4 - Bootstrap comercio Fase 1 (solo primera vez o -BootstrapCommerce)
$bootstrapDone = Test-Path $BOOTSTRAP_FILE
$catalogDone = $false
if ($bootstrapDone) {
    try {
        $meta = Get-Content $BOOTSTRAP_FILE -Raw | ConvertFrom-Json
        $catalogDone = [bool]$meta.catalog_loaded
    } catch {
        $catalogDone = $false
    }
}

$needsFullBootstrap = $BootstrapCommerce -or (-not $bootstrapDone)
$needsCatalogOnly   = (-not $needsFullBootstrap) -and (-not $catalogDone) -and (Test-DatasetReady)

if ($needsFullBootstrap) {
    Write-Step 4 "Bootstrap comercio Fase 1 (ETL 04 + 05 + 06)..."
    Invoke-CommerceBootstrap
} elseif ($needsCatalogOnly) {
    Write-Step 4 "Completando catalogo comercial (ETL 05)..."
    $semana = Get-TargetSemana
    $catalogBody = "{`"semana`": $semana}"
    Start-ETLJob "reload-catalogo" "catalogo" "Paso 05: Catalogo comercial (semana $semana)" $catalogBody
    try {
        $meta = Get-Content $BOOTSTRAP_FILE -Raw | ConvertFrom-Json
        $meta.catalog_loaded = $true
        $meta.semana = $semana
        $meta.catalog_at = (Get-Date).ToString("o")
        $meta | ConvertTo-Json | Set-Content $BOOTSTRAP_FILE -Encoding UTF8
        Write-OK "Catalogo registrado en commerce_bootstrapped.json"
    } catch {
        Write-Warn "No se pudo actualizar commerce_bootstrapped.json"
    }
} else {
    Write-Info "Comercio ya configurado (omitido 04+05+06). Usa -BootstrapCommerce para repetir."
}

# PASO 5 - Bootstrap Fase 2 (wallet, cupones, regalos...)
$phase2Done = Test-Path $PHASE2_FILE
if ($BootstrapCommerce -or (-not $phase2Done)) {
    Write-Step 5 "Bootstrap Fase 2 (tablas + cupones)..."
    Start-ETLJob "create-phase2-tables" "phase2" "Paso 07: Tablas REALTIME Fase 2"
    Start-ETLJob "seed-coupons" "coupons" "Paso 08: Cupones demo (STEAM10, GAME20, WELCOME5)"
    $dir2 = Split-Path $PHASE2_FILE -Parent
    if (-not (Test-Path $dir2)) {
        New-Item -ItemType Directory -Path $dir2 -Force | Out-Null
    }
    @{
        bootstrapped = $true
        at           = (Get-Date).ToString("o")
        coupons      = @("STEAM10", "GAME20", "WELCOME5")
    } | ConvertTo-Json | Set-Content $PHASE2_FILE -Encoding UTF8
    Write-OK "Fase 2 registrada ($PHASE2_FILE)"
} else {
    Write-Info "Fase 2 ya configurada. Usa -BootstrapCommerce para recrear tablas Fase 2."
}

# PASO 6 - Bootstrap Fase 3 (launcher, logros, sesiones)
$phase3Done = Test-Path $PHASE3_FILE
if ($BootstrapCommerce -or (-not $phase3Done)) {
    Write-Step 6 "Bootstrap Fase 3 (distribucion digital)..."
    Start-ETLJob "create-phase3-tables" "phase3" "Paso 09: Tablas REALTIME Fase 3"
    $dir3 = Split-Path $PHASE3_FILE -Parent
    if (-not (Test-Path $dir3)) {
        New-Item -ItemType Directory -Path $dir3 -Force | Out-Null
    }
    @{
        bootstrapped = $true
        at           = (Get-Date).ToString("o")
    } | ConvertTo-Json | Set-Content $PHASE3_FILE -Encoding UTF8
    Write-OK "Fase 3 registrada ($PHASE3_FILE)"
} else {
    Write-Info "Fase 3 ya configurada."
}

# PASO 7 - Bootstrap Fase 4 (social, partners, soporte)
$phase4Done = Test-Path $PHASE4_FILE
if ($BootstrapCommerce -or (-not $phase4Done)) {
    Write-Step 7 "Bootstrap Fase 4 (ecosistema)..."
    Start-ETLJob "create-phase4-tables" "phase4" "Paso 10: Tablas REALTIME Fase 4"
    $dir4 = Split-Path $PHASE4_FILE -Parent
    if (-not (Test-Path $dir4)) {
        New-Item -ItemType Directory -Path $dir4 -Force | Out-Null
    }
    @{
        bootstrapped = $true
        at           = (Get-Date).ToString("o")
    } | ConvertTo-Json | Set-Content $PHASE4_FILE -Encoding UTF8
    Write-OK "Fase 4 registrada ($PHASE4_FILE)"
} else {
    Write-Info "Fase 4 ya configurada."
}

# PASO 8 - Bootstrap Fase 5 (foros, familia, API, búsquedas — 50 tablas)
$phase5Done = Test-Path $PHASE5_FILE
if ($BootstrapCommerce -or (-not $phase5Done)) {
    Write-Step 8 "Bootstrap Fase 5 (Steam completo)..."
    Start-ETLJob "create-phase5-tables" "phase5" "Paso 11: Tablas REALTIME Fase 5"
    $dir5 = Split-Path $PHASE5_FILE -Parent
    if (-not (Test-Path $dir5)) {
        New-Item -ItemType Directory -Path $dir5 -Force | Out-Null
    }
    @{
        bootstrapped = $true
        at           = (Get-Date).ToString("o")
        tables       = 50
    } | ConvertTo-Json | Set-Content $PHASE5_FILE -Encoding UTF8
    Write-OK "Fase 5 registrada — plataforma 50 tablas ($PHASE5_FILE)"
} else {
    Write-Info "Fase 5 ya configurada."
}

# LISTO
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "   Servicios listos!                       " -ForegroundColor Green
Write-Host "   Abre: http://localhost:4200             " -ForegroundColor Green
if (-not (Test-DatasetReady)) {
    Write-Host "   Pendiente: Dashboard paso 01 (dataset)  " -ForegroundColor Yellow
    Write-Host "   y paso 05 si no se cargo el catalogo    " -ForegroundColor Yellow
} else {
    Write-Host "   Tienda/comercio listo para usar         " -ForegroundColor Green
}
Write-Host "   Dashboard 04-06: solo reparacion manual   " -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
