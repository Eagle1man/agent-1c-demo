# -*- coding: utf-8 -*-
"""Патч tools/gen_epf_most.py: диалог-код вырезан (живёт в .bsl),
в форму добавлены реквизиты История/Статус и многострочное поле истории."""
from pathlib import Path

P = Path(r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo\tools\gen_epf_most.py")
t = P.read_text(encoding="utf-8-sig")
if '"История"' in t:
    print("уже пропатчено")
    raise SystemExit(0)

start = t.index('form_code_out += """')
end = t.index('root = (DECL + NS', start)
note = ("# Диалоговое окно с нейросетью живёт в 1c/АгентМост.bsl (блок «ДИАЛОГ С\n"
        "# НЕЙРОСЕТЬЮ»), реквизиты формы — ниже в form_xml.\n"
        "assert \"ПроверитьФразуДиалога\" in form_code_out, \"в .bsl нет кода диалога\"\n\n")
t = t[:start] + note + t[end:]

lines = t.splitlines()
out = []
for ln in lines:
    out.append(ln)
    ind = ln[:len(ln) - len(ln.lstrip())]
    if "<Attribute name=\"Фраза\"" in ln:
        out.append(ind + "+ '<Attribute name=\"История\" id=\"4\"><Type><v8:Type>xs:string</v8:Type></Type></Attribute>\\n'")
        out.append(ind + "+ '<Attribute name=\"Статус\" id=\"5\"><Type><v8:Type>xs:string</v8:Type></Type></Attribute>\\n'")
    if "<InputField name=\"Фраза\"" in ln:
        out.append(ind + "+ '<InputField name=\"История\" id=\"30\"><DataPath>История</DataPath>'")
        out.append(ind + "+ '<MultiLine>true</MultiLine><Height>14</Height></InputField>\\n'")
        out.append(ind + "+ '<InputField name=\"Статус\" id=\"31\"><DataPath>Статус</DataPath></InputField>\\n'")

t2 = "\n".join(out) + "\n"
P.write_text(t2, encoding="utf-8")
print("генератор пропатчен; байт:", len(t2.encode("utf-8")))
print("старый диалог остался:", "ПонятьФразу" in t2, "| История добавлена:", '"История"' in t2)
