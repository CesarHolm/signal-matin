# Lance une étape du journal personnalisé et garde une trace dans output\logs.
#   -Etape generation : collecte, IA, PDF (tâche de 4 h)
#   -Etape impression : impression recto verso du PDF du jour (tâche de 7 h)
param(
    [ValidateSet("generation", "impression")]
    [string]$Etape = "generation"
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { (Get-Command python).Source }

$Logs = Join-Path $Root "output\logs"
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
$Journal = Join-Path $Logs ("{0:yyyy-MM-dd}-{1}.log" -f (Get-Date), $Etape)

$Commande = if ($Etape -eq "generation") { "journal" } else { "journal-imprimer" }
"=== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') : $Commande ===" | Out-File -Append -Encoding utf8 $Journal
$env:PYTHONIOENCODING = "utf-8"
& $Python (Join-Path $Root "main.py") $Commande *>> $Journal
$Code = $LASTEXITCODE
"=== fin (code $Code) ===" | Out-File -Append -Encoding utf8 $Journal
exit $Code
