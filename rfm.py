import streamlit as st
import pandas as pd
import io
import re

# Импортируем наши новые изолированные No-Code модули аналитики из корня проекта
from abc_xyz import show_abc_xyz_page
from rfm import show_rfm_page

st.set_page_config(page_title="Enterprise BI Конструктор (Power Query)", layout="wide")

# РАСШИРЕННЫЙ ПЕРЕКЛЮЧАТЕЛЬ СТРАНИЦ В БОКОВОЙ ПАНЕЛИ
st.sidebar.markdown("### 🗺️ Навигация по BI-платформе")
page = st.sidebar.radio(
    "Перейти к разделу:",
    [
        "🗂️ 1. Загрузка и очистка данных", 
        "📊 2. Конструктор диаграмм",
        "🧮 3. ABC/XYZ-анализ ОЗМ",
        "👥 4. RFM-сегментация"
    ]
)
st.sidebar.markdown("---")

if "manual_charts" not in st.session_state: st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state: st.session_state.manual_cards = 1
if "active_filter_val" not in st.session_state: st.session_state.active_filter_val = None
if "active_filter_col" not in st.session_state: st.session_state.active_filter_col = None
if "main_df" not in st.session_state: st.session_state.main_df = pd.DataFrame()
if "uploaded_backup" not in st.session_state: st.session_state.uploaded_backup = None

# Параметры Power Query шагов очистки в сессии
if "pq_skip_top" not in st.session_state: st.session_state.pq_skip_top = 0
if "pq_merge_headers" not in st.session_state: st.session_state.pq_merge_headers = False
if "pq_remove_footer" not in st.session_state: st.session_state.pq_remove_footer = True

