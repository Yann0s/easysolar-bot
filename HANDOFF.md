# EasySolar bot — état du projet (16/11/2026)

Assistant de support en français pour l'EasySolar 1600 (manuel Victron), petit LLM local + RAG, à packager ensuite en application autonome (Rust).

## Résultats des tests (20 questions, `questions.txt`, notés à la main)
| Montage | Score | Remarque |
|---|---|---|
| Manuel entier dans le prompt, LFM2.5-1.2B | ~3/20 | 2 réponses dangereuses → abandonné |
| RAG BM25, LFM2.5-1.2B | 13/20 | 0 chiffre inventé, comprend mal |
| RAG BM25, LFM2-2.6B | 14/20 | inverse le tableau des câbles (dangereux) |
| RAG BM25, LFM3-1.7B sans raisonnement | 14/20 | 0 chiffre inventé, réponses brouillonnes |
| RAG BM25, LFM3-1.7B avec raisonnement | 10/10 répondues, 10 vides | parfait mais ~100 s/question |
| RAG BM25, LFM3-1.7B + LoRA | ~16/20 | réponses propres et citées ; rate phases de charge, 2e batterie |
| **RAG embeddings, LFM3-1.7B + LoRA** | **~17/20** | **montage actuel**, 40 s pour 20 questions ; rate 2e batterie (page 12 non trouvée), fin d'absorption solaire (mélange avec le chargeur secteur) ; DIP et câbles incomplets |
| RAG embeddings, LoRA réentraîné sur extraits embeddings | ~17/20 | **pas retenu** : invente sur « LED Inverter clignote » et une « annexe A, point S » ; perte dev remonte après la 1re passe (0,60 → 0,63) → `models/LFM3-1.7B-easysolar-emb-Q4_K_M.gguf`, `resultats_rag_emb_sft-emb.md` |
| LFM3-VL-2B pour transcrire les schémas | ✗ | se trompe sur les liaisons (borne 2/10 inversées) → abandonné |

Les scores avant le 15/11 comptaient faux le refus sur « LED Inverter clignote » : vérifié sur le PDF (pages 8-9), aucun état ne fait clignoter Inverter, le refus est la bonne réponse.

Recherche seule (page source dans le top 3, 153 questions de `sft/qa.py`) : BM25 108, embeddings par page 115, **embeddings par paragraphe 126**, fusion BM25 + paragraphes 127 (pas retenue).

## Fichiers
- `pages_corrigees/` : 16 pages transcrites à la main (tableaux, pictogrammes LED, annexes A–D, interrupteur rotatif p24).
- `build_manual.sh [pdf]` → `manuel_fr.md` (pages FR 1–29 + annexes A–D).
- `rag.py` : embeddings Qwen3-Embedding-0.6B (port 8090, un vecteur par paragraphe, 103 paragraphes calculés au démarrage en ~4 s), top 3 pages, puis llama-server (port 8089). `consignes.txt` : prompt système.
- `run.sh [questions.txt]` : lance les deux serveurs ; `MODEL=models/x.gguf ./run.sh` ; sans argument = interactif.
- `models/` : `LFM3-1.7B-easysolar-Q4_K_M.gguf` (fine-tuné) et `Qwen3-Embedding-0.6B-Q8_0.gguf`.
- `sft/qa.py` : 171 paires de référence (18 refus) ; `sft/build_sft.py` → `sft/train.jsonl` / `sft/dev.jsonl` ; `sft/train_mac.sh [--smoke]` : chaîne complète LoRA → GGUF → test (TRL + PEFT sur MPS, ~1 h ; mlx-lm ne gère pas LFM3).
- `models/LFM3-1.7B-easysolar-Q4_K_M.gguf` = modèle retenu (copie : `-bm25`).
- `resultats_rag_emb_sft.md` : sortie du test du montage actuel (Python) ; `resultats_rust_linux_gpu.md` : même test avec l'appli Rust sous Linux.
- `app/` : application Rust (llama-cpp-2), voir ci-dessous.

## Application Rust (`app/`)
- Un binaire : manuel et consignes compilés dedans, modèles lus dans `models/` à côté de l'exe (ou `$EASYSOLAR_MODELS`). `easysolar` = mode interactif avec invite « > » (Ctrl+D pour quitter), `easysolar questions.txt` = lot, `--search` = pages seulement, `EASYSOLAR_LOG=1` = messages llama.cpp.
- Interface graphique (16/11) : `easysolar --ui` sert une page HTML aux couleurs Victron (`app/src/ui.html`, compilée dans le binaire) sur `127.0.0.1:8765` (port libre sinon), une requête à la fois. Bouton Quitter = `POST /quit`.
  Mac : fenêtre native WKWebView reprise de Pulsefy (`app/native/macos_webview.m`, compilée par `app/build.rs`) ; `app/bundle_mac.sh` construit `EasySolar.app` (racine du projet, hors git, 1,6 Go dont les modèles en clones APFS dans `Contents/Resources/models`, lancée via `app/macos/launcher` qui ajoute `--ui`). Icône : `app/macos/icon.py` → `AppIcon.icns`. Non signée : clic droit > Ouvrir sur un autre Mac.
  Linux : la page s'ouvre dans le navigateur (`xdg-open`) ; le programme tourne jusqu'au bouton Quitter (ou `pkill -x easysolar`).
  Piège réglé : `exit()` avec les modèles chargés plante sous Linux/Vulkan (segfault dans le destructeur global `vk_instance_t` de ggml, prouvé avec gdb) → Quitter termine la boucle du serveur pour libérer les modèles avant la sortie.
