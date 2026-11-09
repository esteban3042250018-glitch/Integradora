$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

python -m pip install -r .\requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudieron instalar las dependencias de compilacion.'
}

python -m PyInstaller --noconfirm --clean .\GestionInstitucional.spec
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller no pudo generar la aplicacion.'
}

$release = Join-Path $PSScriptRoot 'dist\GestionInstitucional'
$exampleEnv = Join-Path $PSScriptRoot '.env.example'
$releaseEnv = Join-Path $release '.env'
$sourceEnv = Join-Path $PSScriptRoot '.env'
if (-not (Test-Path -LiteralPath $sourceEnv)) {
    throw 'Falta .env junto al código. Configura las credenciales antes de compilar.'
}
$sourceSettings = @{}
foreach ($line in Get-Content -LiteralPath $sourceEnv) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=') {
        $sourceSettings[$matches[1]] = $line
    }
}
$clientIdLine = $sourceSettings['MICROSOFT_AUTH_API']
$clientId = if ($clientIdLine) { ($clientIdLine -split '=', 2)[1].Trim().Trim('"').Trim("'") } else { '' }
if (-not $clientId -or $clientId -match '^your-') {
    throw 'Configura MICROSOFT_AUTH_API con el ID de cliente de Microsoft Entra en .env antes de compilar.'
}

$requiredSettings = @(
    'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_PASSWORD',
    'POSTGRES_DB'
)
foreach ($key in $requiredSettings) {
    $line = $sourceSettings[$key]
    $value = if ($line) { ($line -split '=', 2)[1].Trim().Trim('"').Trim("'") } else { '' }
    if (-not $value) {
        throw "Configura $key en .env antes de compilar."
    }
}

$envLines = Get-Content -LiteralPath $exampleEnv | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=') {
        $key = $matches[1]
        if ($sourceSettings.ContainsKey($key)) {
            $sourceSettings[$key]
        } else {
            $_
        }
    } else {
        $_
    }
}
[System.IO.File]::WriteAllText(
    $releaseEnv,
    (($envLines -join "`r`n") + "`r`n"),
    (New-Object System.Text.UTF8Encoding($false))
)
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README.md') -Destination $release -Force

Write-Host ''
Write-Host 'Aplicacion lista:' (Join-Path $release 'GestionInstitucional.exe')
Write-Host 'El .env del paquete contiene credenciales. Protege esa carpeta y no la publiques.'
Write-Host 'El historial de documentos y las rutas de PDF se guardan localmente.'
