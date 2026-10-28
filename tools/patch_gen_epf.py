# -*- coding: utf-8 -*-
"""Патч генератора EPF: диалог-код убран (живёт в .bsl), в форму добавлены
реквизиты История/Статус и многострочное поле истории."""
from pathlib import Path

P = Path(r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo\tools\gen_epf_most.py")
t = P.read_text(encoding="utf-8-sig")
if '"История"' in t:
    print("уже пропатчено")
    raise SystemExit(0)

# --- 1) вырезаем встроенный старый диалог (ПонятьФразу и т.п.) ---
start = t.index('form_code_out += """')
end = t.index('root = (DECL + NS', start)
note = (
    '# Диалоговое окно с нейросетью живёт в 1c/АгентМост.bsl (блок «ДИАЛОГ С\n'
    '# НЕЙРОСЕТЬЮ»), а реквизиты формы (Фраза/История/Статус) — в form_xml ниже.\n'
    'assert "ПроверитьФразуДиалога" in form_code_out, "в .bsl нет кода диалога"\n\n'
)
t = t[:start] + note + t[end:]

# --- 2) реквизиты формы ---
old_attr = ('+ ''<Attribute name="Фраза" id="3"><Type><v8:Type>xs:string</v8:Type></Type></Attribute>\\n''')
new_attr = (
    old_attr + '\n'
    '            + ''<Attribute name="История" id="4"><Type><v8:Type>xs:string</v8:Type></Type></Attribute>\\n''' + '\n'
    '            + ''<Attribute name="Статус" id="5"><Type><v8:Type>xs:string</v8:Type></Type></Attribute>\\n'''
)
assert old_attr in t, "не найден реквизит Фраза в form_xml"
t = t.replace(old_attr, new_attr, 1)

# --- 3) поля формы: многострочная история и статус ---
old_field = ('+ ''<InputField name="Фраза" id="20"><DataPath>Фраза</DataPath></InputField>\\n''')
new_field = (
    old_field + '\n'
    '            + ''<InputField name="История" id="30"><DataPath>История</DataPath>''' + '\n'
    '            + ''<MultiLine>true</MultiLine><Height>14</Height></InputField>\\n''' + '\n'
    '            + ''<InputField name="Статус" id="31"><DataPath>Статус</DataPath></InputField>\\n'''
)
assert old_field in t, "не найдено поле Фраза"
t = t.replace(old_field, new_field, 1)

P.write_text(t, encoding="utf-8")
print("генератор пропатчен; байт:", len(t.encode("utf-8")))
print("остался ли старый диалог:", "ПонятьФразу" in t)
