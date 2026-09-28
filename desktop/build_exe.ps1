$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "No se encontró el entorno virtual en $python"
}

Push-Location $projectRoot
try {
    & $python -m PyInstaller --noconfirm --clean desktop\ctc-campus.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller terminó con código $LASTEXITCODE"
    }
    Copy-Item desktop\config.example.json dist\config.json -Force
    $releaseDir = Join-Path $projectRoot "dist\CTC-Campus-release"
    Remove-Item $releaseDir -Recurse -Force -ErrorAction SilentlyContinue
    New-Item $releaseDir -ItemType Directory | Out-Null
    Copy-Item dist\CTC-Campus.exe $releaseDir -Force
    Copy-Item dist\config.json $releaseDir -Force
    Compress-Archive -Path "$releaseDir\*" -DestinationPath "$projectRoot\dist\CTC-Campus.zip" -Force
    Write-Output "Aplicación creada en dist\CTC-Campus-release y dist\CTC-Campus.zip"
}
finally {
    Pop-Location
}