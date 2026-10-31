import re
from pathlib import Path

root = Path(r"D:\agent-1c-demo")
xml = (root / "build" / "epf_src" / "АгентМост" / "Forms" / "Форма" / "Ext" / "Form.xml").read_text(encoding="utf-8-sig")
m = re.search(r'<Attribute name="ПутьКExchange".*?</Attribute>', xml, re.S)
print("--- описание реквизита ПутьКExchange ---")
print(m.group(0) if m else "не найден")

bsl = (root / "1c" / "АгентМост.bsl").read_text(encoding="utf-8-sig").splitlines()
print("\n--- ПриОткрытии ---")
for i, l in enumerate(bsl, 1):
    if "ПриОткрытии" in l:
        for j in range(i - 1, min(len(bsl), i + 12)):
            print(f"{j+1:4}: {bsl[j]}")
