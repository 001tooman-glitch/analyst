import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json

st.set_page_config(page_title="ИИ Агент-Аналитик (DeepSeek)", layout="wide")
st.title("🤖 Полноценный ИИ Агент по аналитике данных")

st.sidebar.success("🚀 Агент переключен на безлимитную модель DeepSeek-R1!")
st.sidebar.info("Этот агент автоматически читает структуру вашей таблицы и строит интерактивные графики без ограничений и лимитов.")

# Компонент для загрузки файлов Excel или CSV
uploaded_file = st.file_uploader("Загрузите файл Excel или CSV для анализа", type=["csv", "xlsx"])

if uploaded_file is not None:
    # Чтение загруженных данных
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
        
    st.success("Файл успешно загружен и прочитан!")
    
    # Разворачивающееся превью таблицы
    with st.expander("📋 Посмотреть структуру данных (первые 5 строк)"):
        st.dataframe(df.head())
    
    # Поле текстового запроса для пользователя
    user_query = st.text_input("Задайте вопрос аналитику (например: 'Построй график прибыли по странам' или 'Построй кольцевую диаграмму по фондам'):")
    
    if user_query:
        with st.spinner("DeepSeek анализирует структуру таблицы и подбирает параметры..."):
            # Формируем схему таблицы для ИИ, чтобы он понимал названия колонок
            data_schema = f"Колонки в таблице: {list(df.columns)}. Типы данных: {df.dtypes.to_dict()}"
            
            prompt = f"""
            Ты — опытный дата-аналитик. У тебя есть DataFrame с именем 'df'.
            Его структура: {data_schema}
            Пользователь просит: "{user_query}"
            
            Твоя задача — написать логику для построения интерактивного графика Plotly Express (px) или сделать расчет.
            Верни ответ СТРОГО в формате JSON со следующими ключами:
            1. "explanation": твой подробный текстовый комментарий, аналитический вывод и ответ на вопрос пользователя на русском языке.
            2. "x_axis": имя колонки из списка для оси X (если нужен график, иначе null).
            3. "y_axis": имя колонки из списка для оси Y (если нужен график, иначе null).
            4. "chart_type": тип графика ('bar', 'line', 'scatter', 'pie' или null, если график не нужен).
            
            Пиши только чистый JSON, без разметки markdown (без ```json).
            """
            
            try:
                # Используем бесплатный публичный API Hugging Face для модели DeepSeek-R1
                API_URL = "https://huggingface.co"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "inputs": prompt,
                    "parameters": {"max_new_tokens": 1000, "return_full_text": False}
                }
                
                response = requests.post(API_URL, headers=headers, json=payload)
                response_json = response.json()
                
                # Достаем текст ответа
                if isinstance(response_json, list) and "generated_text" in response_json[0]:
                    raw_text = response_json[0]["generated_text"]
                else:
                    raw_text = response_json.get("generated_text", str(response_json))
                
                # Очищаем ответ от цепочки рассуждений (thinking process), если она есть
                if "</think>" in raw_text:
                    raw_text = raw_text.split("</think>")[-1]
                
                # Очищаем от markdown-оберток
                clean_text = raw_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
                
                # Парсим JSON-ответ от ИИ
                result = json.loads(clean_text)
                
                # 1. Выводим развернутый текстовый анализ ИИ
                st.subheader("💡 Аналитический вывод ИИ:")
                st.write(result["explanation"])
                
                # 2. Если ИИ определил, что пользователю нужен график — строим его интерактивно через Plotly
                if result["chart_type"] and result["x_axis"] and result["y_axis"]:
                    st.subheader("📈 Сгенерированный график:")
                    
                    x_col = result["x_axis"]
                    y_col = result["y_axis"]
                    
                    # Очищаем возможные скрытые пробелы в названиях колонок
                    df.columns = df.columns.str.strip()
                    x_col = x_col.strip()
                    y_col = y_col.strip()
                    
                    # Группируем данные для более красивого отображения (если это возможно)
                    try:
                        df_grouped = df.groupby(x_col)[y_col].sum().reset_index()
                    except:
                        df_grouped = df
                    
                    # Выбираем тип графика на основе решения ИИ
                    if result["chart_type"] == 'bar':
                        fig = px.bar(df_grouped, x=x_col, y=y_col, color=x_col, title=f"Распределение {y_col} по {x_col}")
                    elif result["chart_type"] == 'line':
                        fig = px.line(df_grouped, x=x_col, y=y_col, title=f"Тренд {y_col} по {x_col}")
                    elif result["chart_type"] == 'pie':
                        fig = px.pie(df_grouped, names=x_col, values=y_col, title=f"Доля {y_col} по {x_col}", hole=0.4) # hole=0.4 делает диаграмму кольцевой
                    else:
                        fig = px.scatter(df, x=x_col, y=y_col, title=f"Взаимосвязь {y_col} и {x_col}")
                        
                    # Отображаем интерактивный график на веб-странице
                    st.plotly_chart(fig, use_container_width=True)
                    
            except Exception as e:
                st.error(f"Произошла ошибка при обработке ИИ: {e}")
                st.text("Ответ от модели:")
                st.text(raw_text if 'raw_text' in locals() else str(response_json))
else:
    st.info("Ожидание загрузки файла таблицы...")
