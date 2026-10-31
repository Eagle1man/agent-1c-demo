#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RAG-поиск в базе знаний 1С.

Что изменено и почему:
- прежняя модель `all-MiniLM-L6-v2` англоязычная; на русских вопросах она
  выдавала score 0.05–0.15 и нерелевантные документы. Заменена на
  `paraphrase-multilingual-MiniLM-L12-v2` (мультиязычная, уже в кеше);
- коллекция `1c_knowledge` собрана старой моделью, размерность не совпадает,
  поэтому поиск идёт по `1c_knowledge_v2` (собирается `rag/index_build.py`);
- «База знаний не построена» больше не возвращается как документ: пустой
  результат — это пустой список, а не псевдо-ответ. Иначе отказ базы
  выглядел как найденный факт.
"""
import os
from pathlib import Path

BASE = Path("D:/1c_ai_data")
CHROMA_DIR = Path(os.environ.get("RAG_CHROMA_DIR", BASE / "chroma_db"))
COLLECTION = os.environ.get("RAG_COLLECTION", "1c_knowledge_v2")
MODEL_NAME = os.environ.get(
    "RAG_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
except ImportError:
    SentenceTransformer = None
    chromadb = None

_model = _client = _collection = None
_init_error = None


def _init():
    global _model, _client, _collection, _init_error
    if _init_error:
        return
    if SentenceTransformer is None or chromadb is None:
        _init_error = "нет зависимостей sentence-transformers/chromadb"
        return
    if _model is None:
        try:
            _model = SentenceTransformer(MODEL_NAME)
        except Exception as exc:                       # noqa: BLE001
            _init_error = f"модель {MODEL_NAME} не загрузилась: {exc}"
            return
    if _client is None and CHROMA_DIR.exists():
        try:
            _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            _collection = _client.get_collection(COLLECTION)
        except Exception as exc:                       # noqa: BLE001
            _init_error = f"коллекция {COLLECTION} недоступна: {exc}"


def status():
    """Состояние поиска — для интерфейса и проверок, без догадок."""
    _init()
    return {
        "ready": _collection is not None,
        "collection": COLLECTION,
        "model": MODEL_NAME,
        "documents": _collection.count() if _collection is not None else 0,
        "error": _init_error,
    }


def search(query, top_k=3):
    """Найти документы. Пустой список — если базы нет или ничего не найдено."""
    _init()
    if _collection is None or not (query or "").strip():
        return []
    q_emb = _model.encode([query]).tolist()[0]
    res = _collection.query(query_embeddings=[q_emb], n_results=top_k,
                            include=["documents", "metadatas", "distances"])
    hits = []
    docs = res.get("documents") or [[]]
    metas = res.get("metadatas") or [[]]
    dists = res.get("distances") or [[]]
    for i, text in enumerate(docs[0]):
        meta = metas[0][i] if i < len(metas[0]) else {}
        dist = dists[0][i] if i < len(dists[0]) else 1.0
        hits.append({
            "text": text,
            "metadata": meta,
            "source": (meta or {}).get("source", "1C_Forums"),
            "score": round(1 - dist, 3),
        })
    return hits


def rag_answer(query):
    hits = search(query, top_k=3)
    if not hits:
        st = status()
        if not st["ready"]:
            return f"База знаний недоступна: {st['error']}"
        return "В базе знаний 1С не найдено подходящих документов."
    parts = []
    for h in hits:
        meta = h.get("metadata") or {}
        src = meta.get("file") or h.get("source")
        parts.append(f"--- {src} (релевантность {h['score']})\n{h['text'][:1200]}")
    return "По базе знаний 1С:\n\n" + "\n\n".join(parts)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "как исправить синтаксическую ошибку в 1С"
    print(status())
    for hit in search(q, top_k=3):
        print(f"\n[{hit['score']}] {hit['text'][:200]}")
