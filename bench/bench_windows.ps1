# Benchmark Windows pour EasySolar : Baseline (easysolar.exe) vs Fox vs Ferrite vs Crane
# Usage : .\bench\bench_windows.ps1

param(
    [string]$EasySolarExe = ".\app\target\release\easysolar.exe",
    [string]$FoxExe = "",
    [string]$FoxModel = "LFM3-1.7B-easysolar-Q4_K_M",
    [string]$FerriteExe = "",
    [string]$FerriteModel = "qwen3.5-0.8b",
    [string]$CraneServeExe = "",
    [string]$CraneModel = "qwen3.5-0.8b"
)

$ErrorActionPreference = "Stop"
$Root = (Get-Location).Path
$MetricsFile = Join-Path $Root "bench\metrics.jsonl"
$ReportFile = Join-Path $Root "bench\resultats_benchmark_windows.md"

if (Test-Path $MetricsFile) { Remove-Item $MetricsFile -Force }

function Wait-HttpPort {
    param([int]$Port, [int]$TimeoutSec = 60)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $Port)
            $tcp.Close()
            return $true
        } catch {
            Start-Sleep -Milliseconds 300
        }
    }
    return $false
}

function Run-HttpBench {
    param(
        [string]$Name,
        [string]$Exe,
        [string[]]$Args,
        [int]$Port,
        [string]$Model
    )
    if ([string]::IsNullOrWhiteSpace($Exe) -or -not (Test-Path $Exe)) {
        Write-Host "[$Name] Ignoré (binaire non fourni ou introuvable : $Exe)" -ForegroundColor Yellow
        return $null
    }

    Write-Host "`n[$Name] Démarrage de $Exe ..." -ForegroundColor Cyan
    $proc = Start-Process -FilePath $Exe -ArgumentList $Args -PassThru -NoNewWindow
    try {
        if (-not (Wait-HttpPort -Port $Port -TimeoutSec 60)) {
            throw "[$Name] Le serveur n'a pas ouvert le port $Port dans les 60 s."
        }
        python .\bench\bench_http.py --name $Name --url "http://127.0.0.1:$Port/v1/chat/completions" --model $Model --root $Root --out $MetricsFile
        $proc.Refresh()
        $peakRamMb = [math]::Round($proc.PeakWorkingSet64 / 1MB, 1)
        Write-Host "[$Name] RAM pic : $peakRamMb Mo" -ForegroundColor Green
        return $peakRamMb
    } finally {
        if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    }
}

$ramStats = @{}

# 1. Baseline : easysolar.exe (llama-cpp-2)
if (Test-Path $EasySolarExe) {
    Write-Host "`n[baseline] Exécution de $EasySolarExe questions.txt ..." -ForegroundColor Cyan
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $p = Start-Process -FilePath $EasySolarExe -ArgumentList "questions.txt" -PassThru -Wait -NoNewWindow -RedirectStandardOutput "bench\baseline_out.txt"
    $sw.Stop()
    $baselineSec = [math]::Round($sw.Elapsed.TotalSeconds, 2)
    Write-Host "[baseline] Terminé en $baselineSec s" -ForegroundColor Green
} else {
    Write-Host "[baseline] $EasySolarExe introuvable, ignoré." -ForegroundColor Yellow
    $baselineSec = "N/A"
}

# 2. Fox (ferrumox/fox)
$ramStats["fox"] = Run-HttpBench -Name "fox" -Exe $FoxExe -Args @("serve", "--port", "8080") -Port 8080 -Model $FoxModel

# 3. Ferrite (razancodes/ferrite)
$ramStats["ferrite"] = Run-HttpBench -Name "ferrite" -Exe $FerriteExe -Args @("serve", "--port", "8081", "--model", $FerriteModel) -Port 8081 -Model $FerriteModel

# 4. Crane (lucasjinreal/Crane)
$ramStats["crane"] = Run-HttpBench -Name "crane" -Exe $CraneServeExe -Args @("--port", "8082", "--model", $CraneModel) -Port 8082 -Model $CraneModel

Write-Host "`nBenchmark terminé. Résultats bruts dans $MetricsFile" -ForegroundColor Cyan
