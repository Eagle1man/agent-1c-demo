import re
from pathlib import Path

root = Path(r"D:\agent-1c-demo")
xml = (root / "build" / "epf_src" / "АгентМост" / "Forms" / "Форма" / "Ext" / "Form.xml").read_text(encoding="utf-8-sig")
bsl = (root / "1c" / "АгентМост.bsl").read_text(encoding="utf-8-sig")

attrs = re.findall(r'<Attribute name="([^"]+)"', xml)
print("реквизиты формы:", attrs)

perms = re.findall(r"^\s*Перем\s+([A-Za-zА-Яа-я_0-9]+)", bsl, re.M)
print("Перем в модуле:", perms)
print("пересечение:", [p for p in perms if p in attrs])
