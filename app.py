import os
import json
import streamlit as st
import google.generativeai as genai
from google.api_core import client_options as client_options_lib
from PIL import Image

# ----------------- 頁面基本配置 -----------------
st.set_page_config(
    page_title="智慧個人營養師分析助理",
    page_icon="🥗",
    layout="wide"
)

# ----------------- 側邊欄：API Key 設定 -----------------
st.sidebar.markdown("### 🔑 API Key 設定")
custom_key = st.sidebar.text_input(
    "自訂金鑰 (留空則使用預設)",
    type="password",
    help="若留空，系統將使用預設的 AI Studio 金鑰"
)

# 依序取得金鑰（自訂 > Streamlit Secrets > 系統環境變數）
api_key = None
if custom_key and custom_key.strip():
    api_key = custom_key.strip()
elif "API_KEY" in st.secrets:
    api_key = st.secrets["API_KEY"]
elif os.getenv("API_KEY"):
    api_key = os.getenv("API_KEY")

# 初始化 Gemini API（支援 AQ 格式與標準格式）
api_ready = False
if api_key:
    api_key = api_key.strip()
    try:
        if api_key.startswith("AQ."):
            # 強制走 REST 協定，避免舊版 gRPC 報 401 錯誤
            genai.configure(
                api_key=api_key,
                transport="rest",
                client_options=client_options_lib.ClientOptions(
                    api_endpoint="generativelanguage.googleapis.com"
                )
            )
        else:
            genai.configure(api_key=api_key)
        api_ready = True
        st.sidebar.success("● 正使用系統預設金鑰" if not custom_key else "● 正使用自訂金鑰")
    except Exception as e:
        st.sidebar.error(f"金鑰配置失敗: {e}")
else:
    st.sidebar.warning("⚠️ 尚未設定 API 金鑰，請輸入金鑰或於 Secrets 配置")

# --- 教別人取得金鑰的教學折疊區塊 ---
with st.sidebar.expander("❓ 如何 10 秒取得免費金鑰？"):
    st.markdown("""
    1. 前往 [Google AI Studio](https://aistudio.google.com/app/apikey)。
    2. 登入 Google 帳號，點擊 **「Create API key」**。
    3. 複製那串金鑰，貼到上方即可！
    
    *免綁信用卡、完全免費、享有個人專屬額度。*
    """)

st.sidebar.markdown("---")

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
tdee = int(bmr * 1.55)  # 抓中度活動量

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
    if not api_ready:
        st.error("請先設定有效的 API 金鑰！")
    elif uploaded_file is None:
        st.warning("請先上傳食物照片再進行分析！")
    else:
        with st.spinner("AI 營養師正在為您計算份量與三大營養素..."):
            try:
                # 使用視覺模型進行多模態辨識分析
                model = genai.GenerativeModel("gemini-1.5-flash")
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
                response = model.generate_content([prompt, image])
                st.success("分析完成！")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"分析失敗，錯誤訊息：{e}")