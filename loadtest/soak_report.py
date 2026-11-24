"""Підсумковий звіт за результатами soak-тесту (та spike-тесту) для Лаб. 8.

    python loadtest/soak_report.py soak_main --skip 300
    python loadtest/soak_report.py spike --spike 60 180

Читає loadtest/results/<name>/: soak_windows.csv, resources.csv, probe.csv (необов'язково),
locust_stats.csv. Пише soak_summary.md та графіки latency.png, throughput.png, cpu.png,
memory.png, connections.png (для spike - spike_summary.md і spike.png).
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

RESULTS = Path(__file__).parent / "results"
LIMIT_CPU, LIMIT_RAM, LIMIT_ERR = 80.0, 80.0, 0.1  # критерії успішності з лаби
LIMIT_LAT_GROWTH, LIMIT_MEM_GROWTH, LIMIT_CONN_GROWTH = 20.0, 10.0, 20.0  # власні критерії стабільності
BLUE, ORANGE, RED, GREEN, GRAY = "#2a6fdb", "#e08a1e", "#d1383d", "#2e9e5b", "#8a8f98"


def yes(cond: bool) -> str:
    return "так" if cond else "НІ"


def num(x, digits=1) -> str:
    return "-" if x is None or pd.isna(x) else f"{x:.{digits}f}"


def pct_change(first, last):
    if first is None or pd.isna(first) or not first:
        return float("nan")
    return (last - first) / first * 100


def read(d: Path, name: str):
    p = d / name
    return pd.read_csv(p) if p.exists() else None


def load(name: str):
    d = RESULTS / name
    win = read(d, "soak_windows.csv")
    if win is None or win.empty:
        sys.exit(f"Немає {d / 'soak_windows.csv'} - чи підключено loadtest/soak_stats.py до locust?")
    for col in ("rps", "err_pct", "avg_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms"):
        win[col] = pd.to_numeric(win[col], errors="coerce")
    t0 = win["timestamp"].iloc[0] - win["elapsed_s"].iloc[0]
    win["t"] = (win["timestamp"] - t0) / 60
    res = read(d, "resources.csv")
    if res is not None:
        res["t"] = (res["timestamp"] - t0) / 60
    probe = read(d, "probe.csv")
    if probe is not None:
        probe["t"] = (probe["timestamp"] - t0) / 60
        for col in probe.columns:
            probe[col] = pd.to_numeric(probe[col], errors="coerce")
    stats = read(d, "locust_stats.csv")
    return d, win, res, probe, stats


def first_last(df: pd.DataFrame, col: str, skip: float, width: float):
    """Медіана показника на початку сталої ділянки та наприкінці тесту (width хвилин)."""
    if df is None or col not in df or df[col].dropna().empty:
        return None, None
    t_end = df["t"].max()
    first = df[(df["t"] >= skip) & (df["t"] < skip + width)][col].median()
    last = df[df["t"] > t_end - width][col].median()
    return first, last


def slope_per_hour(df: pd.DataFrame, col: str, skip: float):
    sub = df[df["t"] >= skip].dropna(subset=[col])
    if len(sub) < 3:
        return float("nan"), float("nan")
    x = sub["t"].to_numpy() / 60
    y = sub[col].to_numpy()
    k = np.polyfit(x, y, 1)[0]
    r = np.corrcoef(x, y)[0, 1] if np.std(y) > 0 else 0.0
    return k, r


def smooth(s: pd.Series, n: int = 15) -> pd.Series:
    return s.rolling(n, center=True, min_periods=1).mean()


def finish(fig, path: Path):
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_all(d, win, res, probe, skip):
    # затримка по вікнах
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(win["t"], win["p50_ms"], color=GREEN, lw=1, label="p50")
    ax.plot(win["t"], win["p95_ms"], color=BLUE, lw=1.2, label="p95")
    ax.plot(win["t"], win["p99_ms"], color=ORANGE, lw=1, label="p99")
    ax.axvline(skip, color=GRAY, ls=":", lw=1)
    ax.set_xlabel("Час, хв")
    ax.set_ylabel("Затримка, мс (вікно 10 с)")
    ax.set_title("Затримка протягом тесту")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left")
    finish(fig, d / "latency.png")

    # RPS та помилки
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(win["t"], win["rps"], color=BLUE, lw=1.2, label="RPS")
    ax.set_xlabel("Час, хв")
    ax.set_ylabel("RPS")
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.3)
    ax2 = ax.twinx()
    ax2.plot(win["t"], win["failures"] / win["elapsed_s"].diff().fillna(win["elapsed_s"].iloc[0]), color=RED, lw=1, label="помилки/с")
    ax2.set_ylabel("Помилок за секунду")
    ax2.set_ylim(bottom=0)
    ax.set_title("Пропускна здатність і помилки")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left")
    finish(fig, d / "throughput.png")

    if res is not None:
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(res["t"], smooth(res["sys_cpu_pct"]), color=BLUE, lw=1.2, label="CPU системи, %")
        ax.plot(res["t"], smooth(res["app_cpu_pct"]), color=ORANGE, lw=1.2, label="CPU застосунку, % одного ядра")
        ax.axhline(LIMIT_CPU, color=RED, ls="--", lw=1, label=f"ліміт {LIMIT_CPU:.0f}%")
        ax.set_xlabel("Час, хв")
        ax.set_ylabel("%")
        ax.set_ylim(bottom=0)
        ax.set_title("Завантаження CPU")
        ax.grid(alpha=0.3)
        ax.legend(loc="upper right")
        finish(fig, d / "cpu.png")

        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(res["t"], res["app_rss_mb"], color=BLUE, lw=1.2, label="RSS застосунку, МБ")
        sub = res[res["t"] >= skip]
        if len(sub) > 3:
            k = np.polyfit(sub["t"], sub["app_rss_mb"], 1)
            ax.plot(sub["t"], np.polyval(k, sub["t"]), color=RED, ls="--", lw=1, label="лінійний тренд")
        ax.set_xlabel("Час, хв")
        ax.set_ylabel("МБ")
        ax.grid(alpha=0.3)
        ax2 = ax.twinx()
        ax2.plot(res["t"], smooth(res["sys_ram_pct"]), color=ORANGE, lw=1, label="RAM системи, %")
        ax2.axhline(LIMIT_RAM, color=RED, ls=":", lw=1)
        ax2.set_ylabel("RAM системи, %")
        ax2.set_ylim(0, 100)
        ax.set_title("Пам'ять")
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc="upper left")
        finish(fig, d / "memory.png")

    if probe is not None and probe[["pg_total", "app_threads"]].notna().any().any():
        fig, ax = plt.subplots(figsize=(10, 4.5))
        for col, label, color in (
            ("pg_total", "з'єднань у PostgreSQL", BLUE),
            ("app_db_conns", "TCP-з'єднань застосунку з БД", GREEN),
            ("app_threads", "потоків застосунку", ORANGE),
        ):
            if probe[col].notna().any():
                ax.plot(probe["t"], probe[col], lw=1.2, label=label, color=color)
        ax.set_xlabel("Час, хв")
        ax.set_ylabel("Кількість")
        ax.set_ylim(bottom=0)
        ax.set_title("З'єднання та потоки")
        ax.grid(alpha=0.3)
        ax.legend(loc="upper left")
        finish(fig, d / "connections.png")


def soak(name: str, skip_s: float):
    d, win, res, probe, stats = load(name)
    skip = skip_s / 60
    total_min = win["t"].max()
    width = min(10.0, max((total_min - skip) / 3, 1.0))
    lines = [f"## Підсумковий протокол soak-тесту: {name}", ""]
    lines.append(
        f"Тривалість: {total_min:.0f} хв; прогрів {skip:.0f} хв виключено з аналізу стабільності; "
        f"порівнюються перші й останні {width:.0f} хв сталої ділянки.\n"
    )

    # --- фінальні метрики Locust
    agg = None
    if stats is not None:
        agg = stats[stats["Name"] == "Aggregated"].iloc[0]
        lines += [
            "### Фінальні метрики (весь тест)",
            "",
            "| Метрика | Значення |",
            "|---|---|",
            f"| Запитів | {int(agg['Request Count'])} |",
            f"| Помилок | {int(agg['Failure Count'])} |",
            f"| Error rate, % | {100 * agg['Failure Count'] / agg['Request Count']:.3f} |",
            f"| RPS (середній) | {agg['Requests/s']:.1f} |",
            f"| Затримка avg, мс | {agg['Average Response Time']:.1f} |",
            f"| Затримка min, мс | {agg['Min Response Time']:.1f} |",
            f"| Затримка max, мс | {agg['Max Response Time']:.0f} |",
            f"| p50, мс | {agg['50%']:.0f} |",
            f"| p95, мс | {agg['95%']:.0f} |",
            f"| p99, мс | {agg['99%']:.0f} |",
            "",
        ]
    if agg is not None:
        err_pct = 100 * agg["Failure Count"] / agg["Request Count"]
    else:
        err_pct = 100 * win["failures"].sum() / max(win["requests"].sum(), 1)

    steady = win[(win["t"] >= skip) & (win["requests"] > 0)]
    lat_ok = mem_ok = conn_ok = True

    # --- стабільність затримки та RPS
    p95_f, p95_l = first_last(win, "p95_ms", skip, width)
    avg_f, avg_l = first_last(win, "avg_ms", skip, width)
    rps_f, rps_l = first_last(win, "rps", skip, width)
    lat_growth = pct_change(p95_f, p95_l)
    lat_ok = not (lat_growth > LIMIT_LAT_GROWTH)
    lines += [
        "### Стабільність затримки та пропускної здатності",
        "",
        f"| Показник | Початок ({width:.0f} хв) | Кінець ({width:.0f} хв) | Зміна |",
        "|---|---|---|---|",
        f"| p95, мс | {num(p95_f)} | {num(p95_l)} | {num(lat_growth)}% |",
        f"| avg, мс | {num(avg_f)} | {num(avg_l)} | {num(pct_change(avg_f, avg_l))}% |",
        f"| RPS | {num(rps_f)} | {num(rps_l)} | {num(pct_change(rps_f, rps_l))}% |",
        "",
        f"Найгірше вікно p95 за стале середовище: {num(steady['p95_ms'].max(), 0)} мс; найгірше вікно p99: {num(steady['p99_ms'].max(), 0)} мс.",
        "",
    ]

    # --- ресурси
    cpu_mean = ram_max = cpu_p95 = cpu_max = ram_mean = None
    if res is not None:
        sr = res[res["t"] >= skip]
        cpu_mean, cpu_p95, cpu_max = sr["sys_cpu_pct"].mean(), sr["sys_cpu_pct"].quantile(0.95), sr["sys_cpu_pct"].max()
        ram_mean, ram_max = sr["sys_ram_pct"].mean(), sr["sys_ram_pct"].max()
        rss_f, rss_l = first_last(res, "app_rss_mb", skip, width)
        rss_growth = pct_change(rss_f, rss_l)
        k, r = slope_per_hour(res, "app_rss_mb", skip)
        mem_ok = not (rss_growth > LIMIT_MEM_GROWTH and r > 0.8)
        lines += [
            "### Ресурси (стала ділянка)",
            "",
            "| Показник | Значення |",
            "|---|---|",
            f"| CPU системи, середнє / p95 / макс, % | {cpu_mean:.1f} / {cpu_p95:.1f} / {cpu_max:.1f} |",
            f"| CPU застосунку, середнє, % одного ядра | {sr['app_cpu_pct'].mean():.1f} |",
            f"| RAM системи, середнє / макс, % | {ram_mean:.1f} / {ram_max:.1f} |",
            f"| RSS застосунку, початок → кінець, МБ | {num(rss_f)} → {num(rss_l)} ({num(rss_growth)}%) |",
            f"| Тренд RSS, МБ/год (кореляція r) | {num(k)} ({num(r, 2)}) |",
            "",
        ]
    if probe is not None and probe["pg_total"].notna().any():
        pg_f, pg_l = first_last(probe, "pg_total", skip, width)
        th_f, th_l = first_last(probe, "app_threads", skip, width)
        hd_f, hd_l = first_last(probe, "app_handles", skip, width)
        pg_growth = pct_change(pg_f, pg_l)
        conn_ok = not (pg_growth > LIMIT_CONN_GROWTH and pg_l - pg_f > 3)
        idle_tx = probe["pg_idle_in_tx"].max()
        lines += [
            "### З'єднання та дескриптори",
            "",
            "| Показник | Початок | Кінець | Зміна | Максимум |",
            "|---|---|---|---|---|",
            f"| З'єднань у PostgreSQL | {num(pg_f, 0)} | {num(pg_l, 0)} | {num(pg_growth)}% | {num(probe['pg_total'].max(), 0)} |",
            f"| Потоків застосунку | {num(th_f, 0)} | {num(th_l, 0)} | {num(pct_change(th_f, th_l))}% | {num(probe['app_threads'].max(), 0)} |",
            f"| Дескрипторів застосунку | {num(hd_f, 0)} | {num(hd_l, 0)} | {num(pct_change(hd_f, hd_l))}% | {num(probe['app_handles'].max(), 0)} |",
            "",
            f"Максимум з'єднань у стані `idle in transaction`: {num(idle_tx, 0)}.",
            "",
        ]
        if probe["redis_used_mb"].notna().any():
            lines.append(
                f"Redis: пам'ять {num(probe['redis_used_mb'].iloc[0], 2)} → {num(probe['redis_used_mb'].iloc[-1], 2)} МБ, "
                f"ключів наприкінці: {num(probe['redis_keys'].iloc[-1], 0)}.\n"
            )

    # --- критерії
    crit = [
        ("CPU системи (середнє) ≤ 80%", cpu_mean is not None and cpu_mean <= LIMIT_CPU, num(cpu_mean)),
        ("RAM системи (максимум) ≤ 80%", ram_max is not None and ram_max <= LIMIT_RAM, num(ram_max)),
        ("Error rate ≤ 0,1%", err_pct <= LIMIT_ERR, num(err_pct, 3)),
        (f"Зростання p95 за тест ≤ {LIMIT_LAT_GROWTH:.0f}% (немає деградації)", lat_ok, f"{num(lat_growth)}%"),
        (f"Немає витоку пам'яті (RSS ≤ +{LIMIT_MEM_GROWTH:.0f}% або немає тренду)", mem_ok, "-"),
    ]
    if probe is not None and probe["pg_total"].notna().any():
        crit.append(("З'єднання БД не накопичуються", conn_ok, "-"))
    lines += ["### Відповідність критеріям", "", "| Критерій | Виконано | Значення |", "|---|---|---|"]
    lines += [f"| {c} | {yes(ok)} | {v} |" for c, ok, v in crit]
    all_ok = all(ok for _, ok, _ in crit)
    lines += ["", f"**Загальний висновок: {'усі критерії виконано' if all_ok else 'є невиконані критерії (див. таблицю)'}.**", ""]

    (d / "soak_summary.md").write_text("\n".join(lines), encoding="utf-8")
    plot_all(d, win, res, probe, skip)
    print(f"-> {d} (soak_summary.md + графіки)")


def spike(name: str, t_start: float, t_end: float):
    d, win, res, probe, stats = load(name)
    win = win.copy()
    base = win[(win["elapsed_s"] >= 20) & (win["elapsed_s"] <= t_start) & (win["requests"] > 0)]
    during = win[(win["elapsed_s"] > t_start) & (win["elapsed_s"] <= t_end)]
    after = win[win["elapsed_s"] > t_end]
    base_p95 = base["p95_ms"].median()
    threshold = max(1.5 * base_p95, base_p95 + 50)
    good = ((after["p95_ms"] <= threshold) & (after["failures"] == 0) & (after["requests"] > 0)).to_numpy()
    recovery = None
    for i in range(len(good) - 2):
        if good[i] and good[i + 1] and good[i + 2]:
            recovery = after["elapsed_s"].iloc[i] - t_end
            break
    peak_err = during["err_pct"].max()
    tail = after[after["elapsed_s"] > after["elapsed_s"].max() - 60] if len(after) else after

    def phase(df, label):
        return (
            f"| {label} | {num(df['rps'].median())} | {num(df['p95_ms'].median(), 0)} | "
            f"{num(df['p95_ms'].max(), 0)} | {num(df['err_pct'].mean(), 2)} | {num(df['err_pct'].max(), 2)} |"
        )

    lines = [
        f"## Spike-тест: {name}",
        "",
        f"Стрибок навантаження: {t_start:.0f}-{t_end:.0f} с. Поріг відновлення: p95 ≤ {threshold:.0f} мс "
        "(1,5 від норми) і 0 помилок у трьох вікнах поспіль.",
        "",
        "| Фаза | RPS (медіана) | p95 медіана, мс | p95 макс, мс | Помилки сер., % | Помилки макс., % |",
        "|---|---|---|---|---|---|",
        phase(base, "До стрибка"),
        phase(during, "Під час стрибка"),
        phase(tail, "Наприкінці (останні 60 с)"),
        "",
        f"- Піковий error rate у вікні під час стрибка: {num(peak_err, 2)}%",
        "- Час відновлення після завершення стрибка: " + (f"{recovery:.0f} с" if recovery is not None else "система не відновилась до кінця тесту"),
        "",
    ]
    (d / "spike_summary.md").write_text("\n".join(lines), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(win["elapsed_s"], win["p95_ms"], color=BLUE, lw=1.3, label="p95, мс")
    ax.axvspan(t_start, t_end, color=ORANGE, alpha=0.15, label="стрибок")
    ax.axhline(threshold, color=GRAY, ls=":", lw=1, label="поріг відновлення")
    ax.set_yscale("log")
    ax.set_xlabel("Час, с")
    ax.set_ylabel("p95, мс (лог. шкала)")
    ax.grid(alpha=0.3)
    ax2 = ax.twinx()
    ax2.plot(win["elapsed_s"], win["rps"], color=GREEN, lw=1, label="RPS")
    ax2.plot(win["elapsed_s"], win["users"], color=GRAY, lw=1, ls="--", label="користувачі")
    ax2.set_ylabel("RPS / користувачі")
    ax.set_title("Реакція на різкий стрибок навантаження")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left")
    finish(fig, d / "spike.png")
    print(f"-> {d} (spike_summary.md + spike.png)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--skip", type=float, default=300, help="прогрів, с (виключається з аналізу)")
    ap.add_argument("--spike", nargs=2, type=float, metavar=("START", "END"), help="режим spike: початок і кінець стрибка, с")
    args = ap.parse_args()
    if args.spike:
        spike(args.name, *args.spike)
    else:
        soak(args.name, args.skip)


if __name__ == "__main__":
    main()
