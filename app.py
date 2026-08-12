import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="Enterprise BI Конструктор (Power Query)", layout="wide")

# АВТОНОМНЫЙ И СТАБИЛЬНЫЙ ПЕРЕКЛЮЧАТЕЛЬ СТРАНИЦ В БОКОВОЙ ПАНЕЛИ
st.sidebar.markdown("### 🗺️ Навигация по BI-платформе")
page = st.sidebar.radio(
    "Перейти к разделу:",
    ["🗂️ 1. Загрузка и очистка данных", "📊 2. Конструктор диаграмм"]
)
st.sidebar.markdown("---")

if "manual_charts" not in st.session_state: st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state: st.session_state.manual_cards = 1
if "active_filter_val" not in st.session_state: st.session_state.active_filter_val = None
if "active_filter_col" not in st.session_state: st.session_state.active_filter_col = None
if "main_df" not in st.session_state: st.session_state.main_df = pd.DataFrame()
if "uploaded_backup" not in st.session_state: st.session_state.uploaded_backup = None

if "pq_skip_top" not in st.session_state: st.session_state.pq_skip_top = 0
if "pq_merge_headers" not in st.session_state: st.session_state.pq_merge_headers = False
if "pq_remove_footer" not in st.session_state: st.session_state.pq_remove_footer = True
# МОДЕРНИЗИРОВАННЫЙ ДВИЖОК POWER QUERY С ФУНКЦИЕЙ ЗАПОЛНЕНИЯ ПРОПУСКОВ И ВЫРАВНИВАНИЯ
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
                row0 = list(df_raw.iloc[0].astype(str).str.strip())
                row1 = list(df_raw.iloc[1].astype(str).str.strip())
                
                # Имитируем Power Query "Fill Down" логику
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
                df_raw.columns = df_raw.iloc[0].astype(str).str.strip()
                df_raw = df_raw.iloc[1:].reset_index(drop=True)
                
            # 3. Шаг PQ: Очистка имен столбцов от мусорных артефактов Excel и пробелов
            cleaned_cols = []
            for idx, col in enumerate(df_raw.columns):
                c_str = str(col).replace('nan №', '').replace('№ nan', '').replace('nan', '').replace('Unnamed:', '').strip()
                c_str = re.sub(r'\s+', ' ', c_str).strip()
                cleaned_cols.append(c_str if c_str else f"Столбец_{idx+1}")
            df_raw.columns = cleaned_cols
            
            df_raw = df_raw.loc[:, ~df_raw.columns.str.contains('^Без названия|^Unnamed')]
            df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()]
            
            # 4. Шаг PQ: Удаление текстовых итоговых подвалов
            if remove_footer:
                for text_col in df_raw.columns:
                    mask_footer = df_raw[text_col].astype(str).str.lower().str.contains('итого|всего|сумма|подпись|сдал|принял', na=False)
                    df_raw = df_raw[~mask_footer]
            
            df_raw = df_raw.dropna(how='all')
            period_name = f.name.replace(".xlsx", "").replace(".xls", "").replace(".csv", "")
            df_raw['Источник (Файл)'] = period_name
            frames_dict[f.name] = df_raw
        except:
            pass
            
    if not frames_dict: return pd.DataFrame(), False
    
    # 5. Шаг PQ: Сшивание (Outer Join) разнородных файлов
    merged_df = pd.concat(frames_dict.values(), ignore_index=True, join='outer')
    
    # Заполнение пропусков и зануление пустых ячеек, возникших из-за разных структур отчетов
    for col in merged_df.columns:
        if col == 'Источник (Файл)': continue
        col_clean_slug = col.lower()
        is_numeric_col = any(w in col_clean_slug for w in ['сумма', 'количество', 'цена', 'стоимост', 'кол-во', 'цена'])
        
        if is_numeric_col:
            merged_df[col] = merged_df[col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0.0)
        else:
            merged_df[col] = merged_df[col].fillna("Не указано").astype(str).str.strip()
            merged_df[col] = merged_df[col].replace(['nan', 'None', '', 'Пусто'], "Не указано")
            
    merged_df = merged_df.dropna(how='all')
    return merged_df, True
