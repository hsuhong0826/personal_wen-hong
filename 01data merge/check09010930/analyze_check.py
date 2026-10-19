from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

SOURCE_DEFAULT = Path(__file__).resolve().parents[1] / "check_merged_09010930.csv"
OUTPUT_DIR = Path(__file__).resolve().parent

TARGET_SECTIONS = {"3148038", "3148040", "2098000"}
ROUTE_1_SECTIONS = ("3148038", "3148040")
ROUTE_1_VENDORS = ("C01", "IISI01")
ROUTE_2_SECTION = "2098000"
ROUTE_2_VENDORS = ("IISI01", "C03")


def position_type(ps_id: str) -> str:
    """將格位分類為 T 開頭或數字／其他開頭。"""
    return "T" if ps_id.upper().startswith("T") else "數字"


def new_totals() -> dict[str, float]:
    """建立單一分組使用的數量累計容器。"""
    return {"total_count": 0.0, "suspect_count": 0.0, "anomaly_count": 0.0}


def add_row(totals: dict[str, float], row: dict[str, str]) -> None:
    """將 CSV 單列的三種數量加入指定分組。"""
    totals["total_count"] += float(row["total_count"] or 0)
    totals["suspect_count"] += float(row["suspect_count"] or 0)
    totals["anomaly_count"] += float(row["anomaly_count"] or 0)


def rate(totals: dict[str, float]) -> float:
    """計算 suspect 與 anomaly 合計除以總數的異常率。"""
    denominator = totals["total_count"]
    if denominator == 0:
        return 0.0
    return (totals["anomaly_count"] + totals["suspect_count"]) / denominator


