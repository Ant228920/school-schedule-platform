"""Збір ресурсів сервера (CPU, RAM) раз на секунду в CSV.

    python loadtest/monitor.py --out loadtest/results/baseline/resources.csv

CPU процесів - у % одного ядра (на багатоядерній машині може перевищувати 100).
Процеси шукаються за фрагментом командного рядка: застосунок - "uvicorn", БД - "postgres",
генератор навантаження - "locust".
"""

import argparse
import csv
import signal
import time
from pathlib import Path

import psutil

GROUPS = {"app": "uvicorn", "db": "postgres", "locust": "locust"}
running = True


def _stop(*_):
    global running
    running = False


def find_group(fragment: str, cache: dict[int, psutil.Process]) -> list[psutil.Process]:
    """Повертає процеси групи; об'єкти кешуються, щоб cpu_percent мав базу для порівняння."""
    alive = {}
    for p in psutil.process_iter(["pid", "cmdline"]):
        cmd = " ".join(p.info["cmdline"] or [])
        if fragment in cmd and "monitor.py" not in cmd:
            alive[p.pid] = cache.get(p.pid) or p
    for pid in list(cache):
        if pid not in alive:
            del cache[pid]
    cache.update(alive)
    return list(alive.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    caches = {name: {} for name in GROUPS}
    psutil.cpu_percent(interval=None)
    start = time.time()

    with open(args.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "timestamp",
                "elapsed_s",
                "sys_cpu_pct",
                "sys_ram_used_mb",
                "sys_ram_pct",
                "app_cpu_pct",
                "app_rss_mb",
                "db_cpu_pct",
                "db_rss_mb",
                "locust_cpu_pct",
            ]
        )
        while running:
            time.sleep(args.interval)
            row = {}
            for name, fragment in GROUPS.items():
                cpu = rss = 0.0
                for p in find_group(fragment, caches[name]):
                    try:
                        cpu += p.cpu_percent(interval=None)
                        rss += p.memory_info().rss / 1024 / 1024
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                row[name] = (cpu, rss)
            vm = psutil.virtual_memory()
            now = time.time()
            w.writerow(
                [
                    int(now),
                    round(now - start, 1),
                    psutil.cpu_percent(interval=None),
                    round((vm.total - vm.available) / 1024 / 1024, 1),
                    vm.percent,
                    round(row["app"][0], 1),
                    round(row["app"][1], 1),
                    round(row["db"][0], 1),
                    round(row["db"][1], 1),
                    round(row["locust"][0], 1),
                ]
            )
            fh.flush()


if __name__ == "__main__":
    main()
