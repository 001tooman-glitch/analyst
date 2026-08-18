import streamlit as st
import pandas as pd
import io
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Интерактивная BI-Платформа", layout="wide")

if "manual_charts" not in st.session_state: st.session_state.manual_charts = 1
if "main_df" not in st.session_state: st.session_state.main_df = pd.DataFrame()
if "uploaded_backup" not in st.session_state: st.session_state.uploaded_backup = None

@st.cache_data(show_spinner=False, ttl=3600) # Кэш живет 1 час
def power_query_clean_engine(uploaded_files_list):
    frames_dict = {}
    if not uploaded_files_list: return pd.DataFrame(), False
    for f in uploaded_files_list:
        try:
            if f.name.endswith('.csv'):
                df_raw = pd.read_csv(f, dtype=str)
            else:
                df_raw = pd.read_excel(f, dtype=str, engine='calamine')
            if df_raw.empty: continue
            
            df_raw.columns = [str(c).strip() for c in df_raw.columns]
            mapped_cols = []
            for col in df_raw.columns:
                c_low = col.lower()
                if any(w in c_low for w in ['озм', 'код материала', 'номенклатур']): mapped_cols.append('ОЗМ')
                elif any(w in c_low for w in ['наименование', 'материал']): mapped_cols.append('Наименование материала')
                elif any(w in c_low for w in ['количество', 'кол-во', 'объем']): mapped_cols.append('Количество')
                elif any(w in c_low for w in ['сумма', 'стоимость', 'цена']): mapped_cols.append('Сумма')
                else: mapped_cols.append(col)
            df_raw.columns = mapped_cols
            
            df_raw = df_raw.loc[:, ~df_raw.columns.str.contains('^Без названия|^Unnamed|^Unnamed:')]
            df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()]
            df_raw = df_raw.dropna(how='all')
            df_raw['Источник (Файл)'] = f.name.replace(".xlsx", "").replace(".csv", "")
            frames_dict[f.name] = df_raw
        except: pass
            
    if not frames_dict: return pd.DataFrame(), False
    merged_df = pd.concat(frames_dict.values(), ignore_index=True, join='outer')
    
    for col in merged_df.columns:
        if col in ['Количество', 'Сумма']:
            merged_df[col] = merged_df[col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0.0).astype('float32') # Сжатие памяти RAM
        else:
            merged_df[col] = merged_df[col].fillna("").astype(str).str.strip()
    return merged_df, True
@st.cache_data(show_spinner=False)
def calculate_abc_xyz(df, a_limit, b_limit):
    df_abc = df.groupby('ОЗМ', as_index=False)['Сумма'].sum().sort_values(by='Сумма', ascending=False).reset_index(drop=True)
    total_sum = df_abc['Сумма'].sum()
    if total_sum == 0: return pd.DataFrame(), pd.DataFrame()
    
    df_abc['Доля'] = df_abc['Сумма'] / total_sum
    df_abc['Кумулятивная доля'] = df_abc['Доля'].cumsum() * 100
    df_abc['Класс ABC'] = df_abc['Кумулятивная доля'].map(lambda x: 'A' if x <= a_limit else ('B' if x <= (a_limit + b_limit) else 'C'))
    
    if 'Источник (Файл)' in df.columns:
        df_xyz_raw = df.groupby(['ОЗМ', 'Источник (Файл)'])['Сумма'].sum().unstack(fill_value=0)
        mean_val = df_xyz_raw.mean(axis=1)
        std_val = df_xyz_raw.std(axis=1, ddof=1 if df_xyz_raw.shape > 1 else 0)
        kv = np.where(mean_val > 0, std_val / mean_val, 999)
        df_xyz = pd.DataFrame({'ОЗМ': df_xyz_raw.index, 'KV': kv})
        df_xyz['Класс XYZ'] = pd.cut(df_xyz['KV'], bins=[-1, 0.10, 0.25, float('inf')], labels=['X', 'Y', 'Z']).astype(str)
    else:
        df_xyz = pd.DataFrame({'ОЗМ': df_abc['ОЗМ'], 'Класс XYZ': 'X'})
        
    df_matrix = pd.merge(df_abc, df_xyz, on='ОЗМ')
    df_matrix['Матрица ABC/XYZ'] = df_matrix['Класс ABC'] + df_matrix['Класс XYZ']
    summary = df_matrix.groupby('Матрица ABC/XYZ').agg(Количество_ОЗМ=('ОЗМ', 'count'), Общая_Сумма=('Сумма', 'sum')).reset_index()
    return summary, df_matrix

def internal_show_abc_xyz_page(filtered_df):
    st.title("🧮 Модуль автоматического ABC/XYZ-анализа")
    if filtered_df.empty: return
    col1, col2 = st.columns(2)
    with col1: a_limit = st.slider("Граница группы A (% выручки):", 50, 90, 80)
    with col2: b_limit = st.slider("Граница группы B (% выручки):", 5, 25, 15)
    
    summary, df_matrix = calculate_abc_xyz(filtered_df, a_limit, b_limit)
    if summary.empty: return
    
    st.subheader("📋 Сводная матрица распределения")
    st.dataframe(summary, use_container_width=True)
    st.plotly_chart(px.pie(summary, values='Общая_Сумма', names='Матрица ABC/XYZ'), use_container_width=True)
    st.subheader("🔍 Детализированный реестр ОЗМ (Топ-1000 по стоимости)")
    st.dataframe(df_matrix.head(1000), use_container_width=True)

