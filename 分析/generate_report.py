import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams
import base64, io, math

rcParams["font.family"] = "Microsoft JhengHei"
rcParams["axes.unicode_minus"] = False

# ========== 設定變數 ==========
SOURCE_PATH  = r"c:\Users\tyhsu39\Desktop\分析\status順序_080508008.csv"      # 原始資料路徑
INPUT_PATH   = r"c:\Users\tyhsu39\Desktop\分析\analyze_result.csv"           # 異常分析結果檔案路徑
STATUS3_PATH = r"c:\Users\tyhsu39\Desktop\分析\analyze_result_status3.csv"   # status=3 紀錄路徑
OUTPUT_PATH  = r"c:\Users\tyhsu39\Desktop\分析\report.html"                  # 輸出檔案路徑

# ========== 讀取資料 ==========
df = pd.read_csv(INPUT_PATH, dtype={"section_id": str, "ps_id": str, "vendorcode": str})
df3 = pd.read_csv(STATUS3_PATH, dtype={"section_id": str, "ps_id": str, "vendorcode": str})

with open(SOURCE_PATH, "r", encoding="utf-8") as f:
    total_source = sum(1 for _ in f) - 1

n_anomaly = len(df[df["類型"] == "異常"])
n_suspect = len(df[df["類型"] == "可疑"])

# 所有廠商主清單（取兩個檔案的聯集）
all_vendors_master = sorted(set(df["vendorcode"].unique()) | set(df3["vendorcode"].unique()))

COLOR_ANOMALY = "#e74c3c"
COLOR_SUSPECT = "#f39c12"

def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f'<img src="data:image/png;base64,{encoded}" style="width:100%;height:auto;">'

# ========== 圖一：圓餅圖 ==========
fig1, ax1 = plt.subplots(figsize=(6, 5), facecolor="white")

sizes  = [n_anomaly, n_suspect]
colors = [COLOR_ANOMALY, COLOR_SUSPECT]
labels_pie = ["異常", "可疑"]

wedges, _ = ax1.pie(
    sizes, labels=None, colors=colors,
    autopct=None,
    startangle=90,
    wedgeprops=dict(width=0.55, edgecolor="white", linewidth=2),
)

for i, (wedge, label) in enumerate(zip(wedges, labels_pie)):
    angle = (wedge.theta2 + wedge.theta1) / 2
    x = 1.18 * math.cos(math.radians(angle))
    y = 1.18 * math.sin(math.radians(angle))
    pct_of_total = sizes[i] / total_source * 100

ax1.set_title("異常 / 可疑 比例", fontsize=15, fontweight="bold", pad=20, color="#2c3e50")
ax1.axis("equal")

patch_a = mpatches.Patch(color=COLOR_ANOMALY, label=f"異常　{n_anomaly:,} 筆")
patch_s = mpatches.Patch(color=COLOR_SUSPECT, label=f"可疑　{n_suspect:,} 筆")
ax1.legend(handles=[patch_a, patch_s], loc="lower center",
           bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=11, frameon=False)

pie_html = fig_to_base64(fig1)

# ========== 圖二：廠商堆疊長條圖 ==========
vendor_summary = (
    df.groupby(["vendorcode", "類型"])
    .size()
    .reset_index(name="筆數")
)
vendor_total = df.groupby("vendorcode").size().reset_index(name="廠商總計")
vendor_summary = vendor_summary.merge(vendor_total, on="vendorcode")
vendor_summary["佔廠商%"] = (vendor_summary["筆數"] / vendor_summary["廠商總計"] * 100).round(1)

all_vendors = all_vendors_master
n_vendors = len(all_vendors)

def get_vals(type_name):
    sub = vendor_summary[vendor_summary["類型"] == type_name].set_index("vendorcode").reindex(all_vendors)
    return sub["筆數"].fillna(0).astype(int).tolist(), sub["佔廠商%"].fillna(0).tolist()

suspect_vals, suspect_pcts = get_vals("可疑")
anomaly_vals, anomaly_pcts = get_vals("異常")

fig2, ax2 = plt.subplots(figsize=(max(8, n_vendors * 1.8), 6), facecolor="white")
x = range(n_vendors)
bar_w = 0.5

ax2.bar(x, suspect_vals, bar_w, color=COLOR_SUSPECT, label="可疑", zorder=3)
ax2.bar(x, anomaly_vals, bar_w, bottom=suspect_vals, color=COLOR_ANOMALY, label="異常", zorder=3)

ax2.set_xticks(list(x))
ax2.set_xticklabels(all_vendors, fontsize=12)
ax2.set_xlabel("廠商代碼", fontsize=12, labelpad=10)
ax2.set_ylabel("筆數", fontsize=12, labelpad=10)
ax2.set_title("各廠商異常 / 可疑筆數", fontsize=15, fontweight="bold", pad=20, color="#2c3e50")
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
ax2.legend(fontsize=11, frameon=False, loc="upper right")
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)
ax2.yaxis.grid(True, color="#ececec", zorder=0)
ax2.set_axisbelow(True)

