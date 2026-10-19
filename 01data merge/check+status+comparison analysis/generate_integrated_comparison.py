from __future__ import annotations

"""整合 check、status 與 comparison 資料，產生廠商比較結果與圖表。"""

import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


# ===== 輸入、輸出與三組比較設定 =====
SCRIPT_DIR = Path(__file__).resolve().parent
MERGE_DIR = SCRIPT_DIR.parent
CHECK_SOURCE = MERGE_DIR / "check_merged_09010930.csv"
STATUS_SOURCE = MERGE_DIR / "status_merged_09010930.csv"
COMPARISON_SOURCE = MERGE_DIR / "comparison_merged_09010930_deduplicated.csv"
OUTPUT_DIR = SCRIPT_DIR

GROUPS = (
    {
        "key": "C01_T",
        "title": "C01_T（歐金）vs IISI01（金磚）",
        "sections": ("3148038", "3148040"),
        "target_vendor": "C01",
        "target_label": "C01_T（歐金）",
        "target_type": "T",
    },
    {
        "key": "C01_NUM",
        "title": "C01_數字（歐尼）vs IISI01（金磚）",
        "sections": ("3148038", "3148040"),
        "target_vendor": "C01",
        "target_label": "C01_數字（歐尼）",
        "target_type": "數字",
    },
    {
        "key": "C03_NUM",
        "title": "C03（國雲）vs IISI01（金磚）",
        "sections": ("2098000",),
        "target_vendor": "C03",
        "target_label": "C03（國雲）",
        "target_type": "數字",
    },
)
COLORS = {"IISI01": "#1b9e77", "C01": "#d95f02", "C03": "#7570b3"}
ANOMALY_RATE_BENCHMARK = 0.05


# ===== 基本欄位轉換與排序 =====
def position_type(ps_id: str) -> str:
    return "T" if ps_id.upper().startswith("T") else "數字"


def sort_key(ps_id: str) -> tuple[int, str]:
    value = ps_id[1:] if ps_id.upper().startswith("T") else ps_id
    return (int(value) if value.isdigit() else 999999999, value)


def read_check_rates() -> dict[tuple[str, str, str], float]:
    """依路段、廠商與格位彙整異常率（suspect + anomaly）。"""
    totals = defaultdict(lambda: [0.0, 0.0])
    required = {"section_id", "vendorcode", "ps_id", "total_count", "suspect_count", "anomaly_count"}
    with CHECK_SOURCE.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"check CSV 缺少必要欄位：{', '.join(sorted(missing))}")
        for row in reader:
            key = (row["section_id"].strip(), row["vendorcode"].strip(), row["ps_id"].strip())
            totals[key][0] += float(row["total_count"] or 0)
            totals[key][1] += float(row["suspect_count"] or 0) + float(row["anomaly_count"] or 0)
    return {key: (value[1] / value[0] if value[0] else 0.0) for key, value in totals.items()}


def read_status_counts() -> dict[tuple[str, str, str], float]:
    """依路段、廠商與格位彙整 STATUS1、STATUS2 回傳數量。"""
    counts = defaultdict(float)
    required = {"section_id", "vendorcode", "ps_id", "status_1_count", "status_2_count"}
    with STATUS_SOURCE.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"status CSV 缺少必要欄位：{', '.join(sorted(missing))}")
        for row in reader:
            key = (row["section_id"].strip(), row["vendorcode"].strip(), row["ps_id"].strip())
            counts[key] += float(row["status_1_count"] or 0) + float(row["status_2_count"] or 0)
    return counts


