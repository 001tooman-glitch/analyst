import streamlit as st
import pandas as pd
import io
import json
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from google import genai
from google.genai import types

st.set_page_config(layout="wide", page_title="BI Custom Platform")

if "main_df" not in st.session_state: st.session_state.main_df = pd.DataFrame()
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "category_mapping_dict" not in st.session_state: st.session_state.category_mapping_dict = {}
if "raw_file_frames" not in st.session_state: st.session_state.raw_file_frames = {}
if "files_processed" not in st.session_state: st.session_state.files_processed = False

if "mapped_target_col" not in st.session_state: st.session_state.mapped_target_col = "-- Выберите --"
if "mapped_value_col" not in st.session_state: st.session_state.mapped_value_col = "-- Выберите --"
if "mapped_time_col" not in st.session_state: st.session_state.mapped_time_col = "-- Выберите --"

if "cards_presets" not in st.session_state:
    st.session_state.cards_presets = [{
        "t_col_metric": "-- Выберите заголовок --", "c_mode": "Сумма", 
        "group_col": "-- Без фильтра --", "filter_value": None,
        "c_fmt": "Числовой", "c_curr_text": "$", "c_rnd": 2,
        "c_size": 28, "c_align": "left", "c_color_main": "#0f172a", "c_color_sub": "#64748b"
    }]

if "charts_presets" not in st.session_state:
    st.session_state.charts_presets = [{
        "style": "Столбчатая диаграмма (Bar)", "x_ax": "-- Выберите заголовок --", "y_ax_list": [], 
        "color": "#1f77b4", "forecast_color": "#ef4444", "lbl_g": True, "f_format": "Числовой", "f_round": 0, "f_curr_text": "$",
        "f_size": 14, "f_color": "#000000", "f_pos": "auto", "horiz": False, "rot": 0, "top_limit": 15,
        "d_fmt": "ГГГГ-ММ-ДД (Исходный ISO)", "f_cast": 0
    }]

def add_card_preset_cb():
    st.session_state.cards_presets.append({
        "t_col_metric": "-- Выберите заголовок --", "c_mode": "Сумма", 
        "group_col": "-- Без фильтра --", "filter_value": None,
        "c_fmt": "Числовой", "c_curr_text": "$", "c_rnd": 2,
        "c_size": 28, "c_align": "left", "c_color_main": "#0f172a", "c_color_sub": "#64748b"
    })

def remove_card_preset_cb():
    if len(st.session_state.cards_presets) > 1: st.session_state.cards_presets.pop()

def add_chart_preset_cb():
    st.session_state.charts_presets.append({
        "style": "Столбчатая диаграмма (Bar)", "x_ax": "-- Выберите заголовок --", "y_ax_list": [], 
        "color": "#1f77b4", "forecast_color": "#ef4444", "lbl_g": True, "f_format": "Числовой", "f_round": 0, "f_curr_text": "$",
        "f_size": 14, "f_color": "#000000", "f_pos": "auto", "horiz": False, "rot": 0, "top_limit": 15,
        "d_fmt": "ГГГГ-ММ-ДД (Исходный ISO)", "f_cast": 0
    })

def remove_chart_preset_cb():
    if len(st.session_state.charts_presets) > 1: st.session_state.charts_presets.pop()

def inject_custom_css():
    st.html("""
        <style>
            html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, label {
                font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
            }
            [data-testid="stMainSpaceBlockContainer"] { background-color: #f8fafc !important; }
            .stApp { background-color: #f8fafc !important; color: #0f172a !important; }
            .stButton>button {
                background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%) !important; color: #ffffff !important;
                border-radius: 10px !important; border: none !important;
            }
        </style>
    """)

