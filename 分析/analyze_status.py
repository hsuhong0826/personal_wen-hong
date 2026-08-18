import pandas as pd
import numpy as np

# ========== 設定變數 ==========
FILE_PATH = r"c:\Users\tyhsu39\Desktop\分析\status順序_080508008.csv"  # 分析檔案路徑
OUTPUT_PATH = r"c:\Users\tyhsu39\Desktop\分析\analyze_result.csv"      # 輸出檔案路徑
STATUS3_PATH = r"c:\Users\tyhsu39\Desktop\分析\analyze_result_status3.csv"    # status=3 紀錄輸出路徑
CHUNK_SIZE = 200_000  # 每批讀取筆數(一次200萬筆)

# ========== 16 種轉換規則定義 ==========
# 格式：(前一筆, 當前) -> (類型, 說明)  類型：None=正常, "可疑", "異常"
TRANSITION_RULES = {
    (1, 1): ("異常", "已經收到進車事件，下一筆又再次收到進車事件"),
    (1, 2): ("可疑", "車輛進入後直接離開；若時間很短，可能為正常短停；若時間過長則代表異常"),
    (1, 5): (None,   "正常"),
    (1, 6): ("異常", "車輛剛進入，但下一筆排程卻顯示車格無車"),
    (2, 1): ("可疑", "前一台車離開後很快又有下一台車進入；若時間很短，可能為正常快速換車；若時間過長則代表異常"),
    (2, 2): ("異常", "已經收到車輛離開事件，下一筆又再次收到離開事件"),
    (2, 5): ("異常", "車輛已離開，但下一筆排程仍顯示車格有車"),
    (2, 6): (None,   "正常"),
    (5, 1): ("異常", "目前顯示車格已有車，但下一筆又收到進車事件"),
    (5, 2): (None,   "正常"),
    (5, 5): (None,   "正常"),
    (5, 6): ("異常", "未收到車輛離開事件，狀態卻直接由有車變成無車"),
    (6, 1): (None,   "正常"),
    (6, 2): ("異常", "目前顯示車格無車，但卻收到車輛離開事件"),
    (6, 5): ("異常", "未收到車輛進入事件，狀態卻直接由無車變成有車"),
    (6, 6): (None,   "正常"),
}

# 需要計算時間差的組合（1→2 和 2→1）
TIME_DIFF_PAIRS = {(1, 2), (2, 1)}

# ========== 可疑紀錄時間差門檻（分鐘） ==========
# 1→2（進車後直接離開）：時間差超過此值才記錄到輸出
MIN_TIME_DIFF_1_TO_2 = 90
# 2→1（離開後快速進車）：時間差超過此值才記錄到輸出
MIN_TIME_DIFF_2_TO_1 = 90

# ========== 向量化異常判斷函式 ==========
def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """對已排序的 DataFrame 進行向量化異常偵測"""
    group_keys = ["section_id", "ps_id", "vendorcode"]

    df = df.sort_values(group_keys + ["sta_dt"]).reset_index(drop=True)
    prev = df.groupby(group_keys)[["sta_dt", "status"]].shift(1)
    df["prev_sta_dt"] = prev["sta_dt"]
    df["prev_status"] = prev["status"]

    # 排除每組第一筆
    df = df.dropna(subset=["prev_status"]).copy()
    df["prev_status"] = df["prev_status"].astype(int)
    df["status"] = df["status"].astype(int)

    # 時間差（分鐘），僅 1→2 和 2→1 填值，其餘為 NaN
    df["time_diff_min"] = np.where(
        list(zip(df["prev_status"], df["status"])) == list(zip(df["prev_status"], df["status"])),  # placeholder
        (df["sta_dt"] - df["prev_sta_dt"]).dt.total_seconds() / 60,
        np.nan,
    )
    # 只保留 TIME_DIFF_PAIRS 的時間差
    is_time_diff_pair = [
        (int(p), int(c)) in TIME_DIFF_PAIRS
        for p, c in zip(df["prev_status"], df["status"])
    ]
    df["差異時間"] = np.where(is_time_diff_pair, df["time_diff_min"].round(2), np.nan)

    # 對應規則
    transition_tuples = list(zip(df["prev_status"].astype(int), df["status"].astype(int)))
    types = [TRANSITION_RULES.get(t, ("異常", f"未定義的轉換：{t[0]}→{t[1]}"))[0] for t in transition_tuples]
    descs = [TRANSITION_RULES.get(t, ("異常", f"未定義的轉換：{t[0]}→{t[1]}"))[1] for t in transition_tuples]

    df["類型"] = types
    df["說明"] = descs

    # 只保留可疑或異常
    result = df[df["類型"].isin(["可疑", "異常"])].copy()

    return result[group_keys + ["prev_sta_dt", "prev_status", "sta_dt", "status", "差異時間", "類型", "說明"]].rename(
        columns={
            "prev_sta_dt": "前一筆時間",
            "prev_status": "前一筆狀態",
            "sta_dt":      "當前時間",
            "status":      "當前狀態",
        }
    )


