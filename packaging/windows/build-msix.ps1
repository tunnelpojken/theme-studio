# Pack the built app folder as an MSIX for the Microsoft Store. Run build.ps1 first.
# Produces, in dist\:
#   ThemeStudio-<ver>.msix         unsigned: upload this to Partner Center (the Store signs it)
#   ThemeStudio-<ver>-test.msix    with -Test: signed with a local test certificate, to install in a VM
# Needs the Windows SDK (makeappx, makepri, signtool):  winget install Microsoft.WindowsSDK.10.0.26100
#   powershell -ExecutionPolicy Bypass -File packaging\windows\build-msix.ps1 [-Test]
# -Test makes (once) a self-signed certificate named after the Store publisher and trusts it on
# this machine, which needs an admin PowerShell the first time.
param([switch]$Test)
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
Set-Location (Resolve-Path (Join-Path $here "..\.."))

$version = (Select-String -Path "theme_studio\__init__.py" -Pattern '__version__ = "(.+)"').Matches[0].Groups[1].Value
$id = Get-Content "$here\msix\identity.json" -Raw | ConvertFrom-Json

$app = "dist\Theme Studio"
if (-not (Test-Path "$app\Theme Studio.exe")) { throw "No ${app}: run build.ps1 first." }

# The SDK tools, newest SDK first
$bin = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\10.*\x64" -Directory -ErrorAction SilentlyContinue |
       Sort-Object Name -Descending | Where-Object { Test-Path "$($_.FullName)\makeappx.exe" } | Select-Object -First 1
if (-not $bin) { throw "Windows SDK not found (winget install Microsoft.WindowsSDK.10.0.26100)." }
$makeappx, $makepri, $signtool = "makeappx", "makepri", "signtool" | ForEach-Object { Join-Path $bin.FullName "$_.exe" }

# 1. Stage: the app folder, the logos and the filled-in manifest
Write-Host "== Theme Studio $version as MSIX ==" -ForegroundColor Cyan
$stage = "build\msix"
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory $stage | Out-Null
Copy-Item "$app\*" $stage -Recurse
Copy-Item "$here\msix\Assets" "$stage\Assets" -Recurse
$manifest = (Get-Content "$here\msix\AppxManifest.xml" -Raw) `
    -replace "@NAME@", $id.Name -replace "@PUBLISHER@", $id.Publisher `
    -replace "@PUBLISHER_DISPLAY_NAME@", $id.PublisherDisplayName `
    -replace "@DISPLAY_NAME@", $id.DisplayName -replace "@VERSION@", "$version.0"   # the Store wants x.y.z.0
[IO.File]::WriteAllText((Resolve-Path $stage).Path + "\AppxManifest.xml", $manifest, [Text.UTF8Encoding]::new($false))

# 2. resources.pri, so Windows picks the right logo size (scale-100/200, targetsize-*)
Push-Location $stage
& $makepri createconfig /cf ..\priconfig.xml /dq en-US /o | Out-Null
& $makepri new /pr . /cf ..\priconfig.xml /mn AppxManifest.xml /of resources.pri /o | Out-Null
if ($LASTEXITCODE) { Pop-Location; throw "makepri failed" }
Pop-Location

# 3. Pack
$msix = "dist\ThemeStudio-$version.msix"
& $makeappx pack /d $stage /p $msix /o | Out-Null
if ($LASTEXITCODE) { throw "makeappx failed" }
Write-Host "Store upload: $msix" -ForegroundColor Green

# 4. A signed copy for testing in the VM
if ($Test) {
    $cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq $id.Publisher } | Select-Object -First 1
    if (-not $cert) {
        $cert = New-SelfSignedCertificate -Type Custom -Subject $id.Publisher -KeyUsage DigitalSignature `
            -FriendlyName "Theme Studio test signing" -CertStoreLocation Cert:\CurrentUser\My `
            -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
    }
    if (-not (Get-ChildItem Cert:\LocalMachine\TrustedPeople | Where-Object Thumbprint -eq $cert.Thumbprint)) {
        $cer = "build\theme-studio-test.cer"
        Export-Certificate -Cert $cert -FilePath $cer | Out-Null
        Import-Certificate -FilePath $cer -CertStoreLocation Cert:\LocalMachine\TrustedPeople | Out-Null   # needs admin
    }
    $testMsix = "dist\ThemeStudio-$version-test.msix"
    Copy-Item $msix $testMsix -Force
    & $signtool sign /fd SHA256 /sha1 $cert.Thumbprint $testMsix | Out-Null
    if ($LASTEXITCODE) { throw "signtool failed" }
    Write-Host "Test package: $testMsix  (install: Add-AppxPackage $testMsix)" -ForegroundColor Green
}
