#!/usr/bin/env bash
# MODEL=models/autre.gguf ./run.sh ...   (choix du modèle, défaut LFM3-1.7B fine-tuné)
# ./run.sh questions.txt > resultats.md   (test en lot)
# ./run.sh                                (interactif : une question par ligne, Ctrl+D pour quitter)
D=$(dirname "$(readlink -f "$0")")
MODEL=${MODEL:-$D/models/LFM3-1.7B-easysolar-Q4_K_M.gguf}
"$D/bin/llama-b12183/llama-server" -m "$MODEL" -c 8192 --port 8089 >/dev/null 2>&1 &
SRV=$!
"$D/bin/llama-b12183/llama-server" -m "$D/models/Qwen3-Embedding-0.6B-Q8_0.gguf" --embedding --pooling last -c 8192 -b 8192 -ub 8192 --port 8090 >/dev/null 2>&1 &
EMB=$!; trap 'kill $SRV $EMB' EXIT
until curl -sf localhost:8089/health >/dev/null && curl -sf localhost:8090/health >/dev/null; do sleep 1; done
python3 -I "$D/rag.py" "$@"
