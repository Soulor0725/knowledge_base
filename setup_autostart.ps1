$ErrorActionPreference = "Stop"
$scriptPath = "C:\Users\Administrator\Documents\trae_projects\test\knowledge_base\app.py"
$appName = "KnowledgeBase"
$pythonPath = "python"

$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`"" -WorkingDirectory "C:\Users\Administrator\Documents\trae_projects\test\knowledge_base"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

try {
    Register-ScheduledTask -TaskName $appName -Action $action -Trigger $trigger -Settings $settings -Force
    Write-Host "Task created successfully!" -ForegroundColor Green
} catch {
    Write-Host "Failed: $_" -ForegroundColor Red
}
