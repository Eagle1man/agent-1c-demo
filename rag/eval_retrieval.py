#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Оценка качества RAG-поиска: старый индекс против нового.

Зачем: «индекс построен» и «поиск находит ответ» — разные утверждения. Прежний
индекс (all-MiniLM-L6-v2, 384 измерения) на русских вопросах давал score
0.05–0.15 и нерелевантные документы. Этот скрипт измеряет попадание по
контрольным вопросам, чтобы замену можно было принять или отклонить по числу,
а не по впечатлению.

Метрики: hit@1, hit@3, MRR (средний обратный ранг первого попадания).
Попадание — в тексте документа есть любой из ожидаемых корней слова.

Запуск:
    py rag/eval_retrieval.py --collection 1c_knowledge --embedder minilm
    py rag/eval_retrieval.py --collection 1c_knowledge_v2 --embedder bge-m3
"""
import argparse
import json
import sys
import urllib.request

CASES = [
    ("как настроить СКД отчет чтобы в колонке дата были количество и сумма",
     ["скд", "колонк"]),
    ("закрытие месяца в бухгалтерии",
     ["закрыт", "месяц"]),
    ("ошибка при проведении документа реализация товаров и услуг",
     ["реализац", "проведен"]),
    ("как создать внешнюю печатную форму",
     ["печатн", "внешн"]),
    ("обмен данными между базами через план обмена",
     ["обмен", "план"]),
    ("почему не считается сумма в отчете",
     ["сумм", "отчет"]),
    ("настройка прав доступа пользователей",
     ["прав", "пользовател"]),
    ("как исправить синтаксическую ошибку в модуле",
     ["синтаксис", "ошибк"]),
]


def embed_query_bge(text):
    body = json.dumps({"model": "bge-m3", "input": [text]}).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/embed", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))["embeddings"][0]


def embed_query_minilm(model, text):
    return model.encode([text]).tolist()[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--collection", default="1c_knowledge_v2")
    ap.add_argument("--embedder", choices=["bge-m3", "minilm", "multilingual"],
                    default="multilingual")
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    import chromadb
    client = chromadb.PersistentClient(path="D:/1c_ai_data/chroma_db")
    col = client.get_collection(args.collection)

    st_model = None
    if args.embedder in ("minilm", "multilingual"):
        from sentence_transformers import SentenceTransformer
        name = ("sentence-transformers/all-MiniLM-L6-v2" if args.embedder == "minilm"
                else "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        st_model = SentenceTransformer(name)

    hit1 = hit3 = 0
    rr_sum = 0.0
    print(f"коллекция={args.collection}, эмбеддер={args.embedder}, документов={col.count()}\n")

    for query, roots in CASES:
        if args.embedder == "bge-m3":
            vec = embed_query_bge(query)
        else:
            vec = st_model.encode([query]).tolist()[0]
        res = col.query(query_embeddings=[vec], n_results=args.top_k,
                        include=["documents", "metadatas", "distances"])
        docs = res["documents"][0]
        ranks = []
        for i, doc in enumerate(docs):
            low = (doc or "").lower()
            if any(r in low for r in roots):
                ranks.append(i + 1)
        best = ranks[0] if ranks else None
        if best == 1:
            hit1 += 1
        if best is not None and best <= 3:
            hit3 += 1
        if best is not None:
            rr_sum += 1.0 / best

        top = docs[0][:90].replace("\n", " ") if docs else ""
        score = round(1 - res["distances"][0][0], 3) if docs else 0
        print(f"[{'OK ' if best else 'MISS'}] rank={best} score={score} | {query[:60]}")
        print(f"        top1: {top}")

    n = len(CASES)
    print(f"\nИТОГ: hit@1={hit1}/{n} ({hit1/n:.0%}), "
          f"hit@3={hit3}/{n} ({hit3/n:.0%}), MRR={rr_sum/n:.2f}")
    return 0 if hit3 >= n * 0.6 else 1


if __name__ == "__main__":
    sys.exit(main())
