import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json

st.set_page_config(page_title="Мульти-ИИ Аналитик Динамики", layout="wide")
st.title("🤖 Сводный ИИ Агент: Анализ сквозной динамики")

# Боковая панель
st.sidebar.success("🚀 Сводный анализ и динамика активны!")
api_key = st.sidebar.text_input("Введите ваш SambaNova API Key", type="password")
st.sidebar.markdown("""
**Как получить бесплатный ключ без лимитов за 30 секунд:**
1. Зайдите на [cloud.sambanova.ai](https://sambanova.ai)
2. Нажмите **Create API Key** и скопируйте его.
""")

# Компонент для загрузки НЕСКОЛЬКИХ файлов одновременно
uploaded_files = st.file_uploader(
    "Загрузите файлы для анализа динамики (например: май 24, май 25, май 26)", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

if uploaded_files and len(uploaded_files) >= 1:
    st.subheader("📋 Загруженные и распознанные таблицы:")
    
    combined_frames = []
    
    # Цикл по всем загруженным файлам для автоматического сшивания
    for file in uploaded_files:
        if file.name.endswith('.csv'):
            current_df = pd.read_csv(file)
        else:
            current_df = pd.read_excel(file)
            
        # Очищаем заголовки колонок от скрытых пробелов
        current_df.columns = current_df.columns.str.strip()
        
        # Добавляем специальную служебную колонку с именем файла, чтобы ИИ понимал временную точку
        period_name = file.name.replace(".xlsx", "").replace(".xls", "").replace(".csv", "")
        current_df['Отчетный период (Файл)'] = period_name
        
        combined_frames.append(current_df)
        
    try:
        # Сшиваем все файлы в одну большую единую сводную таблицу
        main_df = pd.concat(combined_frames, ignore_index=True)
        st.success(f"🔥 Успешно создана сводная база данных! Объединено файлов: {len(uploaded_files)}. Всего строк для анализа: {main_df.shape[0]}")
        
        with st.expander("📊 Посмотреть превью объединенной сводной таблицы"):
            st.dataframe(main_df.head(10))
            
        st.markdown("---")
        st.subheader("📈 Автономный анализ сквозной динамики по всем периодам")
        
        all_columns = [col for col in main_df.columns if col != 'Отчетный период (Файл)']
        
        c1, c2, c3 = st.columns(3)
        with c1:
            group_by_col = st.selectbox("Выберите аналитическую категорию (например: Фонд, Статья, ОЗМ):", all_columns)
        with c2:
            value_col = st.selectbox("Выберите числовой показатель (например: Сумма, Стоимость, Объем):", all_columns)
        with c3:
            chart_style = st.selectbox("Выберите визуализацию:", ["Линейный график тренда (Line)", "Групповая столбчатая диаграмма (Bar)"])
            
        # Подготовка данных: переводим в числа и очищаем
        main_df[value_col] = pd.to_numeric(main_df[value_col], errors='coerce').fillna(0)
        
        # Строим сводную таблицу группировки: Категория + Период времени
        df_trend = main_df.groupby([group_by_col, 'Отчетный период (Файл)'], as_index=False)[value_col].sum()
        
        # Сортируем периоды, чтобы графики шли хронологически (май 24 -> май 25 -> май 26)
        df_trend = df_trend.sort_values(by='Отчетный период (Файл)')
        
        if "Линейный" in chart_style:
            fig = px.line(
                df_trend, 
                x='Отчетный период (Файл)', 
                y=value_col, 
                color=group_by_col,
                markers=True,
                title=f"Сквозной тренд изменения показателя '{value_col}' по категориям '{group_by_col}'"
            )
        else:
            fig = px.bar(
                df_trend, 
                x='Отчетный период (Файл)', 
                y=value_col, 
                color=group_by_col, 
                barmode="group",
                title=f"Сравнительный анализ показателя '{value_col}' по периодам"
            )
            
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as merge_err:
        st.error(f"Не удалось автоматически объединить файлы. Убедитесь, что структура колонок в файлах совпадает. Ошибка: {merge_err}")

    # ИИ АНАЛИЗ СВОДНОЙ ДИНАМИКИ
    st.markdown("---")
    st.subheader("🧠 Стратегический ИИ-анализ объединенной сводной таблицы")
    
    if st.button("🚀 Провести аудит динамики изменений и получить рекомендации ИИ"):
        if not api_key:
            st.warning("Пожалуйста, введите ваш Sambanova API Key в боковой панели слева для запуска ИИ.")
        else:
            with st.spinner("Флагманский ИИ проводит аудит сводных данных и ищет аномалии..."):
                
                # Агрегируем краткую сводную матрицу для передачи в ИИ, чтобы он видел реальные цифры трендов
                try:
                    summary_pivot = main_df.groupby([group_by_col, 'Отчетный период (Файл)'])[value_col].sum().unstack().fillna(0)
                    pivot_dict = summary_pivot.to_dict(orient='index')
                    raw_summary_data = json.dumps(pivot_dict, ensure_ascii=False, indent=2)
                except:
                    raw_summary_data = "Не удалось скомпилировать матрицу, передаются общие метаданные."
                
                prompt = f"""
                Ты — Директор по аналитике и стратегическому планированию. Перед тобой сводный массив данных, полученный путем объединения нескольких файлов за разные отчетные периоды.
                
                Выбранная аналитическая категория: '{group_by_col}'
                Выбранный финансовый/количественный показатель: '{value_col}'
                
                Реальные агрегированные показатели динамики изменений по периодам (в формате Категория -> Период -> Значение):
                {raw_summary_data}
                
                Твоя задача:
                1. Провести детальный аудит сквозной динамики. Четко укажи, в каких категориях произошел наибольший рост показателя от периода к периоду, а в каких — критическое падение.
                2. Выявить скрытые тренды, аномалии или резкие скачки в данных, которые требуют немедленного внимания менеджмента.
                3. Предложить конкретные дальнейшие действия и управленческие рекомендации на основе этой трехлетней/многопериодной динамики.
                4. Напиши профессиональное краткое резюме (Executive Summary) для руководства.
                
                Ответь на русском языке. Оформи ответ структурированно, бизнес-языком, с использованием жирного шрифта, таблиц или списков.
                """
                
                try:
                    url = "https://sambanova.ai"
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    data = {
                        "model": "Meta-Llama-3.1-405B-Instruct",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1
                    }
                    
                    response = requests.post(url, headers=headers, json=data)
                    result_json = response.json()
                    
                    if 'choices' in result_json and len(result_json['choices']) > 0:
                        ai_analysis = result_json['choices']['message']['content']
                        st.markdown("### 💡 Стратегический разбор от ИИ:")
                        st.markdown(ai_analysis)
                    else:
                        st.error("Ошибка API при получении данных.")
                        st.json(result_json)
                    
                except Exception as e:
                    st.error(f"Ошибка при вызове ИИ: {e}")
else:
    st.info("Пожалуйста, загрузите сразу несколько файлов (например: май 24, май 25, май 26) для построения сквозной динамики.")
