# EasySolar bot — état du projet (15/11/2026)

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
- `resultats_rag_emb_sft.md` : sortie du dernier test.

## Prochaines étapes
1. Relire les réponses de `sft/qa.py` (valeurs électriques).
2. Optionnel : réentraîner le LoRA (`sft/train_mac.sh`) pour que les exemples utilisent les extraits trouvés par les embeddings (le modèle actuel a été entraîné avec des extraits BM25).
3. Application Rust (llama-cpp-2) : embarquer les deux GGUF, précalculer les vecteurs des paragraphes.

## Notes
- Dans la version FR du manuel, la température de stockage est « 40 °C à +60 °C » : le signe moins manque déjà dans le PDF.
- Tensions de la page 24 = système 24 V (déduit des valeurs, le manuel ne le dit pas).
- Il faut llama.cpp ≥ 1.0.0 (la build Homebrew 9620 ne connaît pas lfm3).

## Installation sur Mac
    brew install llama.cpp poppler uv
    mkdir -p bin/llama-b12183 && for t in llama-server llama-cli llama-mtmd-cli llama-tokenize; do ln -sf "$(which $t)" bin/llama-b12183/$t; done
