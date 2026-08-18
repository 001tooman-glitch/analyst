import streamlit as st
import pandas as pd
import io
import re
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# АВТОНОМНЫЙ БЛОК 1: УНИВЕРСАЛЬНЫЙ No-Code КОНСТРУКТОР ABC/XYZ
def internal_show_abc_xyz_page(filtered_df):
    st.title("🧮 Универсальный Конструктор матриц ABC/XYZ")
    if filtered_df.empty:
        st.info("ℹ️ Текущая выборка пуста. Пожалуйста, загрузите файлы.")
        return
    df = filtered_df.copy()
    available_cols = list(df.columns)
    
    st.markdown("### 🎯 Настройка параметров анализа")
    col_sel1, col_sel2, col_sel3 = st.columns(3)
    with col_sel1: abc_target = st.selectbox("1. Объект анализа (Что смотрим):", [c for c in available_cols if c not in ['Сумма', 'Количество']], key="abc_t_target")
    with col_sel2: abc_value = st.selectbox("2. Критерий масштаба (ABC):", [c for c in ['Сумма', 'Количество'] if c in available_cols] + available_cols, key="abc_v_value")
    with col_sel3: xyz_period = st.selectbox("3. Периоды/Шкала времени (XYZ):", [c for c in available_cols if c != abc_target], key="xyz_p_period")
    
    col_abc1, col_abc2 = st.columns(2)
    with col_abc1:
        a_limit = st.slider("Граница группы A (% от объема):", 50, 90, 80, key="abc_sl_1")
        b_limit = st.slider("Граница группы B (следующие % объема):", 5, 25, 15, key="abc_sl_2")
    with col_abc2:
        x_limit = st.slider("Граница группы X (Коэфф. вариации KV ≤ %):", 5, 20, 10, key="xyz_sl_1")
        y_limit = st.slider("Граница группы Y (Коэфф. вариации KV ≤ %):", 15, 50, 25, key="xyz_sl_2")

    try:
        df[abc_value] = pd.to_numeric(df[abc_value], errors='coerce').fillna(0.0)
        df[abc_target] = df[abc_target].fillna("Не указано").astype(str).str.strip()
        df[xyz_period] = df[xyz_period].fillna("Не указано").astype(str).str.strip()
        df = df[(df[abc_target] != "") & (df[xyz_period] != "")]

        df_abc = df.groupby(abc_target, as_index=False)[abc_value].sum().sort_values(by=abc_value, ascending=False).reset_index(drop=True)
        total_sum = df_abc[abc_value].sum()
        if total_sum == 0: return
            
        df_abc['Доля'] = df_abc[abc_value] / total_sum
        df_abc['Кумулятивная доля'] = df_abc['Доля'].cumsum() * 100
        df_abc['Class_ABC'] = df_abc['Кумулятивная доля'].map(lambda x: 'A' if x <= a_limit else ('B' if x <= (a_limit + b_limit) else 'C'))
        period_matrix = df.groupby([abc_target, xyz_period])[abc_value].sum().unstack(fill_value=0.0)
        xyz_results = []
        for obj_name, rows in period_matrix.iterrows():
            mean_val = rows.mean()
            std_val = rows.std(ddof=1) if len(rows) > 1 else 0.0
            if mean_val > 0 and np.count_nonzero(rows) > 1:
                kv = (std_val / mean_val) * 100
                класс_xyz = 'X' if kv <= x_limit else ('Y' if kv <= y_limit else 'Z')
            else: kv, класс_xyz = 999.0, 'Z'
            xyz_results.append({abc_target: obj_name, 'KV': kv, 'Класс XYZ': класс_xyz})
            
        df_xyz = pd.DataFrame(xyz_results)
        df_matrix = pd.merge(df_abc[[abc_target, abc_value, 'Class_ABC']], df_xyz, on=abc_target)
        df_matrix['Матрица ABC/XYZ'] = df_matrix['Class_ABC'] + df_matrix['Класс XYZ']

        st.subheader("📊 Итоговая 9-польная матрица управления закупками")
        pivot_matrix = df_matrix.pivot_table(index='Class_ABC', columns='Класс XYZ', values=abc_target, aggfunc='count', fill_value=0)
        for letter in ['A', 'B', 'C']:
            if letter not in pivot_matrix.index: pivot_matrix.loc[letter] = 0
        for letter in ['X', 'Y', 'Z']:
            if letter not in pivot_matrix.columns: pivot_matrix[letter] = 0
        pivot_matrix = pivot_matrix.loc[['A', 'B', 'C'], ['X', 'Y', 'Z']]
        
        col_m1, col_m2 = st.columns(2)
        with col_m1: st.dataframe(pivot_matrix, use_container_width=True)
        with col_m2:
            fig_heat = px.imshow(pivot_matrix, text_auto=True, x=['X', 'Y', 'Z'], y=['A', 'B', 'C'], color_continuous_scale="Blues")
            fig_heat.update_layout(height=220, margin=dict(l=5, r=5, t=5, b=5))
            st.plotly_chart(fig_heat, use_container_width=True)
        st.dataframe(df_matrix.sort_values(by=abc_value, ascending=False), use_container_width=True)
    except Exception as e: st.error(f"❌ Ошибка вычисления матрицы: {e}")

