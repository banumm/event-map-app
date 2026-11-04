#!/usr/bin/env python3
"""
Запуск всех тестов проекта с отчётом о покрытии.

Использование (из корня репозитория):
    python scripts/run_tests.py

Скрипт последовательно запускает:
    users-service      — Django TestCase + SimpleTestCase;
    events-service     — pytest (unit + Flask test client);
    attendance-service — pytest (unit + Flask test client).

Для каждого сервиса создаётся отдельный файл данных coverage в
`.coverage-data/`, затем печатается отчёт `coverage report -m`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COVERAGE_DIR = ROOT / ".coverage-data"

SERVICES = [
    {
        "name": "users-service",
        "cwd": ROOT / "users-service",
        "command": [
            sys.executable, "-m", "coverage", "run",
            "--source=accounts",
            "--omit=accounts/tests.py,accounts/tests_unit.py,"
            "accounts/migrations/*,accounts/management/*",
            "manage.py", "test", "--verbosity", "1",
        ],
    },
    {
        "name": "events-service",
        "cwd": ROOT / "events-service",
        "command": [
            sys.executable, "-m", "coverage", "run",
            "--source=.",
            "--omit=tests/*,verify*.py,alembic/*",
            "-m", "pytest", "-q",
        ],
    },
    {
        "name": "attendance-service",
        "cwd": ROOT / "attendance-service",
        "command": [
            sys.executable, "-m", "coverage", "run",
            "--source=.",
            "--omit=tests/*,verify.py",
            "-m", "pytest", "-q",
        ],
    },
]


def main() -> int:
    COVERAGE_DIR.mkdir(parents=True, exist_ok=True)
    failures = []

    for service in SERVICES:
        name = service["name"]
        coverage_file = COVERAGE_DIR / f"{name}.coverage"
        coverage_file.unlink(missing_ok=True)

        env = os.environ.copy()
        env["COVERAGE_FILE"] = str(coverage_file)

        print(f"\n=== {name} ===", flush=True)
        run = subprocess.run(service["command"], cwd=service["cwd"], env=env)
        if run.returncode != 0:
            failures.append(name)
            continue

        subprocess.run(
            [sys.executable, "-m", "coverage", "report", "-m"],
            cwd=service["cwd"],
            env=env,
        )

    print("\n=== Итог ===")
    if failures:
        print("Тесты упали в сервисах: " + ", ".join(failures))
        return 1
    print("Все тесты прошли. Отчёты coverage: .coverage-data/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