# МОДЕРНИЗИРОВАННЫЙ ДВИЖОК POWER QUERY СО СКЛЕЙКОЙ СИНОНИМОВ СТОЛБЦОВ
def power_query_clean_engine(uploaded_files_list, skip_top, merge_headers, remove_footer):
    frames_dict = {}
    if not uploaded_files_list:
        return pd.DataFrame(), False
        
    for f in uploaded_files_list:
        try:
            if f.name.endswith('.csv'):
                df_raw = pd.read_csv(f, header=None, dtype=str)
            else:
                df_raw = pd.read_excel(f, header=None, dtype=str)
            
            # 1. Шаг PQ: Удалить верхние пустые строки (Skip Rows)
            if skip_top > 0 and skip_top < len(df_raw):
                df_raw = df_raw.iloc[skip_top:].reset_index(drop=True)
                
            if df_raw.empty: continue
            
            # 2. Шаг PQ: Продвинутое схлопывание объединенных многострочных заголовков
            if merge_headers and len(df_raw) > 1:
                row0 = list(df_raw.iloc.astype(str).str.strip())
                row1 = list(df_raw.iloc.astype(str).str.strip())
                current_parent = ""
                for idx in range(len(row0)):
                    val0 = row0[idx]
                    if val0 and val0 != 'nan' and val0 != 'None' and not val0.startswith('Unnamed:'):
                        current_parent = val0
                    else:
                        row0[idx] = current_parent
                
                new_cols = []
                for idx, (c0, c1) in enumerate(zip(row0, row1)):
                    clean_c0 = "" if c0 in ['nan', 'None'] or c0.startswith('Unnamed:') else c0
                    clean_c1 = "" if c1 in ['nan', 'None'] or c1.startswith('Unnamed:') else c1
                    combined = f"{clean_c0}_{clean_c1}".strip("_ ")
                    new_cols.append(combined if combined else f"Колонка_{idx+1}")
                df_raw.columns = new_cols
                df_raw = df_raw.iloc[2:].reset_index(drop=True)
            else:
                df_raw.columns = df_raw.iloc.astype(str).str.strip()
                df_raw = df_raw.iloc[1:].reset_index(drop=True)
                
            # 3. Шаг PQ: Финальная очистка шапки от мусорных артефактов Excel
            cleaned_cols = []
            for idx, col in enumerate(df_raw.columns):
                c_str = str(col).replace('nan №', '').replace('№ nan', '').replace('nan', '').replace('Unnamed:', '').strip()
                c_str = re.sub(r'\s+', ' ', c_str).strip()
                cleaned_cols.append(c_str if c_str else f"Столбец_{idx+1}")
            df_raw.columns = cleaned_cols
            
            # ИНСТРУМЕНТ PQ MAPPING: Склеиваем разнородные названия колонок-синонимов в единый стандарт
            mapped_cols = []
            for col in df_raw.columns:
                c_low = col.lower()
                if any(w in c_low for w in ['озм', 'код материала', 'номенклатур']):
                    mapped_cols.append('ОЗМ')
                elif any(w in c_low for w in ['наименование', 'материал']):
                    mapped_cols.append('Наименование материала')
                elif any(w in c_low for w in ['количество', 'кол-во', 'объем', 'открытой потребн']):
                    mapped_cols.append('Quantity')
                elif any(w in c_low for w in ['сумма', 'стоимость', 'цена', 'капитал']):
                    mapped_cols.append('Amount')
                else:
                    mapped_cols.append(col)
            df_raw.columns = mapped_cols
            df_raw = df_raw.loc[:, ~df_raw.columns.str.contains('^Без названия|^Unnamed')]
            df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()]
            
            if remove_footer:
                for text_col in df_raw.select_dtypes(include=['object']).columns:
                    mask_footer = df_raw[text_col].astype(str).str.lower().str.contains('итого|всего|сумма|подпись|сдал|принял', na=False)
                    df_raw = df_raw[~mask_footer]
            
            df_raw = df_raw.dropna(how='all')
            period_name = f.name.replace(".xlsx", "").replace(".xls", "").replace(".csv", "")
            df_raw['Источник (Файл)'] = period_name
            frames_dict[f.name] = df_raw
        except:
            pass
            
    if not frames_dict: return pd.DataFrame(), False
    merged_df = pd.concat(frames_dict.values(), ignore_index=True, join='outer')
    
    for col in merged_df.columns:
        if col == 'Источник (Файл)': continue
        if col in ['Quantity', 'Amount']:
            merged_df[col] = merged_df[col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0.0)
        else:
            merged_df[col] = merged_df[col].fillna("").astype(str).str.strip().replace(['nan', 'None', 'Не указано'], "")
            
    merged_df = merged_df.dropna(how='all')
    
    if 'Quantity' in merged_df.columns: merged_df.rename(columns={'Quantity': 'Количество'}, inplace=True)
    if 'Amount' in merged_df.columns: merged_df.rename(columns={'Amount': 'Сумма'}, inplace=True)
    
    front_cols = [c for c in ['ОЗМ', 'Наименование материала', 'Количество', 'Сумма', 'Источник (Файл)'] if c in merged_df.columns]
    other_cols = [c for c in merged_df.columns if c not in front_cols]
    merged_df = merged_df[front_cols + other_cols]
    return merged_df, True
