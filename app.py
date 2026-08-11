import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="Enterprise BI Конструктор", layout="wide")

# АВТОНОМНЫЙ И СТАБИЛЬНЫЙ ПЕРЕКЛЮЧАТЕЛЬ СТРАНИЦ
st.sidebar.markdown("### 🗺️ Навигация по BI-платформе")
page = st.sidebar.radio(
    "Перейти к разделу:",
    ["🗂️ 1. Загрузка и очистка данных", "📊 2. Конструктор диаграмм"]
)
st.sidebar.markdown("---")

if "manual_charts" not in st.session_state:
    st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state:
    st.session_state.manual_cards = 1
if "active_filter_val" not in st.session_state:
    st.session_state.active_filter_val = None
if "active_filter_col" not in st.session_state:
    st.session_state.active_filter_col = None
if "main_df" not in st.session_state:
    st.session_state.main_df = pd.DataFrame()

# КЭШ-ДВИЖОК С АВТОМАТИЧЕСКОЙ ОЧИСТКОЙ И ВЫРАВНИВАНИЕМ СТРУКТУРЫ ТАБЛИЦ
@st.cache_data
def load_clean_and_merge_files(uploaded_files_list):
    frames_dict = {}
    if not uploaded_files_list:
        return pd.DataFrame(), {}, False
        
    for f in uploaded_files_list:
        try:
            df_i = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f, header=None)
            
            if df_i.shape > 1:
                row0 = df_i.iloc[0].astype(str).str.strip()
                row1 = df_i.iloc[1].astype(str).str.strip()
                is_row1_text = pd.to_numeric(row1, errors='coerce').isna().all()
                
                if is_row1_text:
                    new_cols = []
                    for c0, c1 in zip(row0, row1):
                        c0_c = "" if c0 in ['nan', 'None', 'Unnamed:'] or 'Unnamed' in c0 else c0
                        c1_c = "" if c1 in ['nan', 'None', 'Unnamed:'] or 'Unnamed' in c1 else c1
                        combined_name = f"{c0_c} {c1_c}".strip()
                        new_cols.append(combined_name if combined_name else "Без названия")
                    df_i.columns = new_cols
                    df_i = df_i.iloc[2:].reset_index(drop=True)
                else:
                    df_i.columns = row0
                    df_i = df_i.iloc[1:].reset_index(drop=True)
            
            cleaned_cols = []
            for col in df_i.columns:
                c_str = str(col).replace('nan №', '').replace('№ nan', '').replace('nan', '').replace('Unnamed:', '').strip()
                c_str = re.sub(r'\s+', ' ', c_str).strip()
                cleaned_cols.append(c_str if c_str else "Без названия")
                
            df_i.columns = cleaned_cols
            df_i = df_i.loc[:, ~df_i.columns.str.contains('^Без названия|^Unnamed')]
            df_i = df_i.loc[:, ~df_i.columns.duplicated()]
            
            period_name = f.name.replace(".xlsx", "").replace(".xls", "").replace(".csv", "")
            df_i['Источник (Файл)'] = period_name
            frames_dict[f.name] = df_i
        except:
            pass
            
    if not frames_dict:
        return pd.DataFrame(), {}, False
        
    f_keys = list(frames_dict.keys())
    first_file_name = f_keys[0] if f_keys else ""
    if not first_file_name: 
        return pd.DataFrame(), {}, False
    
    base_cols = set(frames_dict[first_file_name].columns) - {'Источник (Файл)'}
    merge_possible = True
    
    for n, df_c in frames_dict.items():
        c_cols = set(df_c.columns) - {'Источник (Файл)'}
        if not base_cols.intersection(c_cols):
            merge_possible = False
            break
            
    if merge_possible:
        merged_df = pd.concat(frames_dict.values(), ignore_index=True)
        merged_df = merged_df.dropna(how='all')
        return merged_df, frames_dict, True
    else:
        merged_df = pd.concat(frames_dict.values(), ignore_index=True, join='outer')
        merged_df = merged_df.dropna(how='all')
        return merged_df, frames_dict, False
