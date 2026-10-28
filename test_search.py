#!/usr/bin/env python
# Тест RAG-поиска
import sys
sys.path.insert(0, 'rag')
from search import rag_answer

print("ТЕСТ ПОИСКА В БАЗЕ ЗНАНИЙ 1С")
print("=" * 50)

queries = [
    "как исправить синтаксическую ошибку в 1С",
    "остатки товара на складе",
    "как создать накладную в 1С",
    "как подключиться к базе данных 1С",
]

for q in queries:
    print(f"\nВопрос: {q}")
    print("-" * 30)
    result = rag_answer(q)
    if result:
        print(result[:500] + "..." if len(result) > 500 else result)
    else:
        print("🤷 Нет подходящих ответов в базе знаний")