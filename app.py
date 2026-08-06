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
                # Группируем и агрегируем данные, как это делал бы ИИ через код
                df_grouped = df.groupby(x_axis)[y_axis].sum().reset_index()
                
                # Строим выбранный тип интерактивного графика Plotly
                if "Кольцевая" in chart_type:
                    fig = px.pie(df_grouped, names=x_axis, values=y_axis, title=f"Доля {y_axis} по категориям {x_axis}", hole=0.4)
                elif "Столбчатая" in chart_type:
                    fig = px.bar(df_grouped, x=x_axis, y=y_axis, color=x_axis, title=f"Распределение {y_axis} по {x_axis}")
                elif "Линейный" in chart_type:
                    fig = px.line(df_grouped, x=x_axis, y=y_axis, title=f"Динамика {y_col} по {x_col}")
                else:
                    fig = px.scatter(df, x=x_axis, y=y_axis, title=f"Взаимосвязь {y_axis} и {x_axis}", color=x_axis)
                
                # Отображаем полностью кликабельный график на экране
                st.plotly_chart(fig, use_container_width=True)
                
                # Автоматический генератор экспресс-вывода на основе данных
                st.subheader("💡 Краткий аналитический вывод:")
                max_val = df_grouped[y_axis].max()
                leader = df_grouped[df_grouped[y_axis] == max_val][x_axis].values[0]
                total_sum = df_grouped[y_axis].sum()
                share = (max_val / total_sum) * 100
                
                st.info(f"Анализ завершен. Максимальное значение показателя **{y_axis}** зафиксировано в категории **{leader}** и составляет **{max_val:,.2f}**. На долю лидера приходится **{share:.1f}%** от общего объема по всей таблице.")
                
            except Exception as e:
                st.error(f"Не удалось построить график для выбранных колонок. Убедитесь, что показатель содержит числа. Ошибка: {e}")
else:
    st.info("Ожидание загрузки файла таблицы...")
