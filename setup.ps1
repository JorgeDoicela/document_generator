#Requires -Version 5.1
<#
.SYNOPSIS
    Inicializa y verifica el entorno document_generator en Windows (PowerShell).
.DESCRIPTION
    Crea el entorno virtual .venv, instala dependencias y el paquete editable,
    prepara .env si no existe, configura .githooks y ejecuta la verificacion y tests.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Set-Location -Path $PSScriptRoot

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $false)][string[]]$Arguments = @(),
        [switch]$AllowFailure,
        [switch]$Quiet
    )
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        if ($Quiet) {
            & $FilePath @Arguments *> $null
        } else {
            & $FilePath @Arguments
        }
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prev
    }
    if (-not $AllowFailure -and $code -ne 0) {
        throw "El comando '$FilePath $($Arguments -join ' ')' termino con codigo $code."
    }
    return $code
}

function Find-Python310 {
    $probe = "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
    if (Get-Command "py" -ErrorAction SilentlyContinue) {
        $code = Invoke-Native -FilePath "py" -Arguments @("-3", "-c", $probe) -AllowFailure -Quiet
        if ($code -eq 0) {
            return @("py", "-3")
        }
    }
    if (Get-Command "python" -ErrorAction SilentlyContinue) {
        $code = Invoke-Native -FilePath "python" -Arguments @("-c", $probe) -AllowFailure -Quiet
        if ($code -eq 0) {
            return @("python")
        }
    }
    throw "Se requiere Python 3.10 o superior instalado y disponible en PATH o mediante el launcher 'py'."
}

try {
    $nombreProyecto = Split-Path -Leaf $PSScriptRoot
    Write-Host "=== Inicializando entorno $nombreProyecto en Windows (PowerShell) ==="

    $pyCmd = Find-Python310
    $venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

    if (-not (Test-Path -Path $venvPython -PathType Leaf)) {
        Write-Host "[*] Creando entorno virtual en .venv..."
        $venvArgs = @()
        if ($pyCmd.Count -gt 1) {
            $venvArgs += $pyCmd[1..($pyCmd.Count - 1)]
        }
        $venvArgs += @("-m", "venv", ".venv")
        [void](Invoke-Native -FilePath $pyCmd[0] -Arguments $venvArgs)
    } else {
        Write-Host "[OK] Entorno virtual .venv ya existe."
    }

    Write-Host "[*] Instalando dependencias y paquete editable..."
    [void](Invoke-Native -FilePath $venvPython -Arguments @("-m", "pip", "install", "--quiet", "--upgrade", "pip"))
    [void](Invoke-Native -FilePath $venvPython -Arguments @("-m", "pip", "install", "--quiet", "-r", "requirements.txt"))
    [void](Invoke-Native -FilePath $venvPython -Arguments @("-m", "pip", "install", "--quiet", "-e", "."))

    $envFile = Join-Path $PSScriptRoot ".env"
    $envExample = Join-Path $PSScriptRoot ".env.example"
    if (-not (Test-Path -Path $envFile -PathType Leaf)) {
        Write-Host "[*] Creando .env inicial desde .env.example..."
        Copy-Item -Path $envExample -Destination $envFile -Force
        Write-Host "[AVISO] Se ha creado .env con datos de ejemplo. Editalo con tus datos personales."
    } else {
        Write-Host "[OK] Archivo .env presente."
    }

    if ((Test-Path -Path (Join-Path $PSScriptRoot ".git")) -and (Test-Path -Path (Join-Path $PSScriptRoot ".githooks"))) {
        if (Get-Command "git" -ErrorAction SilentlyContinue) {
            Write-Host "[*] Configurando hooks de seguridad git en .githooks..."
            [void](Invoke-Native -FilePath "git" -Arguments @("config", "core.hooksPath", ".githooks") -AllowFailure)
        }
    }

    Write-Host "[*] Verificando estado del kit y herramientas..."
    $verifyCode = Invoke-Native -FilePath $venvPython -Arguments @((Join-Path $PSScriptRoot "plantillas\tareas.py"), "verificar") -AllowFailure
    if ($verifyCode -ne 0) {
        Write-Host "[AVISO] La verificacion reporto elementos faltantes (por ejemplo, LibreOffice o .env incompleto)."
    }

    Write-Host ""
    Write-Host "[*] Ejecutando suite de pruebas unitarias..."
    [void](Invoke-Native -FilePath $venvPython -Arguments @("-m", "unittest"))

    Write-Host ""
    Write-Host "=== Entorno listo para trabajar en Windows ==="
    exit 0
} catch {
    Write-Error "Error durante la inicializacion: $_"
    exit 1
}