inject_custom_css()
def power_query_clean_engine(uploaded_files_list):
    file_registry = {}
    if not uploaded_files_list: return file_registry
    for f_item in uploaded_files_list:
        try:
            df = pd.read_csv(io.StringIO(f_item.getvalue().decode('utf-8'))) if f_item.name.endswith('.csv') else pd.read_excel(f_item, engine='openpyxl')
            df = df.loc[:, ~df.columns.str.contains('^Без названия|^Unnamed|^Unnamed:')].loc[:, ~df.columns.duplicated()]
            for col in df.columns:
                if any(x in str(col).lower() for x in ['date', 'дата', 'время', 'time', 'период']):
                    parsed_dates = pd.to_datetime(df[col], errors='coerce')
                    if parsed_dates.notna().sum() > 0: df[col] = parsed_dates
            file_registry[f_item.name] = df.dropna(how='all')
        except Exception as file_err: st.sidebar.error(f"Ошибка файла {f_item.name}: {file_err}")
    return file_registry

def ai_generate_text_report(pivot_matrix_df, report_type="ABC/XYZ", data_context="Расход", api_key=None):
    if not api_key: return st.warning("⚠️ Введите API Key Gemini в сайдбаре для активации ИИ.")
    try:
        client = genai.Client(api_key=api_key)
        system_instruction = f"Ты — бизнес-аналитик. Напиши краткий отчет по матрице {report_type}. Контекст: {data_context}."
        with st.spinner("🔮 ИИ интерпретирует матричные слои..."):
            response = client.models.generate_content(
                model='gemini-3.5-flash', contents=f"Данные матрицы:\n{pivot_matrix_df.to_string()}", 
                config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.2)
            )
            st.markdown("---")
            st.markdown(f"### 📝 Аналитический ИИ-Отчет ({report_type})")
            st.info(response.text)
    except Exception as report_err: st.error(f"❌ Ошибка ИИ: {report_err}")
@st.cache_data
def calculate_abc_xyz(df, t_col, v_col, p_col, a_lim, x_lim):
    df_clean = df.copy()
    df_clean[v_col] = pd.to_numeric(df_clean[v_col], errors='coerce').fillna(0.0)
    df_clean = df_clean[(df_clean[t_col].astype(str).str.strip() != "") & (df_clean[p_col].notna())]
    df_abc = df_clean.groupby(t_col, as_index=False)[v_col].sum().sort_values(by=v_col, ascending=False).reset_index(drop=True)
    total_sum = df_abc[v_col].sum()
    if total_sum == 0: return None, None, "Сумма значений равна нулю."
    df_abc['Cum'] = (df_abc[v_col] / total_sum).cumsum() * 100
    df_abc['Class_ABC'] = df_abc['Cum'].map(lambda x: 'A' if x <= a_lim else ('B' if x <= a_lim + 15 else 'C'))
    p_matrix = df_clean.groupby([t_col, p_col])[v_col].sum().unstack(fill_value=0.0)
    xyz_res = []
    for name, rows in p_matrix.iterrows():
        m = rows.mean()
        s = rows.std(ddof=1) if len(rows) > 1 else 0.0
        kv = (s / m) * 100 if m > 0 and np.count_nonzero(rows) > 1 else 999.0
        xyz_res.append({t_col: name, 'KV': kv, 'Класс XYZ': 'X' if kv <= x_lim else ('Y' if kv <= x_lim + 15 else 'Z')})
    df_m = pd.merge(df_abc[[t_col, v_col, 'Class_ABC']], pd.DataFrame(xyz_res), on=t_col)
    raw_pivot = df_m.pivot_table(index='Class_ABC', columns='Класс XYZ', values=t_col, aggfunc='count', fill_value=0)
    pivot_m = pd.DataFrame(0, index=['A', 'B', 'C'], columns=['X', 'Y', 'Z'])
    for idx in pivot_m.index:
        for col in pivot_m.columns:
            if idx in raw_pivot.index and col in raw_pivot.columns: pivot_m.loc[idx, col] = raw_pivot.loc[idx, col]
    return df_m, pivot_m, None

