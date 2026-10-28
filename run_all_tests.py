# -*- coding: utf-8 -*-
"""Обёртка для запуска всех тестов контура улучшения в одном процессе."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TESTS = [
    "tests\\test_event_logger.py",
    "tests\\test_problem_registry.py",
    "tests\\test_permissions.py",
]


def main():
    failed = []
    for t in TESTS:
        print("=" * 60)
        print("RUNNING", t)
        print("=" * 60)
        res = subprocess.run(
            [sys.executable, "-m", "pytest", os.path.join(ROOT, t), "-v"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        print(res.stdout)
        if res.stderr:
            print("STDERR:\n", res.stderr)
        if res.returncode != 0:
            failed.append(t)
    print("=" * 60)
    if failed:
        print("FAILED:", failed)
        sys.exit(1)
    print("ALL TESTS PASSED")
