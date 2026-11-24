"""Вікна статистики Locust для soak/spike-тестів.

Locust у locust_stats_history.csv віддає перцентилі накопичувально (за весь тест), тому
деградацію затримки по ньому не видно. Цей модуль раз на SOAK_INTERVAL секунд пише
перцентилі саме за останнє вікно.

Підключається другим файлом до locustfile:
    locust -f loadtest/locustfile.py,loadtest/soak_stats.py ...

Змінні середовища:
    SOAK_WINDOWS_CSV - куди писати (типово soak_windows.csv)
    SOAK_INTERVAL    - розмір вікна, с (типово 10)
"""

import csv
import os
import time
from pathlib import Path

import gevent
from locust import events

OUT = os.getenv("SOAK_WINDOWS_CSV", "soak_windows.csv")
INTERVAL = float(os.getenv("SOAK_INTERVAL", "10"))

_times: list[float] = []
_failures = 0


def _q(sorted_vals: list[float], q: float) -> float:
    return round(sorted_vals[min(len(sorted_vals) - 1, int(q * len(sorted_vals)))], 1)


@events.request.add_listener
def _collect(response_time, exception, **_kwargs):
    global _failures
    _times.append(response_time)
    if exception:
        _failures += 1


def _writer(environment):
    global _failures
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    start = last = time.time()
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "timestamp",
                "elapsed_s",
                "users",
                "requests",
                "rps",
                "failures",
                "err_pct",
                "avg_ms",
                "p50_ms",
                "p95_ms",
                "p99_ms",
                "max_ms",
            ]
        )
        while True:
            gevent.sleep(INTERVAL)
            now = time.time()
            vals = sorted(_times)
            failed = _failures
            _times.clear()
            _failures = 0
            n = len(vals)
            dt = max(now - last, 0.001)
            last = now
            users = environment.runner.user_count if environment.runner else 0
            head = [int(now), round(now - start, 1), users, n, round(n / dt, 2), failed]
            if n:
                w.writerow(
                    head
                    + [
                        round(100 * failed / n, 3),
                        round(sum(vals) / n, 1),
                        _q(vals, 0.5),
                        _q(vals, 0.95),
                        _q(vals, 0.99),
                        round(vals[-1], 1),
                    ]
                )
            else:
                w.writerow(head + ["", "", "", "", "", ""])
            fh.flush()


@events.test_start.add_listener
def _start(environment, **_kwargs):
    gevent.spawn(_writer, environment)