vendor_bar_html = fig_to_base64(fig2)

# ========== 圖三：未回傳(status=3) 廠商長條圖 ==========
COLOR_STATUS3 = "#8e44ad"
vendor3_summary = df3.groupby("vendorcode").size().reset_index(name="筆數")
vendor3_lookup = vendor3_summary.set_index("vendorcode")["筆數"].to_dict()
all_vendors3 = all_vendors_master
vals3 = [vendor3_lookup.get(v, 0) for v in all_vendors3]
n_vendors3 = len(all_vendors3)

fig3, ax3 = plt.subplots(figsize=(max(8, n_vendors3 * 1.8), 6), facecolor="white")
x3 = range(n_vendors3)
bars3 = ax3.bar(x3, vals3, 0.5, color=COLOR_STATUS3, zorder=3)
ax3.set_xticks(list(x3))
ax3.set_xticklabels(all_vendors3, fontsize=12)
ax3.set_xlabel("廠商代碼", fontsize=12, labelpad=10)
ax3.set_ylabel("筆數", fontsize=12, labelpad=10)
ax3.set_title("各廠商未回傳(status=3)筆數", fontsize=15, fontweight="bold", pad=20, color="#2c3e50")
ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
ax3.spines["top"].set_visible(False)
ax3.spines["right"].set_visible(False)
ax3.yaxis.grid(True, color="#ececec", zorder=0)
ax3.set_axisbelow(True)
max_val3 = max(vals3) if max(vals3) > 0 else 1
for bar, val in zip(bars3, vals3):
    ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max_val3 * 0.01,
             f"{val:,}", ha="center", va="bottom", fontsize=10, color="#555")
status3_bar_html = fig_to_base64(fig3)

# ========== 未回傳資料表 ==========
n_status3 = len(df3)
status3_rows = ""
for vendor in all_vendors_master:
    cnt = vendor3_lookup.get(vendor, 0)
    pct = cnt / n_status3 * 100 if n_status3 > 0 else 0
    status3_rows += f"""
    <tr>
      <td>{vendor}</td>
      <td>{cnt:,}</td>
      <td>{pct:.1f}%</td>
    </tr>"""
status3_rows += f"""
    <tr class="total-row">
      <td>合計</td>
      <td>{n_status3:,}</td>
      <td>100%</td>
    </tr>"""

status3_table_html = f"""
<table>
  <thead>
    <tr>
      <th>廠商代碼</th>
      <th>未回傳筆數</th>
      <th>佔未回傳總筆數</th>
    </tr>
  </thead>
  <tbody>{status3_rows}
  </tbody>
</table>"""
total_result = n_anomaly + n_suspect
pie_table_html = f"""
<table>
  <thead>
    <tr><th>類型</th><th>筆數</th><th>佔異常+可疑</th><th>佔全部原始資料</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><span class="badge badge-anomaly">異常</span></td>
      <td>{n_anomaly:,}</td>
      <td>{n_anomaly/total_result*100:.1f}%</td>
      <td>{n_anomaly/total_source*100:.1f}%</td>
    </tr>
    <tr>
      <td><span class="badge badge-suspect">可疑</span></td>
      <td>{n_suspect:,}</td>
      <td>{n_suspect/total_result*100:.1f}%</td>
      <td>{n_suspect/total_source*100:.1f}%</td>
    </tr>
    <tr class="total-row">
      <td>合計</td>
      <td>{total_result:,}</td>
      <td>100%</td>
      <td>{total_result/total_source*100:.1f}%</td>
    </tr>
  </tbody>
</table>"""

# ========== 廠商資料表 ==========
grand_total   = n_anomaly + n_suspect
vendor_rows = ""
for vendor in all_vendors_master:
    s_val = vendor_summary[(vendor_summary["vendorcode"] == vendor) & (vendor_summary["類型"] == "可疑")]["筆數"].sum()
    a_val = vendor_summary[(vendor_summary["vendorcode"] == vendor) & (vendor_summary["類型"] == "異常")]["筆數"].sum()
    total_v = s_val + a_val
    s_pct  = s_val   / n_suspect    * 100 if n_suspect    > 0 else 0
    a_pct  = a_val   / n_anomaly    * 100 if n_anomaly    > 0 else 0
    t_pct  = total_v / grand_total  * 100 if grand_total  > 0 else 0
    vendor_rows += f"""
    <tr>
      <td>{vendor}</td>
      <td>{s_val:,} ({s_pct:.1f}%)</td>
      <td>{a_val:,} ({a_pct:.1f}%)</td>
      <td>{total_v:,} ({t_pct:.1f}%)</td>
    </tr>"""

vendor_rows += f"""
    <tr class="total-row">
      <td>合計</td>
      <td>{n_suspect:,} (100%)</td>
      <td>{n_anomaly:,} (100%)</td>
      <td>{grand_total:,} (100%)</td>
    </tr>"""

