# -*- coding: utf-8 -*-
"""Запуск 1C-команды с перехватом диалогов (pywinauto, только окна процесса).
Использование: py tools\\probe_1c.py <таймаут_сек> -- <аргументы 1cv8t...>
Результат — в probe_out.txt (UTF-8) рядом со скриптом."""
import shlex
import subprocess
import sys
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "probe_out.txt"


def dump_proc_windows(pid):
    from pywinauto import Desktop
    out = []
    for w in Desktop(backend="uia").windows():
        try:
            if w.process_id() != pid:
                continue
            title = w.window_text()
        except Exception:
            continue
        texts = []
        try:
            for c in w.descendants():
                try:
                    t = c.window_text()
                except Exception:
                    continue
                if t and t.strip() and t not in texts:
                    texts.append(t.strip())
        except Exception:
            pass
        out.append((title or "<no title>", texts[:30]))
    return out


def main():
    sep = sys.argv.index("--")
    timeout = int(sys.argv[1])
    args = sys.argv[sep + 1:]
    lines = ["CMD: " + " ".join(args)]
    p = subprocess.Popen([EXE] + args)
    lines.append("PID: " + str(p.pid))
    seen = set()
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(3)
        if p.poll() is not None:
            lines.append("PROCESS EXITED code=" + str(p.returncode))
            break
        try:
            wins = dump_proc_windows(p.pid)
        except Exception as exc:
            lines.append("enum error: " + str(exc))
            continue
        if not wins:
            lines.append("t+%ds: no windows yet" % int(time.time() - t0))
            continue
        for title, texts in wins:
            key = (title, tuple(texts))
            if key not in seen:
                seen.add(key)
                lines.append("=== WINDOW: " + title)
                for t in texts:
                    lines.append("   | " + t[:300])
    if p.poll() is None:
        lines.append("STILL RUNNING -> killing")
        p.kill()
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote " + str(OUT))


if __name__ == "__main__":
    main()
