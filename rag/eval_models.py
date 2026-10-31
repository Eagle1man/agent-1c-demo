#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Сравнение моделей на одном и том же контексте RAG.

Зачем: выбор модели должен опираться на замер, а не на название. Скрипт задаёт
одинаковые вопросы, подставляет одинаковые документы и печатает время и ответ
каждой модели. Оценка качества здесь — глазами (текст ответа), потому что
автоматически «правильность» ответа на вопрос по 1С не измерить.

Запуск:
    py rag/eval_models.py --models qwen2.5:1.5b,qwen2.5:7b-instruct
    py rag/eval_models.py --models qwen2.5:7b-instruct --questions 3
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "rag"))

import llm                                  # noqa: E402
from search import search, status           # noqa: E402

QUESTIONS = [
    "как создать внешнюю печатную форму",
    "как настроить СКД отчет чтобы в колонке дата были количество и сумма",
    "ошибка при проведении документа реализация товаров и услуг",
    "как настроить права доступа пользователей",
]

PROMPT = (
    "Ты — эксперт по 1С:Предприятие. Ответь на вопрос, опираясь ТОЛЬКО на контекст.\n"
    "Если в контексте нет ответа — напиши: «в базе знаний нет ответа».\n"
    "Ответ — 3-5 предложений, по делу, без рассуждений о своих возможностях.\n\n"
    "КОНТЕКСТ:\n{context}\n\nВОПРОС: {question}\nОТВЕТ:"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="qwen2.5:1.5b")
    ap.add_argument("--questions", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    st = status()
    print(f"индекс: {st['documents']} документов, готов: {st['ready']}")
    if not st["ready"]:
        print("индекса нет — сравнивать нечего")
        return 2

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    llm.TIMEOUT = args.timeout

    for question in QUESTIONS[:args.questions]:
        hits = search(question, top_k=3)
        if not hits:
            print(f"\n=== {question}\n  документов нет — пропуск")
            continue
        context = "\n\n".join(f"--- {h['text'][:900]}" for h in hits)
        print(f"\n=== {question}  (документы: "
              f"{', '.join(str((h.get('metadata') or {}).get('file')) for h in hits)})")
        for model in models:
            t0 = time.time()
            answer = llm.generate(PROMPT.format(context=context, question=question),
                                  model=model)
            dt = time.time() - t0
            if answer is None:
                print(f"  [{model}] ОТКАЗ за {dt:.1f} с (нет ответа от Ollama)")
                continue
            print(f"  [{model}] {dt:.1f} с: {answer[:300].replace(chr(10), ' ')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
