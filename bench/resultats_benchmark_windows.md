# Résultats du Benchmark Windows (`W10OFFICE`)

**Machine de test :** Windows 10 VM (`W10OFFICE`), AMD Ryzen 5 5600G (6 cœurs / 6 threads, AVX2, **sans AVX-512**), 32 Go RAM, **CPU-only** (pas de GPU hardware).
**Jeu de test :** 20 questions de [questions.txt](../questions.txt) avec [consignes.txt](../consignes.txt).

## Tableau comparatif

| Moteur | Modèle | Démarrage | Total 20 Q | TTFT Q1 (cold) | TTFT Q2–Q20 (médiane) | Décodage (médiane) | RAM pic | Statut |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Baseline (`EasySolar.exe` / `llama-cpp-2`)** | `LFM3-1.7B-easysolar-Q4_K_M.gguf` + `Qwen3-Emb-0.6B` | ~0,6 s (emb) | **255,47 s** | — | — | — | — | OK (référence) |
| **`ferrumox/fox`** (`llama.cpp` + Rust) | `Qwen3.5-0.8B-Q4_K_M.gguf` | **1,82 s** | **67,95 s** | **2 681 ms** | **2 549 ms** | **35,39 tok/s** | 7 144 Mo | OK (`LFM3` non supporté par son sous-module `llama.cpp`) |
| **`lucasjinreal/Crane`** (`crane-serve` / Candle) | `Qwen3.5-0.8B` (`--quant q4k --cpu`) | 42,96 s | 647,57 s | 28 059 ms | 28 444 ms | 6,40 tok/s | 2 839 Mo | OK mais ~5,5× plus lent que `fox` sur CPU |
| **`razancodes/ferrite`** (Pur Rust) | `qwen3.5-0.8b-q4.ferrite` | 1,33 s | *Timeout (>120 s sur Q1)* | — | — | — | 819 Mo | **Bloqué en mode `Scalar`** (pas de noyaux AVX2, AVX-512 VNNI requis) |

## Enseignements clés pour `EasySolar` Windows

1. **Aucun moteur "pur Rust" testé ne bat `llama.cpp` sur CPU Windows grand public :**
   * **`ferrite`** n'implémente que des noyaux **AVX-512 VNNI** (`src/kernels/avx512.rs`) et bascule en **Scalar** sur Ryzen 5 5600G (et sur la majorité des CPU Windows grand public sans AVX-512).
   * **`Crane` (Candle)** compile proprement sans CMake, mais reste à **6,4 tok/s** et **28 s de TTFT** sur CPU contre **35,4 tok/s** et **2,5 s de TTFT** pour `fox` (`llama.cpp`).
2. **`ferrumox/fox` confirme la supériorité du socle `llama.cpp` sur CPU Windows**, mais :
   * Son sous-module `llama.cpp` actuel est trop ancien pour **`LFM3-1.7B`**.
   * Sur `Qwen3.5` (architecture hybride récurrente), `fox` alloue ~7,1 Go de RAM par défaut (à cause de `--cache-ram 2048` implicite et des snapshots d'état récurrent).
3. **Recommandation directe pour `easysolar.exe` (`app/src/main.rs`) :**
   * **Garder `llama-cpp-2` (`llama.cpp >= 1.0.0`)** qui supporte déjà `LFM3-1.7B`, démarre en **0,6 s** (embeddings inclus) et consomme peu de RAM.
   * **Supprimer `ctx.clear_kv_cache()` à chaque question** dans `generate()` (`app/src/main.rs`) pour réutiliser le préfixe `consignes.txt` en KV cache (comme le fait `fox`).
   * **Évaluer un passage éventuel à `Qwen3.5-0.8B` fine-tuné** si la qualité suffit : sur `llama.cpp` CPU, il descend à **~68 s pour 20 questions** (~3,7× plus rapide que les **255,47 s** actuelles avec `LFM3-1.7B`).

## Évaluation post-SFT (`Qwen3.5-0.8B-easysolar-Q4_K_M` + Prefix KV Cache)

Fine-tuning LoRA 2 passes (`sft/train_qwen35.py`, `eval_loss = 0.633` à la passe 1 / `0.639` à la passe 2) converti en GGUF `Q4_K_M` (**494 Mo**, commit `cd959bae` compatible `llama-cpp-rs`) et testé directement dans `easysolar.exe` sur `W10OFFICE` :

| Configuration | Total 20 Q (CPU) | Score qualité | Taille modèle | Remarque |
| :--- | :---: | :---: | :---: | :--- |
| `LFM3-1.7B-easysolar-Q4_K_M` (baseline) | **255,47 s** | ~17/20 | ~1,0 Go | Référence |
| `Qwen3.5-0.8B-easysolar-Q4_K_M` (sans prefix cache) | **193,78 s** | **18/20** | **494 Mo** | **-24,1 %** temps, 0 hallucination, tous refus OK |
| `Qwen3.5-0.8B-easysolar-Q4_K_M` (avec `clear_kv_cache_seq`) | **192,35 s** | **18/20** | **494 Mo** | `0/N` tokens réutilisés (architecture hybride récurrente DeltaNet) |

* **Conclusion :** Le passage au modèle fine-tuné `Qwen3.5-0.8B-easysolar-Q4_K_M` apporte **-24,7 % de temps d'exécution** sur CPU Windows et **18/20** en qualité (sortie dans [qwen35_sft_windows_out.md](qwen35_sft_windows_out.md)). Le Prefix KV Cache (`clear_kv_cache_seq`) est inopérant (`0` tokens réutilisés) sur les modèles hybrides récurrents (`LFM3` et `Qwen3.5`).