def internal_show_rfm_page(filtered_df):
    st.title("👥 Модуль RFM-сегментации номенклатуры")
    if filtered_df.empty: return
    rfm_df = filtered_df.groupby('ОЗМ').agg(Frequency=('Источник (Файл)', 'count'), Monetary=('Сумма', 'sum')).reset_index()
    if len(rfm_df) >= 3:
        rfm_df['F_Score'] = pd.qcut(rfm_df['Frequency'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        rfm_df['M_Score'] = pd.qcut(rfm_df['Monetary'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
    else:
        rfm_df['F_Score'] = '1'; rfm_df['M_Score'] = '1'
    rfm_df['RFM_Segment'] = rfm_df['F_Score'] + rfm_df['M_Score']
    seg_counts = rfm_df.groupby('RFM_Segment').size().reset_index(name='Количество ОЗМ')
    st.plotly_chart(px.bar(seg_counts, x='RFM_Segment', y='Количество ОЗМ', text_auto=True), use_container_width=True)
    st.dataframe(rfm_df.head(500), use_container_width=True)
# --- ИНТЕРФЕЙС И МАРШРУТИЗАЦИЯ ---
uploaded_files = st.file_uploader("Загрузите файлы Excel/CSV:", type=["csv", "xlsx"], accept_multiple_files=True)
if uploaded_files:
    if st.session_state.uploaded_backup != uploaded_files: 
        st.session_state.uploaded_backup = uploaded_files; st.session_state.main_df = pd.DataFrame() 
elif st.session_state.uploaded_backup: uploaded_files = st.session_state.uploaded_backup

if uploaded_files:
    if st.session_state.main_df.empty:
        with st.spinner("⏳ Анализ структуры данных..."):
            calculated_df, is_merged = power_query_clean_engine(uploaded_files)
            if not calculated_df.empty: st.session_state.main_df = calculated_df
                
    main_df = st.session_state.main_df
    if not main_df.empty:
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)
        
        # Облегченные фильтры в сайдбаре (Браузер больше не зависает)
        st.sidebar.subheader("⚙️ Глобальные Фильтры")
        filter_col_1 = st.sidebar.selectbox("Поле среза №1:", all_cols, key="fl_col_1")
        active_df = main_df.copy()
        
        if filter_col_1 != "-- Выберите заголовок --":
            # Берем строго первые 500 уникальных значений, чтобы не перегружать выпадающий список
            top_vals = list(active_df[filter_col_1].astype(str).value_counts().head(500).index)
            unique_vals_1 = ["-- Все значения --"] + top_vals
            filter_val_1 = st.sidebar.selectbox("Значение среза №1 (Топ-500):", unique_vals_1, key="fl_val_1")
            if filter_val_1 != "-- Все значения --":
                active_df = active_df[active_df[filter_col_1].astype(str) == str(filter_val_1)]
                
        page = st.sidebar.radio("Навигация:", ["📂 1. Загрузка данных", "📊 2. Executive Диаграммы", "🧮 3. ABC/XYZ-аналитика", "👥 4. RFM-сегментация"])
        
        if page == "📂 1. Загрузка данных":
            st.title("🚀 Модуль Импорта Данных")
            st.success(f"📊 Строк обработано: {len(main_df):,}")
            rows_per_page = 50
            total_pages = max((len(main_df) // rows_per_page), 1)
            current_page = st.number_input(f"Страница (из {total_pages}):", min_value=1, max_value=total_pages, value=1, step=1)
            start_idx = (current_page - 1) * rows_per_page
            st.dataframe(main_df.iloc[start_idx:start_idx+rows_per_page], height=350, use_container_width=True)
            
        elif page == "📊 2. Executive Диаграммы":
            st.title("📊 BI-Панель")
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("➕ Добавить график"): st.session_state.manual_charts += 1
            with c_btn2:
                if st.button("➖ Удалить график") and st.session_state.manual_charts > 1: st.session_state.manual_charts -= 1
                    
            for i in range(st.session_state.manual_charts):
                st.markdown(f"#### 📈 Настройка диаграммы №{i+1}")
                col_g1, col_g2, col_g3 = st.columns(3)
                with col_g1: x_ax = st.selectbox(f"Ось X #{i+1}:", all_cols, key=f"x_{i}")
                with col_g2: y_ax = st.selectbox(f"Ось Y #{i+1}:", [c for c in all_cols if c in ['Количество', 'Сумма']], key=f"y_{i}")
                with col_g3: chart_type = st.selectbox(f"Тип визуализации #{i+1}:", ["Столбчатая", "Линейная"], key=f"t_{i}")
                
                if x_ax != "-- Выберите заголовок --" and y_ax != "-- Выберите заголовок --":
                    # Считаем срез Топ-20 элементов для моментального рендеринга
                    chart_data = active_df.groupby(x_ax, as_index=False)[y_ax].sum().sort_values(by=y_ax, ascending=False).head(20)
                    if chart_type == "Столбчатая":
                        st.plotly_chart(px.bar(chart_data, x=x_ax, y=y_ax, text_auto='.2s'), use_container_width=True)
                    else:
                        st.plotly_chart(px.line(chart_data, x=x_ax, y=y_ax), use_container_width=True)
                        
        elif "3. ABC/XYZ" in page: internal_show_abc_xyz_page(active_df)
        elif "4. RFM" in page: internal_show_rfm_page(active_df)
else:
    st.info("Ожидание загрузки любых файлов Excel/CSV...")
