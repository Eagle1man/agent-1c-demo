"""Остановить процессы, в командной строке которых есть заданная подстрока.

    py tools/kill_by_cmdline.py opcua_test_server
Нужен, чтобы перезапускать фоновые сервисы (панель, тестовый стенд) после правок.
"""
import argparse
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("match")
    args = ap.parse_args()
    out = subprocess.run(
        ["wmic", "process", "get", "processid,commandline", "/format:csv"],
        capture_output=True, text=True, encoding="cp866").stdout
    killed = 0
    for line in out.splitlines():
        if args.match not in line:
            continue
        parts = [p.strip() for p in line.split(",") if p.strip()]
        for p in reversed(parts):
            if p.isdigit():
                subprocess.run(["taskkill", "/PID", p, "/F"], capture_output=True)
                print("остановлен", p)
                killed += 1
                break
    print("итого:", killed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
