#Requires -Version 5.1
<#
.SYNOPSIS
    Wrapper CLI para document_generator en Windows PowerShell.
.DESCRIPTION
    Ejecuta plantillas/tareas.py usando el interprete Python aislado de .venv
    con codificacion UTF-8 habilitada.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$scriptTareas = Join-Path $PSScriptRoot "plantillas\tareas.py"

if (-not (Test-Path -Path $venvPython -PathType Leaf)) {
    Write-Host "[!] No se encontro el entorno virtual en .venv."
    Write-Host "[*] Ejecutando setup.ps1 para inicializar el entorno..."
    & (Join-Path $PSScriptRoot "setup.ps1")
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

$ErrorActionPreference = "Continue"
& $venvPython $scriptTareas @args
exit $LASTEXITCODE
