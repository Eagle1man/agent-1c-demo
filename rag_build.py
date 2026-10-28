# RAG index builder for 1C AI Assistant
import json
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb

BASE = Path('D:/1c_ai_data')
CHROMA_DIR = BASE / 'chroma_db'
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

print('Loading embedding model...')
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

print('Loading documents from all 1C datasets...')
docs = []
count = 0

# 1. 1C_Forums (converted jsonl)
forums_dir = BASE / '1c_forums_converted'
if forums_dir.exists():
    jsonl_files = list(forums_dir.rglob('*.jsonl'))
    print('Found ' + str(len(jsonl_files)) + ' jsonl files in 1c_forums_converted')
    for jsonl_file in jsonl_files:
        print('   Reading: ' + jsonl_file.name)
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    rec = json.loads(line)
                    text = rec.get('text', '')
                    if text:
                        prompt = rec.get('prompt', '') or rec.get('question', '')
                        think = rec.get('think_process', '') or ''
                        solution = rec.get('solution', '') or rec.get('answer', '')
                        if prompt:
                            full_text = 'ВОПРОС: ' + prompt + '\n'
                            if think: full_text += 'ЛОГИКА: ' + think + '\n'
                            if solution: full_text += 'РЕШЕНИЕ: ' + solution + '\n'
                            docs.append({
                                'id': 'forum_' + str(count),
                                'text': full_text,
                                'metadata': {'source': '1C_Forums', 'prompt': prompt[:200]}
                            })
                            count += 1
                except: continue
# 2. 1C_Ebench
print('Checking 1C-Ebench...')
ebench_dir = BASE / '1c_ebench'
if ebench_dir.exists():
    files = list(ebench_dir.rglob('*.jsonl')) + list(ebench_dir.rglob('*.json'))
    print('Found ' + str(len(files)) + ' files in 1c_ebench')
    if len(files) == 0:
        print('No jsonl/json files, trying direct load...')
        try:
            from datasets import load_dataset
            ds = load_dataset('PruhaNLP/1C-Ebench', 'fastcode')
            target = BASE / '1c_ebench_converted'
            target.mkdir(parents=True, exist_ok=True)
            for i, rec in enumerate(ds['test']):
                if i >= 100: break
                prompt = rec.get('question', '') or ''
                think = rec.get('thought_process', '') or ''
                solution = rec.get('answer', '') or ''
                if prompt:
                    text = 'ВОПРОС: ' + prompt + '\n'
                    if think: text += 'ЛОГИКА: ' + think + '\n'
                    if solution: text += 'РЕШЕНИЕ: ' + solution + '\n'
                    with open(target / ('ebench_' + str(count) + '.jsonl'), 'w', encoding='utf-8') as f:
                        json.dump({'prompt': prompt, 'think_process': think, 'solution': solution, 'text': text}, f, ensure_ascii=False)
                    docs.append({
                        'id': 'ebench_' + str(count),
                        'text': text,
                        'metadata': {'source': '1C-Ebench', 'prompt': prompt[:200]}
                    })
                    count += 1
        except Exception as e:
            print('Error loading 1C-Ebench: ' + str(e))
# 3. Spider-1C
print('Checking Spider-1C...')
spider_dir = BASE / 'spider1c'
if spider_dir.exists():
    files = list(spider_dir.rglob('*.jsonl')) + list(spider_dir.rglob('*.json'))
    print('Found ' + str(len(files)) + ' files in spider1c')
    if len(files) > 0:
        try:
            from datasets import load_dataset
            ds = load_dataset('kavlab/Spider-1C')
            target = BASE / 'spider1c_converted'
            target.mkdir(parents=True, exist_ok=True)
            for i, rec in enumerate(ds['train']):
                if i >= 100: break
                question = rec.get('problem', '') or rec.get('question', '') or ''
                answer = rec.get('solution', '') or rec.get('answer', '') or ''
                thought = rec.get('thought_process', '') or rec.get('thought', '') or ''
                if question:
                    text = 'ВОПРОС: ' + question + '\n'
                    if thought: text += 'ЛОГИКА: ' + thought + '\n'
                    if answer: text += 'РЕШЕНИЕ: ' + answer + '\n'
                    docs.append({
                        'id': 'spider_' + str(count),
                        'text': text,
                        'metadata': {'source': 'Spider-1C', 'prompt': question[:200]}
                    })
                    count += 1
                    with open(target / ('spider_' + str(count-1) + '.jsonl'), 'w', encoding='utf-8') as f:
                        json.dump({'problem': question, 'thought_process': thought, 'solution': answer, 'text': text}, f, ensure_ascii=False)
        except Exception as e:
            print('Error loading Spider-1C: ' + str(e))
print('Total documents: ' + str(count))

if docs:
    print('Creating embeddings...')
    texts = [d['text'] for d in docs]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    
    print('Saving to ChromaDB...')
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection('1c_knowledge')
    
    # ChromaDB max batch size is 5461, so we need to add in batches
    MAX_BATCH = 5461
    total_added = 0
    
    for i in range(0, len(docs), MAX_BATCH):
        batch = docs[i:i + MAX_BATCH]
        batch_embeddings = embeddings[i:i + MAX_BATCH].tolist()
        
        collection.add(
            documents=[d['text'] for d in batch],
            embeddings=batch_embeddings,
            metadatas=[d['metadata'] for d in batch],
            ids=[d['id'] for d in batch]
        )
        total_added += len(batch)
        print(f'Added batch {i // MAX_BATCH + 1}: {len(batch)} documents (total: {total_added})')
    
    print('Index ready: ' + str(collection.count()) + ' documents')
    print('Storage: ' + str(CHROMA_DIR.resolve()))
    print('Storage: ' + str(CHROMA_DIR.resolve()))
else:
    print('No documents for indexing')