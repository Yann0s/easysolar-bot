# Étude : moteurs d'inférence Rust pour accélérer EasySolar sous Windows

17/11/2026. Sources : README et arborescence de chaque dépôt (lus via l'API GitHub), page Docker Hub et README de Fox (le fil Reddit n'est pas lisible depuis cet environnement).

## 1. Point de départ : où passe le temps aujourd'hui

Appli actuelle : llama.cpp via `llama-cpp-2` (git rev 955aa2f724), deux modèles GGUF :

- génération : `LFM3-1.7B-easysolar-Q4_K_M.gguf`, architecture GGUF **`lfm3`** (convolutions courtes + attention, avec fenêtre glissante : `lfm3.attention.sliding_window`, `lfm3.shortconv.l_cache`) ;
- recherche : `Qwen3-Embedding-0.6B-Q8_0.gguf`, pooling sur le dernier token, sur environ 103 paragraphes du manuel.

Mesures déjà faites sur la VM Windows 10 (6 cœurs Ryzen 5600G, CPU seul, voir HANDOFF.md) :

| Étape | Temps |
|---|---|
| 20 questions, recherche seule (démarrage compris) | 71 s |
| 20 questions avec réponses | 305 s, soit ~12 s par réponse |
| Un paragraphe vectorisé | 0,1 à 0,3 s |

