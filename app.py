import streamlit as st
import pandas as pd
import io
import re
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# МОДУЛЬ 1: УНИВЕРСАЛЬНЫЙ No-Code КОНСТРУКТОР МАТРИЦ ABC/XYZ
def internal_show_abc_xyz_page(filtered_df):
    st.title("🧮 Уникальный No-Code Конструктор матриц ABC/XYZ")
    if filtered_df.empty:
        st.info("ℹ️ Пожалуйста, загрузите файлы и проверьте фильтры. Текущая выборка пуста.")
        return
    df = filtered_df.copy()
    available_cols = list(df.columns)
    
    st.markdown("### 🎯 Настройка параметров анализа")
    col_sel1, col_sel2, col_sel3 = st.columns(3)
    with col_sel1:
        abc_target = st.selectbox("1. Объект анализа (Что смотрим):", [c for c in available_cols if c not in ['Сумма', 'Количество']], key="abc_t_target")
    with col_sel2:
        abc_value = st.selectbox("2. Критерий масштаба (ABC):", [c for c in ['Сумма', 'Количество'] if c in available_cols] + available_cols, key="abc_v_value")
    with col_sel3:
        xyz_period = st.selectbox("3. Периоды/Шкала времени (XYZ):", [c for c in available_cols if c != abc_target], key="xyz_p_period")
    with st.expander("📖 Аналитический гид: Что мы увидим при этих настройках?"):
        st.markdown(f"""
        * **Группа А (Масштаб)**: Выделит ТОП-позиции по полю `{abc_target}`, на которые уходит до 80% от общего объема по полю `{abc_value}`.
        * **Группа X (Стабильность)**: Подсветит те объекты `{abc_target}`, которые закупаются максимально равномерно от одного периода `{xyz_period}` к другому.
        * **Группа Z (Хаос)**: Выявит позиции `{abc_target}`, закупки которых по шкале `{xyz_period}` носят разовый, спонтанный или аварийный характер.
        """)

    st.markdown("### ⚙️ Границы классификации долей и стабильности")
    col_abc1, col_abc2 = st.columns(2)
    with col_abc1:
        a_limit = st.slider("Граница группы A (% от общего объема):", 50, 90, 80, key="abc_sl_1")
        b_limit = st.slider("Граница группы B (следующие % объема):", 5, 25, 15, key="abc_sl_2")
    with col_abc2:
        x_limit = st.slider("Граница группы X (Коэфф. вариации KV ≤ %):", 5, 20, 10, key="xyz_sl_1")
        y_limit = st.slider("Граница группы Y (Коэфф. вариации KV ≤ %):", 15, 50, 25, key="xyz_sl_2")
    try:
        df[abc_value] = pd.to_numeric(df[abc_value], errors='coerce').fillna(0.0)
        df[abc_target] = df[abc_target].fillna("Не указано").astype(str)
        df[xyz_period] = df[xyz_period].fillna("Не указано").astype(str)
        
        df = df[(df[abc_target].str.strip() != "") & (df[xyz_period].str.strip() != "")]

        df_abc = df.groupby(abc_target, as_index=False)[abc_value].sum()
        df_abc = df_abc.sort_values(by=abc_value, ascending=False).reset_index(drop=True)
        total_sum = df_abc[abc_value].sum()
        
        if total_sum == 0:
            st.warning(f"⚠️ Общая сумма по полю '{abc_value}' равна нулю. Анализ невозможен.")
            return
            
        df_abc['Доля'] = df_abc[abc_value] / total_sum
        df_abc['Кумулятивная доля'] = df_abc['Доля'].cumsum() * 100
        df_abc['Class_ABC'] = df_abc['Кумулятивная доля'].map(lambda x: 'A' if x <= a_limit else ('B' if x <= (a_limit + b_limit) else 'C'))

        period_matrix = df.groupby([abc_target, xyz_period])[abc_value].sum().unstack(fill_value=0.0)
        xyz_results = []
        for obj_name, rows in period_matrix.iterrows():
            mean_val = rows.mean()
            std_val = rows.std(ddof=1) if len(rows) > 1 else 0.0
            active_periods_count = np.count_nonzero(rows)
            
            if mean_val > 0 and active_periods_count > 1:
                kv = (std_val / mean_val) * 100
                класс_xyz = 'X' if kv <= x_limit else ('Y' if kv <= y_limit else 'Z')
            else:
                kv, класс_xyz = 999.0, 'Z'
            xyz_results.append({abc_target: obj_name, 'KV': kv, 'Класс XYZ': класс_xyz})
            
        df_xyz = pd.DataFrame(xyz_results)
        df_matrix = pd.merge(df_abc[[abc_target, abc_value, 'Class_ABC']], df_xyz, on=abc_target)
        df_matrix['Матрица ABC/XYZ'] = df_matrix['Class_ABC'] + df_matrix['Класс XYZ']

        st.markdown("---")
        st.subheader("📊 Итоговая 9-польная матрица управления закупками")
        pivot_matrix = df_matrix.pivot_table(index='Class_ABC', columns='Класс XYZ', values=abc_target, aggfunc='count', fill_value=0)
        for letter in ['A', 'B', 'C']:
            if letter not in pivot_matrix.index: pivot_matrix.loc[letter] = 0
        for letter in ['X', 'Y', 'Z']:
            if letter not in pivot_matrix.columns: pivot_matrix[letter] = 0
        pivot_matrix = pivot_matrix.loc[['A', 'B', 'C'], ['X', 'Y', 'Z']]
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown(f"**Плотность матрицы (Количество объектов `{abc_target}` в секторах):**")
            st.dataframe(pivot_matrix, use_container_width=True)
        with col_m2:
            fig_heat = px.imshow(pivot_matrix, text_auto=True, labels=dict(x="Стабильность спроса (XYZ)", y="Объем масштаба (ABC)", color=f"Кол-во {abc_target}"), x=['X', 'Y', 'Z'], y=['A', 'B', 'C'], color_continuous_scale="Blues")
            fig_heat.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_heat, use_container_width=True)

        st.subheader("💡 Рекомендательный протокол снабжения:")
        col_rec1, col_rec2, col_rec3 = st.columns(3)
        with col_rec1: st.info(f"💎 **Группа AX / AY ({pivot_matrix.loc['A', 'X'] + pivot_matrix.loc['A', 'Y']} поз.):** Самые ценные стабильные позиции. Рекомендуется фиксация цен годовыми контрактами.")
        with col_rec2: st.warning(f"⚠️ **Группа AZ / BZ ({pivot_matrix.loc['A', 'Z'] + pivot_matrix.loc['B', 'Z']} поз.):** Высокие затраты при хаотичном спросе. Закупки проводить только по согласованию.")
        with col_rec3: st.success(f"📦 **Группа CX / CY ({pivot_matrix.loc['C', 'X'] + pivot_matrix.loc['C', 'Y']} поз.):** Дешевая регулярная мелочь. Закупать большими партиями впрок.")

        st.subheader("📋 Детальный реестр матрицы классификации")
        st.dataframe(df_matrix.sort_values(by=abc_value, ascending=False), use_container_width=True)
    except Exception as abc_err:
        st.error(f"❌ Ошибка вычисления матрицы. Технический лог: {abc_err}")