def internal_show_abc_xyz_page(filtered_df, api_key, data_context):
    st.title("🧮 Конструктор матриц ABC/XYZ")
    t_col, v_col, p_col = st.session_state.mapped_target_col, st.session_state.mapped_value_col, st.session_state.mapped_time_col
    if t_col == "-- Выберите --" or v_col == "-- Выберите --" or p_col == "-- Выберите --":
        return st.warning("⚠️ Сначала настройте ручной маппинг колонок в сайдбаре!")
    a_lim = st.slider("Доля класса А (%):", 50, 90, 80, key="abc_s_slider")
    x_lim = st.slider("Граница класса X (KV ≤ %):", 5, 50, 10, key="xyz_s_slider")
    df_m, pivot_m, err = calculate_abc_xyz(filtered_df, t_col, v_col, p_col, a_lim, x_lim)
    if err: return st.warning(err)
    c_m1, c_m2 = st.columns(2)
    with c_m1: st.dataframe(pivot_m, use_container_width=True)
    with c_m2: st.plotly_chart(px.imshow(pivot_m, text_auto=True, color_continuous_scale="Blues"), use_container_width=True)
    if st.button("🔮 Сгенерировать ИИ-отчет по результатам", key="ai_report_abc_btn"):
        ai_generate_text_report(pivot_m, report_type="ABC/XYZ", data_context=data_context, api_key=api_key)
    st.dataframe(df_m.sort_values(by=v_col, ascending=False), use_container_width=True)

@st.cache_data
def calculate_rfm(df, t_col, v_col, p_col):
    df_clean = df.copy()
    df_clean[v_col] = pd.to_numeric(df_clean[v_col], errors='coerce').fillna(0.0)
    df_clean[p_col] = pd.to_datetime(df_clean[p_col], errors='coerce')
    max_date = df_clean[p_col].max() if df_clean[p_col].notna().any() else pd.Timestamp.now()
    rfm = df_clean.groupby(str(t_col)).agg(R_days=(p_col, lambda x: (max_date - x.max()).days if x.notna().any() else 999), F=(v_col, 'count'), M=(v_col, 'sum')).reset_index()
    rfm.columns = ['Объект Анализа', 'R', 'F', 'M']
    if len(rfm) < 3: return None, None, "Недостаточно элементов."
    rfm['R_Score'] = pd.qcut(rfm['R'].rank(method='first'), 3, labels=['1', '2', '3'], duplicates='drop').astype(str)
    rfm['F_Score'] = pd.qcut(rfm['F'].rank(method='first'), 3, labels=['3', '2', '1'], duplicates='drop').astype(str)
    rfm['M_Score'] = pd.qcut(rfm['M'].rank(method='first'), 3, labels=['3', '2', '1'], duplicates='drop').astype(str)
    rfm['RFM'] = rfm['R_Score'] + rfm['F_Score'] + rfm['M_Score']
    seg_counts = rfm.groupby('RFM').size().reset_index(name='Количество элементов')
    return rfm, seg_counts, None

def internal_show_rfm_page(filtered_df, api_key, data_context):
    st.title("👥 Модуль многомерной RFM-сегментации")
    t_col, v_col, p_col = st.session_state.mapped_target_col, st.session_state.mapped_value_col, st.session_state.mapped_time_col
    if t_col == "-- Выберите --" or v_col == "-- Выберите --" or p_col == "-- Выберите --":
        return st.warning("⚠️ Настройте маппинг колонок!")
    rfm, seg_counts, err = calculate_rfm(filtered_df, t_col, v_col, p_col)
    if err: return st.warning(err)
    st.plotly_chart(px.bar(seg_counts, x='RFM', y='Количество элементов', text_auto=True), use_container_width=True)
    if st.button("👥 Сгенерировать ИИ-отчет по сегментам", key="ai_report_rfm_btn"):
        ai_generate_text_report(seg_counts, report_type=f"RFM ({t_col})", data_context=data_context, api_key=api_key)
    st.dataframe(rfm.sort_values(by='M', ascending=False), use_container_width=True)
