#!/usr/bin/env python3
"""
Benchmark HTTP OpenAI-compatible (/v1/chat/completions, streaming SSE) pour EasySolar.
Mesure TTFT (cold Q1 vs warm Q2-Q20 pour prefix caching), tokens/s, latence totale.
Zéro dépendance externe (stdlib uniquement).
"""

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Extrait représentatif (~600 tokens) pour simuler un prompt RAG réel d'EasySolar
SAMPLE_RAG_CONTEXT = """EXTRAITS DU MANUEL :
[Page 8]
4.2 Indications par voyants LED
LED Inverter (vert) : allumée en continu lorsque le convertisseur est actif.
LED Charger (jaune) : allumée pendant la charge batterie.
LED Alarm (rouge) : clignote en pré-alarme (surcharge, tension batterie basse, température convertisseur élevée). Allumée en continu en cas d'arrêt sur alarme.

[Page 21]
Dépannage : si la LED Alarm clignote, vérifiez la charge connectée, la tension batterie et la ventilation.

[Page 28]
Caractéristiques techniques :
Rendement maximal : 92 % (12 V) / 94 % (24 V).
Puissance PV maximale : 700 W (12 V) / 1400 W (24 V)."""


def load_inputs(root: Path) -> tuple[str, list[str]]:
    consignes = (root / "consignes.txt").read_text(encoding="utf-8").strip()
    questions = [
        line.strip()
        for line in (root / "questions.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return consignes, questions


def stream_chat(
    url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    timeout: float,
) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "stream": True,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t_start = time.perf_counter()
    t_first_token = None
    chunks: list[str] = []
    usage_completion_tokens = None

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line or not line.startswith("data:"):
                continue
            body = line[5:].strip()
            if body == "[DONE]":
                break
            try:
                evt = json.loads(body)
            except json.JSONDecodeError:
                continue

            if "usage" in evt and evt["usage"]:
                usage_completion_tokens = evt["usage"].get("completion_tokens")

            choices = evt.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content = delta.get("content")
            if content:
                if t_first_token is None:
                    t_first_token = time.perf_counter()
                chunks.append(content)

    t_end = time.perf_counter()
    text = "".join(chunks)
    total_s = t_end - t_start
    ttft_s = (t_first_token - t_start) if t_first_token is not None else total_s
    decode_s = max(t_end - (t_first_token or t_end), 1e-6)
    # Estimation fallback (~4 chars/token) si le serveur ne renvoie pas usage.completion_tokens
    tokens = usage_completion_tokens if usage_completion_tokens else max(1, len(text) // 4)
    tps = tokens / decode_s if t_first_token is not None else 0.0

    return {
        "ttft_ms": round(ttft_s * 1000, 1),
        "total_s": round(total_s, 3),
        "tokens": tokens,
        "tps": round(tps, 2),
        "answer": text.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark EasySolar OpenAI-compatible HTTP")
    parser.add_argument("--name", required=True, help="Nom du moteur (fox, ferrite, crane)")
    parser.add_argument("--url", required=True, help="URL /v1/chat/completions")
    parser.add_argument("--model", required=True, help="Identifiant du modèle")
    parser.add_argument("--root", default=".", help="Racine du dépôt easysolar")
    parser.add_argument("--max-tokens", type=int, default=160)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--out", default="bench/metrics.jsonl")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    system_prompt, questions = load_inputs(root)
    results = []

    print(f"=== Benchmark {args.name} ({args.model}) @ {args.url} ===")
    t_all_start = time.perf_counter()

    for idx, q in enumerate(questions, start=1):
        user_prompt = f"{SAMPLE_RAG_CONTEXT}\n\nQUESTION : {q}"
        try:
            r = stream_chat(
                args.url, args.model, system_prompt, user_prompt, args.max_tokens, args.timeout
            )
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"[{idx:02d}/20] ERREUR: {exc}", file=sys.stderr)
            return 1

        r["engine"] = args.name
        r["model"] = args.model
        r["q_idx"] = idx
        r["question"] = q
        results.append(r)
        print(
            f"[{idx:02d}/20] TTFT={r['ttft_ms']:7.1f} ms | "
            f"total={r['total_s']:6.2f} s | {r['tps']:6.2f} tok/s | {q[:45]}"
        )

    t_all = time.perf_counter() - t_all_start
    warm_ttft = [r["ttft_ms"] for r in results[1:]] or [results[0]["ttft_ms"]]
    tps_list = [r["tps"] for r in results]

    summary = {
        "engine": args.name,
        "model": args.model,
        "total_20q_s": round(t_all, 2),
        "cold_ttft_ms": results[0]["ttft_ms"],
        "warm_ttft_median_ms": round(statistics.median(warm_ttft), 1),
        "tps_median": round(statistics.median(tps_list), 2),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.write(json.dumps({"summary": summary}, ensure_ascii=False) + "\n")

    print("\n--- Résumé ---")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