def read_data(source: Path):
    """讀取 CSV，依格位及路段／廠商分別彙總資料。"""
    by_position: dict[tuple[str, str, str], dict[str, float]] = defaultdict(new_totals)
    by_route_vendor: dict[tuple[str, str], dict[str, float]] = defaultdict(new_totals)

    with source.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        required = {"vendorcode", "section_id", "ps_id", "total_count", "suspect_count", "anomaly_count"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV 缺少必要欄位: {', '.join(sorted(missing))}")

        for row in reader:
            section = row["section_id"].strip()
            vendor = row["vendorcode"].strip()
            ps_id = row["ps_id"].strip()
            if section not in TARGET_SECTIONS or not ps_id:
                continue
            add_row(by_position[(section, vendor, ps_id)], row)
            add_row(by_route_vendor[(section, vendor)], row)

    return by_position, by_route_vendor


def configure_plot() -> None:
    """設定中文字型、負號顯示及圖表解析度。"""
    plt.rcParams["font.family"] = ["Microsoft JhengHei", "Microsoft YaHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 140


def annotate_bars(axis, bars) -> None:
    """在非零柱體上標示百分比。"""
    for bar in bars:
        value = bar.get_height()
        if value <= 0:
            continue
        axis.annotate(
            f"{value:.2%}",
            (bar.get_x() + bar.get_width() / 2, value),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7,
            rotation=90,
            color=bar.get_facecolor(),
        )


def save_route_1_chart(by_position) -> None:
    """輸出 3148038、3148040 的 C01 與 IISI01 格位比較圖。"""
    fig, axes = plt.subplots(2, 1, figsize=(17, 12), constrained_layout=True)
    colors = {"C01": "#d95f02", "IISI01": "#1b9e77"}

    for axis, kind in zip(axes, ("T", "數字")):
        labels: list[str] = []
        values = {vendor: [] for vendor in ROUTE_1_VENDORS}
        keys = []
        for section in ROUTE_1_SECTIONS:
            ps_ids = sorted(
                {
                    ps_id
                    for route, vendor, ps_id in by_position
                    if route == section and position_type(ps_id) == kind
                },
                key=lambda value: (value.lstrip("T").isdigit(), value.lstrip("T")),
            )
            for ps_id in ps_ids:
                keys.append((section, ps_id))
                labels.append(f"{section} / {ps_id}")
                for vendor in ROUTE_1_VENDORS:
                    values[vendor].append(rate(by_position.get((section, vendor, ps_id), new_totals())))

        if not keys:
            axis.text(0.5, 0.5, "無資料", ha="center", va="center")
            axis.set_axis_off()
            continue

        x = list(range(len(labels)))
        bar_width = 0.38
        for offset, vendor in ((-bar_width / 2, ROUTE_1_VENDORS[0]), (bar_width / 2, ROUTE_1_VENDORS[1])):
            bars = axis.bar([value + offset for value in x], values[vendor], width=bar_width, label=vendor, color=colors[vendor])
            annotate_bars(axis, bars)
        axis.set_xticks(x, labels, rotation=60, ha="right")
        axis.yaxis.set_major_formatter(PercentFormatter(1))
        axis.set_ylabel("整體異常率（anomaly + suspect）")
        axis.set_title(f"3148038、3148040：{kind}開頭原始格位比較")
        axis.grid(axis="y", alpha=0.25)
        axis.legend(loc="lower right")

    fig.suptitle("C01 與 IISI01 原始格位比較", fontsize=16)
    fig.savefig(OUTPUT_DIR / "01_3148038_3148040_C01_vs_IISI01_vertical.png", bbox_inches="tight")
    plt.close(fig)


def save_route_2_chart(by_position) -> None:
    """輸出 2098000 的 IISI01 與 C03 格位比較圖。"""
    fig, axes = plt.subplots(2, 1, figsize=(17, 12), constrained_layout=True)
    colors = {"IISI01": "#1b9e77", "C03": "#7570b3"}
    for axis, kind in zip(axes, ("T", "數字")):
        ps_ids = sorted(
            {
                ps_id
                for section, vendor, ps_id in by_position
                if section == ROUTE_2_SECTION
                and vendor in ROUTE_2_VENDORS
                and position_type(ps_id) == kind
            },
            key=lambda value: value.lstrip("T"),
        )
        if not ps_ids:
            axis.text(0.5, 0.5, "無資料", ha="center", va="center")
            axis.set_axis_off()
            continue
        x = list(range(len(ps_ids)))
        bar_width = 0.38
        for offset, vendor in ((-bar_width / 2, ROUTE_2_VENDORS[0]), (bar_width / 2, ROUTE_2_VENDORS[1])):
            values = [rate(by_position.get((ROUTE_2_SECTION, vendor, ps_id), new_totals())) for ps_id in ps_ids]
            bars = axis.bar([value + offset for value in x], values, width=bar_width, label=vendor, color=colors[vendor])
            annotate_bars(axis, bars)
        axis.set_xticks(x, ps_ids, rotation=60, ha="right")
        axis.yaxis.set_major_formatter(PercentFormatter(1))
        axis.set_ylabel("整體異常率（anomaly + suspect）")
        axis.set_title(f"2098000：{kind}開頭原始格位比較")
        axis.grid(axis="y", alpha=0.25)
        axis.legend(loc="upper right")

    fig.suptitle("2098000：IISI01 與 C03 原始格位比較", fontsize=16)
    fig.savefig(OUTPUT_DIR / "02_2098000_IISI01_vs_C03_vertical.png", bbox_inches="tight")
    plt.close(fig)


def save_summary_chart(by_route_vendor) -> None:
    """輸出各路段／廠商的整體異常率摘要 CSV 與柱狀圖。"""
    comparisons = [
        ("3148038", ROUTE_1_VENDORS),
        ("3148040", ROUTE_1_VENDORS),
        ("2098000", ROUTE_2_VENDORS),
    ]
    rows: list[dict[str, str | float]] = []
    for section, vendors in comparisons:
        for vendor in vendors:
            totals = by_route_vendor.get((section, vendor), new_totals())
            rows.append(
                {
                    "section_id": section,
                    "vendorcode": vendor,
                    "total_count": totals["total_count"],
                    "suspect_count": totals["suspect_count"],
                    "anomaly_count": totals["anomaly_count"],
                    "overall_anomaly_rate": rate(totals),
                }
            )

    with (OUTPUT_DIR / "03_overall_summary.csv").open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    labels = [f"{row['section_id']} / {row['vendorcode']}" for row in rows]
    values = [float(row["overall_anomaly_rate"]) for row in rows]
    colors = ["#d95f02" if row["vendorcode"] == "C01" else "#1b9e77" if row["vendorcode"] == "IISI01" else "#7570b3" for row in rows]

    fig, axis = plt.subplots(figsize=(11, 6), constrained_layout=True)
    axis.bar(labels, values, color=colors)
    axis.yaxis.set_major_formatter(PercentFormatter(1))
    axis.set_ylabel("整體異常率（anomaly + suspect）")
    axis.set_title("三個路段的廠商整體優劣比較")
    axis.grid(axis="y", alpha=0.25)
    for index, value in enumerate(values):
        axis.text(index, value, f"{value:.2%}", ha="center", va="bottom")
    fig.savefig(OUTPUT_DIR / "03_overall_vendor_summary_updated.png", bbox_inches="tight")
    plt.close(fig)


def annotate_comparison_bars(axis, bars, totals_list) -> None:
    """在比較柱狀圖上標示各格位異常率。"""
    for bar, totals in zip(bars, totals_list):
        if totals["total_count"] <= 0:
            continue
        axis.annotate(
            f"{rate(totals):.2%}",
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7,
            rotation=90,
            color=bar.get_facecolor(),
        )


def annotate_line_points(
    axis,
    x_values,
    values,
    totals_list,
    *,
    color,
    offset_points,
    horizontal_offset=0,
) -> None:
    """在折線圖資料點上標示異常率，沒有資料的點不顯示。"""
    for x_value, value, totals in zip(x_values, values, totals_list):
        if totals["total_count"] <= 0:
            continue
        axis.annotate(
            f"{value:.2%}",
            (x_value, value),
            xytext=(horizontal_offset, offset_points),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7,
            rotation=90,
            color=color,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.4, "alpha": 0.8},
        )


def save_mapping_chart(
    by_position,
    *,
    sections: tuple[str, ...],
    target_vendor: str,
    target_prefix: str,
    title: str,
    output_name: str,
) -> None:
    """輸出 IISI01_T 與指定廠商對應格位的折線比較圖。"""
    source_vendor = "IISI01"
    labels: list[str] = []
    source_totals: list[dict[str, float]] = []
    target_totals: list[dict[str, float]] = []

    for section in sections:
        source_ps_ids = sorted(
            {
                ps_id
                for route, vendor, ps_id in by_position
                if route == section and vendor == source_vendor and ps_id.upper().startswith("T")
            },
            key=lambda value: value[1:],
        )
        for source_ps_id in source_ps_ids:
            target_ps_id = source_ps_id if target_prefix == "T" else source_ps_id[1:]
            labels.append(f"{section} / {source_ps_id} -> {target_prefix}{source_ps_id[1:]}")
            source_totals.append(by_position.get((section, source_vendor, source_ps_id), new_totals()))
            target_totals.append(by_position.get((section, target_vendor, target_ps_id), new_totals()))

    fig_width = max(16, len(labels) * 0.42)
    fig, axis = plt.subplots(figsize=(fig_width, 8), constrained_layout=True)
    x = list(range(len(labels)))
    source_values = [rate(totals) for totals in source_totals]
    target_values = [rate(totals) for totals in target_totals]
    axis.plot(
        x,
        source_values,
        label="金磚（IISI01）",
        color="#1b9e77",
        marker="o",
        linewidth=2,
    )
    axis.plot(
        x,
        target_values,
        label=f"{target_vendor}",
        color="#d95f02" if target_vendor == "C01" else "#7570b3",
        marker="o",
        linewidth=2,
    )
    # 來源與目標固定分上下兩列，並以折線顏色標示數字。
    annotate_line_points(
        axis,
        x,
        source_values,
        source_totals,
        color="#1b9e77",
        offset_points=9,
        horizontal_offset=-9,
    )
    annotate_line_points(
        axis,
        x,
        target_values,
        target_totals,
        color="#d95f02" if target_vendor == "C01" else "#7570b3",
        offset_points=-12,
        horizontal_offset=9,
    )
    axis.set_xticks(x, labels, rotation=60, ha="right")
    axis.yaxis.set_major_formatter(PercentFormatter(1))
    axis.set_ylabel("整體異常率（anomaly + suspect）")
    axis.set_title(title)
    axis.grid(axis="y", alpha=0.25)
    axis.legend(loc="upper right")
    fig.savefig(OUTPUT_DIR / output_name, bbox_inches="tight")
    plt.close(fig)


def save_mapping_bar_chart_for_c01(by_position, *, target_prefix: str, title: str, output_name: str) -> None:
    """輸出 C01 對應格位的異常率比較柱狀圖。"""
    labels: list[str] = []
    source_totals: list[dict[str, float]] = []
    target_totals: list[dict[str, float]] = []
    for section in ROUTE_1_SECTIONS:
        source_ps_ids = sorted(
            {
                ps_id
                for route, vendor, ps_id in by_position
                if route == section and vendor == "IISI01" and ps_id.upper().startswith("T")
            },
            key=lambda value: value[1:],
        )
        for source_ps_id in source_ps_ids:
            target_ps_id = source_ps_id if target_prefix == "T" else source_ps_id[1:]
            labels.append(f"{section} / {source_ps_id} -> {target_prefix}{source_ps_id[1:]}")
            source_totals.append(by_position.get((section, "IISI01", source_ps_id), new_totals()))
            target_totals.append(by_position.get((section, "C01", target_ps_id), new_totals()))

    x = list(range(len(labels)))
    bar_width = 0.38
    fig_width = max(16, len(labels) * 0.42)
    fig, axis = plt.subplots(figsize=(fig_width, 8), constrained_layout=True)
    source_bars = axis.bar(
        [value - bar_width / 2 for value in x],
        [rate(totals) for totals in source_totals],
        width=bar_width,
        label="金磚（IISI01）",
        color="#1b9e77",
    )
    target_bars = axis.bar(
        [value + bar_width / 2 for value in x],
        [rate(totals) for totals in target_totals],
        width=bar_width,
        label="C01",
        color="#d95f02",
    )
    annotate_comparison_bars(axis, source_bars, source_totals)
    annotate_comparison_bars(axis, target_bars, target_totals)
    axis.set_xticks(x, labels, rotation=60, ha="right")
    axis.yaxis.set_major_formatter(PercentFormatter(1))
    axis.set_ylabel("整體異常率（anomaly + suspect）")
    axis.set_title(title)
    axis.grid(axis="y", alpha=0.25)
    axis.legend(loc="upper right")
    fig.savefig(OUTPUT_DIR / output_name, bbox_inches="tight")
    plt.close(fig)


def save_mapping_bar_chart(by_position) -> None:
    """輸出 2098000 的 IISI01_T 與 C03 數字格位比例柱狀圖。"""
    labels: list[str] = []
    source_totals: list[dict[str, float]] = []
    target_totals: list[dict[str, float]] = []
    for source_ps_id in sorted(
        {
            ps_id
            for section, vendor, ps_id in by_position
            if section == ROUTE_2_SECTION and vendor == "IISI01" and ps_id.upper().startswith("T")
        },
        key=lambda value: value[1:],
    ):
        target_ps_id = source_ps_id[1:]
        labels.append(f"{ROUTE_2_SECTION} / {source_ps_id} -> {target_ps_id}")
        source_totals.append(by_position.get((ROUTE_2_SECTION, "IISI01", source_ps_id), new_totals()))
        target_totals.append(by_position.get((ROUTE_2_SECTION, "C03", target_ps_id), new_totals()))

    # 第 5 張比例柱狀圖只顯示比例，不顯示 N。
    x = list(range(len(labels)))
    bar_width = 0.38
    fig_width = max(16, len(labels) * 0.42)
    fig, axis = plt.subplots(figsize=(fig_width, 8), constrained_layout=True)
    source_bars = axis.bar(
        [value - bar_width / 2 for value in x],
        [rate(totals) for totals in source_totals],
        width=bar_width,
        label="金磚（IISI01）",
        color="#1b9e77",
    )
    target_bars = axis.bar(
        [value + bar_width / 2 for value in x],
        [rate(totals) for totals in target_totals],
        width=bar_width,
        label="C03",
        color="#7570b3",
    )
    annotate_comparison_bars(axis, source_bars, source_totals)
    annotate_comparison_bars(axis, target_bars, target_totals)
    axis.set_xticks(x, labels, rotation=60, ha="right")
    axis.yaxis.set_major_formatter(PercentFormatter(1))
    axis.set_ylabel("整體異常率（anomaly + suspect）")
    axis.set_title("2098000：金磚（IISI01_T）→ 國雲（C03_數字）")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(loc="upper right")
    fig.savefig(OUTPUT_DIR / "03_IISI01_T_to_C03_numeric.png", bbox_inches="tight")
    plt.close(fig)


def combine_totals(totals_list) -> dict[str, float]:
    """合併多個格位的數量，供整體分組比較使用。"""
    combined = new_totals()
    for totals in totals_list:
        for key in combined:
            combined[key] += totals[key]
    return combined


def build_fair_comparisons(by_position):
    """依相同路段與對應格位建立金磚／目標廠商比較資料。"""
    comparison_specs = [
        (
            "3148038、3148040：IISI01_T vs C01_T",
            lambda section, vendor, ps_id: section in ROUTE_1_SECTIONS
            and vendor == "IISI01"
            and ps_id.upper().startswith("T"),
            lambda section, vendor, ps_id: section in ROUTE_1_SECTIONS
            and vendor == "C01"
            and ps_id.upper().startswith("T"),
        ),
        (
            "3148038、3148040：IISI01_T vs C01_數字",
            lambda section, vendor, ps_id: section in ROUTE_1_SECTIONS
            and vendor == "IISI01"
            and ps_id.upper().startswith("T"),
            lambda section, vendor, ps_id: section in ROUTE_1_SECTIONS
            and vendor == "C01"
            and not ps_id.upper().startswith("T"),
        ),
        (
            "2098000：IISI01_T vs C03_數字",
            lambda section, vendor, ps_id: section == ROUTE_2_SECTION
            and vendor == "IISI01"
            and ps_id.upper().startswith("T"),
            lambda section, vendor, ps_id: section == ROUTE_2_SECTION
            and vendor == "C03"
            and not ps_id.upper().startswith("T"),
        ),
    ]
    labels = []
    source_totals = []
    target_totals = []
    for label, source_selector, target_selector in comparison_specs:
        labels.append(label)
        source_totals.append(
            combine_totals(
                [
                    totals
                    for (section, vendor, ps_id), totals in by_position.items()
                    if source_selector(section, vendor, ps_id)
                ]
            )
        )
        target_totals.append(
            combine_totals(
                [
                    totals
                    for (section, vendor, ps_id), totals in by_position.items()
                    if target_selector(section, vendor, ps_id)
                ]
            )
        )
    return labels, source_totals, target_totals


def save_overall_rate_chart(by_position) -> None:
    """輸出相同路段／對應格位的金磚與目標廠商比較圖。"""
    labels, source_totals, target_totals = build_fair_comparisons(by_position)
    source_values = [rate(totals) for totals in source_totals]
    target_values = [rate(totals) for totals in target_totals]

    fig, axis = plt.subplots(figsize=(11, 7), constrained_layout=True)
    x = list(range(len(labels)))
    axis.plot(x, source_values, label="金磚（IISI01）", color="#1b9e77", marker="o", linewidth=2)
    axis.plot(x, target_values, label="對應廠商", color="#3f6fb5", marker="o", linewidth=2)
    # 兩組標註統一放在資料點上方，左右錯開並避免壓在線上。
    for x_value, value, totals in zip(x, source_values, source_totals):
        if totals["total_count"] > 0:
            at_left_edge = x_value == x[0]
            axis.annotate(
                f"{value:.2%}",
                (x_value, value),
                xytext=(10 if at_left_edge else -10, 8),
                textcoords="offset points",
                ha="left" if at_left_edge else "right",
                va="bottom",
                color="#1b9e77",
            )
    for x_value, value, totals in zip(x, target_values, target_totals):
        if totals["total_count"] > 0:
            at_right_edge = x_value == x[-1]
            at_left_edge = x_value == x[0]
            if at_right_edge:
                axis.text(
                    x_value - 0.05,
                    value + 0.00005,
                    f"{value:.2%}",
                    ha="right",
                    va="bottom",
                    color="#3f6fb5",
                )
                continue
            axis.annotate(
                f"{value:.2%}",
                (x_value, value),
                xytext=(50 if at_left_edge else 10, 8),
                textcoords="offset points",
                ha="left",
                va="bottom",
                color="#3f6fb5",
            )
    axis.set_xticks(x, labels)
    axis.yaxis.set_major_formatter(PercentFormatter(1))
    axis.set_ylabel("整體異常率（anomaly + suspect）")
    axis.set_title("相同路段／對應格位的廠商整體異常率比較")
    axis.grid(axis="y", alpha=0.25)
    axis.legend()
    fig.savefig(OUTPUT_DIR / "03_overall_rate_summary_line_v2.png", bbox_inches="tight")
    plt.close(fig)


def save_overall_rate_bar_chart(by_position) -> None:
    """輸出相同路段／對應格位的廠商整體異常率長條圖。"""
    labels, source_totals, target_totals = build_fair_comparisons(by_position)
    source_values = [rate(totals) for totals in source_totals]
    target_values = [rate(totals) for totals in target_totals]

    # 四個分組各自一根柱，呈現方式比折線圖更接近章節摘要圖。
    fig, axis = plt.subplots(figsize=(11, 6), constrained_layout=True)
    x = list(range(len(labels)))
    bar_width = 0.38
    source_bars = axis.bar(
        [value - bar_width / 2 for value in x],
        source_values,
        width=bar_width,
        label="金磚（IISI01）",
        color="#1b9e77",
    )
    target_bars = axis.bar(
        [value + bar_width / 2 for value in x],
        target_values,
        width=bar_width,
        label="對應廠商",
        color="#3f6fb5",
    )
    axis.yaxis.set_major_formatter(PercentFormatter(1))
    axis.set_ylabel("整體異常率（anomaly + suspect）")
    axis.set_title("25 種規則檢核結果：相同路段／對應格位比較")
    axis.grid(axis="y", alpha=0.25)
    axis.set_xticks(x, labels)
    axis.legend()
    for bar, value in zip(source_bars, source_values):
        axis.annotate(
            f"{value:.2%}",
            (bar.get_x() + bar.get_width() / 2, value),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
        )
    for bar, value in zip(target_bars, target_values):
        axis.annotate(
            f"{value:.2%}",
            (bar.get_x() + bar.get_width() / 2, value),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
        )
    fig.savefig(OUTPUT_DIR / "05_overall_rate_summary_bar.png", bbox_inches="tight")
    plt.close(fig)


def save_requested_charts(by_position) -> None:
    """依需求集中輸出格位對應、比例及整體異常率圖表。"""
    save_mapping_bar_chart_for_c01(
        by_position,
        target_prefix="T",
        title="3148038、3148040：金磚（IISI01_T）→ 歐金（C01_T）",
        output_name="01_IISI01_T_to_C01_T_updated.png",
    )
    save_mapping_bar_chart_for_c01(
        by_position,
        target_prefix="",
        title="3148038、3148040：金磚（IISI01_T）→ 歐尼（C01_數字）",
        output_name="02_IISI01_T_to_C01_numeric_updated.png",
    )
    save_mapping_chart(
        by_position,
        sections=ROUTE_1_SECTIONS,
        target_vendor="C01",
        target_prefix="T",
        title="3148038、3148040：金磚（IISI01_T）→ 歐金（C01_T）",
        output_name="01_IISI01_T_to_C01_T_line_v2.png",
    )
    save_mapping_chart(
        by_position,
        sections=ROUTE_1_SECTIONS,
        target_vendor="C01",
        target_prefix="",
        title="3148038、3148040：金磚（IISI01_T）→ 歐尼（C01_數字）",
        output_name="02_IISI01_T_to_C01_numeric_line_v2.png",
    )
    save_mapping_chart(
        by_position,
        sections=(ROUTE_2_SECTION,),
        target_vendor="C03",
        target_prefix="",
        title="2098000：金磚（IISI01_T）→ 國雲（C03_數字）",
        output_name="04_2098000_IISI01_T_to_C03_numeric_line.png",
    )
    save_mapping_bar_chart(by_position)
    save_overall_rate_chart(by_position)
    save_overall_rate_bar_chart(by_position)


def main() -> None:
    """解析來源檔案、執行分析並將結果寫入本程式所在資料夾。"""
    parser = argparse.ArgumentParser(description="產出 check_merged_09010930.csv 的三張廠商比較圖")
    parser.add_argument("source", nargs="?", type=Path, default=SOURCE_DEFAULT)
    args = parser.parse_args()
    if not args.source.exists():
        raise FileNotFoundError(f"找不到來源 CSV: {args.source}")

    configure_plot()
    by_position, _ = read_data(args.source)
    save_requested_charts(by_position)
    print(f"圖表與彙總已輸出至: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
