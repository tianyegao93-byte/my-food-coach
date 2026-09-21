import os
import streamlit as st
from google import genai
from PIL import Image
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# 1. 頁面整體設定
st.set_page_config(
    page_title="校園智慧飲食營養分析助理",
    page_icon="🥗",
    layout="wide"
)

# 2. 安全讀取 API Key（優先讀取 .env，其次讀取 Streamlit Secrets）
api_key = os.getenv("API_KEY")
if not api_key and "API_KEY" in st.secrets:
    api_key = st.secrets["API_KEY"]

# 3. 側邊欄：個人健康檔案設定
st.sidebar.header("👤 請先設定你的個人健康檔案")
st.sidebar.caption("輸入你的生理數值，AI 會根據你的目標與活動量給予量身建議。")

age = st.sidebar.number_input("年齡", min_value=12, max_value=80, value=16, step=1)
gender = st.sidebar.selectbox("生理性別", ["男", "女"])
height = st.sidebar.number_input("身高 (cm)", min_value=100.0, max_value=220.0, value=170.0, step=0.5)
weight = st.sidebar.number_input("體重 (kg)", min_value=30.0, max_value=150.0, value=60.0, step=0.5)

activity_level = st.sidebar.selectbox(
    "日常活動強度",
    [
        "久坐念書（活動量低，每週幾乎不運動）",
        "輕度活動（每週運動 1-3 天，或常走路走動）",
        "中度活動（體育課 + 每週運動 3-5 天）",
        "高度運動（體育班 / 每日高強度校隊訓練）"
    ]
)

special_goal = st.sidebar.selectbox(
    "目前最希望改善的飲食狀況",
    [
        "容易飯後嗜睡 / 預防下午上課昏睡",
        "青春發育增肌（需要充足蛋白質與能量）",
        "體態控制（控制熱量與油脂，維持輕盈）",
        "腸胃容易脹氣 / 消化吸收較差",
        "無特殊狀況，一般健康維持"
    ]
)

# 自動計算個人基礎代謝 (BMR) 與每日總消耗 (TDEE)
if gender == "男":
    bmr = 10 * weight + 6.25 * height - 5 * age + 5
else:
    bmr = 10 * weight + 6.25 * height - 5 * age - 161

activity_multiplier = {
    "久坐念書（活動量低，每週幾乎不運動）": 1.2,
    "輕度活動（每週運動 1-3 天，或常走路走動）": 1.375,
    "中度活動（體育課 + 每週運動 3-5 天）": 1.55,
    "高度運動（體育班 / 每日高強度校隊訓練）": 1.725
}
tdee = int(bmr * activity_multiplier[activity_level])

st.sidebar.markdown("---")
st.sidebar.markdown(f"**📈 你的每日總消耗 (TDEE)：** 約 `{tdee}` 大卡")
st.sidebar.markdown(f"**🔥 基礎代謝率 (BMR)：** 約 `{int(bmr)}` 大卡")

# 4. 主要畫面：上傳食物照片並分析
st.title("🥗 校園智慧飲食營養分析助理")
st.markdown(f"哈囉！系統已為你載入個人生理檔案（{age} 歲、TDEE 約 {tdee} 大卡）。請在下方上傳餐點照片開始分析！")

meal_type = st.selectbox("這餐是什麼？", ["午餐便當", "早餐", "晚餐", "下午點心 / 手搖杯 / 宵夜"])
user_note = st.text_input("備註（選填）", placeholder="例如：白飯有吃完、排骨去皮、有搭配無糖綠茶")

uploaded_file = st.file_uploader("📸 請拍照或上傳食物照片...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="待分析的餐點照片", use_container_width=True)

    if st.button("🚀 開始量身分析這餐營養", type="primary"):
        if not api_key:
            st.error("找不到 API Key！請檢查專案根目錄的 .env 檔案是否包含 API_KEY=你的金鑰。")
        else:
            with st.spinner("AI 正在結合你的個人數值、估算熱量並診斷飲食中..."):
                try:
                    client = genai.Client(api_key=api_key)
                    
                    prompt = f"""
                    你是一位專業營養師與青少年發育健康顧問。
                    請根據以下這位使用者的「專屬個人檔案」，對這張食物照片進行深度分析：

                    【使用者個人檔案】：
                    - 生理性別：{gender}，年齡：{age} 歲
                    - 身高：{height} cm，體重：{weight} kg
                    - 活動強度：{activity_level}
                    - 每日估算總消耗熱量 (TDEE)：約 {tdee} 大卡
                    - 目前關注重點：{special_goal}
                    - 用餐時段：{meal_type}
                    - 使用者補充備註：{user_note if user_note else "無"}

                    請仔細觀察這張照片，依序產出繁體中文的結構化報告：

                    ### 🍱 一、 食材拆解與烹調方式
                    - 清晰列出辨識到的主要主食、肉類配菜與蔬菜，並點出烹調方式（如裹粉油炸、高鈉滷汁、清炒等）。

                    ### 📊 二、 營養素量化與個人標準對照
                    - 估算本餐總熱量（kcal），並說明約佔他個人每日總消耗 (TDEE {tdee} kcal) 的百分之幾。
                    - 粗估三大營養素：蛋白質 (g)、碳水化合物 (g)、脂肪 (g) 及佔比。

                    ### 🎯 三、 針對個人體質與目標的改善建議
                    - 針對他的主要目標（{special_goal}）與用餐時段（{meal_type}），說明這餐對他下午精神、專注度或增肌發育的影響。
                    - 提供 2 個具體、外食極好執行的加減分微調做法。
                    """

                    response = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=[image, prompt]
                    )

                    st.success("報告產出完成！")
                    st.markdown(response.text)

                except Exception as e:
                    st.error(f"分析過程發生錯誤：{str(e)}")