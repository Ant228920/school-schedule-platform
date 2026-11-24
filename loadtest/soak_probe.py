"""Зонд для soak-тесту: з'єднання БД, потоки/дескриптори застосунку, пам'ять Redis.

Доповнює monitor.py (CPU/RAM). Дозволяє побачити витік з'єднань і дескрипторів.

    python loadtest/soak_probe.py --out loadtest/results/soak/probe.csv --interval 10

Запускати з кореня проєкту з тими ж змінними середовища (DB_NAME, REDIS_URL), що й застосунок.
Якщо БД чи Redis недоступні, відповідні колонки лишаються порожніми.
"""

import argparse
import csv
import signal
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

running = True


def _stop(*_):
    global running
    running = False


def app_processes() -> list[psutil.Process]:
    found = []
    for p in psutil.process_iter(["pid", "cmdline"]):
        cmd = " ".join(p.info["cmdline"] or [])
        if "uvicorn" in cmd and "soak_probe" not in cmd:
            found.append(p)
    return found


def app_numbers(procs: list[psutil.Process], db_port: int):
    threads = handles = conns = 0
    for p in procs:
        try:
            threads += p.num_threads()
            handles += p.num_handles() if hasattr(p, "num_handles") else p.num_fds()
            getter = getattr(p, "net_connections", None) or p.connections
            conns += sum(1 for c in getter(kind="tcp") if c.raddr and c.raddr.port == db_port and c.status == "ESTABLISHED")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return conns, threads, handles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--interval", type=float, default=10.0)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    engine = redis_client = None
    db_port = 5432
    try:
        from sqlalchemy import create_engine, text
        from src.core.config import settings

        db_port = settings.DB_PORT
        engine = create_engine(settings.database_url, pool_size=1, max_overflow=0, pool_pre_ping=True)
        if settings.REDIS_URL:
            import redis

            redis_client = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=1)
    except Exception as exc:  # зонд не має падати через відсутність БД/Redis
        print(f"probe: БД/Redis недоступні ({exc!r}), відповідні колонки будуть порожні", file=sys.stderr, flush=True)

    sql = None
    if engine is not None:
        sql = text(
            "select count(*), "
            "count(*) filter (where state = 'active'), "
            "count(*) filter (where state = 'idle'), "
            "count(*) filter (where state like 'idle in transaction%') "
            "from pg_stat_activity where datname = current_database() and pid <> pg_backend_pid()"
        )

    start = time.time()
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "timestamp",
                "elapsed_s",
                "pg_total",
                "pg_active",
                "pg_idle",
                "pg_idle_in_tx",
                "app_db_conns",
                "app_threads",
                "app_handles",
                "redis_used_mb",
                "redis_keys",
                "redis_hits",
                "redis_misses",
            ]
        )
        while running:
            time.sleep(args.interval)
            try:
                pg = ["", "", "", ""]
                if engine is not None:
                    try:
                        with engine.connect() as conn:
                            pg = list(conn.execute(sql).one())
                    except Exception as exc:
                        print(f"probe: помилка запиту до БД: {exc!r}", file=sys.stderr, flush=True)
                conns, threads, handles = app_numbers(app_processes(), db_port)
                rd = ["", "", "", ""]
                if redis_client is not None:
                    try:
                        mem = redis_client.info("memory")
                        st = redis_client.info("stats")
                        rd = [
                            round(mem["used_memory"] / 1024 / 1024, 2),
                            redis_client.dbsize(),
                            st.get("keyspace_hits", ""),
                            st.get("keyspace_misses", ""),
                        ]
                    except Exception as exc:
                        print(f"probe: помилка запиту до Redis: {exc!r}", file=sys.stderr, flush=True)
                now = time.time()
                w.writerow([int(now), round(now - start, 1), *pg, conns, threads, handles, *rd])
                fh.flush()
            except Exception as exc:
                print(f"probe error: {exc!r}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
