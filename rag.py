"""RAG minimal : embeddings Qwen3 (un vecteur par paragraphe) sur les pages de manuel_fr.md, puis question au llama-server local.
Il faut deux serveurs : le modèle de chat (port 8089) et le modèle d'embeddings (port 8090), lancés par run.sh.
Usage : python3 rag.py questions.txt  (sinon lit les questions sur l'entrée standard)"""
import json, os, re, sys, urllib.request
from pathlib import Path

D = Path(__file__).parent
URL = "http://localhost:8089/v1/chat/completions"
EMB_URL = "http://localhost:8090/v1/embeddings"
TOP_K = 3
TASK = "Instruct: Given a user question about a solar inverter, retrieve the manual page that answers it\nQuery: "

def embed(texts):
    """Vecteurs normalisés (norme 1) : le produit scalaire est la similarité cosinus."""
    req = urllib.request.Request(EMB_URL, json.dumps({"input": texts}).encode(), {"Content-Type": "application/json"})
    return [d["embedding"] for d in json.load(urllib.request.urlopen(req))["data"]]

pages = [p for p in re.split(r"^(?=## )", (D / "manuel_fr.md").read_text(), flags=re.M) if p.strip()]
# un vecteur par paragraphe, préfixé du titre de sa page : 126/153 pages sources trouvées en top 3, contre 108 pour un vecteur par page
chunks = [(i, p.split("\n", 1)[0] + "\n" + c) for i, p in enumerate(pages) for c in re.split(r"\n\s*\n", p) if len(c.strip()) > 40]
vectors = embed([c for _, c in chunks])

def search(q, k=TOP_K):
    """Les k pages dont le meilleur paragraphe est le plus proche de la question."""
    qv = embed([TASK + q])[0]
    best = {}
    for (i, _), v in zip(chunks, vectors):
        best[i] = max(best.get(i, -1.0), sum(a * b for a, b in zip(qv, v)))
    return sorted(best, key=lambda i: -best[i])[:k]

def messages(q, hits):
    """Prompt envoyé au modèle ; aussi utilisé par sft/build_sft.py pour que l'entraînement voie le même format."""
    ctx = "\n".join(pages[i] for i in sorted(hits))
    return [{"role": "system", "content": (D / "consignes.txt").read_text() + "\n=== EXTRAITS DU MANUEL ===\n" + ctx + "\n=== FIN ==="},
            {"role": "user", "content": q}]

def ask(q):
    hits = search(q)
    body = {"messages": messages(q, hits),
            "temperature": 0.1, "top_k": 50, "top_p": 0.1, "repeat_penalty": 1.05, "max_tokens": 300 if os.environ.get("THINK") != "1" else 2000,
            "chat_template_kwargs": {"enable_thinking": os.environ.get("THINK") == "1"}}  # THINK=1 : mode raisonnement (LFM3)
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    answer = json.load(urllib.request.urlopen(req))["choices"][0]["message"]["content"]
    return answer, [pages[i].split("\n", 1)[0][3:] for i in hits]

if __name__ == "__main__":
    src = open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin
    for q in filter(None, map(str.strip, src)):
        a, used = ask(q)
        print(f"## {q}\n\n{a}\n\n_(extraits : {', '.join(used)})_\n", flush=True)
