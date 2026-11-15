#!/usr/bin/env bash
# Chaîne complète sur Mac : environnement -> données -> LoRA -> fusion -> GGUF Q4_K_M -> test des 20 questions.
# Prérequis : brew install llama.cpp poppler uv       Usage : sft/train_mac.sh [--smoke]
set -euo pipefail
D=$(dirname "$(readlink -f "$0")"); P=$(dirname "$D"); cd "$P"

# 1. Environnement Python isolé, versions de la recette Liquid AI (cookbook lfm3_sft_with_trl)
[ -d .venv ] || uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -q "torch==2.14.1" "transformers==5.20.2" "trl==1.16.0" \
  "peft==0.21.2" "accelerate==1.15.0" "datasets==5.1.0" "safetensors==0.8.0"

# 2. Données (prompts de production) puis entraînement
bin/llama-b12183/llama-server -m models/Qwen3-Embedding-0.6B-Q8_0.gguf --embedding --pooling last -c 8192 -b 8192 -ub 8192 --port 8090 >/dev/null 2>&1 &
EMB=$!; until curl -sf localhost:8090/health >/dev/null; do sleep 1; done  # rag.search en a besoin
.venv/bin/python -I sft/build_sft.py; kill $EMB
.venv/bin/python sft/train.py "$@"
[ "${1:-}" = "--smoke" ] && { echo "Smoke test OK"; exit 0; }

# 3. Conversion GGUF avec le script de llama.cpp (même dépôt que les binaires, LFM3 pris en charge)
[ -d sft/llama.cpp ] || git clone --depth 1 https://github.com/ggml-org/llama.cpp sft/llama.cpp
uv pip install --python .venv/bin/python -q -e sft/llama.cpp/gguf-py
.venv/bin/python sft/llama.cpp/convert_hf_to_gguf.py sft/out/merged --outtype bf16 --outfile sft/out/LFM3-1.7B-easysolar-BF16.gguf
llama-quantize sft/out/LFM3-1.7B-easysolar-BF16.gguf models/LFM3-1.7B-easysolar-Q4_K_M.gguf Q4_K_M

# 4. Même test que les autres modèles
MODEL=models/LFM3-1.7B-easysolar-Q4_K_M.gguf ./run.sh questions.txt > resultats_rag_LFM3-1.7B_sft.md
echo "-> resultats_rag_LFM3-1.7B_sft.md"
