#!/usr/bin/env python
# Debug RAG-поиска - показывает все результаты с очками релевантности
import sys
sys.path.insert(0, 'rag')

# Импортируем внутренние функции
from search import _init, search, _model, _collection, _client

print("==" * 50)
print("🔍 ДЕБАГ RAG ПОИСКА")
print("==" * 50)

# Инициализация
_init()
print(f"✅ Модель: {str(_model)[:50]}...")
print(f"✅ Коллекция: {str(_collection)[:40]}...")
print(f"✅ Количество документов: {_collection.count()}")

# Тестовые запросы
queries = [
    "как исправить синтаксическую ошибку в 1С",
    "остатки товара на складе",
    "как создать накладную в 1С",
    "как подключиться к базе данных 1С",
]

for q in queries:
    print(f"\n{'='*50}")
    print(f"Вопрос: {q}")
    print(f"{'='*50}")
    
    # Получаем результаты без фильтра
    results = search(q, top_k=5)
    
    # Показываем детали
    for i, r in enumerate(results):
        score = r.get('score', 0)
        text = r.get('text', '')[:80] + '...' if len(r.get('text', '')) > 80 else r.get('text', '')
        print(f"  [{i+1}] Релевантность: {score:.2f} | {text}")

# Проверяем порог в search.py
print(f"\n{'='*50}")
print("Детали поиска в search.py:")
print("  - Порог схожести: 0.3 (строка 44)")
print("  - N-Результатов: 3 (строка 43)")
print("  - Если все оценки < 0.3 - ничего не возвращается")

print(f"\n{'='*50}")
print("💡 РЕШЕНИЕ:")
print("  Уменьшить порог с 0.3 до 0.1 или 0.0, и добавить логирование")