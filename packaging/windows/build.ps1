# Build Theme Studio for Windows. Produces, in dist\:
#   Theme Studio\                         the app folder (Theme Studio.exe + theme-studio.exe)
#   ThemeStudio-<ver>-windows-portable.zip that folder, zipped
#   ThemeStudio-<ver>-setup.exe           the installer (needs Inno Setup)
# Run from the repository:
#   powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
Set-Location (Resolve-Path (Join-Path $here "..\.."))

$version = (Select-String -Path "theme_studio\__init__.py" -Pattern '__version__ = "(.+)"').Matches[0].Groups[1].Value
Write-Host "== Theme Studio $version ==" -ForegroundColor Cyan

# 1. A clean build environment, separate from any pipx install
if (-not (Test-Path ".build-venv")) { py -3 -m venv .build-venv }
$py = Resolve-Path ".build-venv\Scripts\python.exe"
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet ".[gui]" pyinstaller
if ($LASTEXITCODE) { throw "pip install failed" }

# 2. The app folder
Write-Host "== PyInstaller ==" -ForegroundColor Cyan
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist\Theme Studio") { Remove-Item -Recurse -Force "dist\Theme Studio" }
& $py -m PyInstaller --noconfirm --distpath dist --workpath build "$here\theme-studio.spec"
if ($LASTEXITCODE) { throw "PyInstaller failed" }

# 3. Smoke test: the built command line must start
Write-Host "== Smoke test ==" -ForegroundColor Cyan
& "dist\Theme Studio\theme-studio.exe" list
if ($LASTEXITCODE) { throw "the built theme-studio.exe does not start" }

# 4. Portable zip
$zip = "dist\ThemeStudio-$version-windows-portable.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path "dist\Theme Studio" -DestinationPath $zip

# 5. Installer
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
          "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    Write-Warning "Inno Setup not found (winget install JRSoftware.InnoSetup): only the zip was made."
    exit 0
}
Write-Host "== Inno Setup ==" -ForegroundColor Cyan
& $iscc /Q "/DAppVersion=$version" "$here\theme-studio.iss"
if ($LASTEXITCODE) { throw "Inno Setup failed" }

Write-Host ""
Write-Host "Done:" -ForegroundColor Green
Get-ChildItem dist -File | ForEach-Object { "  {0}  ({1:N0} MB)" -f $_.FullName, ($_.Length / 1MB) }
