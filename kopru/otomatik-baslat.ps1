# Olcum karti PC uygulamasi - Windows acilisinda arka planda baslatma (4A, PC4).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File otomatik-baslat.ps1 -Kur
#   powershell -NoProfile -ExecutionPolicy Bypass -File otomatik-baslat.ps1 -Kaldir
#
# Baslangic klasorune bir kisayol koyar: pythonw.exe "<bu klasor>\pc.py" --sessiz
# (konsol yok, tarayici yok; cokerse iz %LOCALAPPDATA%\olcum-karti\arkaplan-hata.txt).
# Desen stok-takip'ten: "Elektronik Stok (arka plan).lnk".
#
# DIKKAT: kisayol BU calisma agacindaki pc.py'yi gosterir. Birden cok calisma
#   agaci varsa kurulumu kullanmak istediginiz agactan yapin (yol ekrana yazilir).
# DIKKAT: arka plandaki kopru kartin COM portunu TUTAR; tezgah araclari ve
#   yukle.py o sirada portu acamaz ("PC kopru bu portu kullaniyor - kapatin").
#
# -Klasor: Baslangic yerine baska bir klasore yaz (deneme icin).
# Yalniz ASCII: Windows PowerShell 5.1 BOM'suz dosyayi ANSI okur.
param(
    [switch]$Kur,
    [switch]$Kaldir,
    [string]$Klasor = ''
)
$ErrorActionPreference = 'Stop'

$ad = 'Olcum Karti PC (arka plan).lnk'
if (-not $Klasor) { $Klasor = [Environment]::GetFolderPath('Startup') }
$hedef = Join-Path $Klasor $ad
$pc = Join-Path $PSScriptRoot 'pc.py'

if ($Kaldir) {
    if (Test-Path -LiteralPath $hedef) {
        Remove-Item -LiteralPath $hedef -Force
        Write-Output "  Otomatik baslatma kapatildi: $hedef silindi."
    } else {
        Write-Output "  Otomatik baslatma zaten kapali."
    }
    Write-Output "  Su an calisan kopru durmaz: Gorev Yoneticisi > Ayrintilar > pythonw.exe."
    exit 0
}

if (-not $Kur) {
    Write-Output "Kullanim: otomatik-baslat.ps1 -Kur | -Kaldir"
    exit 2
}

# Gercek yorumlayiciyi bul. WindowsApps'teki python.exe bir "uygulama takma adi";
# kisayol hedefi olarak guvenilmez. sys.executable gercek yolu verir.
$exe = $null
foreach ($komut in @('py', 'python')) {
    if (Get-Command $komut -ErrorAction SilentlyContinue) {
        try {
            $exe = (& $komut -c 'import sys; print(sys.executable)' 2>$null | Select-Object -First 1)
        } catch { $exe = $null }
        if ($exe) { break }
    }
}
if (-not $exe) { throw 'Python bulunamadi (py / python). Once Python kurun.' }
$pyw = Join-Path (Split-Path -Parent $exe) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pyw)) { throw "pythonw.exe yok: $pyw" }
if (-not (Test-Path -LiteralPath $pc)) { throw "pc.py yok: $pc" }

New-Item -ItemType Directory -Force -Path $Klasor | Out-Null
$k = (New-Object -ComObject WScript.Shell).CreateShortcut($hedef)
$k.TargetPath = $pyw
$k.Arguments = '"' + $pc + '" --sessiz'
$k.WorkingDirectory = Split-Path -Parent $PSScriptRoot
$k.WindowStyle = 7
$k.Description = 'Olcum karti PC koprusu (arka plan)'
$k.Save()

Write-Output "  Otomatik baslatma kuruldu: $hedef"
Write-Output "    -> $pyw `"$pc`" --sessiz"
Write-Output "  Panel: http://olcum.localhost:8770 (bir sonraki oturum acilisindan itibaren)."
Write-Output "  Hemen baslatmak icin: kopru\PC Baslat.bat"
exit 0
