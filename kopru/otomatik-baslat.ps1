# Olcum karti PC uygulamasi - Windows acilisinda arka planda baslatma (4A, PC4).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File otomatik-baslat.ps1 -Kur
#   powershell -NoProfile -ExecutionPolicy Bypass -File otomatik-baslat.ps1 -Kaldir
#
# Baslangic klasorune bir kisayol koyar: pythonw.exe "<bu klasor>\pc.py" --sessiz
# (konsol yok, tarayici yok; cokerse iz %LOCALAPPDATA%\olcum-karti\arkaplan-hata.txt).
# Desen stok-takip'ten: "Elektronik Stok (arka plan).lnk".
#
# DIKKAT: kisayol BU calisma agacindaki pc.py'yi gosterir. Kurulumu ANA calisma
#   agacindan (projeler/olcum-karti) yapin, ASLA gecici bir dal agacindan
#   (git worktree): agac silinince kopru iz birakmadan olur. Yol ekrana yazilir.
# DIKKAT: arka plandaki kopru kartin COM portunu TUTAR; tezgah araclari o sirada
#   portu acamaz ("PC kopru bu portu kullaniyor - kapatin"). yukle.py bu mesaji
#   vermez. Durdurmak icin: kopru\Kopruyu Durdur.bat (pc.py --durdur). Gorev
#   Yoneticisi'nden pythonw.exe OLDURMEYIN: stok-takip de pythonw ile calisiyor.
#
# -Klasor: Baslangic yerine baska bir klasore yaz (deneme icin).
# Yalniz ASCII: Windows PowerShell 5.1 BOM'suz dosyayi ANSI okur.
param(
    [switch]$Kur,
    [switch]$Kaldir,
    [string]$Klasor = '',
    [switch]$Zorla
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
    Write-Output "  Su an calisan kopru durmaz; durdurmak icin: kopru\Kopruyu Durdur.bat"
    exit 0
}

if (-not $Kur) {
    Write-Output "Kullanim: otomatik-baslat.ps1 -Kur | -Kaldir"
    exit 2
}

# Gecici dal agaci (git worktree) mi? Orada .git bir DOSYA, ana agacta dizin.
# Agac silinince kisayol olu bir pc.py'yi gosterir ve kopru iz birakmadan olur.
$gitYolu = Join-Path (Split-Path -Parent $PSScriptRoot) '.git'
if ((Test-Path -LiteralPath $gitYolu -PathType Leaf) -and -not $Zorla) {
    throw ("Bu bir gecici dal agaci (git worktree): $PSScriptRoot. Kisayolu ana calisma " +
           "agacindan (projeler\olcum-karti\kopru) kurun. Yine de istiyorsaniz: -Zorla")
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
