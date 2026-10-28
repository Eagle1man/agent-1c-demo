# -*- coding: utf-8 -*-
"""Починить DefaultForm в корне seed2 (имя формы побито однострочником)."""
import re
from pathlib import Path

p = Path(r"C:\1c_bases\epf_seed2\SeedData.xml")
x = p.read_text(encoding="utf-8")
x2 = re.sub(r"<DefaultForm>.*?</DefaultForm>",
            "<DefaultForm>ExternalDataProcessor.SeedData.Form.Форма</DefaultForm>", x)
assert x2 != x or "SeedData.Form.Форма" in x
p.write_text(x2, encoding="utf-8")
print("fixed:", "SeedData.Form.Форма" in p.read_text(encoding="utf-8"))