uploaded_files = st.file_uploader("Загрузите один или несколько любых файлов Excel/CSV:", type=["csv", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    st.session_state.uploaded_backup = uploaded_files
elif st.session_state.uploaded_backup:
    uploaded_files = st.session_state.uploaded_backup

if uploaded_files:
    if page == "🗂️ 1. Загрузка и очистка данных":
        st.markdown("### 🛠️ Панель шагов трансформации (Аналог Power Query)")
        col_pq1, col_pq2, col_pq3 = st.columns(3)
        with col_pq1:
            st.session_state.pq_skip_top = st.number_input("1. Пропустить верхние строки (строк):", min_value=0, max_value=20, value=st.session_state.pq_skip_top, step=1)
        with col_pq2:
            st.session_state.pq_merge_headers = st.checkbox("2. Схлопнуть составной заголовок (из 2-х строк)", value=st.session_state.pq_merge_headers)
        with col_pq3:
            st.session_state.pq_remove_footer = st.checkbox("3. Авто-очистка подвала (удалить Итоги и подписи)", value=st.session_state.pq_remove_footer)
        st.markdown("---")

    main_df, is_merged = power_query_clean_engine(uploaded_files, st.session_state.pq_skip_top, st.session_state.pq_merge_headers, st.session_state.pq_remove_footer)
    
    if not main_df.empty:
        st.session_state.main_df = main_df
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)

        # ---------------- ОТРИСОВКА РАЗДЕЛА 1 ----------------
        if page == "🗂️ 1. Загрузка и очистка данных":
            st.title("🚀 Модуль Предобработки & Импорта Данных")
            st.success(f"📊 Идеальная сводная база сформирована! Файлов: {len(uploaded_files)}. Строк: {main_df.shape}, Колонок: {main_df.shape}")
            
            st.markdown("### 📋 Результат очистки (Полный интерактивный просмотр всей сводной таблицы):")
            try:
                full_view_df = main_df.copy()
                st.dataframe(full_view_df, height=450, use_container_width=True)
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
        # ---------------- ОТРИСОВКА РАЗДЕЛА 2 ----------------
        elif page == "📊 2. Конструктор диаграмм":
            import plotly.graph_objects as go
            st.title("📊 Интерактивная BI-Панель Показателей")
            st.sidebar.success("🟢 Интерактивный BI-движок активен!")
            if st.session_state.active_filter_val is not None:
                st.sidebar.markdown(f"**Активный фильтр:**\n`{st.session_state.active_filter_col}` = `{st.session_state.active_filter_val}`")
                if st.sidebar.button("🧹 Очистить все фильтры", type="primary", key="clr_f_cp"): 
                    st.session_state.active_filter_val = None
                    st.session_state.active_filter_col = None; st.rerun()

            df_cards = main_df.copy()
            if st.session_state.active_filter_val is not None and st.session_state.active_filter_col in df_cards.columns:
                df_cards = df_cards[df_cards[st.session_state.active_filter_col].astype(str) == str(st.session_state.active_filter_val)]

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
                        df_chart = main_df.copy()
                        if st.session_state.active_filter_val is not None and st.session_state.active_filter_col in df_chart.columns:
                            if st.session_state.active_filter_col != x_ax:
                                df_chart = df_chart[df_chart[st.session_state.active_filter_col].astype(str) == str(st.session_state.active_filter_val)]
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
                        fig.update_layout(xaxis=dict(tickangle=45 if not horiz else 0), uniformtext=dict(mode="hide", minsize=8), clickmode="event+select")
                        
                        # НАДЁЖНЫЙ ИЗВЛЕКАТЕЛЬ КЛЮЧЕЙ: 100% защита от фоновых ошибок
                        ev_i = st.plotly_chart(fig, use_container_width=True, key=f"p_{i}", on_select="rerun")
                        if ev_i and "selection" in ev_i and "selection" in ev_i["selection"] and "points" in ev_i["selection"]["selection"] and len(ev_i["selection"]["selection"]["points"]) > 0:
                            pt_list = ev_i["selection"]["selection"]["points"]
                            if isinstance(pt_list, list) and len(pt_list) > 0:
                                first_pt = pt_list[0]
                                if isinstance(first_pt, dict):
                                    val = first_pt.get('x', first_pt.get('label', first_pt.get('y')))
                                    if val is not None and str(val) != "ИТОГО":
                                        st.session_state.active_filter_val = val
                                        st.session_state.active_filter_col = x_ax
                                        st.rerun()
                    except Exception as ex: pass
                else: st.info("ℹ️ Выберите категории для построения графика")
                st.markdown("<hr style='border:1px dashed #ddd'>", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            with b1:
                if st.button("➕ Добавить диаграмму"): st.session_state.manual_charts += 1; st.rerun()
            with b2:
                if st.session_state.manual_charts > 1:
                    if st.button("🗑️ Удалить диаграмму"): st.session_state.manual_charts -= 1; st.rerun()
else: st.info("Ожидание загрузки любых файлов Excel/CSV для активации BI-панели...")
