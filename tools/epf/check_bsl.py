import re
from pathlib import Path

src = Path(r"D:\agent-1c-demo") / "1c" / "АгентМост.bsl"
lines = src.read_text(encoding="utf-8-sig").splitlines()

decl = re.compile(r"^\s*(Процедура|Функция|Процедуру|Функцию|КонецПроцедуры|КонецФункции)\b")
ret = re.compile(r"^\s*Возврат\s+(.+?);")

print("=== подозрительные объявления ===")
for i, l in enumerate(lines, 1):
    m = decl.match(l)
    if m and m.group(1) in ("Процедуру", "Функцию"):
        print(f"{i:4}: {l.strip()}")

print("\n=== процедуры, возвращающие значение ===")
stack = []
bad = 0
for i, l in enumerate(lines, 1):
    m = decl.match(l)
    if not m:
        continue
    kind = m.group(1)
    if kind in ("Процедура", "Функция"):
        stack.append((kind, i, l.strip()))
    elif kind in ("КонецПроцедуры", "КонецФункции"):
        if not stack:
            print(f"{i:4}: закрытие без открытия: {l.strip()}")
            continue
        k, start, text = stack.pop()
        expect = "КонецФункции" if k == "Функция" else "КонецПроцедуры"
        if expect != kind:
            print(f"{i:4}: {kind} закрывает {k} (строка {start})")
    elif kind in ("Процедуру", "Функцию"):
        # такие объявления не открывают блок в терминах 1С, но помечаем
        if stack:
            k, start, text = stack.pop()
        continue

# отдельный проход: возврат значения внутри процедуры
stack = []
for i, l in enumerate(lines, 1):
    m = decl.match(l)
    if m:
        kind = m.group(1).replace("у", "а").replace("ю", "я") if False else m.group(1)
        if kind in ("Процедура", "Функция"):
            stack.append((kind, i))
        elif kind in ("КонецПроцедуры", "КонецФункции") and stack:
            stack.pop()
        continue
    r = ret.match(l)
    if r and stack and stack[-1][0] == "Процедура" and r.group(1).strip():
        bad += 1
        print(f"{i:4}: Возврат значения в Процедуре (начало {stack[-1][1]}): {l.strip()[:80]}")
print(f"\nвсего таких возвратов: {bad}")