def read_time_differences() -> dict[tuple[str, str, str], tuple[float, float]]:
    """計算各比較組合的平均時間差與平均絕對時間差。"""
    # 只累計總和、絕對值總和與筆數，避免載入大型 comparison CSV 的全部內容。
    totals = defaultdict(lambda: [0.0, 0.0, 0.0])
    required = {"baseline_vendor", "section_id", "target_vendor", "target_ps_id", "time_difference_seconds"}
    with COMPARISON_SOURCE.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"comparison CSV 缺少必要欄位：{', '.join(sorted(missing))}")
        for row in reader:
            if row["baseline_vendor"].strip() != "IISI01" or not row["time_difference_seconds"].strip():
                continue
            section = row["section_id"].strip()
            target_vendor = row["target_vendor"].strip()
            target_ps_id = row["target_ps_id"].strip()
            group = next(
                (
                    item
                    for item in GROUPS
                    if section in item["sections"]
                    and target_vendor == item["target_vendor"]
                    and position_type(target_ps_id) == item["target_type"]
                ),
                None,
            )
            if group is None:
                continue
            difference = float(row["time_difference_seconds"])
            item = totals[(group["key"], section, target_ps_id)]
            item[0] += difference
            item[1] += abs(difference)
            item[2] += 1
    return {
        key: (values[0] / values[2], values[1] / values[2])
        for key, values in totals.items()
        if values[2]
    }


def build_rows() -> list[dict[str, object]]:
    """合併三種來源資料，建立後續 CSV 與圖表共用的評估資料列。"""
    check_rates = read_check_rates()
    status_counts = read_status_counts()
    time_differences = read_time_differences()
    rows: list[dict[str, object]] = []

    # 以 IISI01 的 T 格位作為基準，依比較組態映射對照廠商格位。
    for group in GROUPS:
        for section in group["sections"]:
            baseline_ids = sorted(
                {
                    ps_id
                    for route, vendor, ps_id in status_counts
                    if route == section and vendor == "IISI01" and position_type(ps_id) == "T"
                },
                key=sort_key,
            )
            for baseline_ps_id in baseline_ids:
                suffix = baseline_ps_id[1:]
                target_ps_id = f"T{suffix}" if group["target_type"] == "T" else suffix
                baseline_key = (section, "IISI01", baseline_ps_id)
                target_key = (section, group["target_vendor"], target_ps_id)
                mean_time, mean_abs_time = time_differences.get((group["key"], section, target_ps_id), (math.nan, math.nan))
                baseline_rate = check_rates.get(baseline_key, 0.0)
                target_rate = check_rates.get(target_key, 0.0)
                baseline_count = status_counts[baseline_key]
                target_count = status_counts[target_key]
                count_gap = abs(target_count - baseline_count)
                count_denominator = max(target_count, baseline_count, 1.0)
                count_agreement = max(0.0, 1.0 - count_gap / count_denominator)
                # 異常率採「越低越好」；5% 作為評估上限，超過即為 0 分。
                baseline_anomaly_quality = max(0.0, 1.0 - baseline_rate / ANOMALY_RATE_BENCHMARK)
                target_anomaly_quality = max(0.0, 1.0 - target_rate / ANOMALY_RATE_BENCHMARK)
                # 時間差缺值時排除該項權重，避免缺資料被當成滿分或零分。
                time_agreement = math.nan if math.isnan(mean_abs_time) else max(0.0, 1.0 - mean_abs_time / 60.0)
                available_weight = 0.60 + 0.25 + (0.15 if not math.isnan(time_agreement) else 0.0)
                baseline_score = (0.60 * count_agreement + 0.25 * baseline_anomaly_quality + (0.15 * time_agreement if not math.isnan(time_agreement) else 0.0)) / available_weight
                target_score = (0.60 * count_agreement + 0.25 * target_anomaly_quality + (0.15 * time_agreement if not math.isnan(time_agreement) else 0.0)) / available_weight
                level = "高評比" if target_score >= 0.90 else "中評比" if target_score >= 0.75 else "低評比"
                rows.append(
                    {
                        "group": group["title"],
                        "group_key": group["key"],
                        "section_id": section,
                        "baseline_ps_id": baseline_ps_id,
                        "target_ps_id": target_ps_id,
                        "baseline_count": baseline_count,
                        "target_count": target_count,
                        "count_difference": target_count - baseline_count,
                        "baseline_anomaly_rate": baseline_rate,
                        "target_anomaly_rate": target_rate,
                        "anomaly_rate_difference": target_rate - baseline_rate,
                        "baseline_anomaly_quality": baseline_anomaly_quality,
                        "target_anomaly_quality": target_anomaly_quality,
                        "mean_time_difference_seconds": mean_time,
                        "mean_absolute_time_difference_seconds": mean_abs_time,
                        "count_agreement": count_agreement,
                        "time_agreement": time_agreement,
                        "baseline_overall_score": baseline_score,
                        "target_overall_score": target_score,
                        "overall_score": target_score,
                        "level": level,
                    }
                )
    return rows