uploaded_files = st.file_uploader("Загрузите один или несколько любых файлов Excel/CSV:", type=["csv", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    main_df, dataframes_dict, is_merged = load_clean_and_merge_files(uploaded_files)
    if not main_df.empty:
        st.session_state.main_df = main_df
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)

        if page == "🗂️ 1. Загрузка и очистка данных":
            st.title("🚀 Модуль Предобработки & Импорта Данных")
            if is_merged: st.success(f"📊 База данных создана! Файлов: {len(uploaded_files)}. Строк: {main_df.shape}")
            else: st.warning(f"⚠️ База объединена через 'Outer Join'. Строк: {main_df.shape}")
                
            st.markdown("### 📋 Структура сводной таблицы (Первые 5 строк):")
            try:
                preview_df = main_df.head(5).copy()
                for c in preview_df.columns: preview_df[c] = preview_df[c].astype(str).fillna("Пусто")
                st.dataframe(preview_df, use_container_width=True)
            except Exception as e: st.error(f"Ошибка превью: {e}")
            
            # УЛЬТРА-СКОРОСТНОЕ БЕЗОШИБОЧНОЕ СКАЧИВАНИЕ В CSV (ОТКРЫВАЕТСЯ В EXCEL)
            try:
                csv_data = main_df.to_csv(index=False, encoding='utf-8-sig', sep=';')
                st.download_button(label="📥 Скачать объединенную базу (Excel CSV)", data=csv_data, file_name="Сводный_отчет_очищенный.csv", mime="text/csv")
            except Exception as de: st.error(f"Ошибка скачивания: {de}")
                
            st.markdown("---")
            st.subheader("🎴 Панель Ключевых Показателей (KPI Карточки)")
            if st.session_state.active_filter_val is not None:
                st.sidebar.markdown(f"**Активный фильтр:**\n`{st.session_state.active_filter_col}` = `{st.session_state.active_filter_val}`")
                if st.sidebar.button("🧹 Очистить все фильтры", type="primary", key="clr_f_mp"): st.session_state.active_filter_val = None; st.session_state.active_filter_col = None; st.rerun()

            df_f = main_df.copy()
            if st.session_state.active_filter_val is not None and st.session_state.active_filter_col in df_f.columns:
                df_f = df_f[df_f[st.session_state.active_filter_col].astype(str) == str(st.session_state.active_filter_val)]

            card_cols = st.columns(st.session_state.manual_cards)
            for j in range(st.session_state.manual_cards):
                with card_cols[j % len(card_cols)]:
                    st.markdown(f"**📌 Карточка № {j+1}**")
                    t_col = st.selectbox(f"Заголовок:", all_cols, key=f"c_t_{j}")
                    c_mode = st.selectbox(f"Расчет:", ["Сумма (SUM)", "Среднее (AVERAGE)"], key=f"c_m_{j}")
                    if t_col != "-- Выберите заголовок --":
                        try:
                            df_c = df_f.copy()
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

        elif page == "📊 2.grid Конструктор диаграмм":
            import plotly.graph_objects as go
            st.title("🛠️ Enterprise No-Code Конструктор Панелей")
            if st.session_state.active_filter_val is not None:
                st.sidebar.markdown(f"**Активный фильтр:**\n`{st.session_state.active_filter_col}` = `{st.session_state.active_filter_val}`")
                if st.sidebar.button("🧹 Очистить все фильтры", type="primary", key="clr_f_cp"): st.session_state.active_filter_val = None; st.session_state.active_filter_col = None; st.rerun()

            df_f = main_df.copy()
            if st.session_state.active_filter_val is not None and st.session_state.active_filter_col in df_f.columns:
                df_f = df_f[df_f[st.session_state.active_filter_col].astype(str) == str(st.session_state.active_filter_val)]

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
                    rot = st.slider("🔄 Поворот (градусы):", 0, 360, 0, step=15, key=f"r_{i}") if "Donut" in style else 0

                if x_ax != "-- Выберите заголовок --" and y_ax != "-- Выберите заголовок --":
                    try:
                        df_m = df_f.copy()
                        df_m[y_ax] = pd.to_numeric(df_m[y_ax], errors='coerce').fillna(0)
                        df_g = df_m.groupby(x_ax, as_index=False)[y_ax].sum()
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
                        ev = st.plotly_chart(fig, use_container_width=True, key=f"p_{i}", on_select="rerun")
                        if ev and "selection" in ev and "points" in ev["selection"] and len(ev["selection"]["points"]) > 0:
                            pt = ev["selection"]["points"]
                            val = pt["pointNumber"] if "pointNumber" in pt else (pt["label"] if "label" in pt else (pt["x"] if "x" in pt else pt["y"]))
                            if "Donut" in style: val = df_g.iloc[val][x_ax]
                            if val is not None and str(val) != "ИТОГО": st.session_state.active_filter_val = val; st.session_state.active_filter_col = x_ax; st.rerun()
                    except Exception as ex: st.error(f"Ошибка: {ex}")
                else: st.info("ℹ️ Выберите категории для построения графика")
                st.markdown("<hr style='border:1px dashed #ddd'>", unsafe_allow_html=True)
                
            b1, b2 = st.columns(2)
            with b1:
                if st.button("➕ Добавить диаграмму"): st.session_state.manual_charts += 1; st.rerun()
            with b2:
                if st.session_state.manual_charts > 1:
                    if st.button("🗑️ Удалить диаграмму"): st.session_state.manual_charts -= 1; st.rerun()
else: st.info("Ожидание загрузки любых файлов Excel/CSV для активации BI-панели...")
