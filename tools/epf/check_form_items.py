import re
from pathlib import Path

root = Path(r"D:\agent-1c-demo")
bsl = (root / "1c" / "АгентМост.bsl").read_text(encoding="utf-8-sig")
form_xml = (root / "build" / "epf_src" / "АгентМост" / "Forms" / "Форма" / "Ext" / "Form.xml").read_text(encoding="utf-8-sig")

used = sorted(set(re.findall(r"Элементы\.([A-Za-zА-Яа-я_0-9]+)", bsl)))
declared = sorted(set(re.findall(r"<Name>([^<]+)</Name>", form_xml)))

print("Используется в BSL:", len(used))
print(", ".join(used))
print("\nОбъявлено в форме:", len(declared))
print(", ".join(declared))
print("\nНет в форме (будет ошибка компиляции):")
missing = [n for n in used if n not in declared]
print(", ".join(missing) if missing else "нет")
