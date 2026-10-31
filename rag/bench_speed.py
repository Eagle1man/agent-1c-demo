#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скорость генерации модели: токенов в секунду по данным самого Ollama.

Нужен, чтобы выбор модели не был догадкой: «7B отвечает лучше» и «7B отвечает
за 4 минуты» — разные утверждения, и второе решает, где модель применима.

Запуск:
    py rag/bench_speed.py qwen2.5:1.5b qwen2.5:7b-instruct
"""
import json
import sys
import time
import urllib.request

URL = "http://127.0.0.1:11434/api/generate"
PROMPT = "Кратко, 3 предложения: что такое регистр накопления в 1С?"
NUM_PREDICT = 80


def run(model: str) -> dict:
    body = json.dumps({"model": model, "prompt": PROMPT, "stream": False,
                       "options": {"num_predict": NUM_PREDICT}}).encode("utf-8")
    req = urllib.request.Request(URL, data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        return {"model": model, "error": f"HTTP {exc.code}: {detail}",
                "wall": time.time() - t0}
    except Exception as exc:                       # noqa: BLE001
        return {"model": model, "error": str(exc)[:120], "wall": time.time() - t0}
    wall = time.time() - t0
    count = int(data.get("eval_count") or 0)
    gen_ns = int(data.get("eval_duration") or 1)
    load_ns = int(data.get("load_duration") or 0)
    return {
        "model": model,
        "wall": wall,
        "tokens": count,
        "load_s": load_ns / 1e9,
        "tok_per_s": count / (gen_ns / 1e9) if gen_ns else 0.0,
        "text": (data.get("response") or "").strip()[:160].replace("\n", " "),
    }


def main():
    models = sys.argv[1:] or ["qwen2.5:1.5b"]
    print(f"{'модель':28} {'всего,с':>8} {'загрузка,с':>11} {'ток/с':>7}  ответ")
    failed = False
    for m in models:
        r = run(m)
        if r.get("error"):
            failed = True
            print(f"{m:28} {'-':>8} {'-':>11} {'-':>7}  ОШИБКА: {r['error']}")
            continue
        print(f"{r['model']:28} {r['wall']:8.1f} {r['load_s']:11.1f} "
              f"{r['tok_per_s']:7.1f}  {r['text']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
