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
        
        df = df[df[abc_target].str.strip() != ""]
        df = df[df[xyz_period].str.strip() != ""]

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
                if kv <= x_limit: класс_xyz = 'X'
                elif kv <= y_limit: класс_xyz = 'Y'
                else: класс_xyz = 'Z'
            else:
                kv = 999.0
                класс_xyz = 'Z'
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
        with col_rec1:
            st.info(f"💎 **Группа AX / AY ({pivot_matrix.loc['A', 'X'] + pivot_matrix.loc['A', 'Y']} поз.):** Стабильные лидеры затрат. Рекомендуется зафиксировать цены годовыми контрактами.")
        with col_rec2:
            st.warning(f"⚠️ **Группа AZ / BZ ({pivot_matrix.loc['A', 'Z'] + pivot_matrix.loc['B', 'Z']} поз.):** Высокие затраты при хаотичном спросе. Закупки проводить только по согласованию.")
        with col_rec3:
            st.success(f"📦 **Группа CX / CY ({pivot_matrix.loc['C', 'X'] + pivot_matrix.loc['C', 'Y']} поз.):** Дешевая регулярная мелочь. Закупать большими партиями впрок.")

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
        rfm_df['F_Score'] = '1'; rfm_df['M_Score'] = '1'
    rfm_df['RFM_Segment'] = rfm_df['F_Score'] + rfm_df['M_Score']
    seg_counts = rfm_df.groupby('RFM_Segment').size().reset_index(name='Количество ОЗМ')
    fig = px.bar(seg_counts, x='RFM_Segment', y='Количество ОЗМ', text_auto=True, title="Плотность сегментов (Частота + Деньги)", color='RFM_Segment')
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(rfm_df.head(100), use_container_width=True)
if "manual_charts" not in st.session_state: st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state: st.session_state.manual_cards = 1
if "pq_skip_top" not in st.session_state: st.session_state.pq_skip_top = 0
if "pq_merge_headers" not in st.session_state: st.session_state.pq_merge_headers = False
if "pq_remove_footer" not in st.session_state: st.session_state.pq_remove_footer = True

# УЛЬТРА-СКОРОСТЬ: Декоратор кэширует данные, прекращая повторное долгое чтение файлов Excel
@st.cache_data(show_spinner=False)
def power_query_clean_engine(uploaded_files_list, skip_top, merge_headers, remove_footer):
    frames_dict = {}
    if not uploaded_files_list: return pd.DataFrame(), False
    for f in uploaded_files_list:
        try:
            df_raw = pd.read_csv(f, dtype=str) if f.name.endswith('.csv') else pd.read_excel(f, dtype=str)
            if df_raw.empty: continue
            if skip_top > 0 and skip_top < len(df_raw): df_raw = df_raw.iloc[skip_top:].reset_index(drop=True)
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
        except: pass
    if not frames_dict: return pd.DataFrame(), False
    merged_df = pd.concat(frames_dict.values(), ignore_index=True, join='outer')
    for col in merged_df.columns:
        if col == 'Источник (Файл)': continue
        if col in ['Quantity', 'Amount', 'Количество', 'Сумма']:
            merged_df[col] = merged_df[col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0.0)
        else: merged_df[col] = merged_df[col].fillna("").astype(str).str.strip().replace(['nan', 'None', 'Не указано'], "")
    merged_df = merged_df.dropna(how='all')
    if 'Quantity' in merged_df.columns: merged_df.rename(columns={'Quantity': 'Количество'}, inplace=True)
    if 'Amount' in merged_df.columns: merged_df.rename(columns={'Amount': 'Сумма'}, inplace=True)
    front_cols = [c for c in ['ОЗМ', 'Наименование материала', 'Количество', 'Сумма', 'Источник (Файл)'] if c in merged_df.columns]
    other_cols = [c for c in merged_df.columns if c not in front_cols]
    return merged_df[front_cols + other_cols], True