# ========== 分批讀取與處理 ==========
print(f"開始讀取檔案，每批 {CHUNK_SIZE:,} 筆...")

chunks = pd.read_csv(
    FILE_PATH,
    parse_dates=["sta_dt"],
    chunksize=CHUNK_SIZE,
    dtype={"section_id": str, "ps_id": str, "vendorcode": str, "status": int},
)

all_results = []
status3_results = []      # status==3 紀錄暫存
buffer = pd.DataFrame()   # 跨批次銜接用的緩衝區
total_rows = 0

for i, chunk in enumerate(chunks):
    # 過濾掉 status == 3 的資料，並另存暫存
    status3_chunk = chunk[chunk["status"] == 3]
    if not status3_chunk.empty:
        status3_results.append(status3_chunk)
    chunk = chunk[chunk["status"] != 3]

    total_rows += len(chunk)
    print(f"  處理第 {i+1} 批，累計 {total_rows:,} 筆...", end="\r")

    # 合併上一批的尾部資料（避免跨批次邊界漏判）
    combined = pd.concat([buffer, chunk], ignore_index=True)

    # 排序
    combined = combined.sort_values(["section_id", "ps_id", "vendorcode", "sta_dt"])

    # 保留每個群組的最後一筆作為下一批的緩衝
    buffer = combined.groupby(["section_id", "ps_id", "vendorcode"]).tail(1).copy()

    # 偵測異常（排除各群組最後一筆，因為需等下一批）
    last_idx = buffer.index
    process_df = combined.drop(index=last_idx)

    if not process_df.empty:
        result = detect_anomalies(process_df)
        if not result.empty:
            all_results.append(result)

# 處理最後一批緩衝（無後續資料，不需跨批比較）
if not buffer.empty:
    result = detect_anomalies(buffer)
    if not result.empty:
        all_results.append(result)

print(f"\n讀取完成，共 {total_rows:,} 筆資料")

# ========== 輸出結果 ==========
if all_results:
    result_df = pd.concat(all_results, ignore_index=True).drop_duplicates()

    # ========== 可疑紀錄時間差篩選 ==========
    # 1→2 可疑：僅保留時間差 > MIN_TIME_DIFF_1_TO_2 的紀錄
    mask_1_to_2 = (result_df["前一筆狀態"] == 1) & (result_df["當前狀態"] == 2) & (result_df["類型"] == "可疑")
    drop_1_to_2 = mask_1_to_2 & (result_df["差異時間"] <= MIN_TIME_DIFF_1_TO_2)
    # 2→1 可疑：僅保留時間差 > MIN_TIME_DIFF_2_TO_1 的紀錄
    mask_2_to_1 = (result_df["前一筆狀態"] == 2) & (result_df["當前狀態"] == 1) & (result_df["類型"] == "可疑")
    drop_2_to_1 = mask_2_to_1 & (result_df["差異時間"] <= MIN_TIME_DIFF_2_TO_1)
    result_df = result_df[~(drop_1_to_2 | drop_2_to_1)].reset_index(drop=True)
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 80)
    anomaly_count  = len(result_df[result_df["類型"] == "異常"])
    suspect_count  = len(result_df[result_df["類型"] == "可疑"])
    print(f"共發現 {len(result_df):,} 筆（異常：{anomaly_count:,} 筆 / 可疑：{suspect_count:,} 筆）\n")

    # ========== 匯出 CSV ==========
    result_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n✅ 判斷異常狀態結果已匯出至：{OUTPUT_PATH}")
else:
    print("✅ 未發現任何異常或可疑！")

# ========== 匯出 status==3 紀錄 ==========
if status3_results:
    status3_df = pd.concat(status3_results, ignore_index=True).drop_duplicates()
    status3_df["類型"] = "未回傳"
    status3_df["說明"] = "設備未回傳"
    status3_df.to_csv(STATUS3_PATH, index=False, encoding="utf-8-sig")
    print(f"✅ 判斷 status=3 紀錄（共 {len(status3_df):,} 筆）已匯出至：{STATUS3_PATH}")
