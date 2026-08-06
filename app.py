import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json

st.set_page_config(page_title="Универсальный ИИ-Аналитик", layout="wide")
st.title("🚀 Универсальный ИИ Агент: Адаптивный анализ любых данных")

# Боковая панель
st.sidebar.success("🟢 Адаптивный ИИ-движок активен!")
api_key = st.sidebar.text_input("Введите ваш SambaNova API Key", type="password")
st.sidebar.markdown("""
**Бесплатный ключ без лимитов за 30 секунд:**
1. Зайдите на [cloud.sambanova.ai](https://sambanova.ai)
2. Нажмите **Create API Key** и скопируйте его.
""")

# Компонент для загрузки ЛЮБЫХ файлов
uploaded_files = st.file_uploader(
    "Загрузите один или несколько любых файлов Excel/CSV (с любыми типами данных)", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

if uploaded_files:
    combined_frames = []
    
    # Сшиваем файлы (если их несколько), добавляя метку источника
    for file in uploaded_files:
        try:
            if file.name.endswith('.csv'):
                current_df = pd.read_csv(file)
            else:
                current_df = pd.read_excel(file)
            current_df.columns = current_df.columns.str.strip()
            period_name = file.name.split('.')[0]
            current_df['Источник (Файл)'] = period_name
            combined_frames.append(current_df)
        except Exception as e:
            st.error(f"Не удалось прочитать файл {file.name}: {e}")
        
    if combined_frames:
        try:
            main_df = pd.concat(combined_frames, ignore_index=True)
            st.success(f"📊 Данные успешно импортированы! Загружено файлов: {len(uploaded_files)}. Общее количество строк: {main_df.shape[0]}")
            
            with st.expander("📋 Посмотреть сырые данные загруженной таблицы"):
                st.dataframe(main_df.head(5))
                
            # Автоматическое разделение колонок по типам для защиты от ошибок
            all_cols = list(main_df.columns)
            numeric_cols = list(main_df.select_dtypes(include=['number']).columns)
            text_cols = [col for col in all_cols if col not in numeric_cols and col != 'Источник (Файл)']
            
            if not numeric_cols:
                numeric_cols = all_cols
            if not text_cols:
                text_cols = all_cols
                
            st.markdown("---")
            st.subheader("⚙️ Управление визуализацией и постановка бизнес-задачи")
            
            # Интерактивный конструктор
            c1, c2, c3 = st.columns(3)
            with c1:
                x_axis = st.selectbox("🗂️ Выберите категорию/аналитический разрез (Ось X):", text_cols)
            with c2:
                y_axis = st.selectbox("🔢 Выберите числовой показатель/метрику (Ось Y):", numeric_cols)
            with c3:
                chart_style = st.selectbox("📈 Выберите тип визуализации под вашу задачу:", [
                    "Столбчатая диаграмма (Bar Chart)",
                    "Линейный график тренда (Line Chart)", 
                    "Кольцевая диаграмма долей (Donut Chart)",
                    "Круговая диаграмма (Pie Chart)",
                    "Точечный график связей (Scatter Plot)"
                ])
                
            # Запуск локальной визуализации
            try:
                main_df[y_axis] = pd.to_numeric(main_df[y_axis], errors='coerce').fillna(0)
                
                if "Кольцевая" in chart_style or "Круговая" in chart_style:
                    df_grouped = main_df.groupby(x_axis)[y_axis].sum().reset_index()
                    fig = px.pie(df_grouped, names=x_axis, values=y_axis, title=f"Структура '{y_axis}' по '{x_axis}'", hole=0.4 if "Кольцевая" in chart_style else 0)
                elif "Точечный" in chart_style:
                    fig = px.scatter(main_df, x=x_axis, y=y_axis, color='Источник (Файл)', title=f"Связь показателей '{y_axis}' и '{x_axis}'")
                else:
                    if len(uploaded_files) > 1 and 'Источник (Файл)' in main_df.columns:
                        df_grouped = main_df.groupby([x_axis, 'Источник (Файл)'], as_index=False)[y_axis].sum()
                        if "Линейный" in chart_style:
                            fig = px.line(df_grouped, x='Источник (Файл)', y=y_axis, color=x_axis, markers=True, title=f"Динамика изменений '{y_axis}'")
                        else:
                            fig = px.bar(df_grouped, x='Источник (Файл)', y=y_axis, color=x_axis, barmode="group", title=f"Сравнение '{y_axis}' по файлам")
                    else:
                        df_grouped = main_df.groupby(x_axis)[y_axis].sum().reset_index()
                        if "Линейный" in chart_style:
                            fig = px.line(df_grouped, x=x_axis, y=y_axis, markers=True, title=f"Тренд '{y_axis}'")
                        else:
                            fig = px.bar(df_grouped, x=x_axis, y=y_axis, color=x_axis, title=f"Распределение '{y_axis}'")
                            
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Ошибка построения графика: {e}")

            # ГИБКАЯ ПОСТАНОВКА ЗАДАЧИ ДЛЯ ИИ
            st.markdown("---")
            st.subheader("🧠 Постановка персональной задачи для ИИ-Аналитика")
            
            custom_task = st.text_area(
                "Опишите, какую задачу должен решить ИИ по этим файлам:",
                value="Проведи комплексный аудит этих данных, найди скрытые закономерности, аномалии и сформируй 5 конкретных рекомендаций для бизнеса."
            )
            
            if st.button("🚀 Запустить ИИ-Анализ задачи"):
                if not api_key:
                    st.warning("Пожалуйста, укажите ваш Sambanova API Key в боковом меню.")
                else:
                    with st.spinner("ИИ исследует структуру и решает вашу бизнес-задачу..."):
                        meta_summary = f"Загружено файлов: {len(uploaded_files)}.\n"
                        meta_summary += f"Доступные текстовые колонки: {text_cols}\nДоступные числовые колонки: {numeric_cols}\n"
                        
                        try:
                            sample_data = main_df.head(5).to_dict(orient='records')
                            meta_summary += f"Пример реальных строк из таблицы:\n{json.dumps(sample_data, ensure_ascii=False)}"
                        except:
                            pass
                        
                        prompt = f"""
                        Ты — ведущий мировой ИИ-эксперт по обработке данных и бизнес-аналитике. 
                        Перед тобой массив данных со следующей структурой:
                        {meta_summary}
                        
                        Текущие выбранные пользователем настройки в интерфейсе:
                        Аналитический разрез: '{x_axis}'
                        Главный показатель: '{y_axis}'
                        
                        Конкретная задача от пользователя:
                        "{custom_task}"
                        
                        Выполни эту задачу качественно, опираясь на структуру предоставленных данных. 
                        Если файлов несколько, обязательно проанализируй их взаимосвязь. 
                        Ответь на русском языке. Оформи ответ с чёткой структурой (заголовки, списки, жирный шрифт), чтобы его можно было сразу вставить в отчет руководству.
                        """
                        
                        try:
                            url = "https://sambanova.ai"
                            headers = {
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            }
                            data = {
                                "model": "Meta-Llama-3.1-70B-Instructor",
                                "messages": [{"role": "user", "content": prompt}],
                                "temperature": 0.2
                            }
                            
                            response = requests.post(url, headers=headers, json=data)
                            result_json = response.json()
                            
                            if 'choices' in result_json and len(result_json['choices']) > 0:
                                st.markdown("### 💡 Глубокий аналитический отчет ИИ по вашей задаче:")
                                st.markdown(result_json['choices']['message']['content'])
                            else:
                                st.error("Ошибка обработки запроса сервером API. Попробуйте нажать кнопку еще раз.")
                                st.json(result_json)
                        except Exception as ai_err:
                            st.error(f"Не удалось выполнить ИИ-анализ: {ai_err}")
        except Exception as merge_err:
            st.error(f"Не удалось автоматически объединить файлы. Ошибка: {merge_err}")
else:
    st.info("Ожидание загрузки любых файлов Excel/CSV для начала работы...")