def configure_plot() -> None:
    """設定中文顯示、負號格式與圖表解析度。"""
    plt.rcParams["font.family"] = ["Microsoft JhengHei", "Microsoft YaHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 140


def group_rows(rows: list[dict[str, object]], key: str) -> list[dict[str, object]]:
    """取得指定比較組合的資料列。"""
    return [row for row in rows if row["group_key"] == key]


def save_scatter(rows: list[dict[str, object]]) -> None:
    """輸出回傳數量一致性散點圖，並以對照廠商異常率著色。"""
    # 三組比較分開輸出，避免不同數量級共用畫布造成閱讀困難。
    output_names = {
        "C01_T": "01_scatter_C01_T_vs_IISI01.png",
        "C01_NUM": "02_scatter_C01_NUM_vs_IISI01.png",
        "C03_NUM": "03_scatter_C03_vs_IISI01.png",
    }
    for group in GROUPS:
        figure, axis = plt.subplots(figsize=(8, 7), constrained_layout=True)
        values = group_rows(rows, group["key"])
        x = np.array([row["baseline_count"] for row in values], dtype=float)
        y = np.array([row["target_count"] for row in values], dtype=float)
        color = np.array([row["target_anomaly_rate"] for row in values], dtype=float)
        points = axis.scatter(x, y, c=color, cmap="YlOrRd", edgecolors="#333333", alpha=0.85)
        colorbar = figure.colorbar(points, ax=axis, pad=0.02)
        limit = max(float(x.max(initial=0)), float(y.max(initial=0)), 1.0) * 1.08
        padding = limit * 0.03
        axis.plot([0, limit], [0, limit], "--", color="#555555", label="y = x")
        axis.set_xlim(-padding, limit)
        axis.set_ylim(-padding, limit)
        axis.set_title(f"IISI01（金磚）vs {group['target_label']}\nSTATUS1 + STATUS2 回傳數量一致性散點圖")
        axis.set_xlabel("IISI01 回傳數量")
        axis.set_ylabel(f"{group['target_label']} 回傳數量")
        axis.grid(alpha=0.25)
        axis.legend()
        figure.savefig(OUTPUT_DIR / output_names[group["key"]], dpi=160, bbox_inches="tight")
        plt.close(figure)


def save_anomaly_scatter(rows: list[dict[str, object]]) -> None:
    """將前三張異常率折線圖改以散點方式比較兩家廠商。"""
    output_names = {
        "C01_T": "09_scatter_anomaly_C01_T_vs_IISI01.png",
        "C01_NUM": "10_scatter_anomaly_C01_NUM_vs_IISI01.png",
        "C03_NUM": "11_scatter_anomaly_C03_vs_IISI01.png",
    }
    for group in GROUPS:
        figure, axis = plt.subplots(figsize=(8, 7), constrained_layout=True)
        values = group_rows(rows, group["key"])
        x = np.array([row["baseline_anomaly_rate"] for row in values], dtype=float)
        y = np.array([row["target_anomaly_rate"] for row in values], dtype=float)
        color = np.array([row["target_anomaly_rate"] for row in values], dtype=float)
        points = axis.scatter(x, y, c=color, cmap="YlGnBu", edgecolors="#333333", alpha=0.85)
        colorbar = figure.colorbar(points, ax=axis, pad=0.02)
        colorbar.set_label(f"{group['target_label']} 異常率（anomaly + suspect）")
        limit = max(float(x.max(initial=0)), float(y.max(initial=0)), 0.01) * 1.12
        padding = limit * 0.03
        axis.plot([0, limit], [0, limit], "--", color="#555555", label="y = x")
        axis.set_xlim(-padding, limit)
        axis.set_ylim(-padding, limit)
        axis.xaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:.2%}"))
        axis.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:.2%}"))
        axis.set_title(f"IISI01（金磚）vs {group['target_label']}\n異常率一致性散點圖")
        axis.set_xlabel("IISI01 異常率")
        axis.set_ylabel(f"{group['target_label']} 異常率")
        axis.grid(alpha=0.25)
        axis.legend()
        figure.savefig(OUTPUT_DIR / output_names[group["key"]], dpi=160, bbox_inches="tight")
        plt.close(figure)


