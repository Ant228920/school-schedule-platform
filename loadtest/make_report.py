"""Побудова графіків і підсумкових таблиць із результатів Locust + monitor.py.

    python loadtest/make_report.py baseline step

Для кожного прогону loadtest/results/<name>/ створюються:
    response_time.png  - затримка (p50, p95) і кількість користувачів у часі
    throughput.png     - RPS і помилки/с у часі
    resources.png      - CPU та RAM сервера у часі
    summary.md         - таблиці: загальні метрики, по ендпоінтах, ресурси (+ по ступенях навантаження)
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

RESULTS = Path(__file__).parent / "results"
BLUE, ORANGE, RED, GREEN, GRAY = "#2a6fdb", "#e08a1e", "#d1383d", "#2e9e5b", "#8a8f98"


def load(name: str):
    d = RESULTS / name
    stats = pd.read_csv(d / "locust_stats.csv")
    hist = pd.read_csv(d / "locust_stats_history.csv")
    hist = hist[hist["Name"] == "Aggregated"].copy()
    hist["t"] = hist["Timestamp"] - hist["Timestamp"].iloc[0]
    for col in ("50%", "95%"):
        hist[col] = pd.to_numeric(hist[col], errors="coerce").replace(0, float("nan"))
    res = pd.read_csv(d / "resources.csv")
    res["t"] = res["timestamp"] - hist["Timestamp"].iloc[0]
    return d, stats, hist, res


def users_axis(ax, hist):
    ax2 = ax.twinx()
    ax2.step(hist["t"], hist["User Count"], where="post", color=GRAY, alpha=0.6, lw=1.2, label="Користувачі")
    ax2.set_ylabel("Віртуальні користувачі", color=GRAY)
    ax2.tick_params(axis="y", colors=GRAY)
    return ax2


def chart_latency(d, name, hist):
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(hist["t"], hist["50%"], color=BLUE, label="p50")
    ax.plot(hist["t"], hist["95%"], color=RED, label="p95")
    if hist["95%"].max() > 20 * hist["95%"].median():
        ax.set_yscale("log")
    ax.set_xlabel("Час тесту, с")
    ax.set_ylabel("Час відповіді, мс")
    ax.set_title(f"Динаміка часу відповіді - {name}")
    ax.grid(alpha=0.25)
    users_axis(ax, hist)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(d / "response_time.png", dpi=140)
    plt.close(fig)


def chart_throughput(d, name, hist):
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(hist["t"], hist["Requests/s"], color=GREEN, label="RPS")
    ax.plot(hist["t"], hist["Failures/s"], color=RED, label="Помилки/с")
    ax.set_xlabel("Час тесту, с")
    ax.set_ylabel("Запитів за секунду")
    ax.set_title(f"Пропускна здатність - {name}")
    ax.grid(alpha=0.25)
    users_axis(ax, hist)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(d / "throughput.png", dpi=140)
    plt.close(fig)


def chart_resources(d, name, res):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 5.4), sharex=True)
    a1.plot(res["t"], res["app_cpu_pct"], color=BLUE, label="Застосунок (uvicorn)")
    a1.plot(res["t"], res["db_cpu_pct"], color=ORANGE, label="PostgreSQL")
    a1.plot(res["t"], res["locust_cpu_pct"], color=GRAY, label="Locust")
    a1.set_ylabel("CPU, % одного ядра")
    a1.set_title(f"Ресурси сервера - {name}")
    a1.grid(alpha=0.25)
    a1.legend(loc="upper right")
    a2.plot(res["t"], res["app_rss_mb"], color=BLUE, label="Застосунок, RSS")
    a2.plot(res["t"], res["db_rss_mb"], color=ORANGE, label="PostgreSQL, RSS")
    a2.set_ylabel("RAM, МБ")
    a2.set_xlabel("Час тесту, с")
    a2.grid(alpha=0.25)
    a2.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(d / "resources.png", dpi=140)
    plt.close(fig)


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def fmt_ms(v) -> str:
    v = float(v)
    return f"{v / 1000:.1f} с" if v >= 10000 else f"{v:.0f}"


def summary(name, stats, hist, res) -> str:
    out = [f"### Прогін `{name}`\n"]

    agg = stats[stats["Name"] == "Aggregated"].iloc[0]
    fail_pct = 100 * agg["Failure Count"] / max(agg["Request Count"], 1)
    out.append("**Загальні метрики**\n")
    out.append(
        md_table(
            pd.DataFrame(
                [
                    {
                        "Запитів": int(agg["Request Count"]),
                        "RPS (середній)": f"{agg['Requests/s']:.1f}",
                        "Error rate": f"{fail_pct:.2f}%",
                        "Latency avg, мс": fmt_ms(agg["Average Response Time"]),
                        "min, мс": fmt_ms(agg["Min Response Time"]),
                        "max, мс": fmt_ms(agg["Max Response Time"]),
                        "p50, мс": fmt_ms(agg["50%"]),
                        "p95, мс": fmt_ms(agg["95%"]),
                    }
                ]
            )
        )
    )

    rows = []
    for _, r in stats[stats["Name"] != "Aggregated"].iterrows():
        rows.append(
            {
                "Ендпоінт": r["Name"],
                "Запитів": int(r["Request Count"]),
                "Помилок": int(r["Failure Count"]),
                "avg, мс": fmt_ms(r["Average Response Time"]),
                "min, мс": fmt_ms(r["Min Response Time"]),
                "max, мс": fmt_ms(r["Max Response Time"]),
                "p95, мс": fmt_ms(r["95%"]),
                "RPS": f"{r['Requests/s']:.2f}",
            }
        )
    out.append("\n**По ендпоінтах**\n")
    out.append(md_table(pd.DataFrame(rows)))

    out.append("\n**Ресурси сервера** (CPU процесу - у % одного ядра)\n")
    out.append(
        md_table(
            pd.DataFrame(
                [
                    {
                        "Показник": "CPU застосунку (uvicorn)",
                        "Середнє": f"{res['app_cpu_pct'].mean():.1f}%",
                        "Максимум": f"{res['app_cpu_pct'].max():.0f}%",
                    },
                    {
                        "Показник": "CPU PostgreSQL",
                        "Середнє": f"{res['db_cpu_pct'].mean():.1f}%",
                        "Максимум": f"{res['db_cpu_pct'].max():.0f}%",
                    },
                    {
                        "Показник": "CPU всієї машини",
                        "Середнє": f"{res['sys_cpu_pct'].mean():.1f}%",
                        "Максимум": f"{res['sys_cpu_pct'].max():.0f}%",
                    },
                    {
                        "Показник": "RAM застосунку (RSS)",
                        "Середнє": f"{res['app_rss_mb'].mean():.0f} МБ",
                        "Максимум": f"{res['app_rss_mb'].max():.0f} МБ",
                    },
                    {
                        "Показник": "RAM машини (використано)",
                        "Середнє": f"{res['sys_ram_used_mb'].mean():.0f} МБ",
                        "Максимум": f"{res['sys_ram_used_mb'].max():.0f} МБ",
                    },
                ]
            )
        )
    )

    counts = hist["User Count"].value_counts()
    levels = [lvl for lvl, n in counts.items() if lvl > 0 and n >= 25]  # лише справжні плато, без проміжних значень розгону
    if len(levels) >= 3:  # ступінчастий прогін - таблиця по ступенях
        rows = []
        for lvl in sorted(levels):
            g = hist[hist["User Count"] == lvl].tail(30)  # остання частина ступеня, без розгону
            t_lo, t_hi = g["t"].min(), g["t"].max()
            r = res[(res["t"] >= t_lo) & (res["t"] <= t_hi)]
            rows.append(
                {
                    "Користувачів": int(lvl),
                    "RPS": f"{g['Requests/s'].mean():.0f}",
                    "Помилок/с": f"{g['Failures/s'].mean():.1f}",
                    "p50, мс": fmt_ms(g["50%"].median()) if g["50%"].notna().any() else "-",
                    "p95, мс": fmt_ms(g["95%"].median()) if g["95%"].notna().any() else "-",
                    "CPU app": f"{r['app_cpu_pct'].mean():.0f}%",
                    "CPU БД": f"{r['db_cpu_pct'].mean():.0f}%",
                }
            )
        out.append("\n**По ступенях навантаження** (остання половина кожного ступеня; p50/p95 - за запитами, що встигли завершитись)\n")
        out.append(md_table(pd.DataFrame(rows)))
    return "\n".join(out) + "\n"


def main():
    names = sys.argv[1:] or ["baseline"]
    for name in names:
        d, stats, hist, res = load(name)
        chart_latency(d, name, hist)
        chart_throughput(d, name, hist)
        chart_resources(d, name, res)
        (d / "summary.md").write_text(summary(name, stats, hist, res), encoding="utf-8")
        print(f"{name}: charts + summary.md -> {d}")


if __name__ == "__main__":
    main()