def render_custom_chart(active_df, x_ax, y_ax_list, style, base_color, lbl, f_format, f_round, f_size, f_color, f_pos, horiz, rot, top_limit, i, date_format_type="ГГГГ-ММ-ДД (Исходный ISO)", custom_currency="", forecast_periods=0, forecast_custom_color="#ef4444"):
    try:
        if not y_ax_list: return
        df_c = active_df.copy()
        for y_col in y_ax_list: df_c[y_col] = pd.to_numeric(df_c[y_col], errors='coerce').fillna(0)
        curr_suffix = f" {str(custom_currency).strip()}" if str(custom_currency).strip() else ""

        def get_formatted_text(value_array):
            labels = []
            for v in value_array:
                if f_format == "Финансовый": labels.append(f"{v:,.{f_round}f}".replace(",", " ") + curr_suffix)
                elif f_format == "Сжатый (млн/млрд)":
                    if abs(v) >= 1_000_000_000: labels.append(f"{v / 1_000_000_000:,.{f_round}f}".replace(",", " ") + f" млрд{custom_currency}")
                    else: labels.append(f"{v / 1_000_000:,.{f_round}f}".replace(",", " ") + f" млн{custom_currency}")
                else: labels.append(f"{v:,.{f_round}f}".replace(",", " "))
            return labels

        is_year_col = "год" in str(x_ax).lower() or "year" in str(x_ax).lower()
        converted_dates = pd.to_datetime(df_c[x_ax], errors='coerce')
        is_date_axis = converted_dates.notna().sum() > (0.5 * len(df_c)) and not is_year_col
        fmt_string = {"ГГГГ-ММ-ДД (Исходный ISO)": "%Y-%m-%d", "ММ.ГГГГ (01.2014)": "%m.%Y", "Месяц ГГГГ (Янв 2014)": "%b %Y", "ДД.ММ.ГГГГ (15.01.2014)": "%d.%m.%Y", "ГГГГ (2014)": "%Y"}.get(date_format_type, "%Y-%m-%d")

        if is_date_axis:
            df_c['_datetime_clean_'] = converted_dates
            df_c = df_c.dropna(subset=['_datetime_clean_'])
            df_g = df_c.groupby('_datetime_clean_', as_index=False)[y_ax_list].sum().sort_values(by='_datetime_clean_').reset_index(drop=True)
            raw_dates_list = df_g['_datetime_clean_'].tolist()
            x_vals = df_g['_datetime_clean_'].dt.strftime(fmt_string).astype(str).tolist()
        else:
            df_g = df_c.groupby(x_ax, as_index=False)[y_ax_list].sum().sort_values(by=x_ax if is_year_col or pd.api.types.is_numeric_dtype(df_c[x_ax]) else y_ax_list, ascending=True).head(top_limit).reset_index(drop=True)
            x_vals = df_g[x_ax].astype(str).tolist()

        fig = go.Figure()
        palette = [base_color, "#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]

        if "Линейный" in style or (is_date_axis and "Столбчатая" not in style and "Кольцевая" not in style and "Водопад" not in style):
            for idx, y_col in enumerate(y_ax_list):
                y_vals = df_g[y_col].tolist()
                fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode="lines+markers+text" if lbl else "lines+markers", name=f"{y_col}", line=dict(color=palette[idx % len(palette)], width=4), text=get_formatted_text(y_vals) if lbl else None, textfont=dict(size=f_size, color=f_color)))
        elif "Столбчатая" in style:
            sp = f_pos if f_pos in ["inside", "outside", "auto"] else "auto"
            for idx, y_col in enumerate(y_ax_list):
                if horiz: fig.add_trace(go.Bar(y=x_vals, x=df_g[y_col], text=get_formatted_text(df_g[y_col].values) if lbl else None, textposition=sp, orientation="h", name=y_col, marker_color=palette[idx % len(palette)], textfont=dict(size=f_size, color=f_color)))
                else: fig.add_trace(go.Bar(x=x_vals, y=df_g[y_col], text=get_formatted_text(df_g[y_col].values) if lbl else None, textposition=sp, orientation="v", name=y_col, marker_color=palette[idx % len(palette)], textfont=dict(size=f_size, color=f_color)))
            fig.update_layout(barmode="group")
        elif "Кольцевая" in style:
            target_y = y_ax_list[0] if isinstance(y_ax_list, list) and len(y_ax_list) > 0 else y_ax_list
            if target_y: fig.add_trace(go.Pie(labels=x_vals, values=df_g[target_y], hole=0.4, rotation=rot, text=get_formatted_text(df_g[target_y].values), textfont=dict(size=f_size, color=f_color)))
        elif "Водопад" in style:
            target_y = y_ax_list[0] if isinstance(y_ax_list, list) and len(y_ax_list) > 0 else y_ax_list
            if target_y: fig.add_trace(go.Waterfall(x=list(x_vals) + ["ИТОГО"], y=list(df_g[target_y]) + [df_g[target_y].sum()], measure=["relative"] * len(df_g[target_y]) + ["total"], increasing={"marker": {"color": base_color}}, textfont=dict(size=f_size, color=f_color)))

        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=40, r=40, t=50, b=50))
        st.plotly_chart(fig, use_container_width=True, key=f"p_fixed_{i}")
    except Exception as chart_err: st.error(f"Ошибка графика №{i+1}: {chart_err}")