def save_bland_altman(rows: list[dict[str, object]]) -> None:
    """輸出回傳數量差異的 Bland-Altman 圖。"""
    figure, axes = plt.subplots(1, 3, figsize=(20, 6), constrained_layout=True)
    for axis, group in zip(axes, GROUPS):
        values = group_rows(rows, group["key"])
        averages = np.array([(row["baseline_count"] + row["target_count"]) / 2 for row in values], dtype=float)
        differences = np.array([row["count_difference"] for row in values], dtype=float)
        axis.scatter(averages, differences, color=COLORS[group["target_vendor"]], alpha=0.8)
        mean_difference = float(differences.mean()) if len(differences) else 0.0
        standard_deviation = float(differences.std()) if len(differences) else 0.0
        axis.axhline(0, color="#555555", linestyle="--", linewidth=1)
        axis.axhline(mean_difference, color="#b22222", label=f"平均差 {mean_difference:.1f}")
        axis.axhline(mean_difference + 1.96 * standard_deviation, color="#b22222", linestyle=":")
        axis.axhline(mean_difference - 1.96 * standard_deviation, color="#b22222", linestyle=":", label="95% 差異範圍")
        axis.set_title(group["title"])
        axis.set_xlabel("兩家回傳數量平均值")
        axis.set_ylabel("對照廠商 - IISI01")
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
    figure.suptitle("Bland-Altman 差異圖：回傳數量偏差方向與幅度", fontsize=15)
    figure.savefig(OUTPUT_DIR / "02_integrated_bland_altman_difference.png", dpi=160, bbox_inches="tight")
    plt.close(figure)


def save_difference_ranking(rows: list[dict[str, object]]) -> None:
    """輸出各格位的回傳數量差異排序圖。"""
    figure, axes = plt.subplots(3, 1, figsize=(15, 16), constrained_layout=True)
    for axis, group in zip(axes, GROUPS):
        values = sorted(group_rows(rows, group["key"]), key=lambda row: abs(float(row["count_difference"])), reverse=True)
        labels = [f"{row['section_id']} / {row['baseline_ps_id']} → {row['target_ps_id']}" for row in values]
        differences = [row["count_difference"] for row in values]
        colors = ["#d95f02" if value >= 0 else "#1b9e77" for value in differences]
        axis.barh(labels, differences, color=colors)
        axis.axvline(0, color="#555555", linewidth=1)
        axis.invert_yaxis()
        axis.set_title(group["title"])
        axis.set_xlabel("對照廠商 - IISI01（回傳數量）")
        axis.grid(axis="x", alpha=0.25)
    figure.suptitle("各路段差異排序：找出回傳數量差異最大的格位", fontsize=15)
    figure.savefig(OUTPUT_DIR / "03_integrated_difference_ranking.png", dpi=160, bbox_inches="tight")
    plt.close(figure)


