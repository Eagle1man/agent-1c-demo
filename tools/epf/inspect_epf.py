from pathlib import Path

root = Path(r"D:\agent-1c-demo")
mod = root / "build" / "epf_src" / "Обработка" / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
src = root / "1c" / "АгентМост.bsl"

for p in (mod, src):
    print(p, p.stat().st_size, "bytes")

lines = mod.read_text(encoding="utf-8-sig").splitlines()
print("\nстрок в модуле epf:", len(lines))
print("\n--- строки 575-595 ---")
for i in range(574, min(595, len(lines))):
    print(f"{i+1:4}: {lines[i]}")
