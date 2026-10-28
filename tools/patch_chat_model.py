# -*- coding: utf-8 -*-
"""Патч chat_service.py: параметр --model (переключение модели без правок кода)."""
from pathlib import Path

P = Path(r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo\agent\chat_service.py")
s = P.read_text(encoding="utf-8-sig")
if '"--model"' in s:
    print("уже пропатчено")
    raise SystemExit(0)

old = '    ap.add_argument("--mock", action="store_true", help="эмулятор 1С (без 1С)")'
new = ('    ap.add_argument("--model", default=QWEN_MODEL,\n'
       '                    help="модель Ollama, например qwen2.5:1.5b или qwen3:4b")\n'
       '    ap.add_argument("--mock", action="store_true", help="эмулятор 1С (без 1С)")')
assert old in s, "не найден разбор аргументов"
s = s.replace(old, new, 1)

old2 = '    svc = ChatService(args.exchange, args.profile, use_mock=args.mock)'
new2 = ('    # модель можно переключить без правок кода: --model qwen3:4b\n'
        '    import web_app as _web\n'
        '    _web.QWEN_MODEL = args.model\n'
        '    globals()["QWEN_MODEL"] = args.model\n'
        '    svc = ChatService(args.exchange, args.profile, use_mock=args.mock)')
assert old2 in s, "не найден запуск службы"
s = s.replace(old2, new2, 1)

P.write_text(s, encoding="utf-8")
print("патч модели применён; байт:", len(s.encode("utf-8")))
