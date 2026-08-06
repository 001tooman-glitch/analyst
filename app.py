import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json

st.set_page_config(page_title="Мульти-ИИ Аналитик", layout="wide")
st.title("🤖 Мульти-файловый ИИ Агент: Поиск зависимостей")

# Боковая панель
st.sidebar.success("🚀 Мультизагрузка и Анализ связей активны!")
api_key = st.sidebar.text_input("Введите ваш Sambaanova API Key (Опционально для ИИ)", type="password")
st.sidebar.markdown("""
**Как получить бесплатный ключ без лимитов за 30 секунд:**
1. Зайдите на [cloud.sambanova.ai](https://sambanova.ai)
2. Нажмите **Create API Key** и скопируйте его.
""")

# Компонент для загрузки НЕСКОЛЬКИХ файлов одновременно
uploaded_files = st.file_uploader(
    "Загрузите один или несколько файлов Excel/CSV для поиска зависимостей", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

dataframes = {}

if uploaded_files:
    st.subheader("📋 Загруженные таблицы:")
    cols = st.columns(len(uploaded_files))
    
    for idx, file in enumerate(uploaded_files):
        # Читаем каждый файл
        if file.name.endswith('.csv'):
            current_df = pd.read_csv(file)
        else:
            current_df = pd.read_excel(file)
            
        # Очищаем колонки от скрытых пробелов
        current_df.columns = current_df.columns.str.strip()
        dataframes[file.name] = current_df
        
        # Показываем превью каждого файла в колонках
        with cols[idx]:
            st.markdown(f"📄 **{file.name}**")
            st.caption(f"Строк: {current_df.shape[0]}, Колонок: {current_df.shape[1]}")
            with st.expander("Посмотреть структуру"):
                st.dataframe(current_df.head(3))

    st.markdown("---")
    st.subheader("⚙️ Автономный экспресс-анализ (Без ИИ)")
    
    # Собираем все колонки из всех файлов для ручного построения графиков
    all_files = list(dataframes.keys())
    
    c1, c2, c3 = st.columns(3)
    with c1:
        selected_file = st.selectbox("Выберите файл для графика:", all_files)
    
    current_columns = list(dataframes[selected_file].columns)
    
    with c2:
        x_axis = st.selectbox("Выберите категорию (Ось X):", current_columns, key="x_ax")
    with c3:
        y_axis = st.selectbox("Выберите показатель (Ось Y):", current_columns, key="y_ax")
        
    # Строим график по выбранному файлу с безопасной очисткой дубликатов
    try:
        df_to_plot = dataframes[selected_file].copy()
        df_to_plot[y_axis] = pd.to_numeric(df_to_plot[y_axis], errors='coerce').fillna(0)
        
        # Безопасная группировка без дублирования колонок
        if x_axis == y_axis:
            df_grouped = df_to_plot[[x_axis]].value_counts().reset_index(name="Количество")
            fig = px.bar(df_grouped, x=x_axis, y="Количество", color=x_axis, title=f"Распределение по {x_axis}")
        else:
            df_grouped = df_to_plot.groupby(x_axis, as_index=False)[y_axis].sum()
            fig = px.bar(df_grouped, x=x_axis, y=y_axis, color=x_axis, title=f"Анализ показателя {y_axis} по {x_axis} ({selected_file})")
            
        st.plotly_chart(fig, use_container_width=True)
    except Exception as chart_err:
        st.error(f"Не удалось построить экспресс-график: {chart_err}")

    # ИИ АНАЛИЗ ВЗАИМОСВЯЗЕЙ
    st.markdown("---")
    st.subheader("🧠 Стратегический ИИ-анализ взаимосвязей между файлами")
    
    if st.button("🚀 Найти скрытые зависимости и составить план анализа"):
        if not api_key:
            st.warning("Пожалуйста, убедитесь, что ваш Sambanova API Key вставлен в боковой панели.")
        else:
            with st.spinner("ИИ сопоставляет структуры таблиц и ищет пересечения..."):
                
                # Формируем детальное описание всех файлов для ИИ
                meta_summary = ""
                for name, df_item in dataframes.items():
                    meta_summary += f"\nФайл: '{name}'\nКолонки: {list(df_item.columns)}\nТипы данных: {df_item.dtypes.to_dict()}\nПревью (первые 2 строки):\n{df_item.head(2).to_dict(orient='records')}\n"
                
                prompt = f"""
                Ты — главный дата-аналитик корпорации. Перед тобой структура нескольких загруженных бизнес-файлов:
                {meta_summary}
                
                Твоя задача:
                1. Тщательно изучить названия колонок и превью данных во ВСЕХ файлах. Найти общие ключи (например, ID, названия городов, фондов, даты, имена сотрудников), по которым эти таблицы можно объединить (JOIN).
                2. Описать, какие критические ЗАВИСИМОСТИ и корреляции могут скрываться между данными этих файлов (например: 'В файле 1 мы видим фонды, а в файле 2 — расходы по месяцам, связав их, мы увидим...').
                3. Предложить четкий пошаговый план дальнейших действий по анализу этих данных.
                4. Порекомендовать, какие типы продвинутых дашбордов или графиков нужно построить на основе объединенного датасета.
                
                Ответь на русском языке. Оформи ответ профессионально, с красивыми заголовками, списками и жирным шрифтом.
                """
                
                try:
                    # Вызов ультра-быстрого и безлимитного API Llama 3 через Sambanova
                    url = "https://sambanova.ai"
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    data = {
                        "model": "Llama-3.1-8B-Instructor",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1
                    }
                    
                    response = requests.post(url, headers=headers, json=data)
                    result_json = response.json()
                    
                    ai_analysis = result_json['choices'][0]['message']['content']
                    
                    st.markdown("### 💡 Результаты исследования ИИ:")
                    st.markdown(ai_analysis)
                    
                except Exception as e:
                    st.error(f"Ошибка при вызове ИИ: {e}")
                    if 'result_json' in locals():
                        st.json(result_json)
else:
    st.info("Пожалуйста, загрузите несколько файлов для начала поиска зависимостей.")
