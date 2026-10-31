#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Построение RAG-индекса 1С-форума с русскоязычной моделью эмбеддингов.

Зачем переписан: прежний индекс собран моделью all-MiniLM-L6-v2 (384 измерения,
англоязычная) по русским вопросам. Формально поиск работал, но релевантность
была 0.05–0.15, и на вопрос «закрытие месяца» возвращались обсуждения нумерации
страниц. Индекс считается заново через bge-m3 (1024 измерения, мультиязычная),
которая уже есть в локальном Ollama — без скачивания моделей.

Особенности:
- идемпотентность: уже вложенные id пропускаются, прогон можно прервать и
  продолжить (важно: 15 600 документов на CPU — это десятки минут);
- документ = вопрос + ответ, `think`-рассуждения в индекс не идут: это шум;
- метаданные хранят исходный вопрос и ответ, чтобы ответ можно было показать
  со ссылкой на источник.

Запуск:
    py rag/index_build.py --limit 300        # пилот
    py rag/index_build.py                    # полный индекс
    py rag/index_build.py --reset            # пересобрать с нуля
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path("D:/1c_ai_data")
SRC_DIR = BASE / "1c_forums_converted"
CHROMA_DIR = BASE / "chroma_db"

COLLECTION = "1c_knowledge_v2"
DEFAULT_EMBEDDER = "multilingual"
EMBEDDERS = {
    # Быстрый вариант: мультиязычная MiniLM уже лежит в кеше HuggingFace,
    # считает на CPU десятки документов в секунду.
    "multilingual": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    # Качественнее, но ~1 с/документ на CPU: полный индекс около 4 часов.
    "bge-m3": None,
}
OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embed"
BATCH = 32
# Длина текста для эмбеддинга: вопрос + начало ответа. Полный ответ хранится
# в метаданных и показывается пользователю как есть.
EMBED_CHARS = 700

_ST_MODEL = None


def _st_model(name):
    global _ST_MODEL
    if _ST_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _ST_MODEL = SentenceTransformer(name)
    return _ST_MODEL


def embed_ollama(texts, timeout=600):
    body = json.dumps({"model": "bge-m3", "input": list(texts)}).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_EMBED_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None
    vecs = data.get("embeddings")
    return vecs if isinstance(vecs, list) and len(vecs) == len(texts) else None


def embed_batch(texts, embedder):
    """Векторы пачки текстов. None — если модель недоступна."""
    if embedder == "bge-m3":
        return embed_ollama(texts)
    model = _st_model(EMBEDDERS[embedder])
    try:
        return model.encode(list(texts), batch_size=BATCH, show_progress_bar=False).tolist()
    except Exception:
        return None


def iter_docs(limit=None):
    """Документы индекса: (id, текст, метаданные)."""
    if not SRC_DIR.exists():
        raise SystemExit(f"нет каталога с исходниками: {SRC_DIR}")
    files = sorted(SRC_DIR.glob("*.jsonl"))
    if not files:
        raise SystemExit(f"в {SRC_DIR} нет *.jsonl")
    count = 0
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            prompt = str(rec.get("prompt") or "").strip()
            solution = str(rec.get("solution") or "").strip()
            if not prompt and not solution:
                continue
            doc_id = f"{path.stem}-{idx}"
            document = (prompt + "\nОТВЕТ: " + solution).strip()
            meta = {
                "source": "1C_Forums",
                "file": path.name,
                "prompt": prompt[:1500],
                "solution": solution[:4000],
            }
            yield doc_id, document[:8000], meta
            count += 1
            if limit and count >= limit:
                return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="сколько документов взять (0 — все)")
    ap.add_argument("--reset", action="store_true", help="удалить коллекцию и собрать заново")
    ap.add_argument("--collection", default=COLLECTION)
    ap.add_argument("--embedder", choices=sorted(EMBEDDERS), default=DEFAULT_EMBEDDER,
                    help="модель эмбеддингов: multilingual (быстро) или bge-m3 (качественно, долго)")
    args = ap.parse_args()

    try:
        import chromadb
    except ImportError:
        raise SystemExit("нет chromadb: установите зависимость")

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if args.reset:
        try:
            client.delete_collection(args.collection)
            print(f"коллекция {args.collection} удалена")
        except Exception:
            pass

    col = client.get_or_create_collection(
        args.collection, metadata={"hnsw:space": "cosine", "embed_model": args.embedder})

    # проверка модели до долгого прогона
    if embed_batch(["проверка модели эмбеддингов"], args.embedder) is None:
        raise SystemExit("модель эмбеддингов недоступна — индекс не построен")

    total_start = time.time()
    added = skipped = failed = 0
    pending = []

    def flush():
        nonlocal added, skipped, failed
        if not pending:
            return
        ids = [p[0] for p in pending]
        existing = set(col.get(ids=ids, include=[]).get("ids") or [])
        todo = [p for p in pending if p[0] not in existing]
        skipped += len(pending) - len(todo)
        pending.clear()
        if not todo:
            return
        vecs = embed_batch([p[1][:EMBED_CHARS] for p in todo], args.embedder)
        if vecs is None:
            failed += len(todo)
        else:
            col.add(ids=[p[0] for p in todo],
                    documents=[p[1] for p in todo],
                    metadatas=[p[2] for p in todo],
                    embeddings=vecs)
            added += len(todo)
        done = added + skipped
        rate = done / max(time.time() - total_start, 1e-6)
        print(f"  вложено: {added}, пропущено: {skipped}, сбоев: {failed} "
              f"({rate:.2f} док/с)", flush=True)

    for doc_id, document, meta in iter_docs(limit=args.limit or None):
        pending.append((doc_id, document, meta))
        if len(pending) >= BATCH:
            flush()

    flush()
    elapsed = time.time() - total_start
    print(f"\nготово: коллекция={args.collection}, вложено={added}, "
          f"пропущено={skipped}, сбоев={failed}, всего в коллекции={col.count()}, "
          f"время={elapsed:.0f} с")
    if failed:
        print("ЧАСТЬ ДОКУМЕНТОВ НЕ ВЛОЖЕНА — повторите запуск, он продолжит с места остановки")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
