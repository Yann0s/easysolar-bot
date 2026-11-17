Set-Location C:\bench
$m = "C:\easysolar\models\LFM3-1.7B-easysolar-Q4_K_M.gguf",
     "models\gguf\Qwen3-1.7B-Q4_K_M.gguf",
     "models\gguf\Qwen3.5-2B-Q4_K_M.gguf",
     "models\gguf\LFM2.5-1.2B-Instruct-Q4_K_M.gguf"
$args_m = $m | ForEach-Object { "-m", $_ }
& llama\llama-bench.exe @args_m -p 1500 -n 300 -t 2,4,6 -r 3 -o md 2>$null | Tee-Object results_llamabench.md
"LLAMABENCH DONE"
