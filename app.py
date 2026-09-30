import os
import base64
import requests
import streamlit as st
from PIL import Image

# ----------------- 頁面基本配置 -----------------
st.set_page_config(
    page_title="智慧個人營養師分析助理",
    page_icon="🥗",
    layout="wide"
)

# ----------------- 系統端讀取金鑰 -----------------
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or st.secrets.get("API_KEY")

# ----------------- 側邊欄：個人檔案與身體數據 -----------------
st.sidebar.markdown("### 👤 個人檔案代號")
user_id = st.sidebar.text_input("輸入代號", value="高天野")

st.sidebar.markdown("### ⚙️ 調整身體數據")
age = st.sidebar.number_input("年齡", min_value=10, max_value=100, value=15)
gender = st.sidebar.selectbox("性別", ["男生", "女生"], index=0)
height = st.sidebar.number_input("身高 (cm)", min_value=100.0, max_value=250.0, value=170.0, step=0.5)
weight = st.sidebar.number_input("目前體重 (kg)", min_value=30.0, max_value=200.0, value=58.5, step=0.5)
target_weight = st.sidebar.number_input("目標體重 (kg)", min_value=30.0, max_value=200.0, value=62.0, step=0.5)
current_body_fat = st.sidebar.number_input("目前體脂 (%)", min_value=3.0, max_value=50.0, value=10.0, step=0.5)
target_body_fat = st.sidebar.number_input("目標體脂 (%)", min_value=3.0, max_value=50.0, value=10.0, step=0.5)
goal_type = st.sidebar.selectbox("目標類型", ["乾淨增肌 / 增重", "減脂 / 塑形", "維持健康體態"], index=0)

# 計算基礎 TDEE 參考
bmr = (10 * weight) + (6.25 * height) - (5 * age) + (5 if gender == "男生" else -161)
tdee = int(bmr * 1.55)

# ----------------- 主畫面 -----------------
st.title("🥗 智慧個人營養師分析助理")
st.caption(f"學員：{user_id} ｜ {age} 歲 {gender} ｜ 身高 {height} cm ｜ 體重 {weight} kg ｜ 體脂 {current_body_fat}%")

weight_diff = round(target_weight - weight, 1)
diff_weight_text = f"+{weight_diff}" if weight_diff > 0 else f"{weight_diff}"

fat_diff = round(target_body_fat - current_body_fat, 1)
diff_fat_text = f"+{fat_diff}" if fat_diff > 0 else f"{fat_diff}"

st.info(f"🎯 **衝刺目標**：【{goal_type}】邁向 {target_weight} kg (差距 {diff_weight_text} kg) ｜ 目標體脂 {target_body_fat}% (差距 {diff_fat_text}%) ｜ 每日建議能量參考 (TDEE)：約 {tdee} kcal")

col1, col2 = st.columns(2)
with col1:
    meal_type = st.selectbox("這餐是什麼？", ["午餐便當", "早餐", "晚餐", "點心 / 運動前後加餐", "高蛋白補充"])
with col2:
    meal_note = st.text_input("備註補充 (選填)", placeholder="例如：飯吃完、雞胸肉一大塊、搭配無糖豆漿")

uploaded_file = st.file_uploader("📸 請拍攝或上傳食物照片...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="餐點照片預覽", use_container_width=True)

if st.button("🪄 開始量身分析這餐營養", use_container_width=True):
    if not api_key:
        st.error("伺服器金鑰未配置，請於 Streamlit Secrets 設定 GEMINI_API_KEY。")
    elif uploaded_file is None:
        st.warning("請先上傳食物照片再進行分析！")
    else:
        with st.spinner("AI 營養師正在為您計算份量與三大營養素..."):
            try:
                uploaded_file.seek(0)
                image_bytes = uploaded_file.read()
                image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                mime_type = uploaded_file.type if uploaded_file.type else "image/jpeg"

                prompt = f"""
你是一位專業的個人運動營養師。
目前正在為學員【{user_id}】進行精準飲食分析：
- 性別：{gender}，年齡：{age} 歲
- 身高：{height} cm，目前體重：{weight} kg，目前體脂：{current_body_fat}%
- 目標設定：{goal_type}（目標體重 {target_weight} kg，目標體脂 {target_body_fat}%）
- 每日建議 TDEE 參考：約 {tdee} kcal
- 餐別：{meal_type}
- 學員備註：{meal_note}

請仔細觀察圖片中的食物：
1. 估算每一項食材的名稱、份量與烹調方式。
2. 條列計算總熱量（kcal）以及三大營養素：蛋白質（g）、碳水化合物（g）、脂肪（g）。
3. 根據他設定的目標（{goal_type}），給出 2~3 點具體且可執行的飲食調整建議（例如：蛋白質是否充足、是否需要補充優質碳水或控制油脂等）。
請以清晰條列、語氣專業且鼓勵的方式回覆。
"""
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": image_b64
                                }
                            }
                        ]
                    }]
                }

                clean_key = str(api_key).strip()
                headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": clean_key
                }

                # 依序使用官方推薦的活躍模型
                models_to_try = [
                    "gemini-3.1-pro-preview",
                    "gemini-3-flash-preview",
                    "gemini-2.5-flash"
                ]
                res = None
                success = False

                for model_name in models_to_try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                    response = requests.post(url, headers=headers, json=payload, timeout=60)
                    if response.status_code == 200:
                        res = response
                        success = True
                        break
                    else:
                        res = response

                if success and res is not None:
                    res_data = res.json()
                    text_result = res_data["candidates"][0]["content"]["parts"][0]["text"]
                    st.success("分析完成！")
                    st.markdown(text_result)
                else:
                    err_msg = ""
                    if res is not None:
                        try:
                            err_msg = res.json().get("error", {}).get("message", res.text)
                        except Exception:
                            err_msg = res.text
                    st.error(f"分析失敗 ({res.status_code if res else '未知錯誤'})：{err_msg}")
            except Exception as e:
                st.error(f"發生未預期的錯誤：{e}")