- Mêmes pages trouvées que `rag.py` sur les 20 questions ; réponses équivalentes (écarts dus au tirage).
- llama-cpp-2 pris depuis git (rev 955aa2f724) : la version crates.io 0.1.161 n'a pas LFM3. Sans OpenMP.
- Mac : Metal, binaire de 11 Mo ne dépendant que de frameworks système. Build : `cd app && cargo build --release` (Rust via `brew install rust`).
- Linux x86_64 : **testé le 16/11 sur ubu1** (Ubuntu 24.04, Ryzen 5 5600G, NVIDIA GTX 1630 4 Go), dossier `~/AI_LLM/CLAUDE/easysolar-bot-git`. Compilation 2 min 15. Vulkan sur la GTX 1630 : 20 questions avec réponses en 1 min 32 (démarrage compris), réponses quasi identiques au Mac (`resultats_rust_linux_gpu.md`). CPU seul (`GGML_VK_VISIBLE_DEVICES=none`) : 0,2 s par paragraphe, démarrage ~50 s → le problème Windows ne se reproduit pas sous Linux. Binaire dépendant seulement de libvulkan, libstdc++, libgcc, libc.
- Windows : CI GitHub Actions (`.github/workflows/windows.yml`, dépôt privé github.com/Yann0s/easysolar-bot) → artefact `easysolar.exe` (47 Mo, CRT statique) + `vulkan-1.dll`. Vulkan si GPU, sinon CPU.
  Pièges réglés : chemins > 260 caractères (`core.longpaths` + `CARGO_NET_GIT_FETCH_WITH_CLI`) ; llama.cpp en /MD malgré `LLAMA_STATIC_CRT` (CMP0091) → `app/cmake/msvc-static-crt.cmake`.
  Sur le runner sans GPU : mêmes pages que le Mac, **mais ~27 s par appel d'embedding** (démarrage 48 min) → **Windows abandonné le 15/11**, CI désactivé (`gh workflow enable windows` pour reprendre).
  Écarté par mesure : Vulkan (tout tourne sur CPU, aucun périphérique), SIMD (AVX2/FMA actifs via `target-cpu=x86-64-v3`), taille du contexte (8192 → 1024 sans effet). Le même code sur le CPU du Mac fait 0,1–0,2 s par appel.
  Pistes non testées : compiler avec clang-cl au lieu de MSVC, réactiver OpenMP, threads (4 par défaut sur 4 vCPU), tester sur un vrai PC plutôt que le runner GitHub.

## Prochaines étapes
0. Windows : la cause de la lenteur est propre à Windows/MSVC ou au runner GitHub (Linux CPU OK) ; tester un vrai PC Windows si besoin.
1. Relire les réponses de `sft/qa.py` (valeurs électriques).
2. Distribution : le modèle fine-tuné n'est pas en ligne (release GitHub privée ?) ; précalculer les vecteurs des paragraphes pour accélérer le démarrage sur CPU.
3. Si réentraînement : 2 passes au lieu de 3 (sur-apprentissage après la 1re).

## Notes
- Dans la version FR du manuel, la température de stockage est « 40 °C à +60 °C » : le signe moins manque déjà dans le PDF.
- Tensions de la page 24 = système 24 V (déduit des valeurs, le manuel ne le dit pas).
- Il faut llama.cpp ≥ 1.0.0 (la build Homebrew 9620 ne connaît pas lfm3).

## Installation sur Mac
    brew install llama.cpp poppler uv rust
    mkdir -p bin/llama-b12183 && for t in llama-server llama-cli llama-mtmd-cli llama-tokenize; do ln -sf "$(which $t)" bin/llama-b12183/$t; done

## Installation sur Linux (application Rust, testé sur Ubuntu 24.04)
    git clone https://github.com/Yann0s/easysolar-bot && cd easysolar-bot
    sudo apt install cmake build-essential git libvulkan-dev glslc spirv-headers   # Ubuntu 24.04 (spirv-headers requis par llama.cpp Vulkan)
    curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal   # Rust (édition 2024 : Rust >= 1.85)
    cd app && cargo build --release                                  # compile aussi llama.cpp (Vulkan + CPU), plusieurs minutes
    mkdir -p target/release/models                                   # modèles à côté de l'exe (ou EASYSOLAR_MODELS=chemin)
    curl -L -o target/release/models/Qwen3-Embedding-0.6B-Q8_0.gguf https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/main/Qwen3-Embedding-0.6B-Q8_0.gguf
    # LFM3-1.7B-easysolar-Q4_K_M.gguf : pas en ligne, le copier depuis le Mac (models/) dans target/release/models/
    EASYSOLAR_LOG=1 target/release/easysolar --search ../questions.txt 2>&1 | grep easysolar   # ~0,1 s par paragraphe attendu ; ~27 s = même problème que Windows
    target/release/easysolar                                         # mode interactif
    target/release/easysolar --ui                                    # interface HTML dans le navigateur
Si un premier build a échoué (paquet manquant) : `cargo clean -p llama-cpp-sys-2 --release` avant de relancer (cache CMake incomplet).
Sans GPU ou sans Vulkan à la compilation : retirer `features = ["vulkan"]` dans `app/Cargo.toml` (bloc non-macOS) pour un build CPU seul.
