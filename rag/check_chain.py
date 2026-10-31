#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Сквозная проверка цепочки «вопрос → RAG → модель → ответ с источниками».

Печатает: сколько документов найдено, откуда они, ответ модели и время.
Нужен, чтобы этап B проверялся командой, а не на глаз в интерактивном чате.

Запуск:
    py rag/check_chain.py "как создать внешнюю печатную форму"
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "rag"))

import llm                                  # noqa: E402
from search import search, status           # noqa: E402
from llm import generate                    # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for a in sys.argv[1:]:
        if a.startswith("--model="):
            llm.OLLAMA_MODEL = a.split("=", 1)[1]
        if a.startswith("--timeout="):
            llm.TIMEOUT = int(a.split("=", 1)[1])
    question = " ".join(args) or "как создать внешнюю печатную форму"
    st = status()
    print(f"индекс: {st['documents']} документов, готов: {st['ready']}, ошибка: {st['error']}")

    t0 = time.time()
    hits = search(question, top_k=3)
    t_search = time.time() - t0
    print(f"поиск: {len(hits)} документов за {t_search:.1f} с")
    for i, h in enumerate(hits, 1):
        src = (h.get("metadata") or {}).get("file") or h.get("source")
        print(f"  [{i}] {h['score']} {src}: {h['text'][:80]}")

    if not hits:
        print("ОТВЕТА НЕ БУДЕТ: база не дала документов — модель не должна выдумывать")
        return 2

    context = "\n\n".join(f"--- {h['text'][:900]}" for h in hits)
    prompt = (
        "Ты — эксперт по 1С. Ответь на вопрос, опираясь ТОЛЬКО на контекст.\n"
        "Если в контексте нет ответа — скажи: «в базе знаний нет ответа».\n"
        "В конце укажи, из какого фрагмента взят ответ.\n\n"
        f"КОНТЕКСТ:\n{context}\n\nВОПРОС: {question}\nОТВЕТ:"
    )
    t0 = time.time()
    answer = generate(prompt)
    t_gen = time.time() - t0
    if answer is None:
        print(f"МОДЕЛЬ НЕДОСТУПНА ({llm.OLLAMA_MODEL}, таймаут {llm.TIMEOUT} с) — ответ не выдумывался")
        return 3
    print(f"\nмодель {llm.OLLAMA_MODEL}, {t_gen:.1f} с:\n{answer[:1200]}")
    print(f"\nисточники: " + ", ".join(
        str((h.get('metadata') or {}).get('file')) for h in hits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
