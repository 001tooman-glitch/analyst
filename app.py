import streamlit as st
import pandas as pd
import io
import re
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Настройка конфигурации страницы Streamlit (должна быть первой в файле)
st.set_page_config(page_title="Интерактивная BI-Платформа", layout="wide")

# Инициализация сессионного состояния
if "manual_charts" not in st.session_state: st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state: st.session_state.manual_cards = 1
if "active_filter_val" not in st.session_state: st.session_state.active_filter_val = None
if "active_filter_col" not in st.session_state: st.session_state.active_filter_col = None
if "main_df" not in st.session_state: st.session_state.main_df = pd.DataFrame()
if "uploaded_backup" not in st.session_state: st.session_state.uploaded_backup = None
# СВЕРХБЫСТРЫЙ КЭШИРУЕМЫЙ ДВИЖОК ОЧИСТКИ (Зависит ТОЛЬКО от самих файлов)
@st.cache_data(show_spinner=False)
def power_query_clean_engine(uploaded_files_list):
    frames_dict = {}
    if not uploaded_files_list: 
        return pd.DataFrame(), False
        
    # Жестко фиксируем параметры парсинга, чтобы избежать случайного сброса кэша из UI
    skip_top = 0  
    remove_footer = True
        
    for f in uploaded_files_list:
        try:
            if f.name.endswith('.csv'):
                df_raw = pd.read_csv(f, dtype=str)
            else:
                # Использование высокопроизводительного движка calamine (Rust под капотом)
                df_raw = pd.read_excel(f, dtype=str, engine='calamine')
            
            if df_raw.empty: continue
            if skip_top > 0 and skip_top < len(df_raw):
                df_raw = df_raw.iloc[skip_top:].reset_index(drop=True)
            if df_raw.empty: continue
            
            df_raw.columns = [str(c).strip() for c in df_raw.columns]
            
            mapped_cols = []
            for col in df_raw.columns:
                c_low = col.lower()
                if any(w in c_low for w in ['озм', 'код материала', 'номенклатур']): mapped_cols.append('ОЗМ')
                elif any(w in c_low for w in ['наименование', 'материал']): mapped_cols.append('Наименование материала')
                elif any(w in c_low for w in ['количество', 'кол-во', 'объем', 'открытой потребн']): mapped_cols.append('Количество')
                elif any(w in c_low for w in ['сумма', 'стоимость', 'цена', 'капитал']): mapped_cols.append('Сумма')
                else: mapped_cols.append(col)
            df_raw.columns = mapped_cols
            
            df_raw = df_raw.loc[:, ~df_raw.columns.str.contains('^Без названия|^Unnamed|^Unnamed:')]
            df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()]
            
            if remove_footer:
                for text_col in df_raw.select_dtypes(include=['object']).columns:
                    mask_footer = df_raw[text_col].astype(str).str.lower().str.contains('итого|всего|сумма|подпись', na=False)
                    df_raw = df_raw[~mask_footer]
            
            df_raw = df_raw.dropna(how='all')
            df_raw['Источник (Файл)'] = f.name.replace(".xlsx", "").replace(".xls", "").replace(".csv", "")
            frames_dict[f.name] = df_raw
        except: 
            pass
            
    if not frames_dict: return pd.DataFrame(), False
    merged_df = pd.concat(frames_dict.values(), ignore_index=True, join='outer')
    
    for col in merged_df.columns:
        if col == 'Источник (Файл)': 
            merged_df[col] = merged_df[col].astype('category') # Оптимизация RAM
            continue
        if col in ['Quantity', 'Amount', 'Количество', 'Сумма']:
            merged_df[col] = merged_df[col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0.0).astype('float32') # Оптимизация RAM
        else:
            merged_df[col] = merged_df[col].fillna("").astype(str).str.strip().replace(['nan', 'None', 'Не указано'], "")
            
    if 'Quantity' in merged_df.columns: merged_df.rename(columns={'Quantity': 'Количество'}, inplace=True)
    if 'Amount' in merged_df.columns: merged_df.rename(columns={'Amount': 'Сумма'}, inplace=True)
    
    front_cols = [c for c in ['ОЗМ', 'Наименование материала', 'Количество', 'Сумма', 'Источник (Файл)'] if c in merged_df.columns]
    other_cols = [c for c in merged_df.columns if c not in front_cols]
    return merged_df[front_cols + other_cols], True