# МОДУЛЬ 2: RFM Сегментация
def internal_show_rfm_page(filtered_df):
    st.title("👥 Модуль RFM-сегментации номенклатуры")
    if filtered_df.empty:
        st.info("ℹ️ Пожалуйста, загрузите файлы и проверьте фильтры. Текущая выборка пуста.")
        return
    df = filtered_df.copy()
    if not all(col in df.columns for col in ['ОЗМ', 'Сумма', 'Источник (Файл)']):
        st.error("❌ Для RFM-анализа требуются столбцы 'ОЗМ', 'Сумма' и 'Источник (Файл)'.")
        return
    st.markdown("### 📊 Распределение ОЗМ по RFM-сегментам")
    rfm_df = df.groupby('ОЗМ').agg(Frequency=('Источник (Файл)', 'count'), Monetary=('Сумма', 'sum')).reset_index()
    if len(rfm_df) >= 3:
        rfm_df['F_Score'] = pd.qcut(rfm_df['Frequency'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        rfm_df['M_Score'] = pd.qcut(rfm_df['Monetary'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
    else:
        rfm_df['F_Score'], rfm_df['M_Score'] = '1', '1'
    rfm_df['RFM_Segment'] = rfm_df['F_Score'] + rfm_df['M_Score']
    seg_counts = rfm_df.groupby('RFM_Segment').size().reset_index(name='Количество ОЗМ')
    fig = px.bar(seg_counts, x='RFM_Segment', y='Количество ОЗМ', text_auto=True, title="Плотность сегментов (Частота + Деньги)", color='RFM_Segment')
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(rfm_df.head(100), use_container_width=True)
