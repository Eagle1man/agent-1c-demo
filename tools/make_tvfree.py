# -*- coding: utf-8 -*-
"""Вариант tvfree: поле БЕЗ реквизита (свободное), как задумано в .bsl."""
import shutil
from pathlib import Path

SRC = Path(r"C:\1c_bases\epf_tvfull")
DST = Path(r"C:\1c_bases\epf_tvfree")
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
            f.write_text(t.replace("TestFull", "TestFree"), encoding="utf-8")
(DST / "TestFull.xml").rename(DST / "TestFree.xml")
(DST / "TestFull").rename(DST / "TestFree")
fp = DST / "TestFree" / "Forms" / "Форма" / "Ext" / "Form.xml"
t = fp.read_text(encoding="utf-8")
# убрать реквизит ПутьКExchange, поле оставить свободным (без DataPath)
import re
t = re.sub(r'<Attribute name="ПутьКExchange".*?</Attribute>', '', t, flags=re.S)
t = t.replace('<InputField name="ПутьКExchange" id="10"><DataPath>ПутьКExchange</DataPath></InputField>',
              '<InputField name="ПутьКExchange" id="10"/>')
fp.write_text(t, encoding="utf-8")
print("tvfree ready")