uploaded_files = st.file_uploader("Загрузите один или несколько любых файлов Excel/CSV:", type=["csv", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    if st.session_state.uploaded_backup != uploaded_files:
        st.session_state.uploaded_backup = uploaded_files
        st.session_state.main_df = pd.DataFrame() 
elif st.session_state.uploaded_backup:
    uploaded_files = st.session_state.uploaded_backup

if uploaded_files:
    if page == "🗂️ 1. Загрузка и очистка данных":
        st.markdown("### 🛠️ Панель шагов трансформации (Аналог Power Query)")
        col_pq1, col_pq2, col_pq3 = st.columns(3)
        with col_pq1:
            new_skip = st.number_input("1. Пропустить верхние строки (строк):", min_value=0, max_value=20, value=st.session_state.pq_skip_top, step=1)
            if new_skip != st.session_state.pq_skip_top:
                st.session_state.pq_skip_top = new_skip; st.session_state.main_df = pd.DataFrame()
        with col_pq2:
            new_merge = st.checkbox("2. Схлопнуть составной заголовок (из 2-х строк)", value=st.session_state.pq_merge_headers)
            if new_merge != st.session_state.pq_merge_headers:
                st.session_state.pq_merge_headers = new_merge; st.session_state.main_df = pd.DataFrame()
        with col_pq3:
            new_foot = st.checkbox("3. Авто-очистка подвала (удалить Итоги и подписи)", value=st.session_state.pq_remove_footer)
            if new_foot != st.session_state.pq_remove_footer:
                st.session_state.pq_remove_footer = new_foot; st.session_state.main_df = pd.DataFrame()
        st.markdown("---")

    if st.session_state.main_df.empty:
        with st.spinner("⏳ Идёт глубокая Power Query очистка данных... Пожалуйста, подождите."):
            calculated_df, is_merged = power_query_clean_engine(
                uploaded_files, st.session_state.pq_skip_top, st.session_state.pq_merge_headers, st.session_state.pq_remove_footer
            )
            if not calculated_df.empty:
                st.session_state.main_df = calculated_df

    main_df = st.session_state.main_df
    
    if not main_df.empty:
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)

        # ---------------- РАЗДЕЛ 1: ЗАГРУЗКА И ОЧИСТКА ДАННЫХ ----------------
        if page == "🗂️ 1. Загрузка и очистка данных":
            st.title("🚀 Модуль Предобработки & Импорта Данных")
            tot_rows = len(main_df)
            tot_cols = len(main_df.columns)
            st.success(f"📊 Идеальная сводная база сформирована! Файлов: {len(uploaded_files)}. Строк: {tot_rows:,}, Колонок: {tot_cols}")
            st.markdown("### 📋 Результат очистки (Постраничный интерактивный просмотр сводной таблицы):")
            
            rows_per_page = 50
            total_pages = (tot_rows // rows_per_page) + (1 if tot_rows % rows_per_page > 0 else 0)
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                current_page = st.number_input(f"Страница (из {total_pages}):", min_value=1, max_value=total_pages, value=1, step=1)
            with col_p2:
                start_idx = (current_page - 1) * rows_per_page
                end_idx = start_idx + rows_per_page
                st.markdown(f"Показаны строки с **{start_idx + 1}** по **{min(end_idx, tot_rows)}** из **{tot_rows:,}** общих строк.")
            
            try:
                page_view_df = main_df.iloc[start_idx:end_idx].copy()
                st.dataframe(page_view_df, height=350, use_container_width=True)
            except Exception as e: st.error(f"Ошибка превью: {e}")
            
            try:
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    main_df.to_excel(writer, index=False, sheet_name='Сводные данные')
                st.download_button(
                    label="📥 Скачать идеальную сводную базу (Excel .xlsx)", 
                    data=excel_buffer.getvalue(), 
                    file_name="Идеальная_сводная_база.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as de: st.error(f"Ошибка подготовки Excel-файла: {de}")
        # ---------------- РАЗДЕЛ 2: КАСКАДНЫЙ КОНСТРУКТОР BI ----------------
        elif page == "📊 2. Конструктор диаграмм":
            import plotly.graph_objects as go
            st.title("📊 Интерактивная BI-Панель Показателей")
            st.sidebar.subheader("🎚️ Панель Многоуровневой Фильтрации")
            
            # --- УРОВЕНЬ ФИЛЬТРАЦИИ №1 ---
            filter_col_1 = st.sidebar.selectbox("Шаг 1. Выберите первое поле:", all_cols, key="fl_col_1_bi")
            active_df = main_df.copy()
            
            if filter_col_1 != "-- Выберите заголовок --":
                unique_vals_1 = ["-- Все значения --"] + list(active_df[filter_col_1].astype(str).unique())
                filter_val_1 = st.sidebar.selectbox("Шаг 2. Выберите значение среза №1:", unique_vals_1, key="fl_val_1_bi")
                if filter_val_1 != "-- Все значения --":
                    active_df = active_df[active_df[filter_col_1].astype(str) == str(filter_val_1)]
                    st.session_state.active_filter_col = filter_col_1
                    st.session_state.active_filter_val = filter_val_1
                else:
                    st.session_state.active_filter_col = None
                    st.session_state.active_filter_val = None
            else:
                st.session_state.active_filter_col = None
                st.session_state.active_filter_val = None

            # --- УРОВЕНЬ ФИЛЬТРАЦИИ №2 (КАСКАДНЫЙ СРЕЗ ПОДДЕРЖКИ) ---
            st.sidebar.markdown("---")
            filter_col_2 = st.sidebar.selectbox("Шаг 3. Добавить второй разрез:", all_cols, key="fl_col_2_bi")
            
            if filter_col_2 != "-- Выберите заголовок --":
                unique_vals_2 = ["-- Все значения --"] + list(active_df[filter_col_2].astype(str).unique())
                filter_val_2 = st.sidebar.selectbox("Шаг 4. Выберите значение среза №2:", unique_vals_2, key="fl_val_2_bi")
                if filter_val_2 != "-- Все значения --":
                    active_df = active_df[active_df[filter_col_2].astype(str) == str(filter_val_2)]
            
            df_cards = active_df.copy()

            st.subheader("🎴 Панель Ключевых Показателей (KPI Карточки)")
            card_cols = st.columns(st.session_state.manual_cards)
            for j in range(st.session_state.manual_cards):
                with card_cols[j % len(card_cols)]:
                    st.markdown(f"**📌 Карточка № {j+1}**")
                    t_col = st.selectbox(f"Заголовок:", all_cols, key=f"c_t_{j}")
                    c_mode = st.selectbox(f"Расчет:", ["Сумма (SUM)", "Среднее (AVERAGE)"], key=f"c_m_{j}")
                    if t_col != "-- Выберите заголовок --":
                        try:
                            df_c = df_cards.copy()
                            df_c[t_col] = pd.to_numeric(df_c[t_col], errors='coerce').fillna(0)
                            val = df_c[t_col].sum() if "Сумма" in c_mode else df_c[t_col].mean()
                            st.markdown(f'<div style="background-color:#f8f9fa; border:1px solid #dee2e6; border-radius:10px; padding:20px; text-align:center; margin-bottom:15px;"><div style="color:#6c757d; font-size:16px;">{t_col}</div><div style="color:#1f77b4; font-size:36px; font-weight:bold;">{val:,.2f}</div></div>', unsafe_allow_html=True)
                        except: st.error("Ошибка")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("➕ Добавить карточку"): st.session_state.manual_cards += 1; st.rerun()
            with cc2:
                if st.session_state.manual_cards > 1:
                    if st.button("🗑️ Удалить карточку"): st.session_state.manual_cards -= 1; st.rerun()

            st.markdown("---")
            st.subheader("🛠️ No-Code Конструктор Графиков")
            for i in range(st.session_state.manual_charts):
                st.markdown(f"##### 📊 Настройка диаграммы № {i+1}")
                c1, c2, c3, c4 = st.columns(4)
                with c1: style = st.selectbox(f"Тип графики:", ["Столбчатая диаграмма (Bar)", "Линейный тренд (Line)", "Кольцевая долей (Donut)", "Диаграмма Водопад (Waterfall)", "Диаграмма Воронка (Funnel)"], key=f"s_{i}")
                with c2: x_ax = st.selectbox(f"Ось X (Категории):", all_cols, key=f"x_{i}")
                with c3: y_ax = st.selectbox(f"Ось Y (Показатели):", all_cols, key=f"y_{i}")
                with c4: color = st.color_picker(f"Цвет элементов:", "#1f77b4", key=f"col_{i}")
                with st.expander("🎨 Настройки отображения"):
                    lbl = st.checkbox("Показывать значения", value=True, key=f"lbl_{i}")
                    horiz = st.checkbox("Горизонтальный вид", value=False, key=f"h_{i}") if "Bar" in style else False
                    rot = st.slider("🔄 Поворот (градусы):", 0, 360, 0, step=15, key=f"rot_{i}") if "Donut" in style else 0

                if x_ax != "-- Выберите заголовок --" and y_ax != "-- Выберите заголовок --":
                    try:
                        df_chart = active_df.copy()
                        if filter_col_1 == x_ax and filter_val_1 != "-- Все значения --":
                            df_chart = main_df.copy()
                            if filter_col_2 != "-- Выберите заголовок --" and filter_val_2 != "-- Все значения --" and filter_col_2 != x_ax:
                                df_chart = df_chart[df_chart[filter_col_2].astype(str) == str(filter_val_2)]
                                
                        if filter_col_2 == x_ax and filter_val_2 != "-- Все значения --":
                            df_chart = main_df.copy()
                            if filter_col_1 != "-- Выберите заголовок --" and filter_val_1 != "-- Все значения --" and filter_col_1 != x_ax:
                                df_chart = df_chart[df_chart[filter_col_1].astype(str) == str(filter_val_1)]

                        df_chart[y_ax] = pd.to_numeric(df_chart[y_ax], errors='coerce').fillna(0)
                        df_g = df_chart.groupby(x_ax, as_index=False)[y_ax].sum()
                        if not horiz: df_g = df_g.sort_values(by=y_ax, ascending=False)
                        fig = go.Figure()
                        if "Waterfall" in style:
                            fig.add_trace(go.Waterfall(x=list(df_g[x_ax].astype(str)) + ["ИТОГО"], y=list(df_g[y_ax]) + [df_g[y_ax].sum()], measure=["relative"] * len(df_g[y_ax]) + ["total"], textposition="auto", text=[f"{v:,.0f}" for v in df_g[y_ax]] + [f"{df_g[y_ax].sum():,.0f}"] if lbl else None, increasing={"marker": {"color": color}}, totals={"marker": {"color": "green"}}))
                        elif "Funnel" in style:
                            fig.add_trace(go.Funnel(y=df_g[x_ax].astype(str), x=df_g[y_ax], textinfo="value+percent initial" if lbl else "none", marker={"color": color}))
                        elif "Donut" in style:
                            fig.add_trace(go.Pie(labels=df_g[x_ax], values=df_g[y_ax], hole=0.4, rotation=rot, textinfo="label+value" if lbl else "none"))
                        elif "Line" in style:
                            fig.add_trace(go.Scatter(x=df_g[x_ax], y=df_g[y_ax], mode="lines+markers+text" if lbl else "lines+markers", text=df_g[y_ax].map(lambda x: f"{x:,.0f}") if lbl else None, line=dict(color=color)))
                        else:
                            fig.add_trace(go.Bar(y=df_g[x_ax].astype(str) if horiz else df_g[y_ax], x=df_g[y_ax] if horiz else df_g[x_ax].astype(str), text=df_g[y_ax].map(lambda x: f"{x:,.0f}") if lbl else None, textposition="auto", orientation="h" if horiz else "v", marker_color=color))
                        fig.update_layout(xaxis=dict(tickangle=45 if not horiz else 0), uniformtext=dict(mode="hide", minsize=8))
                        st.plotly_chart(fig, use_container_width=True, key=f"p_{i}")
                    except Exception as ex: pass
                else: st.info("ℹ️ Выберите категории для построения графика")
                st.markdown("<hr style='border:1px dashed #ddd'>", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            with b1:
                if st.button("➕ Добавить диаграмму"): st.session_state.manual_charts += 1; st.rerun()
            with b2:
                if st.session_state.manual_charts > 1:
                    if st.button("🗑️ Удалить диаграмму"): st.session_state.manual_charts -= 1; st.rerun()

        # ---------------- РАЗДЕЛЫ ДЛЯ НОВЫХ ИЗОЛИРОВАННЫХ СТРАНИЦ ----------------
        elif page == "🗮️ 3. ABC/XYZ-анализ ОЗМ":
            show_abc_xyz_page()

        elif page == "👥 4. RFM-сегментация":
            show_rfm_page()
else: st.info("Ожидание загрузки любых файлов Excel/CSV для активации BI-панели...")
