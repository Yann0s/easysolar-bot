# Benchmark Windows — EasySolar (`llama-cpp-2` vs `fox` vs `ferrite` vs `Crane`)

Ce dossier permet de mesurer sur Windows (CPU seul ou GPU) les performances des 3 moteurs sélectionnés sur les 20 questions de [questions.txt](../questions.txt) avec le prompt système [consignes.txt](../consignes.txt).

## 1. Compiler les 3 moteurs sur Windows (prérequis : Rust `stable-msvc`, Git)

### A. `ferrumox/fox` (Rust + `llama.cpp`, Prefix Caching + Vulkan/CUDA/CPU)
```powershell
git clone --recurse-submodules https://github.com/ferrumox/fox
cd fox
cargo build --release
# Binaire : .\target\release\fox.exe
```

### B. `razancodes/ferrite` (Pur Rust CPU-native AVX2/AVX-512, Qwen3.5)
```powershell
git clone https://github.com/razancodes/ferrite
cd ferrite
cargo build --release
# Binaire : .\target\release\ferrite.exe
```

### C. `lucasjinreal/Crane` (Pur Rust sur Candle, zéro CMake, CPU/CUDA)
```powershell
git clone https://github.com/lucasjinreal/Crane
cd Crane
cargo build --release -p crane-serve
# Binaire : .\target\release\crane-serve.exe
```

## 2. Lancer le benchmark comparatif

Depuis la racine de `easysolar-bot` :
```powershell
.\bench\bench_windows.ps1 `
  -EasySolarExe ".\app\target\release\easysolar.exe" `
  -FoxExe "C:\chemin\vers\fox.exe" -FoxModel "LFM3-1.7B-easysolar-Q4_K_M" `
  -FerriteExe "C:\chemin\vers\ferrite.exe" -FerriteModel "qwen3.5-0.8b" `
  -CraneServeExe "C:\chemin\vers\crane-serve.exe" -CraneModel "qwen3.5-0.8b"
```

Tu peux aussi tester un seul moteur à la fois en ne passant que son paramètre (ex. `-FoxExe ...`).

## 3. Métriques collectées (`bench/metrics.jsonl`)
- **`cold_ttft_ms`** : latence avant le 1er token sur la question 1 (prefill complet du prompt système `consignes.txt`).
- **`warm_ttft_median_ms`** : médiane sur les questions 2 à 20 (mesure directe du gain de **prefix caching**).
- **`tps_median`** : vitesse de génération médiane (tokens/s).
- **`total_20q_s`** : temps total pour les 20 questions.
- **RAM pic (Mo)** : `PeakWorkingSet64` du processus serveur sous Windows.
