"""Порівняльний звіт «ДО / ПІСЛЯ» оптимізації (ЛР №7) з результатів Locust + monitor.py.

    python loadtest/compare.py before_baseline after_baseline --labels ДО ПІСЛЯ --tag base
    python loadtest/compare.py before_step after_step --labels ДО ПІСЛЯ --tag step --step

Вхід: каталоги loadtest/results/<name>/ (locust_stats*.csv, resources.csv).
Вихід: loadtest/results/compare_<tag>/ - таблиця (comparison.md) і графіки (*.png).
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

RESULTS = Path(__file__).parent / "results"
PALETTE = ["#8a8f98", "#e08a1e", "#2a6fdb", "#2e9e5b", "#7b3fb0"]


def load(name: str):
    d = RESULTS / name
    stats = pd.read_csv(d / "locust_stats.csv")
    hist = pd.read_csv(d / "locust_stats_history.csv")
    hist = hist[hist["Name"] == "Aggregated"].copy()
    hist["t"] = hist["Timestamp"] - hist["Timestamp"].iloc[0]
    for col in ("50%", "95%"):
        hist[col] = pd.to_numeric(hist[col], errors="coerce").replace(0, float("nan"))
    res = pd.read_csv(d / "resources.csv")
    return stats, hist, res


def fmt_ms(v: float) -> str:
    return f"{v / 1000:.1f} с" if v >= 10000 else f"{v:.0f}"


def headline(name: str) -> dict:
    stats, _, res = load(name)
    agg = stats[stats["Name"] == "Aggregated"].iloc[0]
    n, fails = int(agg["Request Count"]), int(agg["Failure Count"])
    return {
        "Запитів": n,
        "RPS": float(agg["Requests/s"]),
        "Error rate, %": 100 * fails / max(n, 1),
        "avg, мс": float(agg["Average Response Time"]),
        "p50, мс": float(agg["50%"]),
        "p95, мс": float(agg["95%"]),
        "p99, мс": float(agg["99%"]),
        "CPU app (сер.), %": float(res["app_cpu_pct"].mean()),
        "CPU БД (сер.), %": float(res["db_cpu_pct"].mean()),
        "RAM app (сер.), МБ": float(res["app_rss_mb"].mean()),
    }


def delta(before: float, after: float, lower_is_better: bool) -> str:
    if before == 0:
        return "-"
    pct = 100 * (after - before) / before
    good = (pct < 0) == lower_is_better
    return f"{pct:+.0f}% {'✅' if good else '⚠️'}" if abs(pct) >= 1 else "≈0%"


LOWER_IS_BETTER = {"Error rate, %", "avg, мс", "p50, мс", "p95, мс", "p99, мс", "CPU app (сер.), %", "CPU БД (сер.), %", "RAM app (сер.), МБ"}


def md_table(rows: list[list[str]], header: list[str]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    out += ["| " + " | ".join(map(str, r)) + " |" for r in rows]
    return "\n".join(out)


def comparison_table(names: list[str]) -> str:
    data = {n: headline(n) for n in names}
    metrics = list(next(iter(data.values())))
    header = ["Метрика"] + names + (["Зміна (перший → останній)"] if len(names) > 1 else [])
    rows = []
    for m in metrics:
        vals = [data[n][m] for n in names]
        shown = [f"{v:.1f}" if isinstance(v, float) and v < 1000 else (fmt_ms(v) if m.endswith("мс") else f"{v:.0f}") for v in vals]
        row = [m] + shown
        if len(names) > 1 and m != "Запитів":
            row.append(delta(vals[0], vals[-1], m in LOWER_IS_BETTER))
        elif len(names) > 1:
            row.append(delta(vals[0], vals[-1], False))
        rows.append(row)
    return md_table(rows, header)


def endpoint_table(names: list[str]) -> str:
    frames = {}
    for n in names:
        stats, _, _ = load(n)
        frames[n] = stats[stats["Name"] != "Aggregated"].set_index("Name")
    endpoints = list(frames[names[0]].index)
    header = ["Ендпоінт"] + [f"avg/p95, мс ({n})" for n in names]
    rows = []
    for e in endpoints:
        row = [e]
        for n in names:
            f = frames[n]
            row.append(f"{fmt_ms(f.loc[e, 'Average Response Time'])} / {fmt_ms(f.loc[e, '95%'])}" if e in f.index else "-")
        rows.append(row)
    return md_table(rows, header)


def bar_chart(names: list[str], labels: list[str], out: Path):
    data = [headline(n) for n in names]
    panels = [("RPS", "Пропускна здатність, запитів/с"), ("avg, мс", "Середня затримка, мс"), ("p95, мс", "p95 затримки, мс")]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, (key, title) in zip(axes, panels):
        vals = [d[key] for d in data]
        bars = ax.bar(labels, vals, color=PALETTE[: len(names)])
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:.0f}" if v >= 100 else f"{v:.1f}", ha="center", va="bottom", fontsize=9)
        plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def timeline_chart(names: list[str], labels: list[str], out_latency: Path, out_rps: Path):
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    for i, (n, lab) in enumerate(zip(names, labels)):
        _, h, _ = load(n)
        ax.plot(h["t"], h["95%"], color=PALETTE[i], label=f"{lab}: p95")
        ax.plot(h["t"], h["50%"], color=PALETTE[i], ls="--", alpha=0.7, label=f"{lab}: p50")
    ax.set_yscale("log")
    ax.set_xlabel("Час тесту, с")
    ax.set_ylabel("Час відповіді, мс (лог. шкала)")
    ax.set_title("Затримка в часі: до та після оптимізації")
    ax.grid(alpha=0.25, which="both")
    ax.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(out_latency, dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    for i, (n, lab) in enumerate(zip(names, labels)):
        _, h, _ = load(n)
        ax.plot(h["t"], h["Requests/s"], color=PALETTE[i], label=f"{lab}: RPS")
        ax.plot(h["t"], h["Failures/s"], color=PALETTE[i], ls=":", label=f"{lab}: помилки/с")
    if "User Count" in h:
        ax2 = ax.twinx()
        ax2.step(h["t"], h["User Count"], where="post", color="#bbbbbb", lw=1, label="Користувачі")
        ax2.set_ylabel("Віртуальні користувачі", color="#888888")
    ax.set_xlabel("Час тесту, с")
    ax.set_ylabel("Запитів за секунду")
    ax.set_title("Пропускна здатність у часі: до та після оптимізації")
    ax.grid(alpha=0.25)
    ax.legend(ncol=2, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(out_rps, dpi=140)
    plt.close(fig)


def step_table(names: list[str]) -> str:
    rows = {}
    for n in names:
        _, h, _ = load(n)
        counts = h["User Count"].value_counts()
        for lvl in sorted(level for level, c in counts.items() if level > 0 and c >= 25):
            g = h[h["User Count"] == lvl].tail(30)
            rows.setdefault(int(lvl), {})[n] = (
                g["Requests/s"].mean(),
                g["Failures/s"].mean(),
                g["50%"].median(),
                g["95%"].median(),
            )
    header = ["Користувачів"] + [f"RPS / err/с / p50 / p95 ({n})" for n in names]
    out = []
    for lvl in sorted(rows):
        r = [lvl]
        for n in names:
            v = rows[lvl].get(n)
            r.append("-" if v is None else f"{v[0]:.0f} / {v[1]:.1f} / {fmt_ms(v[2])} / {fmt_ms(v[3])}")
        out.append(r)
    return md_table(out, header)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+")
    ap.add_argument("--labels", nargs="*")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--step", action="store_true", help="додати таблицю по ступенях навантаження")
    args = ap.parse_args()
    labels = args.labels or args.names
    tag = args.tag or "_vs_".join(args.names)
    out = RESULTS / f"compare_{tag}"
    out.mkdir(parents=True, exist_ok=True)
    parts = [
        f"## Порівняння: {', '.join(args.names)}\n",
        "### Загальні метрики\n",
        comparison_table(args.names),
        "\n### По ендпоінтах\n",
        endpoint_table(args.names),
    ]
    if args.step:
        parts += ["\n### По ступенях навантаження\n", step_table(args.names)]
    (out / "comparison.md").write_text("\n".join(parts) + "\n", encoding="utf-8")
    bar_chart(args.names, labels, out / "bars.png")
    timeline_chart(args.names, labels, out / "latency_timeline.png", out / "throughput_timeline.png")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