# МОДУЛЬ 1: СОВМЕЩЕННЫЙ ABC/XYZ АНАЛИЗ (ПОЛНАЯ РЕАЛИЗАЦИЯ)
def internal_show_abc_xyz_page(filtered_df):
    st.title("🧮 Модуль автоматического ABC/XYZ-анализа")
    if filtered_df.empty:
        st.info("ℹ️ Пожалуйста, загрузите файлы и проверьте фильтры. Текущая выборка пуста.")
        return
    df = filtered_df.copy()
    if 'ОЗМ' not in df.columns or 'Сумма' not in df.columns:
        st.error("❌ В данных отсутствуют обязательные столбцы 'ОЗМ' и 'Сумма'.")
        return
    if 'Источник (Файл)' not in df.columns:
        df['Источник (Файл)'] = 'Единый Источник'
        
    if st.session_state.get("active_filter_col") and st.session_state.get("active_filter_val"):
        st.success(f"🎯 Анализ запущен по активному срезу: `{st.session_state.active_filter_col}` = `{st.session_state.active_filter_val}`")
        
    st.markdown("### 📊 Настройка параметров классификации")
    col1, col2 = st.columns(2)
    with col1: a_limit = st.slider("Граница группы A (% кумулятивной выручки):", 50, 90, 80, key="abc_sl_1")
    with col2: b_limit = st.slider("Граница группы B (следующие % выручки):", 5, 25, 15, key="abc_sl_2")
        
    df_abc = df.groupby('ОЗМ', as_index=False)['Сумма'].sum()
    df_abc = df_abc.sort_values(by='Сумма', ascending=False).reset_index(drop=True)
    total_sum = df_abc['Сумма'].sum()
    if total_sum == 0:
        st.warning("⚠️ Общая сумма выбранных позиций равна нулю. Анализ невозможен.")
        return
        
    df_abc['Доля'] = df_abc['Сумма'] / total_sum
    df_abc['Кумулятивная доля'] = df_abc['Доля'].cumsum() * 100
    df_abc['Класс ABC'] = df_abc['Кумулятивная доля'].map(lambda x: 'A' if x <= a_limit else ('B' if x <= (a_limit + b_limit) else 'C'))
    
    df_xyz_raw = df.groupby(['ОЗМ', 'Источник (Файл)'])['Сумма'].sum().unstack(fill_value=0)
    mean_val = df_xyz_raw.mean(axis=1)
    std_val = df_xyz_raw.std(axis=1, ddof=1 if df_xyz_raw.shape > 1 else 0)
    kv = np.where(mean_val > 0, std_val / mean_val, 999)
    df_xyz = pd.DataFrame({'ОЗМ': df_xyz_raw.index, 'KV': kv})
    df_xyz['Класс XYZ'] = pd.cut(df_xyz['KV'], bins=[-1, 0.10, 0.25, float('inf')], labels=['X', 'Y', 'Z']).astype(str)
    
    if df_xyz_raw.shape <= 1:
        df_xyz['Класс XYZ'] = 'X'
        
    df_matrix = pd.merge(df_abc[['ОЗМ', 'Сумма', 'Класс ABC']], df_xyz[['ОЗМ', 'KV', 'Класс XYZ']], on='ОЗМ')
    df_matrix['Матрица ABC/XYZ'] = df_matrix['Класс ABC'] + df_matrix['Класс XYZ']
    
    st.subheader("📋 Сводная матрица распределения номенклатуры")
    summary = df_matrix.groupby('Матрица ABC/XYZ').agg(Количество_ОЗМ=('ОЗМ', 'count'), Общая_Сумма=('Сумма', 'sum')).reset_index()
    st.dataframe(summary, use_container_width=True)
    fig = px.pie(summary, values='Общая_Сумма', names='Матрица ABC/XYZ', title='Доля стоимости по совмещенным классам ABC/XYZ')
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("🔍 Детализированный реестр ОЗМ")
    st.dataframe(df_matrix.sort_values(by='Сумма', ascending=False), use_container_width=True)

