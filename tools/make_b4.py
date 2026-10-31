# -*- coding: utf-8 -*-
"""Вариант b4: процедуры 1-4 + Перем + пустое ПриОткрытии."""
import re
import shutil
from pathlib import Path

PROJ = Path(r"D:\agent-1c-demo")
SRC = Path(r"C:\1c_bases\epf_b2")
DST = Path(r"C:\1c_bases\epf_b4")
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
for f in DST.rglob("*"):
    if f.is_file():
        try:
            t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "B2" in t:
            f.write_text(t.replace("B2", "B4"), encoding="utf-8")
(DST / "B2.xml").rename(DST / "B4.xml")
(DST / "B2").rename(DST / "B4")

bsl = (PROJ / "1c" / "АгентМост.bsl").read_bytes().decode("utf-8-sig")
i_form = bsl.index("// === МОДУЛЬ ФОРМЫ ===")
form_code = bsl[i_form:].strip() + "\n"
parts = re.split(r"(?m)^(?=Процедура |Функция )", form_code)
var_block = parts[0]
procs = parts[1:]
names = []
for pr in procs:
    m = re.match(r"(Процедура|Функция)\s+(\S+?)\(", pr)
    names.append(m.group(2) if m else "?")
keep = procs[:4]
out = var_block + "\n"
for pr in keep:
    out += "&НаКлиенте\n" + pr
    if not pr.endswith("\n"):
        out += "\n"
out += "&НаКлиенте\nПроцедура ПриОткрытии(Отказ)\nКонецПроцедуры\n"
mod = DST / "B4" / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
mod.write_text(out, encoding="utf-8")
print("b4 ready, kept:", [n for n in names[:4]])
