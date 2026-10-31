#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Консольный чат-интерфейс для RAG-ассистента 1С с Ollama"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rag'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from search import search as rag_search, status as rag_status
from llm import OLLAMA_MODEL, generate

SUGGESTIONS = [
    "Как исправить синтаксическую ошибку в 1С?",
    "Как создать накладную в 1С:Предприятие?",
    "Остатки товара на складе — как посчитать?",
    "Как подключиться к базе данных 1С?",
    "Как очистить кэш 1С?",
    "Как восстановить убитую конфигурацию?",
    "Как настроить пользователей и права?",
    "Как выгрузить данные в Excel из 1С?",
]

def show_suggestions():
    print("\n💡 Подсказки по вопросам:")
    for i, s in enumerate(SUGGESTIONS, 1):
        print(f"  [{i}] {s}")
    print()

def ollama_answer(question, context):
    """Ответ модели. Возвращает {"text": ..., "error": ...}; отдельно,
    чтобы отказ модели не выглядел как её ответ."""
    if context:
        prompt = f"""Ты — эксперт по 1С:Предприятие. Отвечай на русском языке, основываясь на предоставленном контексте из базы знаний. Если контекста недостаточно, честно скажи об этом. Не придумывай информацию.

КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ:
{context}

ВОПРОС ПОЛЬЗОВАТЕЛЯ: {question}

Ответ (с указанием источника, если информация из контекста):"""
    else:
        prompt = f"""Ты — эксперт по 1С:Предприятие. Отвечай на русском языке. Если не знаешь ответа, честно скажи об этом. Не придумывай информацию.

ВОПРОС ПОЛЬЗОВАТЕЛЯ: {question}

Ответ:"""

    text = generate(prompt)
    if text is None:
        return {"text": None, "error": f"модель {OLLAMA_MODEL} недоступна (ollama serve)"}
    return {"text": text, "error": None}

def build_context(hits):
    if not hits:
        return ""
    parts = []
    for i, h in enumerate(hits, 1):
        src = h.get("metadata", {}).get("source", "неизвестный источник")
        score = h.get("score", 0)
        text = h.get("text", "")
        parts.append(f"[Источник {i}] (релевантность: {score:.2f}) {src}\n{text}")
    return "\n\n".join(parts)

def main():
    print("=" * 60)
    print("🤖 RAG-ассистент 1С — Консольный чат (Ollama + RAG)")
    print("=" * 60)
    print("Введите 'quit' или 'exit' для выхода")
    print("Введите 'help' для подсказок")
    print("-" * 60)
    show_suggestions()
    st = rag_status()
    if st["ready"]:
        print(f"📚 База знаний: {st['documents']} документов ({st['collection']}, {st['model'].split('/')[-1]})")
    else:
        print(f"⚠ База знаний недоступна: {st['error']}")
    history = []
    while True:
        try:
            question = input("\n👤 Вы: ").strip()
            if question.lower() in ('quit', 'exit'):
                print("👋 До свидания!")
                break
            elif question.lower() == 'help':
                show_suggestions()
                continue
            elif not question:
                continue
            if question.isdigit():
                idx = int(question)
                if 1 <= idx <= len(SUGGESTIONS):
                    question = SUGGESTIONS[idx - 1]
            print("⏳ Поиск в базе знаний 1С...")
            hits = rag_search(question, top_k=3)
            if not hits:
                st = rag_status()
                if not st["ready"]:
                    print(f"⚠ База знаний недоступна: {st['error']}")
                else:
                    print("ℹ Подходящих документов нет — ответ будет без источников.")
            context = build_context(hits)
            print("⏳ Получение ответа от Ollama...")
            res = ollama_answer(question, context)
            if res["error"]:
                print(f"\n⚠ Ответа нет: {res['error']}. Данные не выдумывались.")
                continue
            print(f"\n🤖 Ассистент:\n{res['text']}")
            if hits:
                srcs = [str((h.get('metadata') or {}).get('file') or h.get('source'))
                        for h in hits]
                print("\n📚 Источники: " + ", ".join(srcs))
            history.append({"question": question, "answer": res["text"], "sources": hits})
        except KeyboardInterrupt:
            print("\n\n👋 До свидания!")
            break
        except Exception as e:
            print(f"\n⚠ Ошибка: {e}")

if __name__ == "__main__":
    main()