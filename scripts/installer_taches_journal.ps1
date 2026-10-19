# Installe les deux tâches planifiées du journal personnalisé (du lundi au vendredi) :
#   « Signal Matin - génération »  à 4 h 00 : sort le PC de veille, génère le PDF
#   « Signal Matin - impression »  à 7 h 00 : imprime le PDF en recto verso
# Usage (PowerShell, dans le dossier signal-matin) :
#   powershell -ExecutionPolicy Bypass -File scripts\installer_taches_journal.ps1
param(
    [string]$HeureGeneration = "04:00",
    [string]$HeureImpression = "07:00",
    [switch]$Desinstaller
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Lanceur = Join-Path $PSScriptRoot "lancer_journal.ps1"
$Jours = @("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
$Taches = @{
    "Signal Matin - generation" = @{ Heure = $HeureGeneration; Etape = "generation"; Limite = 3 }
    "Signal Matin - impression" = @{ Heure = $HeureImpression; Etape = "impression"; Limite = 1 }
}

if ($Desinstaller) {
    foreach ($Nom in $Taches.Keys) {
        Unregister-ScheduledTask -TaskName $Nom -Confirm:$false -ErrorAction SilentlyContinue
    }
    Write-Host "Tâches du journal supprimées."
    exit 0
}

foreach ($Nom in $Taches.Keys) {
    $T = $Taches[$Nom]
    $Action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Lanceur`" -Etape $($T.Etape)" `
        -WorkingDirectory $Root
    $Declencheur = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Jours -At $T.Heure
    $Reglages = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Hours $T.Limite)
    Register-ScheduledTask -TaskName $Nom -Action $Action -Trigger $Declencheur -Settings $Reglages `
        -Description "Journal Signal Matin ($($T.Etape))" -Force | Out-Null
    Write-Host "OK  $Nom : du lundi au vendredi à $($T.Heure)"
}

# La sortie de veille exige que Windows autorise les « minuteurs de réveil ».
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 | Out-Null
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 | Out-Null
powercfg /SETACTIVE SCHEME_CURRENT | Out-Null
Write-Host "OK  Minuteurs de réveil autorisés."
Write-Host ""
Write-Host "Le soir, mettez le PC en VEILLE (pas en arrêt complet) et laissez-le branché."
Write-Host "Journaux d'exécution : $Root\output\logs"
