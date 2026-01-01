import gradio as gr
import pandas as pd

# 讀檔
df = pd.read_excel("青年二日遊-點餐表單.xlsx")

# 餐廳欄位對應字典
restaurant_cols = {
    "春水岸": "第一天晚餐 (春水岸-埔里店 )",
    "捌壹倉庫": "第一天午餐 (捌壹倉庫 )"
}

# 模式一：用餐點查人
def search_by_food(restaurant, keyword):
    if restaurant not in restaurant_cols:
        return "⚠️ 無此餐廳選項"
    
    col = restaurant_cols[restaurant]

    filtered = df[df[col].astype(str).str.contains(keyword, case=False, na=False)]

    if filtered.empty:
        return "❗找不到相關餐點。"

    result = [f"{row['姓名']}｜{row[col]}" for _, row in filtered.iterrows()]
    return f"共 {len(result)} 位：\n" + "\n".join(result)

# 模式二：用姓名查餐點
def search_by_name(name):
    if not name:
        return "⚠️ 請輸入姓名"

    result_rows = []
    for label, col in restaurant_cols.items():
        matches = df[df["姓名"].astype(str) == name]
        if not matches.empty:
            meal = matches.iloc[0][col]
            result_rows.append(f"{label}：{meal}")
    if not result_rows:
        return "❗找不到此人"
    return f"{name} 點的餐點如下：\n" + "\n".join(result_rows)

# Gradio Tabs
with gr.Blocks() as demo:
    gr.Markdown("## 青年二日遊 - 點餐查詢系統")

    with gr.Tab("查詢：依餐點找人"):
        with gr.Row():
            dropdown = gr.Dropdown(["捌壹倉庫", "春水岸"], label="選擇餐廳")
            keyword = gr.Textbox(label="輸入餐點關鍵字")
        btn1 = gr.Button("查詢")
        output1 = gr.Textbox(label="查詢結果", lines=10)
        btn1.click(search_by_food, inputs=[dropdown, keyword], outputs=output1)

    with gr.Tab("查詢：依姓名找餐點"):
        name_input = gr.Textbox(label="輸入姓名")
        btn2 = gr.Button("查詢")
        output2 = gr.Textbox(label="查詢結果", lines=5)
        btn2.click(search_by_name, inputs=name_input, outputs=output2)

demo.launch()
