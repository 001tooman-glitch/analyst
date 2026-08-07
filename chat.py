import streamlit as st
import pandas as pd
import requests
import json

st.set_page_config(page_title="ИИ Чат-Аналитик", layout="wide")
st.title("🧠 Персональный ИИ-Аналитик Данных & Стратег")

st.sidebar.success("🚀 Безлимитный текстовый движок ИИ активен!")
st.sidebar.info("Загрузите файлы и общайтесь с ИИ на человеческом языке. Он найдет зависимости, тренды и аномалии.")

# Компонент для загрузки файлов в ИИ-чат
uploaded_files = st.file_uploader(
    "Загрузите один или несколько любых файлов Excel/CSV для глубокого ИИ-анализа:", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

if uploaded_files:
    st.subheader("📋 Загруженные таблицы в памяти ИИ:")
    data_summary_for_ai = ""
    
    # Читаем файлы и готовим краткую выжимку (метаданные) для модели
    for file in uploaded_files:
        try:
            df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
            df.columns = df.columns.str.strip()
            
            st.markdown(f"📄 **{file.name}** (Строк: {df.shape[0]}, Колонок: {df.shape[1]})")
            
            # Собираем метаструктуру
            sample_records = df.head(3).to_dict(orient='records')
            data_summary_for_ai += f"\nИмя файла: '{file.name}'\nВсе доступные столбцы: {list(df.columns)}\nТипы данных: {df.dtypes.to_dict()}\nПример реальных строк из таблицы:\n{json.dumps(sample_records, ensure_ascii=False)}\n---"
        except Exception as e:
            st.error(f"Не удалось прочитать файл {file.name}: {e}")

    st.markdown("---")
    st.subheader("💬 Диалог с ИИ-Аналитиком (Задавайте любые вопросы)")
    
    # Инициализируем историю сообщений чата, как в ChatGPT
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Здравствуйте! Я изучил структуру ваших файлов. Задайте мне любой вопрос. Я могу найти скрытые зависимости, сопоставить данные по годам, выявить финансовые аномалии или составить готовый отчет для руководства."}
        ]

    # Отображаем историю чата на экране с красивыми иконками
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Поле ввода вопроса пользователя
    if user_query := st.chat_input("Напишите ваш вопрос (например: 'Какие критические изменения произошли между 24 и 26 годами?'):"):
        # Показываем сообщение пользователя на экране
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state.messages.append({"role": "user", "content": user_query})

        # Отправляем запрос к ИИ
        with st.chat_message("assistant"):
            with st.spinner("ИИ анализирует таблицы и формирует экспертный ответ..."):
                
                # Составляем расширенный контекст
                prompt = f"""
                Ты — выдающийся мировой директор по аналитике данных, финансовый аудитор и бизнес-стратег уровня Microsoft Copilot.
                Перед тобой подробная структура и срезы данных из загруженных пользователем бизнес-таблиц:
                {data_summary_for_ai}
                
                Текущий вопрос/задача от пользователя: "{user_query}"
                
                Проведи глубокий логический анализ. Ответь развернуто, аргументированно, бизнес-языком. 
                Если загружено несколько файлов за разные года/периоды, обязательно сопоставь их, найди сквозные связи, тренды изменений, укажи на резкие скачки цифр или аномалии. 
                Сформируй конкретные выводы и пошаговые управленческие рекомендации.
                
                Ответь строго на русском языке. Оформи ответ профессионально и красиво: используй понятные заголовки, списки, таблицы и жирный шрифт.
                """
                
                try:
                    # Используем сверхстабильный публичный безлимитный API-сервер Hugging Face
                    API_URL = "https://huggingface.co"
                    headers = {"Content-Type": "application/json"}
                    payload = {
                        "inputs": prompt,
                        "parameters": {"max_new_tokens": 1500, "temperature": 0.3, "return_full_text": False}
                    }
                    
                    response = requests.post(API_URL, headers=headers, json=payload, timeout=25)
                    
                    if response.status_code == 200:
                        res_json = response.json()
                        if isinstance(res_json, list) and len(res_json) > 0 and "generated_text" in res_json[0]:
                            ai_response = res_json[0]["generated_text"].strip()
                        else:
                            ai_response = res_json.get("generated_text", str(res_json))
                            
                        # Очищаем ответ от случайных markdown-оберток prompts
                        if "</think>" in ai_response: ai_response = ai_response.split("</think>")[-1].strip()
                        
                        st.markdown(ai_response)
                        st.session_state.messages.append({"role": "assistant", "content": ai_response})
                    else:
                        st.error(f"Сервер ИИ временно перегружен (Код {response.status_code}). Пожалуйста, отправьте сообщение еще раз через 5 секунд.")
                except Exception as chat_err:
                    st.error(f"Не удалось отправить запрос в ИИ: {chat_err}")
else:
    st.info("💡 Пожалуйста, загрузите один или несколько файлов Excel/CSV сверху, чтобы активировать аналитический мозг ИИ.")