def render_ai_sidebar_chat(current_dataframe, api_key, context_mode_text):
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💬 Чат-ассистент к данным")
    if current_dataframe.empty: return st.sidebar.info("Загрузите файлы для активации чата.")
    if st.sidebar.button("🧹 Очистить историю чата", key="clear_chat_btn"):
        st.session_state.chat_history = []
        st.sidebar.success("История очищена!")
        st.rerun()
    chat_container = st.sidebar.container(height=250)
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]): st.write(message["content"])
    if user_prompt := st.sidebar.chat_input("Спросить ИИ...", key="chat_input_text"):
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with chat_container, st.chat_message("user"): st.write(user_prompt)
        if not api_key: return st.sidebar.error("Укажите API Key.")
        try:
            client = genai.Client(api_key=api_key)
            columns_schema = {str(col): str(current_dataframe[col].dtype) for col in current_dataframe.columns}
            sys_prompt = f"Ты — BI-аналитик. Сопоставь вопрос со схемой {json.dumps(columns_schema, ensure_ascii=False)} и верни СТРОГО JSON: {{\"target_column\": \"имя\", \"operation\": \"sum/mean/count\"}}. Никакого markdown."
            with chat_container, st.chat_message("assistant"), st.spinner("🤖 Вычисляю..."):
                response = client.models.generate_content(model='gemini-3.5-flash', contents=f"Вопрос: {user_prompt}", config=types.GenerateContentConfig(system_instruction=sys_prompt, temperature=0.1, response_mime_type="application/json"))
                pq = json.loads(response.text.strip())
                tc, op = pq.get("target_column"), pq.get("operation")
                if tc in current_dataframe.columns:
                    ser = pd.to_numeric(current_dataframe[tc], errors='coerce').fillna(0)
                    res_val = ser.sum() if op == "sum" else (ser.mean() if op == "mean" else ser.count())
                    inter_data = f"Результат вычисления ({op}) для '{tc}' равен: {res_val}"
                else: inter_data = "Требуется текстовый анализ контекста."
                final_res = client.models.generate_content(model='gemini-3.5-flash', contents=f"Метрики: {inter_data}\nВопрос: '{user_prompt}'", config=types.GenerateContentConfig(system_instruction=f"Ты — BI-аналитик. Переведи цифру на понятный язык. Контекст: {context_mode_text}.", temperature=0.2))
                st.write(final_res.text)
            st.session_state.chat_history.append({"role": "assistant", "content": final_res.text})
        except Exception as chat_err: st.sidebar.error(f"Ошибка чата: {chat_err}")

