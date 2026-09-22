import os
import json
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="智慧個人營養師分析助理",
    page_icon="🥗",
    layout="wide"
)

# 注入 Apple 簡約視覺 CSS
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
        letter-spacing: -0.015em;
    }
    .stApp {
        background-color: #000000;
        color: #f5f5f7;
    }
    h1 {
        font-weight: 700 !important;
        font-size: 2.1rem !important;
        letter-spacing: -0.03em !important;
        color: #ffffff !important;
        margin-bottom: 0.3rem !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #161617 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    div.stButton > button {
        border-radius: 980px !important;
        font-weight: 500 !important;
        font-size: 0.92rem !important;
        padding: 0.55rem 1.2rem !important;
        transition: all 0.2s cubic-bezier(0.25, 1, 0.5, 1) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        background-color: #1c1c1e !important;
        color: #f5f5f7 !important;
    }
    div.stButton > button:hover {
        background-color: #2c2c2e !important;
        border-color: rgba(255, 255, 255, 0.24) !important;
        transform: scale(1.01);
    }
    div.stButton > button[kind="primary"] {
        background-color: #0071e3 !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(0, 113, 227, 0.35) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #0077ed !important;
        box-shadow: 0 4px 14px rgba(0, 113, 227, 0.45) !important;
        transform: scale(1.015);
    }
    .stTextInput > div > div > input, 
    .stNumberInput > div > div > input {
        background-color: #1c1c1e !important;
        color: #f5f5f7 !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    .stTextInput > div > div > input:focus, 
    .stNumberInput > div > div > input:focus {
        border-color: #0071e3 !important;
        box-shadow: 0 0 0 1px #0071e3 !important;
    }
    section[data-testid="stFileUploaderDropzone"] {
        background-color: #161617 !important;
        border: 1px dashed rgba(255, 255, 255, 0.18) !important;
        border-radius: 16px !important;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
        font-size: 0.95rem;
    }
    th {
        background-color: #1c1c1e !important;
        color: #2997ff !important;
        padding: 10px 14px !important;
        border-bottom: 2px solid rgba(255, 255, 255, 0.15) !important;
        text-align: left;
    }
    td {
        padding: 10px 14px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
        color: #e5e5ea;
    }
</style>
""", unsafe_allow_html=True)

# 讀取預設 API Key
default_api_key = os.getenv("API_KEY")
if not default_api_key and "API_KEY" in st.secrets:
    default_api_key = st.secrets["API_KEY"]

PROFILE_FILE = "user_profiles.json"

def load_all_profiles():
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_single_profile(username, data):
    profiles = load_all_profiles()
    profiles[username] = data
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

if "user_code" not in st.session_state:
    st.session_state["user_code"] = "高天野"
if "w_age" not in st.session_state:
    st.session_state["w_age"] = 15
if "w_gender" not in st.session_state:
    st.session_state["w_gender"] = "男"
if "w_height" not in st.session_state:
    st.session_state["w_height"] = 170.0
if "w_weight" not in st.session_state:
    st.session_state["w_weight"] = 58.5
if "w_body_fat" not in st.session_state:
    st.session_state["w_body_fat"] = 10.0
if "w_target_weight" not in st.session_state:
    st.session_state["w_target_weight"] = 62.0
if "w_target_fat" not in st.session_state:
    st.session_state["w_target_fat"] = 10.0
if "w_activity" not in st.session_state:
    st.session_state["w_activity"] = "中度活動（每週運動 3-5 天）"
if "w_goal_type" not in st.session_state:
    st.session_state["w_goal_type"] = "乾淨增肌 / 增重"
if "meal_history" not in st.session_state:
    st.session_state["meal_history"] = []
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "latest_report" not in st.session_state:
    st.session_state["latest_report"] = ""

# ================= 側邊欄 =================
st.sidebar.markdown("### 🔑 API Key 設定")
custom_api_key = st.sidebar.text_input(
    "自訂金鑰（留空則使用預設）",
    type="password",
    placeholder="貼上 AI Studio 金鑰...",
    help="留空時會自動使用系統預設金鑰；填入後會改走您自己的專屬額度。"
)

active_api_key = custom_api_key.strip() if custom_api_key else default_api_key

if custom_api_key:
    st.sidebar.caption("🟢 正使用自訂金鑰")
elif default_api_key:
    st.sidebar.caption("⚪ 正使用系統預設金鑰")
else:
    st.sidebar.caption("🔴 未偵測到任何可用金鑰")

with st.sidebar.expander("❓ 如何 10 秒取得免費金鑰？"):
    st.markdown("""
    1. 前往 **[Google AI Studio](https://aistudio.google.com/app/apikey)**。
    2. 登入 Google 帳號，點擊 **「Create API key」**。
    3. 複製那串金鑰，貼到上方即可！
    
    *免綁信用卡、完全免費、享有個人專屬額度。*
    """)

st.sidebar.divider()

st.sidebar.markdown("### 👤 個人檔案代號")
user_code_input = st.sidebar.text_input("輸入代號", key="user_code")

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.sidebar.button("📂 載入", use_container_width=True):
        all_data = load_all_profiles()
        if user_code_input in all_data:
            p = all_data[user_code_input]
            st.session_state["w_age"] = int(p.get("age", 15))
            st.session_state["w_gender"] = p.get("gender", "男")
            st.session_state["w_height"] = float(p.get("height", 170.0))
            st.session_state["w_weight"] = float(p.get("weight", 58.5))
            st.session_state["w_body_fat"] = float(p.get("body_fat", 10.0))
            st.session_state["w_target_weight"] = float(p.get("target_weight", 62.0))
            st.session_state["w_target_fat"] = float(p.get("target_fat", 10.0))
            st.session_state["w_activity"] = p.get("activity_level", "中度活動（每週運動 3-5 天）")
            st.session_state["w_goal_type"] = p.get("goal_type", "乾淨增肌 / 增重")
            st.sidebar.caption("✅ 載入成功")
            st.rerun()
        else:
            st.sidebar.caption("⚠️ 查無代號")

with col2:
    if st.sidebar.button("💾 儲存", use_container_width=True):
        data_to_save = {
            "age": st.session_state["w_age"],
            "gender": st.session_state["w_gender"],
            "height": st.session_state["w_height"],
            "weight": st.session_state["w_weight"],
            "body_fat": st.session_state["w_body_fat"],
            "target_weight": st.session_state["w_target_weight"],
            "target_fat": st.session_state["w_target_fat"],
            "activity_level": st.session_state["w_activity"],
            "goal_type": st.session_state["w_goal_type"]
        }
        save_single_profile(user_code_input, data_to_save)
        st.sidebar.caption("✅ 已儲存")

st.sidebar.divider()

st.sidebar.markdown("### ⚙️ 調整身體數據")
age = st.sidebar.number_input("年齡", min_value=12, max_value=100, step=1, key="w_age")
gender = st.sidebar.selectbox("生理性別", ["男", "女"], key="w_gender")
height = st.sidebar.number_input("身高 (cm)", min_value=100.0, max_value=230.0, step=0.5, key="w_height")
weight = st.sidebar.number_input("目前體重 (kg)", min_value=30.0, max_value=200.0, step=0.5, key="w_weight")
body_fat = st.sidebar.number_input("目前體脂率 (%)", min_value=3.0, max_value=60.0, step=0.5, key="w_body_fat")

activity_options = [
    "久坐念書 / 上班（幾乎不運動）",
    "輕度活動（每週運動 1-3 天）",
    "中度活動（每週運動 3-5 天）",
    "高度運動（每週運動 6-7 天 / 校隊訓練）"
]
activity_level = st.sidebar.selectbox("日常活動強度", activity_options, key="w_activity")

st.sidebar.divider()
st.sidebar.markdown("### 🎯 目標設定")
goal_options = ["乾淨增肌 / 增重", "減脂塑形", "維持現狀與運動表現", "改善精神（預防飯後嗜睡）"]
goal_type = st.sidebar.selectbox("核心體態方向", goal_options, key="w_goal_type")

target_weight = st.sidebar.number_input("目標體重 (kg)", min_value=30.0, max_value=200.0, step=0.5, key="w_target_weight")
target_fat = st.sidebar.number_input("目標體脂率 (%)", min_value=3.0, max_value=60.0, step=0.5, key="w_target_fat")

if st.sidebar.button("🔄 同步更新數據", use_container_width=True, type="primary"):
    st.rerun()

if gender == "男":
    bmr = 10 * weight + 6.25 * height - 5 * age + 5
else:
    bmr = 10 * weight + 6.25 * height - 5 * age - 161

multipliers = {
    "久坐念書 / 上班（幾乎不運動）": 1.2,
    "輕度活動（每週運動 1-3 天）": 1.375,
    "中度活動（每週運動 3-5 天）": 1.55,
    "高度運動（每週運動 6-7 天 / 校隊訓練）": 1.725
}
tdee = bmr * multipliers.get(activity_level, 1.55)

st.sidebar.divider()
st.sidebar.markdown(f"🔥 **BMR**：`{int(bmr)}` kcal ｜ ⚡ **TDEE**：`{int(tdee)}` kcal")

diff_weight = round(target_weight - weight, 1)
diff_fat = round(target_fat - body_fat, 1)
weight_desc = f"+{diff_weight} kg" if diff_weight > 0 else f"{diff_weight} kg"
fat_desc = f"+{diff_fat} %" if diff_fat > 0 else f"{diff_fat} %"

# ================= 主頁面 =================
st.title("🥗 智慧個人營養師分析助理")
st.caption(f"學員：{st.session_state.user_code} ｜ {age} 歲 {gender}生 ｜ 身高 {height} cm")

st.info(f"🎯 **衝刺目標**：【{goal_type}】邁向 **{target_weight} kg**（差距 {weight_desc}）、目標體脂 **{target_fat}%**（差距 {fat_desc}）｜ 每日建議能量參考 (TDEE)：約 **{int(tdee)}** kcal")

meal_type = st.selectbox("這餐是什麼？", ["午餐便當", "早餐", "晚餐", "運動前後加餐", "點心 / 宵夜"])
user_note = st.text_input("備註補充（選填）", placeholder="例如：飯吃完、雞胸肉一大塊、搭配無糖豆漿")

uploaded_file = st.file_uploader("📸 請拍攝或上傳食物照片...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    img_bytes = uploaded_file.getvalue()
    mime = uploaded_file.type if uploaded_file.type else "image/jpeg"

    image_for_display = Image.open(uploaded_file)
    st.image(image_for_display, caption="餐點照片預覽", use_container_width=True)

    if st.button("🚀 開始量身分析這餐營養", type="primary", use_container_width=True):
        if not active_api_key:
            st.error("未偵測到有效 API Key！請在側邊欄填入自訂金鑰，或檢查伺服器環境變數。")
        else:
            status_placeholder = st.empty()
            status_placeholder.info("⚡ 正在為您建立專業量化估算與目標對照報告...")

            try:
                client = genai.Client(api_key=active_api_key)

                history_context = ""
                if st.session_state.meal_history:
                    history_context = "【使用者今日先前已記錄餐點摘要】：\n"
                    for idx, item in enumerate(st.session_state.meal_history, 1):
                        history_context += f"- 餐別 {idx} ({item['meal_type']})：{item['summary']}\n"

                prompt = f"""
                你是一位頂尖的資深運動營養師。
                請依據以下這位學員的詳細指標，嚴格按照指定的輸出結構對這張食物照片進行深度專業分析：

                【學員詳細指標】：
                - 學員姓名：{st.session_state.user_code}
                - 生理年齡/性別：{age} 歲，生理{gender}性
                - 身高/體重：{height} cm / {weight} kg
                - 目前體脂率：{body_fat} %（具備腹肌線條）
                - 體態衝刺目標：邁向體重 {target_weight} kg（差距 {weight_desc}）、目標體脂 {target_fat} %（差距 {fat_desc}）
                - 每日總能量消耗 (TDEE)：約 {int(tdee)} kcal
                - 核心方向：{goal_type}（兼顧青少年成長發育、骨骼生長與乾淨增肌）
                - 本餐時段：{meal_type}
                - 學員補充備註：{user_note if user_note else "無"}
                {history_context}

                請嚴格依照以下結構輸出繁體中文診斷（不可缺漏任何項目）：

                輸入類型：飲食評估（{meal_type}紀錄）  
                結論：[精闢、專業且針對學員體態目標的 1-2 句話總結，點評熱量、蛋白質與發育/增肌優劣]

                ### 一、 量化營養估算
                項目包含：[條列識別照片中所有的精確品項名稱與預估份量大小]

                | 食材項目 | 份量 | 熱量 (kcal) | 蛋白質 (g) | 碳水化合物 (g) | 脂肪 (g) | 鈣質/微量亮點 (mg) |
                | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
                | [品項1] | [份量] | [數值區間] | [數值區間] | [數值區間] | [數值區間] | [數值區間] |
                | [品項2] | [份量] | [數值區間] | [數值區間] | [數值區間] | [數值區間] | [數值區間] |
                | **本餐總計（誤差範圍）** | **—** | **[總計 kcal]** | **[總計 g]** | **[總計 g]** | **[總計 g]** | **[總計 mg]** |

                ### 二、 對照目標分析
                * **發育與骨骼健康（身高潛力）**：[分析本餐鈣質、微量元素與生長因子對 15 歲發育的推進成效]。
                * **增肌目標（{target_weight}kg 邁進）**：[分析蛋白質克數是否達標、高生物價佔比、碳水化合物是否足夠啟動胰島素合成肌肉]。
                * **飲食品質與體脂控制（維持 {target_fat}% 腹肌）**：[分析油脂來源、加工度、乾淨度與腹肌線條維持之關係]。

                ### 三、 具體行動建議（今日後續餐點銜接處方）
                1. **[第一點關鍵補強]**：[針對這餐所缺乏的營養素，給出下午或下一餐的精準補充清單]。
                2. **[第二點外食/超商實操方針]**：[針對高中生校園、外食或 7-11/全家，給出最方便入手的組合商品]。
                3. **[第三點生理刺激/生活型態]**：[例如訓練時間點、水分、睡眠或戶外維生素 D 吸收建議]。
                """

                image_part = types.Part.from_bytes(
                    data=img_bytes,
                    mime_type=mime
                )

                config = types.GenerateContentConfig(
                    max_output_tokens=3000,
                    temperature=0.2
                )

                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[image_part, prompt],
                    config=config
                )

                status_placeholder.empty()

                if response and response.text:
                    st.session_state["latest_report"] = response.text
                    st.session_state.meal_history.append({
                        "meal_type": meal_type,
                        "summary": f"{meal_type} - 深度診斷完成",
                        "full_report": response.text
                    })
                    st.rerun()
                else:
                    st.error("模型未回傳有效文本，請稍候重試。")

            except Exception as e:
                status_placeholder.empty()
                st.error(f"分析失敗，錯誤訊息：{e}")

# 渲染報告
if st.session_state["latest_report"]:
    st.markdown("---")
    st.markdown("### 📋 專屬營養診斷報告")
    st.markdown(st.session_state["latest_report"])

    st.markdown("---")
    st.subheader("💬 與專屬教練對話討論")
    st.caption("您可以針對這份表格數據、下一餐如何吃或訓練搭配，隨時向教練提問！")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_msg := st.chat_input("輸入您的問題（例如：如果下一餐我想在超商買地瓜，要買幾公克的？）"):
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)

        with st.chat_message("assistant"):
            with st.spinner("教練思考中..."):
                try:
                    client = genai.Client(api_key=active_api_key)
                    coach_prompt = f"""
                    你是一位頂尖運動營養教練。
                    學員檔案：{age}歲男性、{height}cm、{weight}kg、體脂率{body_fat}%。
                    目標：{target_weight}kg 乾淨增肌、維持 {target_fat}% 腹肌。
                    TDEE：{int(tdee)} kcal。

                    剛剛分析的餐點量化報告：
                    {st.session_state['latest_report']}

                    學員現在提問：
                    「{user_msg}」

                    請依據剛剛表格中的熱量與三大營養素缺口，給予專業、精準、可落地的繁體中文指導。
                    """
                    coach_res = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=coach_prompt,
                        config=types.GenerateContentConfig(max_output_tokens=1500)
                    )
                    st.markdown(coach_res.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": coach_res.text})
                except Exception as e:
                    st.error(f"對話異常：{e}")

if st.session_state.meal_history:
    st.markdown("---")
    st.markdown("### 📚 今日專屬飲食檔案庫（歷史紀錄）")
    for i, record in enumerate(reversed(st.session_state.meal_history), 1):
        with st.expander(f"📌 第 {len(st.session_state.meal_history) - i + 1} 筆紀錄：{record['meal_type']}"):
            st.markdown(record["full_report"])