# МОДУЛЬ 2: RFM СЕГМЕНТАЦИЯ
def internal_show_rfm_page(filtered_df):
    st.title("👥 Модуль RFM-сегментации номенклатуры")
    if filtered_df.empty:
        st.info("ℹ️ Пожалуйста, загрузите файлы и проверьте фильтры. Текущая выборка пуста.")
        return
    df = filtered_df.copy()
    if not all(col in df.columns for col in ['ОЗМ', 'Сумма', 'Источник (Файл)']):
        st.error("❌ Для RFM-анализа требуются столбцы 'ОЗМ', 'Сумма' и 'Источник (Файл)'.")
        return
    if st.session_state.get("active_filter_col") and st.session_state.get("active_filter_val"):
        st.success(f"🎯 Сегментация запущена по активному срезу: `{st.session_state.active_filter_col}` = `{st.session_state.active_filter_val}`")
        
    st.markdown("### 📊 Распределение ОЗМ по RFM-сегментам")
    rfm_df = df.groupby('ОЗМ').agg(Frequency=('Источник (Файл)', 'count'), Monetary=('Сумма', 'sum')).reset_index()
    if len(rfm_df) >= 3:
        try:
            rfm_df['F_Score'] = pd.qcut(rfm_df['Frequency'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
            rfm_df['M_Score'] = pd.qcut(rfm_df['Monetary'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        except Exception:
            rfm_df['F_Score'] = '1'; rfm_df['M_Score'] = '1'
    else:
        rfm_df['F_Score'] = '1'; rfm_df['M_Score'] = '1'
        
    rfm_df['RFM_Segment'] = rfm_df['F_Score'] + rfm_df['M_Score']
    seg_counts = rfm_df.groupby('RFM_Segment').size().reset_index(name='Количество ОЗМ')
    fig = px.bar(seg_counts, x='RFM_Segment', y='Количество ОЗМ', text_auto=True, title="Плотность сегментов (Частота + Деньги)", color='RFM_Segment')
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(rfm_df.head(100), use_container_width=True)
# --- ГЛАВНЫЙ ИНТЕРФЕЙС И ЗАГРУЗКА ДАННЫХ ---
uploaded_files = st.file_uploader("Загрузите один или несколько любых файлов Excel/CSV:", type=["csv", "xlsx"], accept_multiple_files=True)
if uploaded_files:
    if st.session_state.uploaded_backup != uploaded_files: 
        st.session_state.uploaded_backup = uploaded_files; st.session_state.main_df = pd.DataFrame() 
elif st.session_state.uploaded_backup: 
    uploaded_files = st.session_state.uploaded_backup

if uploaded_files:
    if st.session_state.main_df.empty:
        with st.spinner("⏳ Идёт глубокая Power Query очистка данных... Пожалуйста, подождите."):
            calculated_df, is_merged = power_query_clean_engine(uploaded_files)
            if not calculated_df.empty: st.session_state.main_df = calculated_df
                
    main_df = st.session_state.main_df
    if not main_df.empty:
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚙️ Глобальные Фильтры BI-платформы")
        filter_col_1 = st.sidebar.selectbox("Шаг 1. Первое поле среза:", all_cols, key="fl_col_1_global")
        active_df_global = main_df.copy()
        
        if filter_col_1 != "-- Выберите заголовок --":
            unique_vals_1 = ["-- Все значения --"] + list(active_df_global[filter_col_1].astype(str).unique())
            filter_val_1 = st.sidebar.selectbox("Шаг 2. Значение среза №1:", unique_vals_1, key="fl_val_1_global")
            if filter_val_1 != "-- Все Oncology --" and filter_val_1 != "-- Все значения --":
                active_df_global = active_df_global[active_df_global[filter_col_1].astype(str) == str(filter_val_1)]
                st.session_state.active_filter_col = filter_col_1; st.session_state.active_filter_val = filter_val_1
                
        st.sidebar.markdown("---")
        filter_col_2 = st.sidebar.selectbox("Шаг 3. Второе поле среза:", all_cols, key="fl_col_2_global")
        if filter_col_2 != "-- Выберите заголовок --":
            unique_vals_2 = ["-- Все значения --"] + list(active_df_global[filter_col_2].astype(str).unique())
            filter_val_2 = st.sidebar.selectbox("Шаг 4. Значение среза №2:", unique_vals_2, key="fl_val_2_global")
            if filter_val_2 != "-- Все значения --":
                active_df_global = active_df_global[active_df_global[filter_col_2].astype(str) == str(filter_val_2)]
                
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📖 Меню разделов:")
        page = st.sidebar.radio("Перейти к разделу:", ["📂 1. Загрузка и очистка данных", "📊 2. Executive Диаграммы", "🧮 3. ABC/XYZ-аналитика ОЗМ", "👥 4. RFM-сегментация"], label_visibility="collapsed")
        
        if page == "📂 1. Загрузка и очистка данных":
            st.title("🚀 Модуль Предобработки & Импорта Данных")
            tot_rows, tot_cols = len(main_df), len(main_df.columns)
            st.success(f"📊 Идеальная сводная база сформирована! Строк: {tot_rows:,}, Колонок: {tot_cols}")
            rows_per_page = 50
            total_pages = (tot_rows // rows_per_page) + (1 if tot_rows % rows_per_page > 0 else 0)
            col_p1, col_p2 = st.columns(2)
            with col_p1: current_page = st.number_input(f"Страница (из {total_pages}):", min_value=1, max_value=total_pages, value=1, step=1, key="nav_pg_idx")
            with col_p2:
                start_idx = (current_page - 1) * rows_per_page; end_idx = start_idx + rows_per_page
                st.markdown(f"Показаны строки с **{start_idx + 1}** по **{min(end_idx, tot_rows)}** из **{tot_rows:,}** строк.")
            df_to_show = main_df.iloc[start_idx:end_idx].copy()
            st.dataframe(df_to_show, height=350, use_container_width=True)
            try:
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer: main_df.to_excel(writer, index=False, sheet_name='Сводные данные')
                st.download_button(label="📥 Скачать идеальную сводную базу (Excel .xlsx)", data=excel_buffer.getvalue(), file_name="Идеальная_сводная_база.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as de: st.error(f"Ошибка формирования Excel: {de}")
                
        elif page == "📊 2. Executive Диаграммы":
            st.title("📊 Интерактивная BI-Панель Показателей")
            df_chart = active_df_global.copy()
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("➕ Добавить график/диаграмму"): st.session_state.manual_charts += 1
            with c_btn2:
                if st.button("➖ Удалить последний график") and st.session_state.manual_charts > 1: st.session_state.manual_charts -= 1
            for i in range(st.session_state.manual_charts):
                st.markdown(f"#### 📈 Настройка диаграммы №{i+1}")
                col_g1, col_g2, col_g3 = st.columns(3)
                with col_g1: x_ax = st.selectbox(f"Ось X (Группировка) #{i+1}:", all_cols, key=f"x_ax_{i}")
                with col_g2: y_ax = st.selectbox(f"Ось Y (Показатель) #{i+1}:", [c for c in all_cols if c in ['Количество', 'Сумма']], key=f"y_ax_{i}")
                with col_g3: chart_type = st.selectbox(f"Тип визуализации #{i+1}:", ["Столбчатая", "Линейная", "Кольцевая (Donut)"], key=f"type_{i}")
                if x_ax != "-- Выберите заголовок --" and y_ax != "-- Выберите заголовок --":
                    chart_data = df_chart.groupby(x_ax, as_index=False)[y_ax].sum().sort_values(by=y_ax, ascending=False).head(30)
                    if chart_type == "Столбчатая": fig = px.bar(chart_data, x=x_ax, y=y_ax, text_auto='.2s', title=f"{y_ax} по категориям {x_ax}")
                    elif chart_type == "Линейная": fig = px.line(chart_data, x=x_ax, y=y_ax, title=f"Временная зависимость: {y_ax} по {x_ax}")
                    else: fig = px.pie(chart_data, values=y_ax, names=x_ax, hole=0.4, title=f"Структурная доля {y_ax} по {x_ax}")
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info(f"💡 Для отображения диаграммы №{i+1} укажите параметры группировки и показателей выше.")
        elif "3. ABC/XYZ" in page: internal_show_abc_xyz_page(active_df_global)
        elif "4. RFM" in page: internal_show_rfm_page(active_df_global)
else:
    st.info("Ожидание загрузки любых файлов Excel/CSV для активации BI-панели...")
