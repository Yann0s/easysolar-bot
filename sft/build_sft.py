"""Construit sft/train.jsonl et sft/dev.jsonl (format conversation) à partir de sft/qa.py.
Chaque exemple = prompt de production (consignes + 3 extraits trouvés par rag.search) + réponse de référence.
- Si la recherche rate une page source, on l'injecte à la place du dernier extrait : le modèle apprend à lire.
- Exemples négatifs : pour ~15 % des questions, on retire les pages sources -> la réponse attendue devient le refus.
Usage : python3 -I sft/build_sft.py"""
import json, random, re, sys
from pathlib import Path

D = Path(__file__).resolve().parent
sys.path[:0] = [str(D), str(D.parent)]
import rag
from qa import QA, R

random.seed(0)
label = {p.split("\n", 1)[0][3:]: i for i, p in enumerate(rag.pages)}  # "Page 10" / "Annexe A" -> index

def example(q, a, hits):
    return {"messages": rag.messages(q, hits) + [{"role": "assistant", "content": a}]}

def numbers(text):
    return set(re.findall(r"\d+(?:,\d+)?", text.split("(manuel")[0])) - {str(i) for i in range(10)}

out, stats = [], {"normal": 0, "injecte": 0, "negatif": 0, "refus": 0}
for q, a, src in QA:
    hits = rag.search(q)
    gold = [label[s] for s in src]  # KeyError ici = section inconnue dans qa.py
    missing = [g for g in gold if g not in hits]
    if missing:
        hits = [h for h in hits if h in gold] + missing + [h for h in hits if h not in gold]
        hits = hits[:max(rag.TOP_K, len(gold))]
        stats["injecte"] += 1
    out.append(example(q, a, hits))
    stats["refus" if not src else "normal"] += 1
    # négatif : mêmes extraits sans les pages sources, seulement si aucun chiffre de la réponse n'y apparaît
    if src and random.random() < 0.15:
        neg = [i for i in rag.search(q, k=10) if i not in gold][:rag.TOP_K]
        ctx = " ".join(rag.pages[i] for i in neg)
        if not numbers(a) & numbers(ctx):
            out.append(example(q, R, neg))
            stats["negatif"] += 1

random.shuffle(out)
n_dev = len(out) // 10
for name, rows in [("dev", out[:n_dev]), ("train", out[n_dev:])]:
    with open(D / f"{name}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(stats, f"-> train {len(out) - n_dev}, dev {n_dev}")

# self-check : chaque exemple non-refus contient bien ses pages sources dans le prompt
for q, a, src in QA:
    ex = next(e for e in out if e["messages"][1]["content"] == q and e["messages"][2]["content"] == a)
    assert all(f"## {s}\n" in ex["messages"][0]["content"] for s in src), q
print("self-check OK")
