# -*- coding: utf-8 -*-
"""Патч корня M1: структура Properties как у seed2 + свежие TypeId/ValueId."""
import re
import uuid as _uuid
from pathlib import Path

p = Path(r"C:\1c_bases\epf_m1\M1.xml")
x = p.read_text(encoding="utf-8")

syn_block = ("<Synonym><v8:item><v8:lang></v8:lang><v8:content>M1</v8:content>"
             "</v8:item></Synonym>")
x = re.sub(r"<Synonym/>", syn_block, x, count=1)
x = x.replace("</Properties>",
              "<AuxiliaryForm/></Properties>" if "<AuxiliaryForm/>" not in x else "</Properties>")
# свежие TypeId/ValueId для GeneratedType
x = re.sub(r"<xr:TypeId>[0-9a-f-]+</xr:TypeId>",
           "<xr:TypeId>" + str(_uuid.uuid4()) + "</xr:TypeId>", x, count=1)
x = re.sub(r"<xr:ValueId>[0-9a-f-]+</xr:ValueId>",
           "<xr:ValueId>" + str(_uuid.uuid4()) + "</xr:ValueId>", x, count=1)
p.write_text(x, encoding="utf-8")
print("m1 root patched")
