import streamlit as st
import pandas as pd
import plotly.express as px

def show_rfm_page():
    st.title("👥 Модуль RFM-сегментации номенклатуры")
    
    if st.session_state.main_df.empty:
        st.info("ℹ️ Пожалуйста, сначала загрузите файлы на первой странице.")
        return
        
    df = st.session_state.main_df.copy()
    
    if not all(col in df.columns for col in ['ОЗМ', 'Сумма', 'Источник (Файл)']):
        st.error("❌ Для RFM-анализа требуются столбцы 'ОЗМ', 'Сумма' и 'Источник (Файл)'.")
        return

    st.markdown("### 🔥 Матрица ценности номенклатурных позиций")
    
    # Имитируем расчет частоты (Frequency) по числу упоминаний в файлах периодов
    rfm_df = df.groupby('ОЗМ').agg(
        Frequency=('Источник (Файл)', 'count'),
        Monetary=('Сумма', 'sum')
    ).reset_index()

    # Разделяем на 3 тертиля (Score от 1 до 3)
    if len(rfm_df) >= 3:
        rfm_df['F_Score'] = pd.qcut(rfm_df['Frequency'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        rfm_df['M_Score'] = pd.qcut(rfm_df['Monetary'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
    else:
        rfm_df['F_Score'] = '1'
        rfm_df['M_Score'] = '1'

    rfm_df['RFM_Segment'] = rfm_df['F_Score'] + rfm_df['M_Score']

    st.subheader("📊 Распределение ОЗМ по RFM-сегментам")
    seg_counts = rfm_df.groupby('RFM_Segment').size().reset_index(name='Количество ОЗМ')
    
    fig = px.bar(seg_counts, x='RFM_Segment', y='Количество ОЗМ', text_auto=True, title="Плотность сегментов (Частота + Деньги)", color='RFM_Segment')
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(rfm_df.head(100), use_container_width=True)

