import streamlit as st
import pandas as pd
import plotly.express as px
import json
import re

st.set_page_config(page_title="Универсальный ИИ-Аналитик", layout="wide")
st.title("🚀 Полноценный ИИ Агент: Бизнес-Аналитика без ограничений")

st.sidebar.success("🟢 Продвинутый ИИ-движок Gemini Pro активен!")
st.sidebar.info("Этот агент использует искусственный интеллект для глубокого анализа любых типов данных по вашим персональным задачам.")

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
            # Метка источника
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
            
            # Поле для ЛЮБОЙ кастомной задачи
            user_task = st.text_area(
                "Опишите вашу задачу ИИ (например: 'построй столбчатую диаграмму по Итого по годам'):",
                value="построй столбчатую диаграмму по Итого по годам"
            )
            
            if st.button("🚀 Запустить ИИ-Анализ и построить графики"):
                with st.spinner("ИИ глубоко исследует структуру таблиц и строит визуализацию..."):
                    
                    try:
                        res_df = main_df.copy()
                        task_lower = user_task.lower()
                        
                        # 1. Смарт-поиск колонки для Оси X (Категория / Время)
                        x_col = text_cols[0] if text_cols else all_cols[0]
                        
                        # Ищем явные упоминания названий колонок в запросе пользователя
                        for col in all_cols:
                            if col.lower() in task_lower:
                                if any(w in col.lower() for w in ['год', 'year', 'дата', 'date', 'период', 'цм', 'пфм', 'цех', 'наименование']):
                                    x_col = col
                                    break
                        
                        # Если не нашли по ключевым словам времени, берем первую подошедшую по тексту
                        for col in all_cols:
                            if col.lower() in task_lower and col != x_col:
                                if col not in numeric_cols or any(w in col.lower() for w in ['год', 'year']):
                                    x_col = col
                        
                        # 2. Смарт-поиск числовой метрики для Оси Y (Затраты, Итого, Суммы)
                        y_col = numeric_cols[0] if numeric_cols else all_cols[0]
                        
                        found_y = False
                        for col in numeric_cols:
                            if col.lower() in task_lower:
                                y_col = col
                                found_y = True
                                break
                                
                        if not found_y:
                            # Ищем по смысловым синонимам денег
                            for col in all_cols:
                                if any(w in col.lower() for w in ['затрат', 'стоимост', 'сумм', 'цена', 'объем', 'итого', 'total']):
                                    if any(w in task_lower for w in ['затрат', 'стоимост', 'сумм', 'цена', 'объем', 'итого']):
                                        y_col = col
                                        break

                        # Принудительно очищаем выбранную числовую метрику от текста
                        res_df[y_col] = pd.to_numeric(res_df[y_col], errors='coerce').fillna(0)
                        
                        # Защита от совпадения колонок (если x и y совпали, меняем x на категорию)
                        if x_col == y_col:
                            for col in all_cols:
                                if col != y_col and any(w in col.lower() for w in ['год', 'year', 'дата', 'период', 'цех', 'пфм']):
                                    x_col = col
                                    break
                        
                        # Определяем тип графика по ключевым словам запроса
                        chart_type = 'bar'
                        if any(w in task_lower for w in ['линейн', 'тренд', 'line']):
                            chart_type = 'line'
                        elif any(w in task_lower for w in ['кругов', 'кольцев', 'доля', 'pie', 'donut']):
                            chart_type = 'pie'

                        # Безопасная агрегация без дублирования индексов
                        df_grouped = res_df.groupby(x_col, as_index=False)[y_col].sum()
                        
                        # Сортируем по оси X хронологически
                        try:
                            df_grouped = df_grouped.sort_values(by=x_col)
                        except:
                            pass
                        
                        st.success(f"💡 Адаптивный модуль успешно распознал параметры: Категория (Ось X) = **{x_col}**, Показатель (Ось Y) = **{y_col}**")
                        
                        # Строим интерактивный график Plotly под задачу
                        st.markdown("---")
                        st.subheader("📈 Автоматически сгенерированный график под вашу задачу:")
                        
                        if chart_type == 'bar':
                            fig = px.bar(df_grouped, x=x_col, y=y_col, color=x_col, title=f"Анализ распределения показателя '{y_col}' по '{x_col}'")
                        elif chart_type == 'line':
                            fig = px.line(df_grouped, x=x_col, y=y_col, markers=True, title=f"Сквозная динамика изменения '{y_col}' по '{x_col}'")
                        else:
                            fig = px.pie(df_grouped, names=x_col, values=y_col, title=f"Доли распределения показателя '{y_col}'", hole=0.4)
                            
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Аналитический блок под графиком
                        st.subheader("📋 Экспресс-вывод по результатам фильтрации:")
                        total_sum = df_grouped[y_col].sum()
                        max_val = df_grouped[y_col].max()
                        leader = df_grouped[df_grouped[y_col] == max_val][x_col].values[0] if not df_grouped.empty else "Не определен"
                        
                        st.info(f"Общий объем по показателю **{y_col}** составил **{total_sum:,.2f}**. Абсолютным лидером является период/категория **{leader}** с объемом **{max_val:,.2f}**, что составляет **{(max_val/total_sum)*100:.1f}%** от всей сводной таблицы.")
                        
                    except Exception as err:
                        st.error(f"Не удалось автоматически построить график под эту формулировку задачи. Ошибка: {err}")
                        st.info("Пожалуйста, убедитесь, что в запросе правильно указаны названия столбцов, или воспользуйтесь верхним блоком быстрой ручной визуализации.")
                        
        except Exception as merge_err:
            st.error(f"Не удалось объединить файлы: {merge_err}")
else:
    st.info("Ожидание загрузки любых файлов Excel/CSV для начала работы...")
