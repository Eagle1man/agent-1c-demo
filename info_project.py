# -*- coding: utf-8 -*-
import os

base = r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo"

print("=== Интерфейсный компонент ===")
for f in ['index.html', 'style.css', 'app.js']:
    p = os.path.join(base, 'agent', f)
    if os.path.exists(p):
        print(f"{f}: {os.path.getsize(p)} байт")
    else:
        print(f"{f}: NOT FOUND")

print("\n=== Проектная структура ===")
for r, d, fs in os.walk(base):
    for f in fs:
        if f in ('index.html', 'style.css', 'app.js') or (f.endswith('.py') and r.endswith('agent')):
            rel = os.path.relpath(os.path.join(r, f), base)
            print(f"  {rel}")

