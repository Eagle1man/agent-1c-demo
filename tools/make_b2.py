# -*- coding: utf-8 -*-
"""Вариант b2: процедуры 1-9 моста + пустое ПриОткрытии (тест времени компиляции)."""
import re
import shutil
from pathlib import Path

PROJ = Path(r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo")
SRC = Path(r"C:\1c_bases\epf_b1")
DST = Path(r"C:\1c_bases\epf_b2")
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
for f in DST.rglob("*"):
    if f.is_file():
        try:
            t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "B1" in t:
            f.write_text(t.replace("B1", "B2"), encoding="utf-8")
(DST / "B1.xml").rename(DST / "B2.xml")
(DST / "B1").rename(DST / "B2")

bsl = (PROJ / "1c" / "АгентМост.bsl").read_bytes().decode("utf-8-sig")
i_form = bsl.index("// === МОДУЛЬ ФОРМЫ ===")
form_code = bsl[i_form:].strip() + "\n"
# разбить на процедуры по границам
parts = re.split(r"(?m)^(?=Процедура |Функция )", form_code)
# parts[0] = заголовок+Перем; далее процедуры. Взять первые 9 процедур.
var_block = parts[0]
procs = parts[1:]
names = []
for pr in procs:
    m = re.match(r"(Процедура|Функция)\s+(\S+?)\(", pr)
    names.append(m.group(2) if m else "?")
print("procedures:", names)
keep = procs[:9]
out = var_block + "\n"
for pr in keep:
    out += "&НаКлиенте\n" + pr
    if not pr.endswith("\n"):
        out += "\n"
out += "&НаКлиенте\nПроцедура ПриОткрытии(Отказ)\nКонецПроцедуры\n"
mod = DST / "B2" / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
mod.write_text(out, encoding="utf-8")
print("b2 ready, kept:", [n for n in names[:9]])
