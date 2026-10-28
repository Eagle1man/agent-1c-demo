# -*- coding: utf-8 -*-
"""Порядок полей в форме: История (сверху) -> Фраза -> Статус."""
from pathlib import Path

P = Path(r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo\tools\gen_epf_most.py")
lines = P.read_text(encoding="utf-8-sig").splitlines()
hist = [l for l in lines if "<InputField name=\"История\"" in l]
mult = [l for l in lines if "MultiLine>true" in l]
assert hist and mult, "не найдены строки поля История"
idx_phr = next(i for i, l in enumerate(lines) if "<InputField name=\"Фраза\"" in l)
lines = [l for l in lines if l not in (hist[0], mult[0])]
idx_phr = next(i for i, l in enumerate(lines) if "<InputField name=\"Фраза\"" in l)
lines[idx_phr:idx_phr] = [hist[0], mult[0]]
P.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("порядок полей обновлён")