def save_assessment_heatmap(rows: list[dict[str, object]]) -> None:
    """輸出數量、異常率與綜合一致度熱圖。"""
    figure, axes = plt.subplots(3, 1, figsize=(12, 15), constrained_layout=True)
    columns = ("count_agreement", "anomaly_agreement", "overall_score")
    labels = ("數量一致度", "異常率一致度", "綜合一致度")
    for axis, group in zip(axes, GROUPS):
        values = sorted(group_rows(rows, group["key"]), key=lambda row: float(row["overall_score"]))
        matrix = np.array([[float(row[column]) for column in columns] for row in values])
        y_labels = [f"{row['section_id']} / {row['baseline_ps_id']} → {row['target_ps_id']}" for row in values]
        image = axis.imshow(matrix, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
        axis.set_title(group["title"])
        axis.set_xticks(range(len(labels)), labels)
        axis.set_yticks(range(len(y_labels)), y_labels, fontsize=7)
        for row_index, row in enumerate(matrix):
            for column_index, value in enumerate(row):
                axis.text(column_index, row_index, f"{value:.0%}", ha="center", va="center", fontsize=7)
        for row_index, row in enumerate(values):
            axis.text(len(columns) + 0.05, row_index, row["level"], va="center", fontsize=7)
        axis.set_xlim(-0.5, len(columns) + 0.8)
    figure.colorbar(image, ax=axes, label="一致度（0 至 100%）", shrink=0.8)
    figure.suptitle("路段綜合評估熱圖：一致度分級", fontsize=15)
    figure.savefig(OUTPUT_DIR / "04_integrated_assessment_heatmap.png", dpi=160, bbox_inches="tight")
    plt.close(figure)


def write_assessment_csv(rows: list[dict[str, object]]) -> None:
    """將整合後的評估資料寫入 CSV。"""
    output_path = OUTPUT_DIR / "integrated_assessment.csv"
    with output_path.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_final_comprehensive_assessment(rows: list[dict[str, object]]) -> None:
    """輸出指標、柱狀、折線與散點四種最終評比圖。"""
    # 各項指標先按比較組合取平均，再輸出四種不同閱讀角度的圖表。
    metrics = (
        ("count_agreement", "STATUS1+STATUS2\n數量一致度"),
        ("baseline_anomaly_quality", "IISI01\n低異常率品質"),
        ("target_anomaly_quality", "對照廠商\n低異常率品質"),
        ("time_agreement", "時間差\n一致度"),
    )
    group_scores = []
    for group in GROUPS:
        values = group_rows(rows, group["key"])
        group_scores.append([float(np.nanmean([float(row[column]) for row in values])) for column, _ in metrics])

    x_values = np.arange(len(GROUPS))
    bar_width = 0.18
    colors = ("#3182bd", "#1b9e77", "#d95f02", "#756bb1")
    labels = [f"{group['target_label']}\nvs IISI01（金磚）" for group in GROUPS]

    # 圖一：分開呈現四個評估指標，避免標籤互相遮擋。
    figure, axis = plt.subplots(figsize=(14, 7))
    for index, ((_, label), color) in enumerate(zip(metrics, colors)):
        values = [scores[index] for scores in group_scores]
        bars = axis.bar(x_values + (index - 1.5) * bar_width, values, width=bar_width, label=label.replace("\n", " "), color=color)
        for bar, value in zip(bars, values):
            axis.text(bar.get_x() + bar.get_width() / 2, value + 0.025, f"{value:.0%}", ha="center", va="bottom", fontsize=8)
    axis.set_xticks(x_values, labels)
    axis.set_ylim(0, 1.18)
    axis.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:.0%}"))
    axis.set_ylabel("分數（越高越好）")
    axis.set_title("三組比較各項指標平均評分")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(loc="upper right")
    figure.text(0.5, 0.02, "異常率越低分數越高；5% 以上為 0 分。時間差以平均絕對差 60 秒為一致範圍。", ha="center", fontsize=9)
    figure.tight_layout(rect=(0, 0.08, 1, 1))
    figure.savefig(OUTPUT_DIR / "05_final_metric_scores.png", dpi=160, bbox_inches="tight")
    plt.close(figure)

    # 將同一組比較的兩家廠商分別計算最終分數，直接呈現優劣。
    baseline_scores = [float(np.nanmean([row["baseline_overall_score"] for row in group_rows(rows, group["key"])])) for group in GROUPS]
    target_scores = [float(np.nanmean([row["target_overall_score"] for row in group_rows(rows, group["key"])])) for group in GROUPS]

    # 圖二：三組比較的最終評比分數柱狀圖。
    figure, score_axis = plt.subplots(figsize=(12, 7))
    score_width = 0.34
    baseline_bars = score_axis.bar(x_values - score_width / 2, baseline_scores, width=score_width, label="IISI01（金磚）", color=COLORS["IISI01"])
    target_bars = score_axis.bar(x_values + score_width / 2, target_scores, width=score_width, label="對照廠商", color="#d95f02")
    for bars in (baseline_bars, target_bars):
        for bar in bars:
            value = bar.get_height()
            score_axis.text(bar.get_x() + bar.get_width() / 2, value + 0.025, f"{value:.0%}", ha="center", va="bottom", fontsize=9)
    score_axis.set_xticks(x_values, [group["target_label"] for group in GROUPS])
    score_axis.set_ylim(0, 1.18)
    score_axis.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:.0%}"))
    score_axis.set_ylabel("最終評比（越高越好）")
    score_axis.set_title("三組比較最終評比")
    score_axis.grid(axis="y", alpha=0.25)
    score_axis.legend(loc="upper right")
    score_axis.text(0.01, 0.02, "分數越高代表綜合表現越好；數量與時間一致度為兩家共同比較指標。", transform=score_axis.transAxes, fontsize=9, bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"})
    figure.tight_layout()
    figure.savefig(OUTPUT_DIR / "06_final_vendor_scores.png", dpi=160, bbox_inches="tight")
    plt.close(figure)

    # 圖三：觀察三組比較中兩家廠商分數的變化趨勢。
    figure, axis = plt.subplots(figsize=(13, 7))
    axis.plot(labels, baseline_scores, marker="o", linewidth=2, label="IISI01（金磚）", color=COLORS["IISI01"])
    axis.plot(labels, target_scores, marker="o", linewidth=2, label="對照廠商", color="#d95f02")
    for values, color, offset in ((baseline_scores, COLORS["IISI01"], 12), (target_scores, "#d95f02", -16)):
        for index, value in enumerate(values):
            axis.annotate(f"{value:.0%}", (index, value), xytext=(0, offset), textcoords="offset points", ha="center", color=color)
    axis.set_ylim(0, 1.18)
    axis.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:.0%}"))
    axis.set_ylabel("最終評比（越高越好）")
    axis.set_title("三組比較最終評比折線圖")
    axis.grid(axis="y", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(OUTPUT_DIR / "07_final_vendor_scores_line.png", dpi=160, bbox_inches="tight")
    plt.close(figure)

    # 圖四：以 IISI01 為 X 軸、對照廠商為 Y 軸，檢視兩家最終分數關係。
    figure, axis = plt.subplots(figsize=(9, 8))
    axis.scatter(baseline_scores, target_scores, s=100, color="#d95f02", edgecolors="#333333")
    axis.plot([0, 1], [0, 1], "--", color="#555555", label="y = x")
    for x_value, y_value, label in zip(baseline_scores, target_scores, [group["target_label"] for group in GROUPS]):
        axis.annotate(label, (x_value, y_value), xytext=(7, 7), textcoords="offset points", fontsize=9)
    axis.set_xlim(0, 1.1)
    axis.set_ylim(0, 1.1)
    axis.xaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:.0%}"))
    axis.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:.0%}"))
    axis.set_xlabel("IISI01（金磚）最終評比")
    axis.set_ylabel("對照廠商最終評比")
    axis.set_title("三組比較最終評比散點圖")
    axis.grid(alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(OUTPUT_DIR / "08_final_vendor_scores_scatter.png", dpi=160, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    """依序完成設定、資料整合、CSV 輸出與圖表輸出。"""
    configure_plot()
    rows = build_rows()
    if not rows:
        raise ValueError("找不到可供三組比較的格位資料")
    write_assessment_csv(rows)
    save_scatter(rows)
    save_anomaly_scatter(rows)
    save_final_comprehensive_assessment(rows)
    print(f"已完成三組比較，共 {len(rows):,} 個格位，輸出三張散點圖與四張最終評比圖。")


if __name__ == "__main__":
    main()