def render_cross_file_mapping_ui(file_registry):
    st.markdown("---")
    st.markdown("### 🔀 Панель ручного сопоставления разнородных структур")
    file_names = list(file_registry.keys())
    if not file_names: return st.info("ℹ️ Загрузите файлы.")
    cf1, cf2 = st.columns(2)
    with cf1: f1_name = st.selectbox("Базовый Layer 1:", file_names, key="cross_file_select_1")
    with cf2: f2_name = st.selectbox("Сравниваемый Layer 2:", file_names, key="cross_file_select_2")
    df1, df2 = file_registry[f1_name], file_registry[f2_name]
    c1, c2 = st.columns(2)
    with c1: f1_col = st.selectbox(f"Категория 1 (`{f1_name}`):", ["-- Выберите --"] + list(df1.columns), key="cf_ui_1")
    with c2: f2_col = st.selectbox(f"Категория 2 (`{f2_name}`):", ["-- Выберите --"] + list(df2.columns), key="cf_ui_2")
    if f1_col == "-- Выберите --" or f2_col == "-- Выберите --": return st.warning("⚠️ Укажите оба столбца.")
    unique_f1_vals = sorted(list(df1[f1_col].dropna().astype(str).unique()))
    unique_f2_vals = ["-- Не сопоставлено --"] + sorted(list(df2[f2_col].dropna().astype(str).unique()))
    mapping_rows = [{"Элемент Слоя 1": v, "Эквивалент в Слое 2": st.session_state.category_mapping_dict.get(v, "-- Не сопоставлено --")} for v in unique_f1_vals]
    edited_df = st.data_editor(pd.DataFrame(mapping_rows), column_config={"Элемент Слоя 1": st.column_config.TextColumn("Слой 1", disabled=True), "Эквивалент в Слое 2": st.column_config.SelectboxColumn("Слой 2", options=unique_f2_vals, required=True)}, hide_index=True, use_container_width=True)
    temp_mapping = {row["Элемент Слоя 1"]: row["Эквивалент в Слое 2"] for _, row in edited_df.iterrows() if row["Эквивалент в Слое 2"] != "-- Не сопоставлено --"}
    st.session_state.category_mapping_dict = temp_mapping
    if st.button("🚀 Применить кросс-маппинг"):
        clean_df1, clean_df2 = df1.copy(), df2.copy()
        clean_df1['Унифицированная_Категория'], clean_df1['Тип_Слоя'] = clean_df1[f1_col].astype(str), "Слой_1"
        rev_map = {v: k for k, v in temp_mapping.items()}
        clean_df2['Унифицированная_Категория'] = clean_df2[f2_col].astype(str).map(rev_map)
        clean_df2['Тип_Слоя'] = "Слой_2"
        st.session_state.main_df = pd.concat([clean_df1, clean_df2.dropna(subset=['Унифицированная_Категория'])], ignore_index=True)
        st.session_state.files_processed = True
        st.rerun()
