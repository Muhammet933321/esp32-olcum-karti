# YAYIN (release) APK'si — kendi kalici anahtarinla imzali.
#
#   powershell -ExecutionPolicy Bypass -File mobil\araclar\surum_apk.ps1 -Depo <anahtar-deposu.jks>
#
# - Anahtar deposu DEPONUN DISINDA durur (ornegin calisma alaninin .yedek klasorunde). Dosya yoksa bu betik
#   olusturur: keytool parolayi KENDISI sorar (ekranda gorunmez). Sertifikaya kisisel bilgi YAZILMAZ
#   ("CN=Olcum Karti") — sertifika APK'nin icinde herkese acik durur.
# - Parola her calistirmada sorulur, diske YAZILMAZ; yalniz bu surecin ortam degiskeninde yasar.
# - Anahtar deposunu ve parolasini KAYBETME: ayni imza olmadan kurulu uygulama guncellenemez.
param(
    [Parameter(Mandatory = $true)][string]$Depo,
    [string]$Ad = "olcum-karti"
)
$ErrorActionPreference = "Stop"
$mobil = Split-Path -Parent $PSScriptRoot
$keytool = Join-Path $env:JAVA_HOME "bin\keytool.exe"
if (-not (Test-Path $keytool)) { throw "keytool bulunamadi: JAVA_HOME ayarli mi?" }

if (-not (Test-Path $Depo)) {
    Write-Host "Anahtar deposu yok, olusturuluyor: $Depo"
    Write-Host "keytool simdi YENI bir parola soracak (en az 6 karakter, iki kez). Bu parolayi sakla."
    $klasor = Split-Path -Parent $Depo
    if ($klasor -and -not (Test-Path $klasor)) { New-Item -ItemType Directory -Force $klasor | Out-Null }
    & $keytool -genkeypair -v -keystore $Depo -alias $Ad -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Olcum Karti"
    if ($LASTEXITCODE -ne 0) { throw "anahtar deposu olusturulamadi" }
}

$guvenli = Read-Host -AsSecureString "Anahtar deposu parolasi"
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($guvenli)
try {
    $env:OLCUM_IMZA_PAROLA = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}
$env:OLCUM_IMZA_DEPO = (Resolve-Path $Depo).Path
$env:OLCUM_IMZA_AD = $Ad
if (-not $env:ANDROID_HOME) { $env:ANDROID_HOME = Join-Path $env:LOCALAPPDATA "Android\Sdk" }

try {
    Push-Location $mobil
    npm run esitle
    if ($LASTEXITCODE -ne 0) { throw "panel paketlenemedi (npm run esitle)" }
    Push-Location (Join-Path $mobil "android")
    & .\gradlew.bat assembleRelease
    if ($LASTEXITCODE -ne 0) { throw "derleme basarisiz (parola yanlis olabilir)" }
    Pop-Location
    $apk = Join-Path $mobil "android\app\build\outputs\apk\release\app-release.apk"
    if (-not (Test-Path $apk)) { throw "imzali APK cikmadi: $apk" }
    Write-Host ""
    Write-Host "IMZALI APK HAZIR: $apk"
} finally {
    $env:OLCUM_IMZA_PAROLA = $null
    $env:OLCUM_IMZA_DEPO = $null
    Pop-Location
}
