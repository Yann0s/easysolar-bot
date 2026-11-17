# Lance chaque serveur l'un après l'autre, mesure avec bench_api.py, puis l'arrête.
Set-Location C:\bench
$env:RAYON_NUM_THREADS = "6"
$runs = @(
  @{ l = "llama.cpp / LFM3-1.7B easysolar Q4_K_M"; exe = "llama\llama-server.exe"; a = "-m C:\easysolar\models\LFM3-1.7B-easysolar-Q4_K_M.gguf -t 6 -c 8192 --port 8090" },
  @{ l = "llama.cpp / Qwen3-1.7B Q4_K_M";          exe = "llama\llama-server.exe"; a = "-m models\gguf\Qwen3-1.7B-Q4_K_M.gguf -t 6 -c 8192 --port 8090" },
  @{ l = "llama.cpp / Qwen3.5-2B Q4_K_M";          exe = "llama\llama-server.exe"; a = "-m models\gguf\Qwen3.5-2B-Q4_K_M.gguf -t 6 -c 8192 --port 8090" },
  @{ l = "Crane / Qwen3-1.7B Q4_K_M";              exe = "Crane\target\release\crane-serve.exe"; a = "--cpu -m models\gguf\Qwen3-1.7B-Q4_K_M.gguf --model-type qwen3 --host 127.0.0.1 -p 8090" },
  @{ l = "Crane / Qwen3.5-2B Q4_K_M";              exe = "Crane\target\release\crane-serve.exe"; a = "--cpu -m models\gguf\Qwen3.5-2B-Q4_K_M.gguf --model-type qwen3_5 --host 127.0.0.1 -p 8090" },
  @{ l = "ferrite / Qwen3.5-2B q4";                exe = "ferrite\target\release\ferrite.exe"; a = "serve -m models\qwen3.5-2b-q4.ferrite --host 127.0.0.1 --port 8090" }
)
foreach ($r in $runs) {
  $log = "log_" + ($r.l -replace '[^A-Za-z0-9]', '_') + ".txt"
  $p = Start-Process -FilePath $r.exe -ArgumentList $r.a -PassThru -NoNewWindow -RedirectStandardOutput $log -RedirectStandardError "$log.err"
  $ok = $false
  for ($i = 0; $i -lt 150 -and -not $p.HasExited; $i++) {
    try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8090/v1/models -TimeoutSec 2 | Out-Null; $ok = $true; break } catch { Start-Sleep 2 }
  }
  if ($ok) { uv run --no-project python bench_api.py http://127.0.0.1:8090 $r.l 3 2>> reponses.txt }
  else { "| $($r.l) | ECHEC demarrage (voir $log) |" }
  if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
  Start-Sleep 3
}
"API DONE"