# АВТОНОМНЫЙ БЛОК 2: RFM СЕГМЕНТАЦИЯ
def internal_show_rfm_page(filtered_df):
    st.title("👥 Модуль RFM-сегментации номенклатуры")
    if filtered_df.empty: return
    df = filtered_df.copy()
    if not all(col in df.columns for col in ['ОЗМ', 'Сумма', 'Источник (Файл)']): return
    rfm_df = df.groupby('ОЗМ').agg(Frequency=('Источник (Файл)', 'count'), Monetary=('Сумма', 'sum')).reset_index()
    if len(rfm_df) >= 3:
        rfm_df['F_Score'] = pd.qcut(rfm_df['Frequency'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        rfm_df['M_Score'] = pd.qcut(rfm_df['Monetary'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
    else: rfm_df['F_Score'], rfm_df['M_Score'] = '1', '1'
    rfm_df['RFM_Segment'] = rfm_df['F_Score'] + rfm_df['M_Score']
    seg_counts = rfm_df.groupby('RFM_Segment').size().reset_index(name='Количество ОЗМ')
    st.plotly_chart(px.bar(seg_counts, x='RFM_Segment', y='Количество ОЗМ', text_auto=True, color='RFM_Segment'), use_container_width=True)
# АВТОНОМНЫЙ БЛОК 3: ПОЛНОСТЬЮ КАСТОМИЗИРУЕМЫЙ ГРАФИЧЕСКИЙ ДВИЖОК PLOTLY
def render_custom_chart(active_df, x_ax, y_ax, style, color, lbl, f_format, f_round, f_size, f_color, f_pos, horiz, rot, top_limit, i):
    try:
        df_chart = active_df.copy()
        df_chart[y_ax] = pd.to_numeric(df_chart[y_ax], errors='coerce').fillna(0)
        df_chart[x_ax] = df_chart[x_ax].fillna("Не указано").astype(str)
        
        # ТОП-ОГРАНИЧЕНИЕ: Возвращен встроенный фильтр для очистки графиков от каши
        df_g = df_chart.groupby(x_ax, as_index=False)[y_ax].sum().sort_values(by=y_ax, ascending=False).head(top_limit)
        if horiz: df_g = df_g.sort_values(by=y_ax, ascending=True)
        
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
        safe_pos = f_pos if ("Donut" not in style or f_pos in ["inside", "outside", "auto"]) else "auto"

        fig = go.Figure()
        if "Waterfall" in style: fig.add_trace(go.Waterfall(x=list(df_g[x_ax].astype(str)) + ["ИТОГО"], y=list(df_g[y_ax]) + [total_sum_val], text=formatted_text_list + [get_formatted_str(total_sum_val)] if lbl else None, textposition="auto" if safe_pos == "auto" else safe_pos, measure=["relative"] * len(df_g[y_ax]) + ["total"], increasing={"marker": {"color": color}}))
        elif "Donut" in style: fig.add_trace(go.Pie(labels=df_g[x_ax], values=df_g[y_ax], hole=0.4, rotation=rot, textinfo="label+value" if lbl else "none", textposition=safe_pos, texttemplate="%{label}<br>%{text}" if lbl else None, text=[get_formatted_str(v) for v in df_g[y_ax]]))
        elif "Line" in style: fig.add_trace(go.Scatter(x=df_g[x_ax], y=df_g[y_ax], mode="lines+markers+text" if lbl else "lines+markers", text=formatted_text_list if lbl else None, textposition="top center" if safe_pos == "auto" else safe_pos, line=dict(color=color, width=4), marker=dict(size=8)))
        else: fig.add_trace(go.Bar(y=df_g[x_ax] if horiz else df_g[y_ax], x=df_g[y_ax] if horiz else df_g[x_ax], text=formatted_text_list if lbl else None, textposition="auto" if safe_pos == "auto" else safe_pos, orientation="h" if horiz else "v", marker_color=color))
        
        fig.update_layout(xaxis=dict(type='category', tickangle=45 if not horiz else 0), uniformtext=dict(mode="hide", minsize=8))
        if lbl and "Donut" not in style: fig.update_traces(textfont=dict(size=f_size, color=f_color))
        st.plotly_chart(fig, use_container_width=True, key=f"p_{i}")
    except: pass
# АВТОНОМНЫЙ БЛОК 4: ИМПОРТ И ПРЕДОБРАБОТКА ДАННЫХ RUST CALAMINE
def power_query_clean_engine(uploaded_files_list, skip_top, merge_headers, remove_footer):
    frames_dict = {}
    if not uploaded_files_list: return pd.DataFrame(), False
    for f in uploaded_files_list:
        try:
            if f.name.endswith('.csv'): df_raw = pd.read_csv(f, dtype=str)
            else: df_raw = pd.read_excel(f, dtype=str, engine='calamine')
            if df_raw.empty: continue
            if skip_top > 0 and skip_top < len(df_raw): df_raw = df_raw.iloc[skip_top:].reset_index(drop=True)
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
    front_cols = [c for c in ['ОЗМ', 'Наименование материала', 'Количество', 'Сумма', 'Источник (Файл)'] if c in merged_df.columns]
    other_cols = [c for c in merged_df.columns if c not in front_cols]
    return merged_df[front_cols + other_cols], True

if "manual_charts" not in st.session_state: st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state: st.session_state.manual_cards = 1
if "pq_skip_top" not in st.session_state: st.session_state.pq_skip_top = 0
if "pq_merge_headers" not in st.session_state: st.session_state.pq_merge_headers = False
if "pq_remove_footer" not in st.session_state: st.session_state.pq_remove_footer = True
if "main_df" not in st.session_state: st.session_state.main_df = pd.DataFrame()

uploaded_files = st.file_uploader("Загрузите файлы Excel/CSV:", type=["csv", "xlsx"], accept_multiple_files=True)
if not uploaded_files: st.session_state.main_df = pd.DataFrame()
if uploaded_files:
    if st.session_state.main_df.empty:
        with st.spinner("⏳ Идёт глубокая Rust Calamine очистка данных... Пожалуйста, подождите."):
            calculated_df, is_merged = power_query_clean_engine(uploaded_files, st.session_state.pq_skip_top, st.session_state.pq_merge_headers, st.session_state.pq_remove_footer)
            if not calculated_df.empty: st.session_state.main_df = calculated_df

    main_df = st.session_state.main_df
    if not main_df.empty:
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)
        st.sidebar.subheader("🎚️ Глобальные Фильтры")
        filter_col_1 = st.sidebar.selectbox("Поле среза №1:", all_cols, key="fl_col_1_global")
        active_df_global = main_df.copy()
        
        if filter_col_1 != "-- Выберите заголовок --":
            unique_vals_1 = ["-- Все значения --"] + list(active_df_global[filter_col_1].astype(str).unique())
            filter_val_1 = st.sidebar.selectbox("Значение среза №1:", unique_vals_1, key="fl_val_1_global")
            if filter_val_1 != "-- Все значения --": active_df_global = active_df_global[active_df_global[filter_col_1].astype(str) == str(filter_val_1)]
        
        filter_col_2 = st.sidebar.selectbox("Поле среза №2:", all_cols, key="fl_col_2_global")
        if filter_col_2 != "-- Выберите заголовок --":
            unique_vals_2 = ["-- Все значения --"] + list(active_df_global[filter_col_2].astype(str).unique())
            filter_val_2 = st.sidebar.selectbox("Значение среза №2:", unique_vals_2, key="fl_val_2_global")
            if filter_val_2 != "-- Все значения --": active_df_global = active_df_global[active_df_global[filter_col_2].astype(str) == str(filter_val_2)]

        st.sidebar.markdown("---")
        page = st.sidebar.radio("Перейти к разделу:", ["🗂️ 1. Загрузка и очистка данных", "📊 2. Executive Диаграммы", "🧮 3. ABC/XYZ-аналитика ОЗМ", "👥 4. RFM-сегментация"], label_visibility="collapsed")

        if "1. Загрузка" in page:
            col_pq1, col_pq2, col_pq3 = st.columns(3)
            with col_pq1:
                new_skip = st.number_input("1. Пропустить верхние строки (строк):", min_value=0, max_value=20, value=st.session_state.pq_skip_top, step=1)
                if new_skip != st.session_state.pq_skip_top: st.session_state.pq_skip_top = new_skip; st.session_state.main_df = pd.DataFrame(); st.rerun()
            with col_pq2:
                new_merge = st.checkbox("2. Схлопнуть заголовок из 2-х строк", value=st.session_state.pq_merge_headers)
                if new_merge != st.session_state.pq_merge_headers: st.session_state.pq_merge_headers = new_merge; st.session_state.main_df = pd.DataFrame(); st.rerun()
            with col_pq3:
                new_foot = st.checkbox("3. Авто-очистка подвала", value=st.session_state.pq_remove_footer)
                if new_foot != st.session_state.pq_remove_footer: st.session_state.pq_remove_footer = new_foot; st.session_state.main_df = pd.DataFrame(); st.rerun()
            
            tot_rows, tot_cols = len(main_df), len(main_df.columns)
            st.success(f"📊 База сформирована! Строк: {tot_rows:,}")
            current_page = st.number_input(f"Страница (из {(tot_rows // 50) + 1}):", min_value=1, max_value=(tot_rows // 50) + 1, value=1, step=1)
            st.dataframe(main_df.iloc[(current_page - 1) * 50: current_page * 50], height=350, use_container_width=True)

        elif "2. Executive" in page:
            st.title("📊 Интерактивная BI-Панель Показателей")
            card_cols = st.columns(st.session_state.manual_cards)
            for j in range(st.session_state.manual_cards):
                with card_cols[j % len(card_cols)]:
                    t_col = st.selectbox(f"Заголовок карточки №{j+1}:", all_cols, key=f"c_t_{j}")
                    c_mode = st.selectbox(f"Расчет карточки №{j+1}:", ["Сумма (SUM)", "Среднее (AVERAGE)"], key=f"c_m_{j}")
                    if t_col != "-- Выберите заголовок --":
                        try:
                            df_c = active_df_global.copy()
                            df_c[t_col] = pd.to_numeric(df_c[t_col], errors='coerce').fillna(0)
                            cv = df_c[t_col].sum() if "Сумма" in c_mode else df_c[t_col].mean()
                            st.markdown(f'<div style="background-color:#f8f9fa; border:1px solid #dee2e6; border-radius:10px; padding:20px; text-align:center; margin-bottom:15px;"><div style="color:#6c757d; font-size:15px;">{t_col}</div><div style="color:#1f77b4; font-size:26px; font-weight:bold; margin-top:5px;">{cv:,.2f}</div></div>', unsafe_allow_html=True)
                        except: pass
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("➕ Добавить карточку"): st.session_state.manual_cards += 1; st.rerun()
            with cc2:
                if st.session_state.manual_cards > 1: st.session_state.manual_cards -= 1; st.rerun()

            st.markdown("---")
            st.subheader("🛠️ No-Code Конструктор Графиков")
            for i in range(st.session_state.manual_charts):
                st.markdown(f"##### 📊 Настройка диаграммы № {i+1}")
                c1, c2, c3, c4 = st.columns(4)
                with c1: style = st.selectbox(f"Тип графики №{i+1}:", ["Столбчатая диаграмма (Bar)", "Линейный тренд (Line)", "Кольцевая долей (Donut)", "Диаграмма Водопад (Waterfall)"], key=f"s_{i}")
                with c2: x_ax = st.selectbox(f"Ось X №{i+1}:", all_cols, key=f"x_{i}")
                with c3: y_ax = st.selectbox(f"Ось Y №{i+1}:", all_cols, key=f"y_{i}")
                with c4: color = st.color_picker(f"Цвет №{i+1}:", "#1f77b4", key=f"col_{i}")
                
                # ВСЕ НАСТРОЙКИ НАДПИСЕЙ И ШРИФТОВ СНОВА ДОСТУПНЫ!
                with st.expander("🎨 Настройки отображения шрифтов, меток и округления"):
                    col_u1, col_u2, col_u3 = st.columns(3)
                    with col_u1:
                        lbl = st.checkbox("Показывать значения на графике", value=True, key=f"lbl_{i}")
                        f_format = st.selectbox("Формат представления:", ["Числовой с пробелами", "Финансовый (₸)", "Финансовый сжатый (млн/млрд ₸)", "Десятичный дробный"], key=f"fmt_{i}")
                        f_round = st.slider("Округление знаков после запятой:", 0, 4, 0, key=f"rnd_{i}")
                    with col_u2:
                        f_size = st.slider("Размер шрифта надписей (px):", 8, 24, 12, key=f"sz_{i}")
                        f_color = st.color_picker("Цвет шрифта надписей:", "#000000", key=f"fcol_{i}")
                    with col_u3:
                        f_pos = st.selectbox("Расположение надписей:", ["auto", "inside", "outside"], key=f"pos_{i}")
                        horiz = st.checkbox("Горизонтальный вид столбцов", value=False, key=f"h_{i}") if "Bar" in style else False
                        rot = st.slider("🔄 Поворот кольца (градусы):", 0, 360, 0, step=15, key=f"rot_{i}") if "Donut" in style else 0
                        top_limit = st.slider("🔝 Ограничить вывод (Показать только ТОП позиций):", 5, 200, 15, key=f"top_{i}")

                if x_ax != "-- Выберите заголовок --" and y_ax != "-- Выберите заголовок --":
                    render_custom_chart(active_df_global, x_ax, y_ax, style, color, lbl, f_format, f_round, f_size, f_color, f_pos, horiz, rot, top_limit, i)
                st.markdown("<hr style='border:1px dashed #ddd'>", unsafe_allow_html=True)
                
            b1, b2 = st.columns(2)
            with b1:
                if st.button("➕ Добавить диаграмму"): st.session_state.manual_charts += 1; st.rerun()
            with b2:
                if st.session_state.manual_charts > 1:
                    if st.button("🗑️ Удалить диаграмму"): st.session_state.manual_charts -= 1; st.rerun()

        elif "3. ABC/XYZ" in page: internal_show_abc_xyz_page(active_df_global)
        elif "4. RFM" in page: internal_show_rfm_page(active_df_global)
else: st.info("Ожидание загрузки любых файлов Excel/CSV...")
