import streamlit as st
import pandas as pd
import io
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# МАТРИЦА ABC/XYZ-АНАЛИЗА (ИЗОЛИРОВАННАЯ ФУНКЦИЯ)
def internal_show_abc_xyz_page(filtered_df):
    st.title("🧮 Универсальный Конструктор матриц ABC/XYZ")
    if filtered_df.empty: return st.info("ℹ️ Выборка пуста. Загрузите файлы.")
    df, available_cols = filtered_df.copy(), list(filtered_df.columns)
    c1, c2, c3 = st.columns(3)
    with c1: abc_target = st.selectbox("1. Объект анализа:", [c for c in available_cols if c not in ['Сумма', 'Количество']], key="abc_t")
    with c2: abc_value = st.selectbox("2. Критерий масштаба:", [c for c in ['Сумма', 'Количество'] if c in available_cols] + available_cols, key="abc_v")
    with c3: xyz_period = st.selectbox("3. Шкала времени:", [c for c in available_cols if c != abc_target], key="xyz_p")
    a_lim = st.slider("Граница группы A (%):", 50, 90, 80, key="abc_s")
    x_lim = st.slider("Граница группы X (KV ≤ %):", 5, 20, 10, key="xyz_s")
    try:
        df[abc_value] = pd.to_numeric(df[abc_value], errors='coerce').fillna(0.0)
        df = df[(df[abc_target].astype(str).str.strip() != "") & (df[xyz_period].astype(str).str.strip() != "")]
        df_abc = df.groupby(abc_target, as_index=False)[abc_value].sum().sort_values(by=abc_value, ascending=False).reset_index(drop=True)
        total_sum = df_abc[abc_value].sum()
        if total_sum == 0: return
        df_abc['Cum'] = (df_abc[abc_value] / total_sum).cumsum() * 100
        df_abc['Class_ABC'] = df_abc['Cum'].map(lambda x: 'A' if x <= a_lim else ('B' if x <= a_lim + 15 else 'C'))
        p_matrix = df.groupby([abc_target, xyz_period])[abc_value].sum().unstack(fill_value=0.0)
        xyz_res = []
        for name, rows in p_matrix.iterrows():
            m, s = rows.mean(), rows.std(ddof=1) if len(rows) > 1 else 0.0
            kv = (s / m) * 100 if m > 0 and np.count_nonzero(rows) > 1 else 999.0
            xyz_res.append({abc_target: name, 'KV': kv, 'Класс XYZ': 'X' if kv <= x_lim else ('Y' if kv <= x_lim + 15 else 'Z')})
        df_m = pd.merge(df_abc[[abc_target, abc_value, 'Class_ABC']], pd.DataFrame(xyz_res), on=abc_target)
        pivot_m = df_m.pivot_table(index='Class_ABC', columns='Класс XYZ', values=abc_target, aggfunc='count', fill_value=0)
        for l in ['A','B','C']: 
            if l not in pivot_m.index: pivot_m.loc[l] = 0
        for l in ['X','Y','Z']: 
            if l not in pivot_m.columns: pivot_m[l] = 0
        pivot_m = pivot_m.loc[['A','B','C'], ['X','Y','Z']]
        mc1, mc2 = st.columns(2)
        with mc1: st.dataframe(pivot_m, use_container_width=True)
        with mc2: st.plotly_chart(px.imshow(pivot_m, text_auto=True, color_continuous_scale="Blues"), use_container_width=True)
        st.dataframe(df_m.sort_values(by=abc_value, ascending=False), use_container_width=True)
    except Exception as e: st.error(f"Ошибка ABC: {e}")
