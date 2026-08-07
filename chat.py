import streamlit as st
import pandas as pd
import requests
import json

st.set_page_config(page_title="ИИ Чат-Аналитик", layout="wide")
st.title("🧠 Персональный ИИ-Аналитик Данных & Стратег")

st.sidebar.success("🚀 Безлимитный текстовый движок ИИ активен!")
st.sidebar.info("Загрузите файлы и общайтесь с ИИ на человеческом языке. Он найдет зависимости, тренды и аномалии.")

uploaded_files = st.file_uploader(
    "Загрузите один или несколько любых файлов Excel/CSV для глубокого ИИ-анализа:", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

if uploaded_files:
    st.subheader("📋 Загруженные таблицы в памяти ИИ:")
    data_summary_for_ai = ""
    
    for file in uploaded_files:
        try:
            df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
            df.columns = df.columns.str.strip()
            st.markdown(f"📄 **{file.name}** (Строк: {df.shape[0]}, Колонок: {df.shape[1]})")
            sample_records = df.head(3).to_dict(orient='records')
            data_summary_for_ai += f"\nИмя файла: '{file.name}'\nВсе доступные столбцы: {list(df.columns)}\nПример реальных строк из таблицы:\n{json.dumps(sample_records, ensure_ascii=False)}\n---"
        except Exception as e:
            st.error(f"Не удалось прочитать файл {file.name}: {e}")

    st.markdown("---")
    st.subheader("💬 Диалог с ИИ-Аналитиком (Задавайте любые вопросы)")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Здравствуйте! Я изучил структуру ваших файлов. Задайте мне любой вопрос. Я могу найти скрытые зависимости, сопоставить данные по годам, выявить финансовые аномалии или составить готовый отчет для руководства."}
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_query := st.chat_input("Напишите ваш вопрос..."):
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state.messages.append({"role": "user", "content": user_query})

        with st.chat_message("assistant"):
            with st.spinner("ИИ анализирует таблицы и формирует экспертный ответ..."):
                prompt = f"Ты — Главный дата-аналитик корпорации. Изучи данные таблиц:\n{data_summary_for_ai}\n\nЗадача от пользователя: \"{user_query}\"\nВыдай подробный профессиональный разбор со списками, таблицами и жирным шрифтом на русском языке."
                
                try:
                    # Переключаемся на безотказный безлимитный шлюз DeepSeek-R1
                    API_URL = "https://huggingface.co"
                    headers = {"Content-Type": "application/json"}
                    payload = {
                        "inputs": prompt,
                        "parameters": {"max_new_tokens": 1500, "temperature": 0.3, "return_full_text": False}
                    }
                    
                    response = requests.post(API_URL, headers=headers, json=payload, timeout=25)
                    
                    if response.status_code == 200:
                        res_json = response.json()
                        if isinstance(res_json, list) and len(res_json) > 0 and "generated_text" in res_json:
                            ai_response = res_json["generated_text"].strip()
                        else:
                            ai_response = res_json.get("generated_text", str(res_json))
                            
                        # Очищаем от цепочки рассуждений (thinking process) DeepSeek
                        if "</think>" in ai_response: 
                            ai_response = ai_response.split("</think>")[-1].strip()
                        
                        st.markdown(ai_response)
                        st.session_state.messages.append({"role": "assistant", "content": ai_response})
                    else:
                        st.error(f"Сервер временно перегружен (Код {response.status_code}). Пожалуйста, нажмите кнопку отправки запроса (стрелочку) еще раз.")
                except Exception as chat_err:
                    st.error(f"Не удалось отправить запрос в ИИ: {chat_err}")
else:
    st.info("💡 Пожалуйста, загрузите один или несколько файлов Excel/CSV сверху, чтобы активировать аналитический мозг ИИ.")