Une réponse, c'est un prefill d'environ 1 700 tokens (consignes + 3 pages d'extraits, ~6 000 caractères), puis jusqu'à 300 tokens générés. Le démarrage, lui, est dominé par la vectorisation des 103 paragraphes, refaite à chaque lancement.

## 2. La contrainte qui décide de tout

**Aucun moteur de la liste ne lit l'architecture `lfm3`.** Changer de moteur veut donc dire, au choix :

- porter LFM3 dans ce moteur (code de modèle à écrire et à valider) ;
- ou changer de modèle de base, puis refaire le LoRA, les tests sur 20 questions et les scores sur 153 questions.

Le benchmark de la deuxième étape doit donc comparer les moteurs sur des **modèles de substitution** de taille proche, avant d'engager l'un de ces deux chantiers.

## 3. Les moteurs un par un

| Moteur | Ce que c'est | CPU / GPU | Windows | GGUF | LFM | Qwen3 (embeddings) | Verdict |
|---|---|---|---|---|---|---|---|
| [samsja/rusty-llm](https://github.com/samsja/rusty-llm) | GPT-2 jouet, 3 étoiles, abandonné depuis 05/2023 | CPU | ? | non | non | non | **Écarté** |
| [guoqingbao/xinfer](https://github.com/guoqingbao/xinfer) | Serveur de production pour gros modèles (27B à 397B), batching, FP8/NVFP4 | CUDA, Metal | CUDA seulement | oui | non | oui | **Écarté** : aucun chemin CPU ni Vulkan, alors que les PC des utilisateurs n'ont pas forcément de GPU NVIDIA |
| [lucasjinreal/Crane](https://github.com/lucasjinreal/Crane) | Moteur sur candle, très actif (MAJ 16/11), MIT | CPU, CUDA, Metal, ROCm, SYCL | non documenté (candle compile sous Windows) | oui | **LFM2/2.5** (`crane-core/src/models/lfm2_5`, chargé depuis des safetensors) | oui | **Retenu** |
| [Classevelabs/rai](https://github.com/Classevelabs/rai) | CPU pur, noyaux AVX2 écrits à la main, format `.raimodel`, Apache-2.0 | CPU (AVX2, repli scalaire) | **oui**, lanceurs double-clic | non (conversion depuis safetensors) | non (refusé : pas de forme Llama) | Qwen3 dense oui | **Retenu** |
| [razancodes/ferrite](https://github.com/razancodes/ferrite) | Spécialiste Qwen3.5 écrit de zéro, annonce 1,4 à 2,4 fois llama.cpp en génération, et plus avec spéculation MTP | CPU (AVX-512 VNNI, sinon repli scalaire « beaucoup plus lent ») | **oui**, testé sur Windows 11 seulement | non (ses propres quantifications) | non | non (Qwen3.5 seulement) | **Retenu**, avec réserves |
| [tamirkifle/mini-rust-inference](https://github.com/tamirkifle/mini-rust-inference) (inferrs) | Moteur pédagogique Llama, Q8_0 seulement, 0 étoile | CPU | ? | Q8_0 | non | non | **Écarté** |
| [fruitvibes123/creatine](https://github.com/fruitvibes123/creatine) | CPU, AVX2/VNNI, au niveau de llama.cpp (1,14 fois en prefill sur Raptor Lake), serveur sécurisé | CPU x86-64-v3 | **non** (binaire musl Linux seulement) | Q4_K_M | non | Qwen3 dense (chat, embeddings non exposés) | **Écarté** : pas de Windows, licence GPL |
| [ferrumox/fox](https://github.com/ferrumox/fox) (fil Reddit) | Serveur compatible Ollama **qui embarque llama.cpp** | CUDA, ROCm, Vulkan, Metal, CPU | build depuis les sources | oui | comme le llama.cpp embarqué | oui | **Écarté** : les « 2× » viennent du cache de préfixes partagé entre **requêtes concurrentes**. Pour une seule requête, le README dit lui-même que ce sont les mêmes noyaux que `llama-server`. Un seul utilisateur, donc aucun gain |

Remarques :

- **Crane** est le seul qui ait déjà la famille LFM. Pour passer de LFM2 à LFM3, il faudrait ajouter l'attention à fenêtre glissante et le chargement GGUF quantifié de cette architecture. Son README reconnaît un retard d'environ 1,7 fois sur llama.cpp en décodage (mesuré sur ROCm). Le CPU sous candle est à mesurer.
- **rai** est le mieux pensé pour Windows grand public (CPU seul, double-clic, pas de DLL). Ses chiffres ne montrent pas d'avance claire sur llama.cpp : 21,8 tok/s sur TinyLlama-1.1B avec 4 cœurs, comparé seulement à transformers en fp32. Il peut faire tourner un Qwen3 dense, donc l'étage embeddings.
- **ferrite** donne les meilleurs chiffres, mais seulement à pleine vitesse sur les CPU avec AVX-512 VNNI (Intel 11e génération, Zen 4, Zen 5). Les Intel 12e à 14e génération, les Core Ultra et les Zen 3 (dont le Ryzen 5600G de la VM) passent en repli scalaire. Un parc d'utilisateurs Windows est très mélangé : c'est le risque principal.

## 4. Les trois moteurs proposés pour le benchmark

Tous comparés à **la référence : llama.cpp, tel qu'utilisé par l'appli** (`llama-cpp-2`, même nombre de threads).

### A. Crane (candle) : la piste « garder LFM »

- Pourquoi : seul moteur avec la famille LFM, CPU et GPU, embeddings Qwen3 possibles dans la même pile, code Rust idiomatique, licence MIT.
- Modèles du banc : `LFM2.5-1.2B` (safetensors, pris en charge tel quel) contre le même modèle en GGUF dans llama.cpp ; `Qwen3-Embedding-0.6B` pour l'étage recherche.
- Si Crane gagne : porter LFM3 dans Crane (fenêtre glissante + GGUF).

### B. rai : la piste « CPU Windows grand public »

- Pourquoi : CPU seul AVX2 (présent sur pratiquement tous les PC depuis 2013), Windows de première classe, Apache-2.0.
- Modèles du banc : `Qwen3-1.7B` (chat, taille proche de LFM3-1.7B) et `Qwen3-Embedding-0.6B`, convertis avec `rai convert`, contre les GGUF Q4_K_M et Q8_0 dans llama.cpp.
- Si rai gagne : changer de modèle de base pour Qwen3-1.7B et refaire le LoRA, car LFM n'entre pas dans son format.

### C. ferrite : la piste « vitesse maximale »

- Pourquoi : les plus gros gains annoncés face à llama.cpp, développé et testé sous Windows.
- Modèle du banc : `Qwen3.5-2B` en 4 bits contre `Qwen3.5-2B-Q4_K_M.gguf` dans llama.cpp.
- À mesurer **sur deux machines** : une avec AVX-512 VNNI (Intel 11e génération ou Zen 4) et la VM Zen 3 (repli scalaire), pour voir l'écart réel sur un parc mélangé.
- Si ferrite gagne : changer de modèle de base pour Qwen3.5-2B et refaire le LoRA. La recherche resterait sur un autre moteur (ferrite ne fait pas les embeddings Qwen3).

## 5. Protocole de benchmark (deuxième étape)

Sur la VM Windows (`ssh test@192.168.10.35`, 6 cœurs, CPU seul), puis sur une machine avec AVX-512 pour ferrite :

1. **Charge type EasySolar** : un prompt de 1 700 tokens (un vrai prompt RAG sorti de l'appli), puis 300 tokens générés en greedy.
2. **Mesures** : temps de chargement, prefill (tok/s), génération (tok/s), mémoire maximale, temps de vectorisation des 103 paragraphes (moteurs avec Qwen3 dense).
3. **Threads** : 2, 4 et 6 (le bug Windows des threads en surnombre l'impose).
4. **Médiane de 3 passes**, machine au repos, un moteur à la fois.
5. **Qualité** : même texte en sortie greedy, ou au moins une perplexité comparable. Un moteur plus rapide mais qui dégrade les réponses ne compte pas.

Critère de décision : un gain d'au moins 1,5 fois sur le temps par réponse face à llama.cpp, à qualité égale. En dessous, le coût du portage ou du changement de modèle n'est pas justifié.

## 6. Gains possibles sans changer de moteur (à mesurer en parallèle)

Ces pistes ne demandent ni portage ni réentraînement. D'après les mesures du § 1, elles pèsent probablement plus lourd :

1. **Précalculer les vecteurs des 103 paragraphes** (déjà prévu dans HANDOFF.md) : ils seraient livrés dans un fichier, au lieu de les recalculer à chaque démarrage. C'est le gain le plus net sur le temps d'ouverture.
2. **Garder en cache le KV des consignes** (préfixe identique pour chaque question) : moins de prefill par réponse.
3. **Mettre à jour llama.cpp** (rev plus récente) et tester `flash_attn` sur CPU et sur Vulkan.
4. **Mesurer un `n_threads` égal au nombre de cœurs physiques** au lieu de `min(cœurs, 4)` : sur 6 cœurs, 3 à 6 threads donnaient 0,1 à 0,3 s par paragraphe.
