# GlobalJobs - Windows Task Scheduler Setup for Background Ingestion Worker
# Registers a scheduled task to launch the worker at system startup or periodically.

$TaskName = "GlobalJobsIngestionWorker"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Split-Path -Parent $ScriptDir
$PythonExe = Join-Path $BackendDir "venv\Scripts\python.exe"

Write-Host "Registering Windows Scheduled Task: $TaskName" -ForegroundColor Cyan
Write-Host "Executable: $PythonExe"
Write-Host "Arguments:  -m app.worker --single-run"

$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "-m app.worker --single-run" -WorkingDirectory $BackendDir
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15)
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Runs GlobalJobs background ingestion worker every 15 minutes." -Force

Write-Host "Task '$TaskName' registered successfully!" -ForegroundColor Green