vendor_table_html = f"""
<table>
  <thead>
    <tr>
      <th>廠商代碼</th>
      <th>可疑筆數（比例）</th>
      <th>異常筆數（比例）</th>
      <th>合計（比例）</th>
    </tr>
  </thead>
  <tbody>{vendor_rows}
  </tbody>
</table>"""
def stat_card(title, value, color, sub=""):
    return f"""
    <div class="card" style="border-left: 6px solid {color};">
        <div class="card-title">{title}</div>
        <div class="card-value" style="color:{color};">{value:,}</div>
        {f'<div class="card-sub">{sub}</div>' if sub else ''}
    </div>"""

cards_html = f"""
<div class="cards">
    {stat_card("原始總筆數", total_source, "#3498db")}
    {stat_card("異常筆數", n_anomaly, "#e74c3c", f"佔全部 {n_anomaly/total_source*100:.1f}%")}
    {stat_card("可疑筆數", n_suspect, "#f39c12", f"佔全部 {n_suspect/total_source*100:.1f}%")}
    {stat_card("未回傳筆數", n_status3, "#8e44ad", f"佔全部 {n_status3/total_source*100:.1f}%")}
    {stat_card("涉及廠商數", df['vendorcode'].nunique(), "#9b59b6")}
</div>"""

# ========== 組合 HTML ==========
html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>停車狀態異常分析報表</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: "Microsoft JhengHei", Arial, sans-serif; background: #f4f6f9; color: #333; }}
  header {{ background: #2c3e50; color: white; padding: 24px 40px; }}
  header h1 {{ font-size: 1.8rem; }}
  header p {{ margin-top: 6px; font-size: 0.95rem; color: #bdc3c7; }}
  .container {{ max-width: 1300px; margin: 0 auto; padding: 30px 24px; }}
  .section-title {{
    font-size: 1.2rem; font-weight: bold; color: #2c3e50;
    border-left: 4px solid #3498db; padding-left: 12px;
    margin: 36px 0 18px;
  }}
  .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 28px; }}
  .card {{
    flex: 1; min-width: 160px; background: white;
    border-radius: 10px; padding: 20px 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
  }}
  .card-title {{ font-size: 0.85rem; color: #888; margin-bottom: 8px; }}
  .card-value {{ font-size: 2rem; font-weight: bold; }}
  .card-sub {{ font-size: 0.9rem; color: #aaa; margin-top: 4px; }}
  .chart-box {{
    background: white; border-radius: 10px; padding: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07); margin-bottom: 24px;
  }}
  .chart-box.half {{ max-width: 520px; }}
  .chart-with-table {{ display: flex; gap: 24px; align-items: flex-start; margin-bottom: 24px; flex-wrap: wrap; }}
  .chart-with-table .chart-box {{ flex: 1; min-width: 300px; margin-bottom: 0; }}
  .table-box {{
    flex: 1; min-width: 280px; background: white;
    border-radius: 10px; padding: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
  }}
  .table-box h3 {{ font-size: 1rem; color: #2c3e50; margin-bottom: 14px; font-weight: bold; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
  thead tr {{ background: #2c3e50; color: white; }}
  thead th {{ padding: 10px 14px; text-align: center; font-weight: 600; }}
  tbody tr {{ border-bottom: 1px solid #f0f0f0; }}
  tbody tr:hover {{ background: #fafafa; }}
  tbody td {{ padding: 9px 14px; text-align: center; color: #444; }}
  tbody td:first-child {{ text-align: center; font-weight: 500; }}
  tr.total-row {{ background: #f8f9fa; font-weight: bold; }}
  tr.total-row td {{ color: #2c3e50; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px; color: white; font-size: 0.82rem; font-weight: bold; }}
  .badge-anomaly {{ background: #e74c3c; }}
  .badge-suspect {{ background: #f39c12; }}
  footer {{ text-align: center; padding: 24px; color: #aaa; font-size: 0.85rem; }}
</style>
</head>
<body>
<header>
  <h1>🅿️ 停車狀態異常分析報表</h1>
  <p>資料來源：analyze_result.csv　　產製時間：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</p>
</header>
<div class="container">
  <div class="section-title">📊 區塊一：總覽統計</div>
  {cards_html}
  <div class="chart-with-table">
    <div class="chart-box">{pie_html}</div>
    <div class="table-box">
      <h3>📋 異常 / 可疑 統計表</h3>
      {pie_table_html}
    </div>
  </div>

  <div class="section-title">🏭 區塊二：依廠商（vendorcode）分類</div>
  <div class="chart-box">{vendor_bar_html}</div>
  <div class="table-box" style="margin-bottom:24px;">
    <h3>📋 各廠商明細表</h3>
    {vendor_table_html}
  </div>

  <div class="section-title">📵 區塊三：各廠商未回傳（status=3）統計</div>
  <div class="chart-box">{status3_bar_html}</div>
  <div class="table-box" style="margin-bottom:24px;">
    <h3>📋 各廠商未回傳明細表</h3>
    {status3_table_html}
  </div>
</div>
<footer>停車狀態順序異常分析系統</footer>
</body>
</html>"""

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ 報表已產製完成：{OUTPUT_PATH}")