uploaded_files = st.file_uploader("Загрузите один или несколько любых файлов Excel/CSV:", type=["csv", "xlsx"], accept_multiple_files=True)
if uploaded_files:
    # Очистка и сборка выполняются со спиннером ОДИН РАЗ, далее всё летает из памяти кэша!
    with st.spinner("⏳ Идёт молниеносная Power Query сборка данных... Пожалуйста, подождите."):
        calculated_df, is_merged = power_query_clean_engine(uploaded_files, st.session_state.pq_skip_top, st.session_state.pq_merge_headers, st.session_state.pq_remove_footer)
    
    if not calculated_df.empty:
        main_df = calculated_df
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)

        st.sidebar.markdown("---")
        st.sidebar.subheader("🎚️ Глобальные Фильтры BI-платформы")
        filter_col_1 = st.sidebar.selectbox("Шаг 1. Первое поле среза:", all_cols, key="fl_col_1_global")
        active_df_global = main_df.copy()
        
        if filter_col_1 != "-- Выберите заголовок --":
            unique_vals_1 = ["-- Все значения --"] + list(active_df_global[filter_col_1].astype(str).unique())
            filter_val_1 = st.sidebar.selectbox("Шаг 2. Значение среза №1:", unique_vals_1, key="fl_val_1_global")
            if filter_val_1 != "-- Все значения --":
                active_df_global = active_df_global[active_df_global[filter_col_1].astype(str) == str(filter_val_1)]
        
        st.sidebar.markdown("---")
        filter_col_2 = st.sidebar.selectbox("Шаг 3. Второе поле среза:", all_cols, key="fl_col_2_global")
        if filter_col_2 != "-- Выберите заголовок --":
            unique_vals_2 = ["-- Все значения --"] + list(active_df_global[filter_col_2].astype(str).unique())
            filter_val_2 = st.sidebar.selectbox("Шаг 4. Значение среза №2:", unique_vals_2, key="fl_val_2_global")
            if filter_val_2 != "-- Все значения --":
                active_df_global = active_df_global[active_df_global[filter_col_2].astype(str) == str(filter_val_2)]

        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🗺️ Меню разделов:")
        page = st.sidebar.radio("Перейти к разделу:", ["🗂️ 1. Загрузка и очистка данных", "📊 2. Executive Диаграммы", "🧮 3. ABC/XYZ-аналитика ОЗМ", "👥 4. RFM-сегментация"], label_visibility="collapsed")

        if page == "🗂️ 1. Загрузка и очистка данных":
            st.markdown("### 🛠️ Панель шагов трансформации (Аналог Power Query)")
            col_pq1, col_pq2, col_pq3 = st.columns(3)
            with col_pq1:
                new_skip = st.number_input("1. Пропустить верхние строки (строк):", min_value=0, max_value=20, value=st.session_state.pq_skip_top, step=1)
                if new_skip != st.session_state.pq_skip_top: st.session_state.pq_skip_top = new_skip; st.cache_data.clear()
            with col_pq2:
                new_merge = st.checkbox("2. Схлопнуть заголовок из 2-х строк", value=st.session_state.pq_merge_headers)
                if new_merge != st.session_state.pq_merge_headers: st.session_state.pq_merge_headers = new_merge; st.cache_data.clear()
            with col_pq3:
                new_foot = st.checkbox("3. Авто-очистка подвала", value=st.session_state.pq_remove_footer)
                if new_foot != st.session_state.pq_remove_footer: st.session_state.pq_remove_footer = new_foot; st.cache_data.clear()
            st.markdown("---")
            
            st.title("🚀 Модуль Предобработки & Импорта Данных")
            tot_rows, tot_cols = len(main_df), len(main_df.columns)
            st.success(f"📊 База сформирована! Строк: {tot_rows:,}, Колонок: {tot_cols}")
            rows_per_page = 50
            total_pages = (tot_rows // rows_per_page) + (1 if tot_rows % rows_per_page > 0 else 0)
            col_p1, col_p2 = st.columns(2)
            with col_p1: current_page = st.number_input(f"Страница (из {total_pages}):", min_value=1, max_value=total_pages, value=1, step=1)
            with col_p2:
                start_idx = (current_page - 1) * rows_per_page
                end_idx = start_idx + rows_per_page
                st.markdown(f"Строки с **{start_idx + 1}** по **{min(end_idx, tot_rows)}** из **{tot_rows:,}**")
            st.dataframe(main_df.iloc[start_idx:end_idx], height=350, use_container_width=True)
            
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer: main_df.to_excel(writer, index=False, sheet_name='Сводные данные')
            st.download_button(label="📥 Скачать базу (Excel .xlsx)", data=excel_buffer.getvalue(), file_name="Сводная_база.xlsx")

        elif page == "📊 2. Executive Диаграммы":
            st.title("📊 Интерактивная BI-Панель Показателей")
            def format_kpi_value(value):
                abs_val = abs(value)
                if abs_val >= 1_000_000_000: return f"{value / 1_000_000_000:,.2f} млрд ₸"
                if abs_val >= 1_000_000: return f"{value / 1_000_000:,.2f} млн ₸"
                if abs_val >= 1_000: return f"{value / 1_000:,.1f} тыс. ₸"
                return f"{value:,.2f}"

            card_cols = st.columns(st.session_state.manual_cards)
            for j in range(st.session_state.manual_cards):
                with card_cols[j % len(card_cols)]:
                    st.markdown(f"**📌 Карточка № {j+1}**")
                    t_col = st.selectbox(f"Заголовок:", all_cols, key=f"c_t_{j}")
                    c_mode = st.selectbox(f"Расчет:", ["Сумма (SUM)", "Среднее (AVERAGE)"], key=f"c_m_{j}")
                    if t_col != "-- Выберите заголовок --":
                        try:
                            df_c = active_df_global.copy()
                            df_c[t_col] = pd.to_numeric(df_c[t_col], errors='coerce').fillna(0)
                            current_val = df_c[t_col].sum() if "Сумма" in c_mode else df_c[t_col].mean()
                            delta_html = ""
                            if st.session_state.get("fl_col_1_global") and st.session_state.fl_col_1_global != "-- Выберите заголовок --" and st.session_state.get("fl_val_1_global") and st.session_state.fl_val_1_global != "-- Все значения --":
                                trend_column = st.session_state.fl_col_1_global
                                current_period = str(st.session_state.fl_val_1_global)
                                all_periods = sorted(list(main_df[trend_column].astype(str).unique()), key=lambda x: int(x) if x.isdigit() else x)
                                if current_period in all_periods:
                                    curr_idx = all_periods.index(current_period)
                                    if curr_idx > 0:
                                        prev_period = all_periods[curr_idx - 1]
                                        df_prev = main_df[main_df[trend_column].astype(str) == str(prev_period)].copy()
                                        if st.session_state.get("fl_col_2_global") and st.session_state.get("fl_val_2_global") and st.session_state.fl_val_2_global != "-- Все значения --":
                                            if st.session_state.fl_col_2_global != trend_column: df_prev = df_prev[df_prev[st.session_state.fl_col_2_global].astype(str) == str(st.session_state.fl_val_2_global)]
                                        df_prev[t_col] = pd.to_numeric(df_prev[t_col], errors='coerce').fillna(0)
                                        prev_val = df_prev[t_col].sum() if "Сумма" in c_mode else df_prev[t_col].mean()
                                        if prev_val > 0:
                                            pct_diff = ((current_val - prev_val) / prev_val) * 100
                                            is_cost = any(w in t_col.lower() for w in ['сумма', 'цена', 'стоимость', 'amount'])
                                            color_trend = "#d9534f" if (pct_diff > 0 if is_cost else pct_diff < 0) else "#5cb85c"
                                            arrow = "▲" if pct_diff > 0 else "▼"
                                            delta_html = f'<div style="color:{color_trend}; font-size:14px; font-weight:bold; margin-top:5px;">{arrow} {pct_diff:+.1f}% <span style="color:#6c757d; font-weight:normal;">к {prev_period}</span></div>'
                            st.markdown(f'<div style="background-color:#f8f9fa; border:1px solid #dee2e6; border-radius:10px; padding:20px; text-align:center; margin-bottom:15px;"><div style="color:#6c757d; font-size:15px; font-weight:500;">{t_col}</div><div style="color:#1f77b4; font-size:26px; font-weight:bold; margin-top:5px;">{format_kpi_value(current_val)}</div>{delta_html}</div>', unsafe_allow_html=True)
                        except: pass
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("➕ Добавить карточку"): st.session_state.manual_cards += 1; st.rerun()
            with cc2:
                if st.session_state.manual_cards > 1: st.session_state.manual_cards -= 1; st.rerun()
            st.markdown("---")
            st.subheader("🛠️ No-Code Конструктор Графиков (Расширенный)")
            for i in range(st.session_state.manual_charts):
                st.markdown(f"##### 📊 Настройка диаграммы № {i+1}")
                c1, c2, c3, c4 = st.columns(4)
                with c1: style = st.selectbox(f"Тип графики:", ["Столбчатая диаграмма (Bar)", "Линейный тренд (Line)", "Кольцевая долей (Donut)", "Диаграмма Водопад (Waterfall)"], key=f"s_{i}")
                with c2: x_ax = st.selectbox(f"Ось X (Категории):", all_cols, key=f"x_{i}")
                with c3: y_ax = st.selectbox(f"Ось Y (Показатели):", all_cols, key=f"y_{i}")
                with c4: color = st.color_picker(f"Цвет элементов:", "#1f77b4", key=f"col_{i}")
                
                with st.expander("🎨 Настройки отображения шрифтов, меток и округления"):
                    col_u1, col_u2, col_u3 = st.columns(3)
                    with col_u1:
                        lbl = st.checkbox("Показывать значения на графике", value=True, key=f"lbl_{i}")
                        f_format = st.selectbox("Формат представления:", ["Числовой с пробелами", "Финансовый (₸)", "Финансовый сжатый (млн/млрд ₸)", "Десятичный дробный"], key=f"fmt_{i}")
                        f_round = st.slider("Округление знаков после запятой:", 0, 4, 0, key=f"rnd_{i}")
                    with col_u2:
                        f_size = st.slider("Размер шрифта надписей (px):", 8, 24, 12, key=f"sz_{i}")
                        f_color = st.color_picker("Цвет шрифта надписей:", "#ffffff" if style != "Линейный тренд (Line)" else "#000000", key=f"fcol_{i}")
                    with col_u3:
                        f_pos = st.selectbox("Расположение надписей:", ["auto", "inside", "outside"], key=f"pos_{i}")
                        horiz = st.checkbox("Горизонтальный вид столбцов", value=False, key=f"h_{i}") if "Bar" in style else False
                        rot = st.slider("🔄 Поворот кольца (градусы):", 0, 360, 0, step=15, key=f"rot_{i}") if "Donut" in style else 0

                if x_ax != "-- Выберите заголовок --" and y_ax != "-- Выберите заголовок --":
                    try:
                        df_chart = active_df_global.copy()
                        df_chart[y_ax] = pd.to_numeric(df_chart[y_ax], errors='coerce').fillna(0)
                        df_chart[x_ax] = df_chart[x_ax].fillna("Не указано").astype(str)
                        df_g = df_chart.groupby(x_ax, as_index=False)[y_ax].sum()
                        if not horiz: df_g = df_g.sort_values(by=y_ax, ascending=False)
                        
                        formatted_text_list = []
                        total_sum_val = df_g[y_ax].sum()
                        
                        def get_formatted_str(value_input):
                            r_v = round(value_input, f_round)
                            if f_format == "Финансовый (₸)": return f"{r_v:,.{f_round}f}".replace(",", " ") + " ₸"
                            elif f_format == "Финансовый сжатый (млн/млрд ₸)":
                                if abs(value_input) >= 1_000_000_000: return f"{value_input / 1_000_000_000:,.2f} млрд ₸"
                                elif abs(value_input) >= 1_000_000: return f"{value_input / 1_000_000:,.2f} млн ₸"
                                else: return f"{value_input / 1_000:,.1f} тыс. ₸"
                            elif f_format == "Десятичный дробный": return f"{r_v:.{f_round}f}"
                            else: return f"{r_v:,.{f_round}f}".replace(",", " ")

                        for val in df_g[y_ax]: formatted_text_list.append(get_formatted_str(val))
                        safe_pos = f_pos
                        if "Donut" in style and f_pos not in ["inside", "outside", "auto"]: safe_pos = "auto"

                        fig = go.Figure()
                        if "Waterfall" in style: fig.add_trace(go.Waterfall(x=list(df_g[x_ax].astype(str)) + ["ИТОГО"], y=list(df_g[y_ax]) + [total_sum_val], text=formatted_text_list + [get_formatted_str(total_sum_val)] if lbl else None, textposition="auto" if safe_pos == "auto" else safe_pos, measure=["relative"] * len(df_g[y_ax]) + ["total"], increasing={"marker": {"color": color}}))
                        elif "Donut" in style: fig.add_trace(go.Pie(labels=df_g[x_ax], values=df_g[y_ax], hole=0.4, rotation=rot, textinfo="label+value" if lbl else "none", textposition="auto" if safe_pos not in ["inside", "outside"] else safe_pos, texttemplate="%{label}<br>%{text}" if lbl else None, text=[get_formatted_str(v) for v in df_g[y_ax]]))
                        elif "Line" in style: fig.add_trace(go.Scatter(x=df_g[x_ax], y=df_g[y_ax], mode="lines+markers+text" if lbl else "lines+markers", text=formatted_text_list if lbl else None, textposition="top center" if safe_pos == "auto" else safe_pos, line=dict(color=color, width=4), marker=dict(size=8)))
                        else: fig.add_trace(go.Bar(y=df_g[x_ax] if horiz else df_g[y_ax], x=df_g[y_ax] if horiz else df_g[x_ax], text=formatted_text_list if lbl else None, textposition="auto" if safe_pos == "auto" else safe_pos, orientation="h" if horiz else "v", marker_color=color))
                        
                        fig.update_layout(xaxis=dict(type='category', tickangle=45 if not horiz else 0), uniformtext=dict(mode="hide", minsize=8))
                        if lbl and "Donut" not in style: fig.update_traces(textfont=dict(size=f_size, color=f_color))
                        st.plotly_chart(fig, use_container_width=True, key=f"p_{i}")
                    except: pass
                st.markdown("<hr style='border:1px dashed #ddd'>", unsafe_allow_html=True)
                
            b1, b2 = st.columns(2)
            with b1:
                if st.button("➕ Добавить диаграмму", key="add_chart_btn"): st.session_state.manual_charts += 1; st.rerun()
            with b2:
                if st.session_state.manual_charts > 1:
                    if st.button("🗑️ Удалить диаграмму", key="del_chart_btn"): st.session_state.manual_charts -= 1; st.rerun()

        elif "3. ABC/XYZ" in page: internal_show_abc_xyz_page(active_df_global)
        elif "4. RFM" in page: internal_show_rfm_page(active_df_global)
else: st.info("Ожидание загрузки любых файлов Excel/CSV для активации BI-панели...")
