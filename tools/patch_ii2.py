# -*- coding: utf-8 -*-
"""Тест: InternalInfo пустым в КОНЦЕ объекта."""
from pathlib import Path

p = Path(r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo\tools\gen_cfg_v1.py")
s = p.read_text(encoding="utf-8")
# 1. Убрать все вызовы ii(...) вместе с прилежащими переносами
import re
s = re.sub(r'\s*\+ ii\([^)]*\) \+ "\\n"', '', s)
# 2. Вставить пустой InternalInfo перед закрывающими тегами объектов
s = s.replace('+ T + T + \'</ChildObjects>\' + "\\n"\n    + T + \'</Catalog>\'',
              '+ T + T + \'</ChildObjects>\' + "\\n"\n    + T + \'<InternalInfo/>\\n\'\n    + T + \'</Catalog>\'')
s = s.replace('+ T + T + T + \'</ChildObjects>\' + "\\n"\n    + T + T + T + \'</TabularSection>\'',
              '+ T + T + T + \'</ChildObjects>\' + "\\n"\n    + T + T + T + \'<InternalInfo/>\\n\'\n    + T + T + T + \'</TabularSection>\'')
s = s.replace('+ T + T + \'</ChildObjects>\' + "\\n"\n    + T + \'</Document>\'',
              '+ T + T + \'</ChildObjects>\' + "\\n"\n    + T + \'<InternalInfo/>\\n\'\n    + T + \'</Document>\'')
s = s.replace('+ T + T + \'</ChildObjects>\' + "\\n"\n    + T + \'</Configuration>\'',
              '+ T + T + \'</ChildObjects>\' + "\\n"\n    + T + \'<InternalInfo/>\\n\'\n    + T + \'</Configuration>\'')
s = s.replace('+ T + T + \'<ChildObjects/>\' + "\\n"\n    + T + \'</Catalog>\'',
              '+ T + T + \'<ChildObjects/>\' + "\\n"\n    + T + \'<InternalInfo/>\\n\'\n    + T + \'</Catalog>\'')
p.write_text(s, encoding="utf-8")
print("remain ii calls:", s.count("ii(") - s.count("def ii("))
