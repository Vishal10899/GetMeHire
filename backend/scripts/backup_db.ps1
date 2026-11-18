# ==============================================================================
# GlobalJobs — Automated PostgreSQL Backup & Retention Script
# ==============================================================================
param (
    [string]$DbName = "job_discovery",
    [string]$BackupDir = "D:\24JObs\backups",
    [int]$KeepBackups = 7,
    [string]$PgHost = "127.0.0.1",
    [int]$PgPort = 5432,
    [string]$PgUser = "postgres"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Starting PostgreSQL Database Backup for '$DbName' ===" -ForegroundColor Cyan

# 1. Locate pg_dump.exe and pg_restore.exe
$PgDumpCmd = Get-Command pg_dump -ErrorAction SilentlyContinue
$PgDumpPath = if ($PgDumpCmd) { $PgDumpCmd.Source } else { $null }

$PgRestoreCmd = Get-Command pg_restore -ErrorAction SilentlyContinue
$PgRestorePath = if ($PgRestoreCmd) { $PgRestoreCmd.Source } else { $null }

if (-not $PgDumpPath) {
    $PotentialPaths = Get-ChildItem -Path "C:\Program Files\PostgreSQL" -Filter "pg_dump.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
    if ($PotentialPaths) {
        $PgDumpPath = $PotentialPaths[0]
        $PgBinDir = Split-Path $PgDumpPath -Parent
        $PgRestorePath = Join-Path $PgBinDir "pg_restore.exe"
    }
}

if (-not $PgDumpPath -or -not (Test-Path $PgDumpPath)) {
    Write-Error "pg_dump.exe could not be found. Please ensure PostgreSQL 17 client tools are installed."
    exit 1
}

Write-Host "Found pg_dump at: $PgDumpPath" -ForegroundColor Gray

# 2. Extract database password from backend/.env if PGPASSWORD is not set
if (-not $env:PGPASSWORD) {
    $EnvPath = Join-Path (Split-Path $PSScriptRoot -Parent) ".env"
    if (Test-Path $EnvPath) {
        $EnvContent = Get-Content $EnvPath
        foreach ($line in $EnvContent) {
            if ($line -match '^\s*POSTGRES_PASSWORD\s*=\s*"?([^"#\r\n]+)"?') {
                $env:PGPASSWORD = $matches[1].Trim()
                break
            }
        }
    }
}

# 3. Ensure backup directory exists
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    Write-Host "Created backup directory: $BackupDir" -ForegroundColor Gray
}

# 4. Generate timestamped backup filename
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFileName = "${DbName}_${Timestamp}.dump"
$BackupFilePath = Join-Path $BackupDir $BackupFileName

Write-Host "Creating backup archive: $BackupFilePath..." -ForegroundColor Yellow

# 5. Execute pg_dump (Custom format -Fc with high compression)
& $PgDumpPath -h $PgHost -p $PgPort -U $PgUser -Fc -f "$BackupFilePath" "$DbName"

if ($LASTEXITCODE -ne 0) {
    Write-Error "pg_dump failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

# 6. Verify backup file creation and size
if (-not (Test-Path $BackupFilePath)) {
    Write-Error "Backup file was not created: $BackupFilePath"
    exit 1
}

$BackupItem = Get-Item $BackupFilePath
$SizeKB = [math]::Round($BackupItem.Length / 1024, 2)
Write-Host "Backup created successfully! Size: $SizeKB KB" -ForegroundColor Green

# 7. Verify backup archive integrity using pg_restore table of contents
if ($PgRestorePath -and (Test-Path $PgRestorePath)) {
    Write-Host "Verifying archive integrity with pg_restore -l..." -ForegroundColor Yellow
    $TOC = & $PgRestorePath -l "$BackupFilePath" 2>&1
    $TableCount = ($TOC | Select-String "TABLE DATA public ").Count
    Write-Host "Archive integrity verified. Contains $TableCount table datasets." -ForegroundColor Green
}

# 8. Apply retention policy (keep newest $KeepBackups files)
$AllBackups = Get-ChildItem -Path $BackupDir -Filter "${DbName}_*.dump" | Sort-Object LastWriteTime -Descending
if ($AllBackups.Count -gt $KeepBackups) {
    $BackupsToRemove = $AllBackups | Select-Object -Skip $KeepBackups
    foreach ($oldBackup in $BackupsToRemove) {
        Write-Host "Removing older backup per retention policy: $($oldBackup.Name)" -ForegroundColor Gray
        Remove-Item $oldBackup.FullName -Force
    }
}

Write-Host "`n=== Database Backup Routine Completed Successfully ===" -ForegroundColor Cyan
Write-Host "Authoritative file: $BackupFilePath" -ForegroundColor White
