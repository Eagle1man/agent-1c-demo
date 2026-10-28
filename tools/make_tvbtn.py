# -*- coding: utf-8 -*-
"""Вариант tvbtn: команды + кнопки, БЕЗ поля. Локализация падения."""
import shutil
from pathlib import Path

SRC = Path(r"C:\1c_bases\epf_tvfull")
DST = Path(r"C:\1c_bases\epf_tvbtn")
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
for f in DST.rglob("*"):
    if f.is_file():
        try:
            t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "TestFull" in t:
            f.write_text(t.replace("TestFull", "TestBtn"), encoding="utf-8")
(DST / "TestFull.xml").rename(DST / "TestBtn.xml")
(DST / "TestFull").rename(DST / "TestBtn")
fp = DST / "TestBtn" / "Forms" / "Форма" / "Ext" / "Form.xml"
t = fp.read_text(encoding="utf-8")
import re
# убрать атрибут пути и поле ввода
t = re.sub(r'<Attribute name="ПутьКExchange".*?</Attribute>', '', t, flags=re.S)
t = t.replace('<InputField name="ПутьКExchange" id="10"><DataPath>ПутьКExchange</DataPath></InputField>', '')
fp.write_text(t, encoding="utf-8")
print("tvbtn ready")
