# -*- coding: utf-8 -*-
"""Патч 001: InternalInfo ПЕРВЫМ узлом с записями (класс из argv)."""
import sys
from pathlib import Path

cls = sys.argv[1]
P = "3b9b2a01-7c4e-4b1d-9f2a-"


def entries(short_ids):
    out = ""
    for sh in short_ids:
        out += ("<xr:ContainedObject><xr:ClassId>" + cls + "</xr:ClassId>"
                + "<xr:ObjectId>" + P + sh + "</xr:ObjectId></xr:ContainedObject>")
    return out


p = Path(r"C:\1c_bases\cfg_src\Catalogs\3b9b2a01-7c4e-4b1d-9f2a-000000000001.xml")
x = p.read_text(encoding="utf-8")
x = x.replace("<InternalInfo/>", "<InternalInfo>" + entries(["000000000002", "000000000003"]) + "</InternalInfo>")
# переместить InternalInfo первым узлом: вырезать и вставить после <Catalog ...>
import re
m = re.search(r"<InternalInfo>.*?</InternalInfo>", x, flags=re.S)
node = m.group(0)
x = x[:m.start()] + x[m.end():]
x = re.sub(r'(<Catalog uuid="[^"]+">)', r"\1" + node, x, count=1)
p.write_text(x, encoding="utf-8")
print("001 first+content with", cls)
