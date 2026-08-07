import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json
import re

st.set_page_config(page_title="Универсальный ИИ-Аналитик", layout="wide")
st.title("🚀 Полноценный ИИ Агент: Бизнес-Аналитика без ограничений")

st.sidebar.success("🧠 Флагманский ИИ-движок Llama Pro активен!")
st.sidebar.info("Этот агент использует полноценный искусственный интеллект для глубокого анализа данных и точного построения графиков по вашим запросам.")

# Достаем ключ ИИ из безопасных настроек Streamlit Cloud
api_key = st.secrets.get("openrouter_key", "")

# Компонент для загрузки ЛЮБЫХ файлов одновременно
uploaded_files = st.file_uploader(
    "Загрузите один или несколько любых файлов Excel/CSV для ИИ-анализа", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

if uploaded_files:
    combined_frames = []
    
    # Сшиваем файлы
    for file in uploaded_files:
        try:
            if file.name.endswith('.csv'):
                current_df = pd.read_csv(file)
            else:
                current_df = pd.read_excel(file)
            current_df.columns = current_df.columns.str.strip()
            period_name = file.name.replace(".xlsx", "").replace(".xls", "").replace(".csv", "")
            current_df['Отчетный период'] = period_name
            combined_frames.append(current_df)
        except Exception as e:
            st.error(f"Не удалось прочитать файл {file.name}: {e}")
        
    if combined_frames:
        try:
            main_df = pd.concat(combined_frames, ignore_index=True)
            st.success(f"📊 База данных успешно сформирована! Загружено файлов: {len(uploaded_files)}. Всего строк: {main_df.shape}")
            
            with st.expander("📋 Посмотреть структуру данных (первые 5 строк)"):
                st.dataframe(main_df.head(5))
                
            all_cols = list(main_df.columns)
            numeric_cols = list(main_df.select_dtypes(include=['number']).columns)
            text_cols = [col for col in all_cols if col not in numeric_cols and col != 'Отчетный период']
            
            if not numeric_cols:
                numeric_cols = all_cols
            if not text_cols:
                text_cols = all_cols

            st.markdown("---")
            st.subheader("🧠 Постановка персональной бизнес-задачи для ИИ")
            
            user_task = st.text_area(
                "Опишите вашу задачу ИИ (например: 'построй столбчатую диаграмму по оси Х - год, по оси Y - значения Итого'):",
                value="построй столбчатую диаграмму по оси Х - год, по оси Y - значения Итого"
            )
            
            if st.button("🚀 Запустить ИИ-Анализ и построить графики"):
                if not api_key:
                    st.error("⚠️ Ключ ИИ не найден в Secrets! Пожалуйста, добавьте его в настройках Streamlit Cloud (ключ: openrouter_key).")
                else:
                    with st.spinner("ИИ исследует структуру таблиц и строит визуализацию..."):
                        
                        try:
                            sample_data = main_df.head(5).to_dict(orient='records')
                            data_context = f"Доступные колонки в таблице: {all_cols}\nЧисловые колонки: {numeric_cols}\nПример строк:\n{json.dumps(sample_data, ensure_ascii=False)}"
                        except:
                            data_context = f"Доступные колонки: {all_cols}"
                        
                        prompt = f"""
                        Ты — ведущий эксперт по бизнес-аналитике уровня Microsoft Copilot.
                        Перед тобой массив данных со следующей структурой:
                        {data_context}
                        
                        Пользователь поставил тебе задачу: "{user_task}"
                        
                        Тщательно изучи названия колонок. Выбери из списка доступных колонок ОДНУ точную колонку для оси X и ОДНУ для оси Y, которые идеально соответствуют запросу пользователя. Прими во внимание указания осей 'ось X' и 'ось Y', если пользователь их дал.
                        
                        Верни ответ СТРОГО в формате JSON со следующими ключами (пиши только чистый JSON без разметки markdown ```json, не пиши ничего кроме этого JSON):
                        {{
                            "explanation": "Твой подробный аналитический комментарий на русском языке по результатам выполнения этой задачи.",
                            "x_axis": "Точное имя колонки из списка для оси X графика (категория/дата)",
                            "y_axis": "Точное имя колонки из списка для оси Y графика (числовой показатель/метрика)",
                            "chart_type": "Тип визуализации: 'bar' (столбчатый), 'line' (линейный тренд) или 'pie' (доли)"
                        }}
                        """
                        
                        try:
                            # Переключаемся на супер-стабильный шлюз SambaNova
                            url = "https://sambanova.ai"
                            headers = {
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            }
                            data = {
                                "model": "Meta-Llama-3.1-70B-Instruct",
                                "messages": [{"role": "user", "content": prompt}],
                                "temperature": 0.1
                            }
                            
                            response = requests.post(url, headers=headers, json=data, timeout=20)
                            
                            if response.status_code == 200:
                                result_json = response.json()
                                raw_text = result_json['choices']['message']['content'].strip()
                                
                                if raw_text.startswith("```json"):
                                    raw_text = raw_text[7:]
                                if raw_text.endswith("```"):
                                    raw_text = raw_text[:-3]
                                raw_text = raw_text.strip()
                                
                                result = json.loads(raw_text)
                                
                                # Вывод полноценного отчета ИИ
                                st.subheader("💡 Результаты стратегического ИИ-анализа:")
                                st.markdown(result["explanation"])
                                
                                # Построение графика по решению ИИ
                                if result["chart_type"] and result["x_axis"] and result["y_axis"]:
                                    st.markdown("---")
                                    st.subheader("📈 Автоматически сгенерированный ИИ-график под задачу:")
                                    
                                    x_col = result["x_axis"].strip()
                                    y_col = result["y_axis"].strip()
                                    
                                    if x_col in main_df.columns and y_col in main_df.columns:
                                        df_chart = main_df.copy()
                                        df_chart[y_col] = pd.to_numeric(df_chart[y_col], errors='coerce').fillna(0)
                                        df_grouped = df_chart.groupby(x_col, as_index=False)[y_col].sum()
                                        
                                        try:
                                            df_grouped = df_grouped.sort_values(by=x_col)
                                        except:
                                            pass
                                            
                                        if result["chart_type"] == 'bar':
                                            fig = px.bar(df_grouped, x=x_col, y=y_col, color=x_col, title=f"Анализ распределения показателя {y_col} по {x_col}")
                                        elif result["chart_type"] == 'line':
                                            fig = px.line(df_grouped, x=x_col, y=y_col, markers=True, title=f"Динамика тренда {y_col} по {x_col}")
                                        else:
                                            fig = px.pie(df_grouped, names=x_col, values=y_col, title=f"Доли распределения {y_col}", hole=0.4)
                                            
                                        st.plotly_chart(fig, use_container_width=True)
                                    else:
                                        st.error(f"ИИ выбрал колонки {x_col} или {y_col}, но они не найдены в файле.")
                            else:
                                st.error("ИИ-сервер временно перегружен. Перезапустите запрос.")
                                
                        except Exception as ai_err:
                            st.error(f"Ошибка парсинга ответа ИИ: {ai_err}")
                            if 'raw_text' in locals():
                                st.text("Сырой ответ сервера:")
                                st.text(raw_text)
                            
        except Exception as merge_err:
            st.error(f"Не удалось объединить файлы: {merge_err}")
else:
    st.info("Ожидание загрузки любых файлов Excel/CSV для начала работы...")
