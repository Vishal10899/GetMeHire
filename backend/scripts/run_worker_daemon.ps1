# GlobalJobs Background Ingestion Worker Daemon Supervisor (Windows)
# Runs the standalone background ingestion worker in a supervised loop with auto-restart.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Split-Path -Parent $ScriptDir
$PythonExe = Join-Path $BackendDir "venv\Scripts\python.exe"
$LogFile = Join-Path $BackendDir "storage\worker.log"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  GlobalJobs Ingestion Worker Daemon (Supervised Mode)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "• Working Directory: $BackendDir"
Write-Host "• Python Executable: $PythonExe"
Write-Host "• Log Destination:   $LogFile"
Write-Host "• Press Ctrl+C to terminate the supervisor." -ForegroundColor Yellow
Write-Host "============================================================`n"

$RestartCount = 0

while ($true) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting Ingestion Worker process..." -ForegroundColor Green
    
    try {
        $Process = Start-Process -FilePath $PythonExe `
            -ArgumentList "-m app.worker --interval 300 --max-sources 10" `
            -WorkingDirectory $BackendDir `
            -RedirectStandardOutput $LogFile `
            -RedirectStandardError $LogFile `
            -NoNewWindow `
            -PassThru

        # Wait for the worker process to exit
        $Process.WaitForExit()
        $ExitCode = $Process.ExitCode

        if ($ExitCode -eq 0) {
            Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Worker exited cleanly (Code 0)." -ForegroundColor Yellow
            break
        } else {
            $RestartCount++
            Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Worker exited unexpectedly (Code $ExitCode). Restart #$RestartCount in 10s..." -ForegroundColor Red
            Start-Sleep -Seconds 10
        }
    } catch {
        Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Supervisor error: $_. Retrying in 15s..." -ForegroundColor Red
        Start-Sleep -Seconds 15
    }
}