st.sidebar.markdown("### 🤖 Настройки ИИ-Слой")
gemini_api_key = st.sidebar.text_input("Введите Gemini API Key:", type="password")
ai_context_mode = st.sidebar.selectbox("Контекст для AI:", ["📊 Продажи / Ритейл", "📊 Сравнительный кросс-анализ", "📅 Закупки", "📦 Запасы"])
uploaded_files = st.sidebar.file_uploader("Загрузите файлы Excel/CSV:", type=["csv", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    current_file_names = [f.name for f in uploaded_files]
    if current_file_names != list(st.session_state.raw_file_frames.keys()):
        with st.spinner("⏳ Обновление базы данных..."):
            st.session_state.raw_file_frames = power_query_clean_engine(uploaded_files)
            if "Сравнительный" not in ai_context_mode and st.session_state.raw_file_frames:
                st.session_state.main_df = pd.concat(list(st.session_state.raw_file_frames.values()), ignore_index=True)
                st.session_state.files_processed = True
                st.rerun()

if "Сравнительный" in ai_context_mode and st.session_state.raw_file_frames and st.session_state.main_df.empty:
    render_cross_file_mapping_ui(st.session_state.raw_file_frames)

main_df = st.session_state.main_df
if st.session_state.files_processed and not main_df.empty:
    render_ai_sidebar_chat(main_df, gemini_api_key, ai_context_mode)
    if st.sidebar.button("♻️ Сбросить базу данных"):
        st.session_state.main_df, st.session_state.raw_file_frames, st.session_state.chat_history = pd.DataFrame(), {}, []
        st.session_state.mapped_target_col, st.session_state.mapped_value_col, st.session_state.mapped_time_col = "-- Выберите --", "-- Выберите --", "-- Выберите --"
        st.session_state.files_processed = False
        st.rerun()
        
    st.sidebar.markdown("### 🎛️ Ручной маппинг шкал")
    raw_headers = list(main_df.columns)
    st.session_state.mapped_target_col = st.sidebar.selectbox("🔑 КЛЮЧ:", ["-- Выберите --"] + raw_headers, index=(["-- Выберите --"] + raw_headers).index(st.session_state.mapped_target_col) if st.session_state.mapped_target_col in (["-- Выберите --"] + raw_headers) else 0)
    st.session_state.mapped_value_col = st.sidebar.selectbox("💰 ОБЪЕМ:", ["-- Выберите --"] + raw_headers, index=(["-- Выберите --"] + raw_headers).index(st.session_state.mapped_value_col) if st.session_state.mapped_value_col in (["-- Выберите --"] + raw_headers) else 0)
    st.session_state.mapped_time_col = st.sidebar.selectbox("📅 ВРЕМЯ:", ["-- Выберите --"] + raw_headers, index=(["-- Выберите --"] + raw_headers).index(st.session_state.mapped_time_col) if st.session_state.mapped_time_col in (["-- Выберите --"] + raw_headers) else 0)
    
    if st.session_state.mapped_value_col != "-- Выберите --":
        main_df[st.session_state.mapped_value_col] = pd.to_numeric(main_df[st.session_state.mapped_value_col].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.'), errors='coerce').fillna(0.0)

    all_cols_list = ["-- Выберите заголовок --"] + raw_headers
    page = st.sidebar.radio("Перейти:", ["🗂️ Данные", "📊 EXECUTIVE", "🗮️ ABC/XYZ", "👥 RFM"])
    
    if page == "🗂️ Данные":
        st.success(f"📊 Строк: {len(main_df):,}")
        cp = st.number_input("Страница:", min_value=1, value=1)
        st.dataframe(main_df.iloc[(cp - 1) * 50: cp * 50], height=350, use_container_width=True)
    elif page == "📊 EXECUTIVE":
        canvas_col, control_col = st.columns([0.7, 0.3])
        active_filtered_df = main_df.copy()
        
        with control_col:
            st.subheader("⚙️ Панель BI")
            if st.session_state.mapped_time_col in main_df.columns and st.session_state.mapped_time_col != "-- Выберите --":
                active_filtered_df['_datetime_filter_internal_'] = pd.to_datetime(active_filtered_df[st.session_state.mapped_time_col], errors='coerce')
                min_d, max_d = active_filtered_df['_datetime_filter_internal_'].min(), active_filtered_df['_datetime_filter_internal_'].max()
                if not pd.isna(min_d) and not pd.isna(max_d):
                    chosen_dates = st.date_input("Интервал:", value=(min_d.date(), max_d.date()), key="global_bi_date_range_picker")
                    if isinstance(chosen_dates, tuple) and len(chosen_dates) == 2:
                        active_filtered_df = active_filtered_df[(active_filtered_df['_datetime_filter_internal_'].dt.date >= chosen_dates[0]) & (active_filtered_df['_datetime_filter_internal_'].dt.date <= chosen_dates[1])]
            
            st.button("➕ Добавить карту", on_click=add_card_preset_cb)
            st.button("🗑️ Удалить карту", on_click=remove_card_preset_cb)
            selected_card_idx = st.selectbox("Выбор карты:", range(len(st.session_state.cards_presets)))
            cp = st.session_state.cards_presets[selected_card_idx]
            cp["t_col_metric"] = st.selectbox("Метрика:", all_cols_list, index=all_cols_list.index(cp["t_col_metric"]) if cp["t_col_metric"] in all_cols_list else 0, key=f"c_t_{selected_card_idx}")
            cp["c_mode"] = st.selectbox("Агрегация:", ["Сумма", "Среднее"], index=["Сумма", "Среднее"].index(cp["c_mode"]), key=f"c_m_{selected_card_idx}")
            cp["group_col"] = st.selectbox("Фильтр по:", ["-- Без фильтра --"] + raw_headers, index=(["-- Без фильтра --"] + raw_headers).index(cp["group_col"]) if cp["group_col"] in (["-- Без фильтра --"] + raw_headers) else 0, key=f"c_g_{selected_card_idx}")
            cp["filter_value"] = st.selectbox("Значение:", list(active_filtered_df[cp["group_col"]].astype(str).unique()), key=f"c_v_{selected_card_idx}") if cp["group_col"] != "-- Без фильтра --" else None
            
            st.button("➕ Добавить график", on_click=add_chart_preset_cb)
            st.button("🗑️ Удалить график", on_click=remove_chart_preset_cb)
            selected_chart_idx = st.selectbox("Выбор графика:", range(len(st.session_state.charts_presets)))
            preset = st.session_state.charts_presets[selected_chart_idx]
            preset["style"] = st.selectbox("Тип графика:", ["Столбчатая диаграмма (Bar)", "Линейный тренд (Line)", "Кольцевая долей (Donut)", "Диаграмма Водопад (Waterfall)"], key=f"st_{selected_chart_idx}")
            preset["x_ax"] = st.selectbox("Ось X:", all_cols_list, index=all_cols_list.index(preset["x_ax"]) if preset["x_ax"] in all_cols_list else 0, key=f"x_{selected_chart_idx}")
            preset["y_ax_list"] = st.multiselect("Оси Y:", [c for c in raw_headers if c != preset["x_ax"]], default=[val for val in preset["y_ax_list"] if val in raw_headers], key=f"y_{selected_chart_idx}")

        with canvas_col:
            st.subheader("Сводные KPI")
            card_grid = st.columns(len(st.session_state.cards_presets))
            for idx, cp in enumerate(st.session_state.cards_presets):
                if cp["t_col_metric"] != "-- Выберите заголовок --":
                    with card_grid[idx % len(card_grid)]:
                        df_card = active_filtered_df.copy()
                        if cp["group_col"] != "-- Без фильтра --" and cp["filter_value"]: 
                            df_card = df_card[df_card[cp["group_col"]].astype(str) == str(cp["filter_value"])]
                        df_card[cp["t_col_metric"]] = pd.to_numeric(df_card[cp["t_col_metric"]], errors='coerce').fillna(0)
                        cv = df_card[cp["t_col_metric"]].sum() if "Сумма" in cp["c_mode"] else df_card[cp["t_col_metric"]].mean()
                        st.metric(label=f"{cp['t_col_metric']} ({cp['c_mode']})", value=f"{cv:,.2f}".replace(",", " "))
            
            st.markdown("---")
            for i, preset in enumerate(st.session_state.charts_presets):
                if preset["x_ax"] != "-- Выберите заголовок --" and preset["y_ax_list"]:
                    render_custom_chart(active_filtered_df, preset["x_ax"], preset["y_ax_list"], preset["style"], "#1f77b4", True, "Числовой", 0, 14, "#000000", "auto", False, 0, 15, i)
                    
    elif page == "🗮️ ABC/XYZ": internal_show_abc_xyz_page(main_df, gemini_api_key, ai_context_mode)
    elif page == "👥 RFM": internal_show_rfm_page(main_df, gemini_api_key, ai_context_mode)
else:
    st.sidebar.info("📊 Загрузите файлы Excel/CSV в сайдбар...")
