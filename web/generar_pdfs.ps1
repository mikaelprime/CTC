# Convierte las guías de web/guias/*.html a PDF en web/descargas/ usando
# Microsoft Edge sin ventana (viene instalado en Windows). Ejecutar después de
# editar cualquier guía:  & .\web\generar_pdfs.ps1
$ErrorActionPreference = "Stop"

$edge = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) { throw "No se encontró Microsoft Edge" }

$guias = @{
    "manual-usuario.html" = "CTC-Campus-Manual-de-Usuario.pdf"
    "manual-tecnico.html" = "CTC-Campus-Manual-Tecnico.pdf"
    "respaldos.html"      = "CTC-Campus-Respaldos.pdf"
}

foreach ($html in $guias.Keys) {
    $origen = Join-Path $PSScriptRoot "guias\$html"
    $destino = Join-Path $PSScriptRoot "descargas\$($guias[$html])"
    $url = "file:///" + ($origen -replace "\\", "/")
    Remove-Item $destino -ErrorAction SilentlyContinue
    # Edge escribe avisos inofensivos en stderr; no deben detener el script.
    $ErrorActionPreference = "Continue"
    & $edge --headless --disable-gpu --no-pdf-header-footer "--print-to-pdf=$destino" $url 2>&1 | Out-Null
    $ErrorActionPreference = "Stop"
    if (-not (Test-Path $destino)) { throw "No se pudo crear $destino" }
    Write-Output "Creado $destino"
}
