"""Найти и остановить запущенные panel_server.py (для перезапуска после правок).

Печатает pid, при --kill завершает процесс. Нужен, потому что сервер держит
порт и старый код продолжает отвечать после правок.
"""
import argparse
import subprocess
import sys


def pids():
    out = subprocess.run(
        ["wmic", "process", "get", "processid,commandline", "/format:csv"],
        capture_output=True, text=True, encoding="cp866").stdout
    found = []
    for line in out.splitlines():
        if "panel_server" in line:
            parts = [p.strip() for p in line.split(",") if p.strip()]
            for p in reversed(parts):
                if p.isdigit():
                    found.append(int(p))
                    break
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kill", action="store_true")
    args = ap.parse_args()
    found = pids()
    print("найдено:", found or "ничего")
    if args.kill:
        for pid in found:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                           capture_output=True)
            print("остановлен", pid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
