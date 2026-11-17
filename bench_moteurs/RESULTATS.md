# Benchmark des moteurs d'inférence sur la VM Windows

17/11/2026. Suite de `../etude_moteurs_inference.md`.

## Conditions

- VM Windows 10 sur ubu1 (`ssh test@192.168.10.35`) : Ryzen 5 5600G (Zen 3 : AVX2, pas d'AVX-512), 6 cœurs, 32 Go, CPU seul.
- Un moteur à la fois, machine au repos (téléchargements et compilations terminés avant les mesures).
- Prompt réel d'EasySolar (`system.txt` + `question.txt`) : consignes + pages 8, 21 et 25 du manuel, soit environ 1 450 à 1 530 tokens selon le tokenizer ; 300 tokens générés au plus, en greedy.
- Serveurs mesurés avec `bench_api.py` : streaming OpenAI, une requête de chauffe puis médiane de 3. Un préfixe unique par requête empêche le cache de prompt. Prefill = tokens du prompt / temps jusqu'au premier token.
- Versions : llama.cpp b12469 (build officiel `win-cpu-x64`), Crane HEAD du 17/11 (`cargo build --release`), ferrite HEAD (`target-cpu=native`), rai 0.2.5 (release officielle).

## 1. Référence llama.cpp (`llama-bench`, pp1500 / tg300, médiane de 3)

| Modèle | Threads | Prefill (tok/s) | Génération (tok/s) |
|---|---:|---:|---:|
| **LFM3-1.7B easysolar Q4_K_M** (le nôtre) | 2 | 99,6 | 20,6 |
| | 4 | 183,3 | **23,5** |
| | 6 | **251,4** | 21,5 |
| Qwen3-1.7B Q4_K_M | 4 | 165,8 | 22,4 |
| | 6 | 219,4 | 20,5 |
| Qwen3.5-2B Q4_K_M | 4 | 179,4 | 17,6 |
| | 6 | 237,1 | 16,3 |
| LFM2.5-1.2B Q4_K_M | 4 | 263,9 | 35,3 |
| | 6 | 366,9 | 32,5 |

Tableau complet : `llama_bench_brut.md`.

## 2. Moteurs comparés, même prompt, 6 threads

| Moteur / modèle | Tokens du prompt | Temps jusqu'au 1er token (s) | Prefill (tok/s) | Génération (tok/s) | Face à llama.cpp |
|---|---:|---:|---:|---:|---|
| llama.cpp / LFM3-1.7B easysolar | 1 419 | 5,8 | 245 | 20,2 | référence de l'appli |
| llama.cpp / Qwen3-1.7B | 1 530 | 7,1 | 216 | 16,3 | référence |
| **Crane** / Qwen3-1.7B (même GGUF) | 1 530 | 18,3 | 84 | 10,5 | prefill ×0,39, génération ×0,64 |
| **rai** / Qwen3-1.7B (4 bits rai) | 1 775 | 28,4 | 63 | 13,0 | prefill ×0,29, génération ×0,80 |
| llama.cpp / Qwen3.5-2B | 1 449 | 6,3 | 232 | 15,6 | référence |
| **Crane** / Qwen3.5-2B (même GGUF) | 1 451 | 103,0 | 14 | 6,6 | prefill ×0,06, génération ×0,42 |
| **ferrite** / Qwen3.5-2B (q4 ferrite) | 26 | | 1,2 | 0,28 | prefill ×0,005, génération ×0,02 |

Notes :

- **rai** n'a pas d'option pour régler les threads (réglage par défaut du moteur). Ses chiffres viennent de ses propres statistiques (`rai run`, 3 passes de 52 s chacune). Le prompt lui est arrivé avec des accents mal décodés par PowerShell 5.1 (d'où 1 775 tokens). Ça change le nombre de tokens, pas la vitesse par token.
- **Crane** charge Qwen3.5 en F32 sur CPU (log : `dtype=F32`). Sur Qwen3.5, il s'arrête de lui-même vers 90 tokens (EOS).
- **ferrite** tourne sur son chemin de repli `Scalar`, car la VM n'a pas d'AVX-512 VNNI. Le prompt EasySolar n'a rien rendu en 15 minutes (délai du script dépassé). Mesure faite à la place avec `ferrite run` sur un prompt de 26 tokens et 30 tokens générés : 130 s au total.
- Le module LFM de Crane (`crane-core/src/models/lfm2_5`) n'est **pas déclaré** dans `models/mod.rs`, et ni `crane-serve` ni `chat_cli` ne le proposent : impossible de tester LFM dans Crane sans écrire du code.

## 3. Conclusions

1. **Aucun des trois moteurs n'accélère l'appli sous Windows.** Sur le même GGUF, llama.cpp est 1,6 à 2,6 fois plus rapide que Crane (Qwen3) et jusqu'à 17 fois plus rapide (Qwen3.5). rai est plus lent sur les deux étapes. ferrite est inutilisable sans AVX-512 : c'est le cas de cette VM, et aussi des Intel de 12e à 14e génération et des Core Ultra, qu'on trouve sur la plupart des PC grand public.
2. Le critère fixé dans l'étude (au moins 1,5 fois plus rapide que llama.cpp, à qualité égale) n'est rempli par aucun. **On garde llama.cpp.**
3. **Gain mesuré à appliquer dans l'appli** : la génération plafonne à 4 threads (23,5 tok/s, puis 21,5 à 6), alors que le prefill monte jusqu'à 6 threads (183 puis 251 tok/s, +37 %). Aujourd'hui, `n_threads()` vaut `min(cœurs, 4)` pour les deux. Il faudrait garder `with_n_threads` à `min(cœurs, 4)` et passer `with_n_threads_batch` à tous les cœurs. Sur ce prompt, le prefill passerait d'environ 7,7 s à environ 5,6 s par question. La vectorisation des paragraphes, qui est aussi un traitement par lots, en profiterait aussi au démarrage. À confirmer dans l'appli elle-même.
4. Les autres pistes de l'étude (§ 6) restent les plus prometteuses : vecteurs précalculés, cache KV des consignes, llama.cpp à jour.

## Reproduire

Scripts dans ce dossier, à copier dans `C:\bench` sur la VM : `setup.ps1` (llama.cpp, rai, clones), `models.ps1` (modèles HF), `build.ps1` (ferrite, Crane), `llamabench.ps1`, `run_api.ps1` (serveurs + `bench_api.py`), `rai.ps1`. Conversions faites à la main :

    ferrite\target\release\ferrite.exe convert --hf models\Qwen3.5-2B -o models\qwen3.5-2b-q4.ferrite -q q4
    rai\rai-0.2.5-x86_64-pc-windows-msvc\rai.exe convert models\Qwen3-1.7B -o models\qwen3-1.7b-q4.raimodel
