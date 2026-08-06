import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Автономный ИИ-Аналитик", layout="wide")
st.title("📊 Автономный Интерактивный Дашборд Аналитики")

st.sidebar.success("🟢 Локальный движок визуализации активен!")
st.sidebar.info("Этот режим работает полностью автономно на вашем сервере, не зависит от сторонних ИИ и никогда не выдает ошибок лимита.")

# Компонент для загрузки файлов Excel или CSV
uploaded_file = st.file_uploader("Загрузите файл Excel или CSV для анализа", type=["csv", "xlsx"])

if uploaded_file is not None:
    # Чтение загруженных данных
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
        
    st.success("Файл успешно загружен и прочитан!")
    
    # Очищаем заголовки колонок от скрытых пробелов
    df.columns = df.columns.str.strip()
    columns_list = list(df.columns)
    
    # Разворачивающееся превью таблицы
    with st.expander("📋 Посмотреть структуру данных (первые 5 строк)"):
        st.dataframe(df.head())
    
    st.markdown("---")
    st.subheader("⚙️ Настройка интерактивной визуализации")
    
    # Создаем удобные селекторы для пользователя в один клик
    col1, col2, col3 = st.columns(3)
    
    with col1:
        x_axis = st.selectbox("🗂️ Выберите категорию (Ось X / Сегмент):", columns_list)
    with col2:
        y_axis = st.selectbox("🔢 Выберите показатель (Ось Y / Метрика):", columns_list)
    with col3:
        chart_type = st.selectbox("📈 Выберите тип графика:", ["Кольцевая диаграмма (Pie/Donut)", "Столбчатая диаграмма (Bar)", "Линейный график (Line)", "Точечный график (Scatter)"])
        
    if x_axis and y_axis:
        st.markdown("---")
        st.subheader("📈 Результат анализа и визуализации:")
        
        with st.spinner("Локальный интерпретатор обрабатывает таблицу..."):
            try:
                # Создаем копию для безопасной обработки типов данных
                df_clean = df.copy()
                # Принудительно превращаем колонку показателей в числа, а текст заменяем на 0
                df_clean[y_axis] = pd.to_numeric(df_clean[y_axis], errors='coerce').fillna(0)
                
                # Группируем и агрегируем данные
                df_grouped = df_clean.groupby(x_axis)[y_axis].sum().reset_index()
                
                # Строим выбранный тип интерактивного графика Plotly
                if "Кольцевая" in chart_type:
                    fig = px.pie(df_grouped, names=x_axis, values=y_axis, title=f"Доля {y_axis} по категориям {x_axis}", hole=0.4)
                elif "Столбчатая" in chart_type:
                    fig = px.bar(df_grouped, x=x_axis, y=y_axis, color=x_axis, title=f"Распределение {y_axis} по {x_axis}")
                elif "Линейный" in chart_type:
                    fig = px.line(df_grouped, x=x_axis, y=y_axis, title=f"Динамика {y_axis} по {x_axis}")
                else:
                    fig = px.scatter(df_clean, x=x_axis, y=y_axis, title=f"Взаимосвязь {y_axis} и {x_axis}", color=x_axis)
                
                # Отображаем полностью кликабельный график на экране
                st.plotly_chart(fig, use_container_width=True)
                
                # Автоматический генератор экспресс-вывода на основе очищенных данных
                st.subheader("💡 Краткий аналитический вывод:")
                total_sum = df_grouped[y_axis].sum()
                
                if total_sum > 0:
                    max_val = df_grouped[y_axis].max()
                    leader_row = df_grouped[df_grouped[y_axis] == max_val]
                    leader = leader_row[x_axis].values[0] if not leader_row.empty else "Не определен"
                    share = (max_val / total_sum) * 100
                    
                    st.info(f"Анализ завершен успешно. Максимальное значение показателя **{y_axis}** зафиксировано в категории **{leader}** и составляет **{max_val:,.2f}**. На долю лидера приходится **{share:.1f}%** от общего объема по всей таблице (общая сумма: **{total_sum:,.2f}**).")
                else:
                    st.warning("Выбранная колонка показателей содержит только текст или нули. Пожалуйста, выберите другую числовую колонку во втором выпадающем списке.")
                
            except Exception as e:
                st.error(f"Не удалось построить вывод для выбранных колонок. Ошибка: {e}")
else:
    st.info("Ожидание загрузки файла таблицы...")
