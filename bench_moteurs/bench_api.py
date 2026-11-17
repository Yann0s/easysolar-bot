"""Mesure un serveur OpenAI-compatible avec le prompt EasySolar : TTFT (prefill) et vitesse de génération.

Usage : uv run --no-project python bench_api.py <url_base> <label> [runs]
"""
import json
import statistics
import sys
import time
import urllib.request

URL, LABEL = sys.argv[1], sys.argv[2]
RUNS = int(sys.argv[3]) if len(sys.argv) > 3 else 3
SYSTEM = open("C:/bench/system.txt", encoding="utf-8").read()
QUESTION = open("C:/bench/question.txt", encoding="utf-8").read()


def one_run():
    """Une requête en streaming ; renvoie (ttft, tokens générés, durée de génération, tokens du prompt).

    Le préfixe unique empêche tout cache de préfixe côté serveur.
    """
    nonce = f"Session {time.time_ns()}.\n"
    body = {
        "model": "default",
        "messages": [{"role": "system", "content": nonce + SYSTEM}, {"role": "user", "content": QUESTION}],
        "max_tokens": 300,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    req = urllib.request.Request(URL + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.perf_counter()
    first = None
    chunks = 0
    usage = {}
    text = []
    with urllib.request.urlopen(req, timeout=900) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            data = json.loads(line[5:])
            usage = data.get("usage") or usage
            for c in data.get("choices", []):
                d = c.get("delta", {})
                piece = (d.get("content") or "") + (d.get("reasoning_content") or "")
                if piece:
                    first = first or time.perf_counter()
                    chunks += 1
                    text.append(piece)
    end = time.perf_counter()
    n = usage.get("completion_tokens") or chunks
    return first - t0, n, end - first, usage.get("prompt_tokens"), "".join(text)


def main():
    one_run()  # chauffe : chargement paresseux, caches
    rows = [one_run() for _ in range(RUNS)]
    ttft = statistics.median(r[0] for r in rows)
    tg = statistics.median((r[1] - 1) / r[2] for r in rows)
    ntok = rows[0][1]
    ptok = rows[0][3]
    pp = f"{ptok / ttft:.1f}" if ptok else "n/a"
    print(f"| {LABEL} | {ptok} | {ttft:.2f} | {pp} | {ntok} | {tg:.1f} |")
    print("REPONSE:", rows[0][4][:400].replace("\n", " "), file=sys.stderr)


main()
