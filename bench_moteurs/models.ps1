Set-Location C:\bench
$hf = "uvx --from huggingface_hub hf download"
function dl($repo, $dir, $pat) { Invoke-Expression "$hf $repo $pat --local-dir models\$dir" }
dl unsloth/Qwen3-1.7B-GGUF gguf "Qwen3-1.7B-Q4_K_M.gguf"
dl unsloth/Qwen3.5-2B-GGUF gguf "Qwen3.5-2B-Q4_K_M.gguf"
dl LiquidAI/LFM2.5-1.2B-Instruct-GGUF gguf "LFM2.5-1.2B-Instruct-Q4_K_M.gguf"
dl Qwen/Qwen3-1.7B Qwen3-1.7B ""
dl Qwen/Qwen3.5-2B Qwen3.5-2B ""
dl LiquidAI/LFM2.5-1.2B-Instruct LFM2.5-1.2B-Instruct ""
dl Qwen/Qwen3-Embedding-0.6B Qwen3-Embedding-0.6B ""
"MODELS DONE"