# НЕУБИВАЕМЫЙ RFM-АНАЛИЗ И КОНСТРУКТОР ГРАФИКОВ PLOTLY
def internal_show_rfm_page(filtered_df):
    st.title("👥 Модуль RFM-сегментации номенклатуры")
    if filtered_df.empty: return st.info("ℹ️ Выборка пуста. Загрузите файлы.")
    df = filtered_df.copy()
    t_ozm = 'ОЗМ' if 'ОЗМ' in df.columns else df.columns[0]
    t_sum = 'Сумма' if 'Сумма' in df.columns else df.select_dtypes(include=[np.number]).columns[0]
    try:
        df[t_sum] = pd.to_numeric(df[t_sum], errors='coerce').fillna(0.0)
        rfm = df.groupby(t_ozm).agg(F=(df.columns[0], 'count'), M=(t_sum, 'sum')).reset_index()
        rfm['F_Score'] = pd.qcut(rfm['F'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str) if len(rfm) >= 3 and rfm['F'].nunique() > 1 else '1'
        rfm['M_Score'] = pd.qcut(rfm['M'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str) if len(rfm) >= 3 and rfm['M'].nunique() > 1 else '1'
        rfm['RFM'] = rfm['F_Score'] + rfm['M_Score']
        seg_counts = rfm.groupby('RFM').size().reset_index(name='Количество ОЗМ')
        st.plotly_chart(px.bar(seg_counts, x='RFM', y='Количество ОЗМ', text_auto=True, title="📊 Распределение RFM-сегментов", color='RFM', color_continuous_scale="Purples"), use_container_width=True)
        st.dataframe(rfm.sort_values(by='M', ascending=False), use_container_width=True)
    except Exception as rfe: st.error(f"Ошибка RFM: {rfe}")

def render_custom_chart(active_df, x_ax, y_ax, style, color, lbl, f_format, f_round, f_size, f_color, f_pos, horiz, rot, top_limit, i):
    try:
        df_c = active_df.copy()
        df_c[y_ax] = pd.to_numeric(df_c[y_ax], errors='coerce').fillna(0)
        df_g = df_c.groupby(x_ax, as_index=False)[y_ax].sum().sort_values(by=y_ax, ascending=False).head(top_limit)
        if horiz: df_g = df_g.sort_values(by=y_ax, ascending=True)
        txt = [f"{round(v, f_round):,}".replace(",", " ") + (" ₸" if "Финанс" in f_format else "") for v in df_g[y_ax]]
        fig = go.Figure()
        if "Waterfall" in style: fig.add_trace(go.Waterfall(x=list(df_g[x_ax].astype(str)) + ["ИТОГО"], y=list(df_g[y_ax]) + [df_g[y_ax].sum()], text=txt + [f"{df_g[y_ax].sum():,}"], textposition="auto", measure=["relative"] * len(df_g[y_ax]) + ["total"], increasing={"marker": {"color": color}}))
        elif "Donut" in style: fig.add_trace(go.Pie(labels=df_g[x_ax], values=df_g[y_ax], hole=0.4, rotation=rot, textinfo="label+value" if lbl else "none", text=txt))
        elif "Line" in style: fig.add_trace(go.Scatter(x=df_g[x_ax], y=df_g[y_ax], mode="lines+markers+text" if lbl else "lines+markers", text=txt, textposition="top center", line=dict(color=color, width=4)))
        else: fig.add_trace(go.Bar(y=df_g[x_ax] if horiz else df_g[y_ax], x=df_g[y_ax] if horiz else df_g[x_ax], text=txt if lbl else None, textposition=f_pos, orientation="h" if horiz else "v", marker_color=color))
        fig.update_layout(xaxis=dict(type='category', tickangle=45 if not horiz else 0))
        st.plotly_chart(fig, use_container_width=True, key=f"p_{i}")
    except: pass
# МОДУЛЬ ОЧИСТКИ ТАБЛИЦ POWER QUERY НА СВЕРХБЫСТРОМ ДВИЖКЕ RUST CALAMINE
def power_query_clean_engine(uploaded_files_list):
    frames = {}
    for f in uploaded_files_list:
        try:
            df = pd.read_csv(f, dtype=str) if f.name.endswith('.csv') else pd.read_excel(f, dtype=str, engine='calamine')
            df.columns = [str(c).strip() for c in df.columns]
            mapped = []
            for col in df.columns:
                c_low = col.lower()
                if any(w in c_low for w in ['озм', 'код материала', 'номенклатур']): mapped.append('ОЗМ')
                elif any(w in c_low for w in ['наименование', 'материал']): mapped.append('Наименование материала')
                elif any(w in c_low for w in ['количество', 'кол-во', 'объем']): mapped.append('Количество')
                elif any(w in c_low for w in ['сумма', 'стоимость', 'цена']): mapped.append('Сумма')
                else: mapped.append(col)
            df.columns = mapped
            df = df.loc[:, ~df.columns.str.contains('^Без названия|^Unnamed|^Unnamed:')].loc[:, ~df.columns.duplicated()]
            df['Источник (Файл)'] = f.name.replace(".xlsx", "").replace(".csv", "")
            frames[f.name] = df.dropna(how='all')
        except: pass
    if not frames: return pd.DataFrame()
    res = pd.concat(frames.values(), ignore_index=True, join='outer')
    for c in ['Количество', 'Сумма']:
        if c in res.columns: res[c] = pd.to_numeric(res[c].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.'), errors='coerce').fillna(0.0)
    return res.dropna(how='all')

if "manual_charts" not in st.session_state: st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state: st.session_state.manual_cards = 1
if "main_df" not in st.session_state: st.session_state.main_df = pd.DataFrame()

uploaded_files = st.file_uploader("Загрузите файлы Excel/CSV:", type=["csv", "xlsx"], accept_multiple_files=True)
if not uploaded_files: st.session_state.main_df = pd.DataFrame()
if uploaded_files:
    if st.session_state.main_df.empty:
        with st.spinner("⏳ Идёт глубокая Rust Calamine сборка данных..."):
            calc_df = power_query_clean_engine(uploaded_files)
            if not calc_df.empty: st.session_state.main_df = calc_df
    main_df = st.session_state.main_df
    if not main_df.empty:
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)
        f_col1 = st.sidebar.selectbox("Поле среза №1:", all_cols, key="fl_c1")
        act_df = main_df.copy()
        if f_col1 != "-- Выберите заголовок --":
            u_v1 = ["-- Все значения --"] + list(act_df[f_col1].astype(str).unique())
            f_v1 = st.sidebar.selectbox("Значение среза №1:", u_v1, key="fl_v1")
            if f_v1 != "-- Все значения --": act_df = act_df[act_df[f_col1].astype(str) == str(f_v1)]
        
        page = st.sidebar.radio("Навигация:", ["🗂️ 1. Загрузка и очистка данных", "📊 2. Executive Диаграммы", "🧮 3. ABC/XYZ-аналитика ОЗМ", "👥 4. RFM-сегментация"])
        
        if "1. Загрузка" in page:
            st.success(f"📊 База сформирована! Строк: {len(main_df):,}")
            cp = st.number_input(f"Страница (из {(len(main_df) // 50) + 1}):", min_value=1, max_value=(len(main_df) // 50) + 1, value=1, step=1)
            st.dataframe(main_df.iloc[(cp - 1) * 50: cp * 50], height=350, use_container_width=True)
        elif "2. Executive" in page:
            st.title("📊 Интерактивная BI-Панель Показателей")
            card_cols = st.columns(st.session_state.manual_cards)
            for j in range(st.session_state.manual_cards):
                with card_cols[j % len(card_cols)]:
                    st.markdown(f"**📌 Карточка № {j+1}**")
                    t_col = st.selectbox(f"Поле:", all_cols, key=f"c_t_{j}")
                    c_mode = st.selectbox(f"Агрегация:", ["Сумма", "Среднее"], key=f"c_m_{j}")
                    with st.expander("🎨 Настройки"):
                        c_fmt = st.selectbox("Формат:", ["Числовой", "Финансовый (₸)", "Сжатый (млн/млрд)"], key=f"c_f_{j}")
                        c_rnd = st.slider("Округление:", 0, 4, 2, key=f"c_r_{j}")
                        c_sz = st.slider("Шрифт (px):", 16, 48, 28, key=f"c_s_{j}")
                    if t_col != "-- Выберите заголовок --":
                        df_c = act_df.copy()
                        df_c[t_col] = pd.to_numeric(df_c[t_col], errors='coerce').fillna(0)
                        cv = df_c[t_col].sum() if "Сумма" in c_mode else df_c[t_col].mean()
                        if c_fmt == "Финансовый (₸)": lbl = f"{round(cv, c_rnd):,}".replace(",", " ") + " ₸"
                        elif c_fmt == "Сжатый (млн/млрд)":
                            if abs(cv) >= 1_000_000_000: lbl = f"{cv / 1_000_000_000:,.2f} млрд ₸"
                            else: lbl = f"{cv / 1_000_000:,.2f} млн ₸"
                        else: lbl = f"{round(cv, c_rnd):,}".replace(",", " ")
                        st.markdown(f'<div style="background-color:#f8f9fa; border:1px solid #dee2e6; border-radius:10px; padding:20px; text-align:center; margin-bottom:15px;"><div style="color:#6c757d; font-size:14px;">{t_col}</div><div style="color:#1f77b4; font-size:{c_sz}px; font-weight:bold;">{lbl}</div></div>', unsafe_allow_html=True)
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("➕ Добавить карточку"): st.session_state.manual_cards += 1; st.rerun()
            with cc2:
                if st.session_state.manual_cards > 1: st.session_state.manual_cards -= 1; st.rerun()
            st.markdown("---")
            st.subheader("🛠️ No-Code Конструктор Графиков")
            for i in range(st.session_state.manual_charts):
                c1, c2, c3, c4 = st.columns(4)
                with c1: style = st.selectbox(f"Тип №{i+1}:", ["Столбчатая диаграмма (Bar)", "Линейный тренд (Line)", "Кольцевая долей (Donut)", "Диаграмма Водопад (Waterfall)"], key=f"s_{i}")
                with c2: x_ax = st.selectbox(f"Ось X №{i+1}:", all_cols, key=f"x_{i}")
                with c3: y_ax = st.selectbox(f"Ось Y №{i+1}:", all_cols, key=f"y_{i}")
                with c4: color = st.color_picker(f"Цвет №{i+1}:", "#1f77b4", key=f"col_{i}")
                with st.expander("🎨 Настройки надписей"):
                    cu1, cu2, cu3 = st.columns(3)
                    with cu1:
                        lbl_g = st.checkbox("Показывать значения", value=True, key=f"lbl_{i}")
                        f_format = st.selectbox("Формат:", ["Числовой", "Финансовый (₸)"], key=f"fmt_{i}")
                        f_round = st.slider("Округление:", 0, 4, 0, key=f"rnd_{i}")
                    with cu2:
                        f_size = st.slider("Шрифт (px):", 8, 24, 12, key=f"sz_{i}")
                        f_color = st.color_picker("Цвет:", "#000000", key=f"fcol_{i}")
                    with cu3:
                        f_pos = st.selectbox("Положение:", ["auto", "inside", "outside"], key=f"pos_{i}")
                        horiz = st.checkbox("Горизонтально", value=False, key=f"h_{i}") if "Bar" in style else False
                        rot = st.slider("🔄 Поворот:", 0, 360, 0, step=15, key=f"rot_{i}") if "Donut" in style else 0
                        top_limit = st.slider("🔝 ТОП позиций:", 5, 200, 15, key=f"top_{i}")
                if x_ax != "-- Выберите заголовок --" and y_ax != "-- Выберите заголовок --":
                    render_custom_chart(act_df, x_ax, y_ax, style, color, lbl_g, f_format, f_round, f_size, f_color, f_pos, horiz, rot, top_limit, i)
                st.markdown("<hr style='border:1px dashed #ddd'>", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            with b1:
                if st.button("➕ Добавить диаграмму"): st.session_state.manual_charts += 1; st.rerun()
            with b2:
                if st.session_state.manual_charts > 1:
                    if st.button("🗑️ Удалить диаграмму"): st.session_state.manual_charts -= 1; st.rerun()
        elif "3. ABC/XYZ" in page: internal_show_abc_xyz_page(act_df)
        elif "4. RFM" in page: internal_show_rfm_page(act_df)
else: st.info("Ожидание загрузки любых файлов Excel/CSV...")
