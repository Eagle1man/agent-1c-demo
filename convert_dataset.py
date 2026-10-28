# Convert 1C_Forums dataset to jsonl files
import json
from pathlib import Path
from datasets import load_dataset

BASE = Path('D:/1c_ai_data')
target = BASE / '1c_forums_converted'
target.mkdir(parents=True, exist_ok=True)

ds = load_dataset('arefaste/1C_Forums')
print('Dataset loaded, converting...')

count = 0
for rec in ds['train']:
    prompt = rec.get('prompt', '') or ''
    think = rec.get('think_process', '') or ''
    solution = rec.get('solution', '') or ''
    if prompt:
        text = 'ВОПРОС: ' + prompt + '\n'
        if think: text += 'ЛОГИКА: ' + think + '\n'
        if solution: text += 'РЕШЕНИЕ: ' + solution + '\n'
        with open(target / ('forum_' + str(count) + '.jsonl'), 'w', encoding='utf-8') as f:
            json.dump({'prompt': prompt, 'think_process': think, 'solution': solution, 'text': text}, f, ensure_ascii=False)
        count += 1
        if count % 5000 == 0:
            print('Processed: ' + str(count))

print('Done! Total:', count)