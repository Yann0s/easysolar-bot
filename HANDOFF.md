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
Autres modèles d'embeddings (17/11, même mesure, découpage par paragraphe ; l'appli Rust actuelle donne 131 avec Qwen3-Embedding-0.6B) : EmbeddingGemma 2 Q8_0 120 (121 avec « task: question answering »), LFM2.5-Embedding-350M Q8_0 113 (115 sans préfixe). Vecteurs llama.cpp vérifiés identiques à sentence-transformers (cosinus ≥ 0,999) : pas retenus.

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
- `models/paragraphes.bin` : vecteurs des 103 paragraphes (`easysolar --save-vectors`, 412 Ko), à livrer avec les modèles.

## Application Rust (`app/`)
- Un binaire : manuel et consignes compilés dedans, modèles lus dans `models/` à côté de l'exe (ou `$EASYSOLAR_MODELS`). `easysolar` = mode interactif avec invite « > » (Ctrl+D pour quitter), `easysolar questions.txt` = lot, `--search` = pages seulement, `EASYSOLAR_LOG=1` = messages llama.cpp.
- Vecteurs précalculés (17/11) : `easysolar --save-vectors` écrit `models/paragraphes.bin` (empreinte FNV-1a des paragraphes + f32) ; au démarrage, l'appli le lit, et le recalcule en mémoire s'il manque ou ne correspond plus au manuel (message « absent ou périmé »). Elle ne l'écrit jamais d'elle-même (dossier en lecture seule, signature de l'app Mac). `bundle_mac.sh` le régénère et l'embarque. `.gitattributes` force LF sur `manuel_fr.md` : un clone CRLF sous Windows changerait l'empreinte. Mesures (`--search`) : VM Windows CPU 20 questions 71,9 s → 3,5 s, Mac 6,1 s → 0,56 s. Vecteurs calculés sur le Mac (Metal) et utilisés sous Windows (CPU) : mêmes pages sur les 20 questions (un seul échange d'ordre, sans effet), 130/153 pages sources en top 3 avec ou sans fichier (Mac : 131). `flash_attn` déjà actif (auto) ; `llama-bench -fa 1` sur la VM : +3 à 7 % seulement, pas de mise à jour de llama.cpp pour ça.
- Interface graphique (16/11) : `easysolar --ui` sert une page HTML aux couleurs Victron (`app/src/ui.html`, compilée dans le binaire) sur `127.0.0.1:8765` (port libre sinon), une requête à la fois. Bouton Quitter = `POST /quit`.
  Mac : fenêtre native WKWebView reprise de Pulsefy (`app/native/macos_webview.m`, compilée par `app/build.rs`) ; `app/bundle_mac.sh` construit `EasySolar.app` (racine du projet, hors git, 1,6 Go dont les modèles en clones APFS dans `Contents/Resources/models`, lancée via `app/macos/launcher` qui ajoute `--ui`). Icône : `app/macos/icon.py` → `AppIcon.icns`. Non signée : clic droit > Ouvrir sur un autre Mac.
  Linux : la page s'ouvre dans le navigateur (`xdg-open`, sorties redirigées vers /dev/null : sinon Chrome écrit ses logs « zygote ... Broken pipe » dans le terminal, sans conséquence) ; le programme tourne jusqu'au bouton Quitter (ou `pkill -x easysolar` ; pas `pkill -f "easysolar --ui"` dans une commande ssh, qui tue sa propre session).
  Windows (testé le 16/11 sur la VM) : fenêtre Edge en mode application (`msedge --app`, 900×700, profil propre à chaque lancement dans `%LOCALAPPDATA%\EasySolar\edge-<pid>`, anciens profils supprimés au lancement suivant) ; fermer la fenêtre envoie `/quit` (le processus Edge est surveillé), Quitter ferme la fenêtre (`window.close()`). Double-clic sur `easysolar.exe` = `--ui` sans console (détecté par `GetConsoleProcessList` == 1, puis `FreeConsole`) ; depuis une invite de commandes, mode texte inchangé. En double-clic, messages et erreurs vont dans `%LOCALAPPDATA%\EasySolar\easysolar.log`. Icône : `app/windows/easysolar.ico` (générée par `app/macos/icon.py`), intégrée par `build.rs` (crate winresource) ; favicon dans `ui.html` (icône de la fenêtre Edge).
  ERR_CONNECTION_REFUSED intermittent au double-clic, deux causes prouvées : le `msedge.exe` lancé passe la main et se termine, l'appli croit la fenêtre fermée et s'arrête après le chargement. (1) Profil partagé + un Edge de ce profil déjà ouvert → reprise de la fenêtre (reproduit). (2) `__COMPAT_LAYER` hérité (posé parfois par Windows au double-clic depuis l'Explorateur, `easysolar.exe` est dans `AppCompatFlags\Compatibility Assistant\Store`) → Edge se relance avec `--edge-skip-compat-layer-relaunch` ; A/B avec `__COMPAT_LAYER=RunAsInvoker` : Edge mort sans `env_remove`, vivant avec. Les lancements par tâche planifiée ou ssh ne passent pas par l'Explorateur et ne reproduisent pas (2).
  Une connexion coupée par le navigateur (rechargement, fenêtre fermée) ne fait plus tomber le serveur (avant : sortie sur ConnectionAborted).
  Piège réglé : `exit()` avec les modèles chargés plante sous Linux/Vulkan (segfault dans le destructeur global `vk_instance_t` de ggml, prouvé avec gdb) → Quitter termine la boucle du serveur pour libérer les modèles avant la sortie.
- Mêmes pages trouvées que `rag.py` sur les 20 questions ; réponses équivalentes (écarts dus au tirage).
- llama-cpp-2 pris depuis git (rev 955aa2f724) : la version crates.io 0.1.161 n'a pas LFM3. Sans OpenMP.
- Mac : Metal, binaire de 11 Mo ne dépendant que de frameworks système. Build : `cd app && cargo build --release` (Rust via `brew install rust`).
- Linux x86_64 : **testé le 16/11 sur ubu1** (Ubuntu 24.04, Ryzen 5 5600G, NVIDIA GTX 1630 4 Go), réinstallé le 16/11 par `gh repo clone` dans `~/AI_LLM/CLAUDE/easysolar-bot` (anciennes copies supprimées), modèles dans `app/target/release/models/`. Compilation complète depuis le dépôt : 1 min 24, sans erreur. `--search` diffère du Mac sur 2 questions en Vulkan, 3 en CPU (pages à scores très proches, arrondis différents selon le backend ; presque toujours un simple changement d'ordre, sans effet car les extraits sont triés). Vulkan sur la GTX 1630 : 20 questions avec réponses en 1 min 32 (démarrage compris), réponses quasi identiques au Mac (`resultats_rust_linux_gpu.md`). CPU seul (`GGML_VK_VISIBLE_DEVICES=none`) : 0,2 s par paragraphe, démarrage ~50 s → le problème Windows ne se reproduit pas sous Linux. Binaire dépendant seulement de libvulkan, libstdc++, libgcc, libc.
- Windows : CI GitHub Actions (`.github/workflows/windows.yml`, dépôt privé github.com/Yann0s/easysolar-bot) → artefact `easysolar.exe` (47 Mo, CRT statique) + `vulkan-1.dll`. Vulkan si GPU, sinon CPU.
  Pièges réglés : chemins > 260 caractères (`core.longpaths` + `CARGO_NET_GIT_FETCH_WITH_CLI`) ; llama.cpp en /MD malgré `LLAMA_STATIC_CRT` (CMP0091) → `app/cmake/msvc-static-crt.cmake`.
  Sur le runner sans GPU (4 vCPU) : mêmes pages que le Mac, mais ~27 s par appel d'embedding → Windows abandonné le 15/11, CI désactivé (`gh workflow enable windows` pour reprendre).
  **Cause trouvée le 16/11 sur une VM Windows 10 (ubu1, Ryzen 5 5600G)** : plus de threads que de cœurs. 2 cœurs + 4 threads (défaut de llama.cpp) : 156 s par paragraphe ; 2 threads : 0,5 s ; 1 thread : 1,0 s. Avec 6 cœurs, 3 à 6 threads : 0,1–0,3 s. Correctif : `n_threads() = min(cœurs, 4)` (sans effet sur Mac/Linux). Le cas du runner (4 threads sur 4 vCPU, lent) ne se reproduit pas sur la VM à 6 cœurs : vCPU partagés du runner, non vérifié.
  VM : `ssh test@192.168.10.35` (clé), Windows 10 voit au plus 2 sockets → topologie 1 socket × 6 cœurs. Chemins longs activés le 16/11 (`reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f`, en admin) : le build Vulkan passe alors dans `C:\esb\app` (3 min 22 sur 6 cœurs), mais **un build propre échoue au premier `cargo build`** (étape configure de `vulkan-shaders-gen` interrompue, « missing CMakeCache.txt », « VCEnd » introuvable) et réussit au second. Non reproduit en appelant CMake directement (même chemin, `--parallel 6`, ALL_BUILD) : probable concurrence MSBuild dépendant du timing, non prouvée. Exe Vulkan sur la VM sans GPU : repli CPU, `--search` identique au Mac, 75 s. Compilation 4 min 31 (2 cœurs). Résultats (6 cœurs, CPU) : `--search` identique au Mac ; 20 questions : 71 s en recherche seule, 305 s avec réponses (`resultats_rust_windows_cpu.md`), 4 réponses formulées un peu différemment de Linux GPU.
  Sortie redirigée par PowerShell (`>`) : UTF-8 relu en cp850 puis réécrit en UTF-16 ; le binaire écrit bien de l'UTF-8.

- Release v0.1.0 (16/11, dépôt privé) : `EasySolar-Mac.zip` (`app/bundle_mac.sh` puis `ditto -c -k --keepParent EasySolar.app`, signature ad hoc : Gatekeeper refuse « non vérifiée » mais pas « endommagée ») et `EasySolar-Windows.zip` (dossier `EasySolar\` : `EasySolar.exe` compilé sur la VM, `vulkan-1.dll`, `models\`), modèles inclus, ~1,7 Go chacun (limite GitHub : 2 Go par fichier). Tuto d'installation pour débutants dans README.md.
- Release v0.1.1 (17/11, « latest ») : mêmes zips + `models/paragraphes.bin` ; exe Windows compilé sur la VM (`C:\esb\build.bat`), zips assemblés sur le Mac (`zip -rX` du dossier `EasySolar\`, `ditto` pour l'app).

## Prochaines étapes
0. Windows : réactiver le CI (`gh workflow enable windows`) pour vérifier le correctif des threads sur le runner ; build Vulkan local : relancer `cargo build` si le premier échoue (cause non prouvée).
1. Relire les réponses de `sft/qa.py` (valeurs électriques).
2. Distribution : le modèle fine-tuné n'est pas en ligne (release GitHub privée ?) ; publication hors du dépôt privé à décider.
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
    target/release/easysolar --save-vectors                          # vecteurs des paragraphes (ou copier models/paragraphes.bin du Mac)
    target/release/easysolar                                         # mode interactif
    target/release/easysolar --ui                                    # interface HTML dans le navigateur
Si un premier build a échoué (paquet manquant) : `cargo clean -p llama-cpp-sys-2 --release` avant de relancer (cache CMake incomplet).
Sans GPU ou sans Vulkan à la compilation : retirer `features = ["vulkan"]` dans `app/Cargo.toml` (bloc non-macOS) pour un build CPU seul.
