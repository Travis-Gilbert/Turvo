# CI-only software OpenGL display support, not a Turvo bundle dependency.
# Uses the Mesa distribution also used by f3d-app/install-mesa-windows-action.
param([Parameter(Mandatory = $true)][string]$Destination)

$ErrorActionPreference = 'Stop'
if (-not $env:RUNNER_TEMP -or -not $env:GITHUB_ENV) {
    throw 'This helper must run inside GitHub Actions.'
}
$mesaDestination = (Resolve-Path -LiteralPath $Destination).Path
$mesaScratch = Join-Path $env:RUNNER_TEMP ('turvo-mesa-' + [Guid]::NewGuid())
New-Item -ItemType Directory -Path $mesaScratch | Out-Null
$mesaArchive = Join-Path $mesaScratch 'mesa.7z'
$mesaUrl = 'https://github.com/pal1000/mesa-dist-win/releases/download/26.2.0/mesa3d-26.2.0-release-msvc.7z'
$mesaSha256 = 'dcb2719ef346dab5b609fcb193a5f13cfc4b0502e3f4de1ad43d349477402f47'
Invoke-WebRequest -Uri $mesaUrl -OutFile $mesaArchive
if ((Get-FileHash -LiteralPath $mesaArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $mesaSha256) {
    throw 'Mesa archive checksum does not match the pinned release.'
}
$mesaExtractor = Join-Path $env:ProgramFiles '7-Zip/7z.exe'
& $mesaExtractor x $mesaArchive "-o$mesaScratch" -y 'x64/opengl32.dll' 'x64/libgallium_wgl.dll'
if ($LASTEXITCODE -ne 0) { throw 'Mesa extraction failed.' }
foreach ($mesaFile in @('opengl32.dll', 'libgallium_wgl.dll')) {
    Copy-Item -LiteralPath (Join-Path $mesaScratch "x64/$mesaFile") -Destination $mesaDestination
}
Add-Content -LiteralPath $env:GITHUB_ENV -Value 'GALLIUM_DRIVER=llvmpipe'
Write-Output 'Installed checksum-verified Mesa 26.2.0 for native CI only.'
