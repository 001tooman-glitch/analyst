import streamlit as st
import pandas as pd
import plotly.express as px

def show_abc_xyz_page():
    st.title("🧮 Модуль автоматического ABC/XYZ-анализа")
    
    if st.session_state.main_df.empty:
        st.info("ℹ️ Пожалуйста, сначала загрузите файлы на первой странице.")
        return
        
    df = st.session_state.main_df.copy()
    
    if 'ОЗМ' not in df.columns or 'Сумма' not in df.columns:
        st.error("❌ В данных отсутствуют обязательные столбцы 'ОЗМ' и 'Сумма' для проведения анализа.")
        return

    st.markdown("### 📊 Настройка параметров классификации")
    col1, col2 = st.columns(2)
    with col1:
        a_limit = st.slider("Граница группы A (по умолчанию 80% выручки):", 50, 90, 80)
    with col2:
        b_limit = st.slider("Граница группы B (по умолчанию следующие 15%):", 5, 25, 15)

    # Расчет ABC
    df_abc = df.groupby('ОЗМ', as_index=False)['Сумма'].sum()
    df_abc = df_abc.sort_values(by='Сумма', ascending=False).reset_index(drop=True)
    total_sum = df_abc['Сумма'].sum()
    
    if total_sum == 0:
        st.warning("⚠️ Общая сумма всех позиций равна нулю. Анализ невозможен.")
        return

    df_abc['Доля'] = df_abc['Сумма'] / total_sum
    df_abc['Кумулятивная доля'] = df_abc['Доля'].cumsum() * 100

    def classify_abc(row):
        if row['Кумулятивная доля'] <= a_limit: return 'A'
        elif row['Кумулятивная доля'] <= (a_limit + b_limit): return 'B'
        return 'C'

    df_abc['Класс ABC'] = df_abc.apply(classify_abc, axis=1)

    # Отображение результатов
    st.subheader("📋 Результаты распределения позиций по группам")
    abc_summary = df_abc.groupby('Класс ABC').agg(
        Количество_ОЗМ=('ОЗМ', 'count'),
        Общая_Сумма=('Сумма', 'sum')
    ).reset_index()
    
    st.dataframe(abc_summary, use_container_width=True)

    fig = px.pie(abc_summary, values='Общая_Сумма', names='Класс ABC', title='Доля стоимости по классам ABC', color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig, use_container_width=True)

