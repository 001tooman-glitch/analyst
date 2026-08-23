import streamlit as st
import pandas as pd
import io
import json
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from google import genai
from google.genai import types
import streamlit.components.v1 as components

# СВЕРХСТОЙКАЯ ПАМЯТЬ СЕССИИ (Не сбрасывается при st.rerun)
if "manual_charts" not in st.session_state: st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state: st.session_state.manual_cards = 1
if "main_df" not in st.session_state: st.session_state.main_df = pd.DataFrame()
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# Фиксированные ключи для сохранения выбранных шкал маппинга колонок
if "mapped_target_col" not in st.session_state: st.session_state.mapped_target_col = "-- Выберите --"
if "mapped_value_col" not in st.session_state: st.session_state.mapped_value_col = "-- Выберите --"
if "mapped_time_col" not in st.session_state: st.session_state.mapped_time_col = "-- Выберите --"

if "category_mapping_dict" not in st.session_state: st.session_state.category_mapping_dict = {}
if "raw_file_frames" not in st.session_state: st.session_state.raw_file_frames = {}
if "files_processed" not in st.session_state: st.session_state.files_processed = False

def add_chart_cb(): st.session_state.manual_charts += 1
def remove_chart_cb(): 
    if st.session_state.manual_charts > 1: st.session_state.manual_charts -= 1
def add_card_cb(): st.session_state.manual_cards += 1
def remove_card_cb(): 
    if st.session_state.manual_cards > 1: st.session_state.manual_cards -= 1
def inject_custom_css():
    # ИСПРАВЛЕНО: Полный отказ от st.markdown. Стили передаются через shadow-iframe родительского окна.
    # Это полностью исключает физическую возможность появления текста на экране.
    components.html("""
        <script>
        const style = window.parent.document.createElement('style');
        style.innerHTML = `
            html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, label {
                font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
                -webkit-font-smoothing: antialiased;
            }
            [data-testid="stMainSpaceBlockContainer"] { background-color: #f8fafc !important; }
            .stApp { background-color: #f8fafc !important; color: #0f172a !important; }
            h1, h2, h3, h4, h5, h6, [data-testid="stMainSpaceBlockContainer"] p, [data-testid="stMainSpaceBlockContainer"] label, [data-testid="stMainSpaceBlockContainer"] .stMarkdown { color: #0f172a !important; }
            
            [data-testid="stSidebar"] { 
                background-color: #ffffff !important; 
                border-right: 1px solid #e2e8f0 !important; 
            }
            [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { 
                color: #0f172a !important; 
            }
            [data-testid="stSidebar"] div[data-baseweb="select"] {
                background-color: #ffffff !important;
                border: 1px solid #cbd5e1 !important;
                color: #0f172a !important;
            }
            
            .stButton>button {
                background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%) !important; color: #ffffff !important;
                border-radius: 10px !important; border: none !important; padding: 10px 20px !important;
                font-weight: 500 !important; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
                box-shadow: 0 4px 12px rgba(79, 70, 229, 0.12) !important;
            }
            .stButton>button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 24px rgba(79, 70, 229, 0.25) !important; }
            [data-testid="stMainSpaceBlockContainer"] div[data-baseweb="select"], [data-testid="stMainSpaceBlockContainer"] div[data-baseweb="input"] { border-radius: 10px !important; background-color: #ffffff !important; border: 1px solid #cbd5e1 !important; }
            .streamlit-expanderHeader { background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 10px !important; color: #0f172a !important; }
            div[data-testid="stExpander"] { background-color: #ffffff !important; border-radius: 10px !important; }
        `;
        window.parent.document.head.appendChild(style);
        </script>
    """, height=0)

inject_custom_css()
def ai_generate_text_report(pivot_matrix_df, report_type="ABC/XYZ", data_context="Расход", api_key=None):
    if not api_key: return st.warning("⚠️ Введите API Key Gemini в сайдбаре для активации ИИ.")
    try:
        client = genai.Client(api_key=api_key)
        context_rules = f"Отчет строится в рамках аналитического контекста: {data_context}."
        system_instruction = f"""
        Ты — ведущий бизнес-аналитик международной компании. Напиши краткий аналитический отчет по матрице {report_type}.
        БИЗНЕС-КОНТЕКСТ ДАННЫХ: {context_rules}
        СТРОГИЕ ПРАВИЛА: Использовать нейтральные термины: 'предприятие', 'компания', 'структура активов'. Начинай сразу с анализа.
        """
        with st.spinner("🔮 ИИ интерпретирует матричные слои..."):
            response = client.models.generate_content(
                model='gemini-3.5-flash', contents=f"Данные сводной матрицы:\n{pivot_matrix_df.to_string()}", 
                config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.2)
            )
            st.markdown("---")
            st.markdown(f"### 📝 Аналитический ИИ-Отчет ({report_type})")
            st.info(response.text)
            st.download_button(label="📥 Скачать заключение ИИ (.txt)", data=response.text, file_name=f"ai_report.txt", mime="text/plain")
    except Exception as report_err: st.error(f"❌ Ошибка ИИ при генерации отчета: {report_err}")
@st.cache_data
def calculate_abc_xyz(df, t_col, v_col, p_col, a_lim, x_lim):
    df_clean = df.copy()
    df_clean[v_col] = pd.to_numeric(df_clean[v_col], errors='coerce').fillna(0.0)
    df_clean = df_clean[(df_clean[t_col].astype(str).str.strip() != "") & (df_clean[p_col].astype(str).str.strip() != "")]
    df_abc = df_clean.groupby(t_col, as_index=False)[v_col].sum().sort_values(by=v_col, ascending=False).reset_index(drop=True)
    total_sum = df_abc[v_col].sum()
    if total_sum == 0: return None, None, "Сумма значений равна нулю."
    df_abc['Cum'] = (df_abc[v_col] / total_sum).cumsum() * 100
    df_abc['Class_ABC'] = df_abc['Cum'].map(lambda x: 'A' if x <= a_lim else ('B' if x <= a_lim + 15 else 'C'))
    p_matrix = df_clean.groupby([t_col, p_col])[v_col].sum().unstack(fill_value=0.0)
    xyz_res = []
    for name, rows in p_matrix.iterrows():
        m, s = rows.mean(), rows.std(ddof=1) if len(rows) > 1 else 0.0
        kv = (s / m) * 100 if m > 0 and np.count_nonzero(rows) > 1 else (0.0 if m > 0 and s == 0 else 999.0)
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
    if len(rfm) < 3: return None, None, "Недостаточно уникальных элементов для деления."
    rfm['R_Score'] = pd.qcut(rfm['R'].rank(method='first'), 3, labels=['1', '2', '3']).astype(str)
    rfm['F_Score'] = pd.qcut(rfm['F'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
    rfm['M_Score'] = pd.qcut(rfm['M'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
    rfm['RFM'] = rfm['R_Score'] + rfm['F_Score'] + rfm['M_Score']
    seg_counts = rfm.groupby('RFM').size().reset_index(name='Количество элементов')
    return rfm, seg_counts, None

def internal_show_rfm_page(filtered_df, api_key, data_context):
    st.title("👥 Модуль многомерной RFM-сегментации")
    t_col, v_col, p_col = st.session_state.mapped_target_col, st.session_state.mapped_value_col, st.session_state.mapped_time_col
    if t_col == "-- Выберите --" or v_col == "-- Выберите --" or p_col == "-- Выберите --":
        return st.warning("⚠️ Настройте маппинг колонок (включая Шкалу Времени)!")
    rfm, seg_counts, err = calculate_rfm(filtered_df, t_col, v_col, p_col)
    if err:
        st.warning(err)
        if rfm is not None: st.dataframe(rfm, use_container_width=True)
        return
    st.plotly_chart(px.bar(seg_counts, x='RFM', y='Количество элементов', text_auto=True, color='RFM', color_continuous_scale="Purples"), use_container_width=True)
    if st.button("👥 Сгенерировать ИИ-отчет по сегментам", key="ai_report_rfm_btn"):
        ai_generate_text_report(seg_counts, report_type=f"RFM ({t_col})", data_context=data_context, api_key=api_key)
    st.dataframe(rfm.sort_values(by='M', ascending=False), use_container_width=True)
def render_custom_chart(active_df, x_ax, y_ax, style, color, lbl, f_format, f_round, f_size, f_color, f_pos, horiz, rot, top_limit, i, date_format_type="Исходный", custom_currency="", forecast_periods=0):
    try:
        df_c = active_df.copy()
        df_c[y_ax] = pd.to_numeric(df_c[y_ax], errors='coerce').fillna(0)
        curr_suffix = f" {str(custom_currency).strip()}" if str(custom_currency).strip() else ""
        scatter_pos = f_pos if f_pos in ["top center", "inside", "outside"] else "top center"
        if scatter_pos == "inside": scatter_pos = "middle center"
        elif scatter_pos == "outside": scatter_pos = "top center"

        def get_formatted_text(value_array):
            labels = []
            for v in value_array:
                if f_format == "Финансовый": 
                    labels.append(f"{v:,.{f_round}f}".replace(",", " ") + curr_suffix)
                elif f_format == "Сжатый (млн/млрд)":
                    if abs(v) >= 1_000_000_000: 
                        labels.append(f"{v / 1_000_000_000:,.{f_round}f}".replace(",", " ") + f" млрд{custom_currency}")
                    else: 
                        labels.append(f"{v / 1_000_000:,.{f_round}f}".replace(",", " ") + f" млн{custom_currency}")
                else: 
                    labels.append(f"{v:,.{f_round}f}".replace(",", " "))
            return labels

        is_year_col = "год" in str(x_ax).lower() or "year" in str(x_ax).lower()
        converted_dates = pd.to_datetime(df_c[x_ax], errors='coerce')
        is_date_axis = converted_dates.notna().sum() > (0.5 * len(df_c)) and not is_year_col
        idx_split = -1
        
        if is_date_axis:
            df_c['_datetime_clean_'] = converted_dates
            df_c = df_c.dropna(subset=['_datetime_clean_'])
            df_c['_month_period_'] = df_c['_datetime_clean_'].dt.to_period('M').dt.to_timestamp()
            df_fact = df_c.groupby('_month_period_', as_index=False)[y_ax].sum().sort_values(by='_month_period_', ascending=True).reset_index(drop=True)
            format_mapping = {"ММ.ГГГГ (01.2014)": "%m.%Y", "Месяц ГГГГ (Янв 2014)": "%b %Y", "ДД.ММ.ГГГГ (15.01.2014)": "%d.%m.%Y", "ГГГГ (2014)": "%Y"}
            chosen_pattern = format_mapping.get(date_format_type, "%b %Y")
            final_x = list(df_fact['_month_period_'].dt.strftime(chosen_pattern).astype(str))
            final_y = list(df_fact[y_ax].values)
            legend_names = ["Факт"] * len(final_y)
            idx_split = len(df_fact) - 1
            
            if forecast_periods > 0 and len(df_fact) > 1:
                y_arr = df_fact[y_ax].values
                slope, intercept = np.polyfit(np.arange(len(y_arr)), y_arr, 1)
                is_yearly = df_fact['_month_period_'].diff().dropna().dt.days.mean() > 300
                last_date = df_fact['_month_period_'].max()
                for m in range(1, forecast_periods + 1):
                    next_date = last_date + pd.DateOffset(years=m) if is_yearly else last_date + pd.DateOffset(months=m)
                    pred_val = slope * (len(y_arr) - 1 + m) + intercept
                    final_x.append(next_date.strftime(chosen_pattern))
                    final_y.append(max(0.0, pred_val))
                    legend_names.append("Прогноз ИИ")
            df_g = pd.DataFrame({x_ax: final_x, y_ax: final_y, "Тип данных": legend_names})
        else:
            sort_asc = is_year_col or pd.api.types.is_numeric_dtype(df_c[x_ax])
            df_g = df_c.groupby(x_ax, as_index=False)[y_ax].sum().sort_values(by=x_ax if sort_asc else y_ax, ascending=sort_asc).head(top_limit).reset_index(drop=True)
            df_g["Тип данных"] = "Факт"
            idx_split = len(df_g) - 1
            if forecast_periods > 0 and (is_year_col or pd.api.types.is_numeric_dtype(df_c[x_ax])) and len(df_g) > 1:
                try:
                    last_yr = int(float(df_g[x_ax].iloc[-1]))
                    y_arr = df_g[y_ax].values
                    slope, intercept = np.polyfit(np.arange(len(y_arr)), y_arr, 1)
                    fx, fy, fl = list(df_g[x_ax].astype(str).values), list(df_g[y_ax].values), ["Факт"] * len(df_g)
                    for offset in range(1, forecast_periods + 1):
                        fx.append(str(last_yr + offset))
                        pred_val = slope * (len(y_arr) - 1 + offset) + intercept
                        fy.append(max(0.0, pred_val))
                        fl.append("Прогноз ИИ")
                    df_g = pd.DataFrame({x_ax: fx, y_ax: fy, "Тип данных": fl})
                except: pass

        fig = go.Figure()
        if "Линейный" in style or (is_date_axis and "Столбчатая" not in style and "Кольцевая" not in style and "Водопад" not in style):
            if forecast_periods > 0 and idx_split > 0 and len(df_g) > idx_split + 1:
                txt_full = get_formatted_text(df_g[y_ax].values)
                fig.add_trace(go.Scatter(x=df_g[x_ax].iloc[:idx_split+1], y=df_g[y_ax].iloc[:idx_split+1], mode="lines+markers+text" if lbl else "lines+markers", name="Факт", line=dict(color=color, width=4), text=txt_full[:idx_split+1] if lbl else None, textposition=scatter_pos, textfont=dict(size=f_size, color=f_color)))
                fig.add_trace(go.Scatter(x=df_g[x_ax].iloc[idx_split:], y=df_g[y_ax].iloc[idx_split:], mode="lines+markers+text" if lbl else "lines+markers", name="Прогноз ИИ", line=dict(color="#ff4b4b", width=4, dash="dash"), text=txt_full[idx_split:] if lbl else None, textposition=scatter_pos, textfont=dict(size=f_size, color=f_color)))
            else:
                fig.add_trace(go.Scatter(x=df_g[x_ax], y=df_g[y_ax], mode="lines+markers+text" if lbl else "lines+markers", name="Факт", line=dict(color=color, width=4), text=get_formatted_text(df_g[y_ax].values) if lbl else None, textposition=scatter_pos, textfont=dict(size=f_size, color=f_color)))
        elif "Столбчатая" in style:
            sp = f_pos if f_pos in ["inside", "outside", "auto"] else "auto"
            if horiz: fig.add_trace(go.Bar(y=df_g[x_ax].astype(str), x=df_g[y_ax].values, text=get_formatted_text(df_g[y_ax].values) if lbl else None, textposition=sp, orientation="h", marker_color=color, textfont=dict(size=f_size, color=f_color)))
            else: fig.add_trace(go.Bar(x=df_g[x_ax].astype(str), y=df_g[y_ax].values, text=get_formatted_text(df_g[y_ax].values) if lbl else None, textposition=sp, orientation="v", marker_color=color, textfont=dict(size=f_size, color=f_color)))
        elif "Кольцевая" in style:
            fig.add_trace(go.Pie(labels=df_g[x_ax], values=df_g[y_ax], hole=0.4, rotation=rot, text=get_formatted_text(df_g[y_ax].values), textinfo="text+percent" if lbl else "none", texttemplate="%{label}: %{text} (%{percent})" if lbl else "none", textposition="auto", textfont=dict(size=f_size, color=f_color)))
        elif "Водопад" in style:
            ts = df_g[y_ax].sum()
            fig.add_trace(go.Waterfall(x=list(df_g[x_ax].astype(str)) + ["ИТОГО"], y=list(df_g[y_ax]) + [ts], text=get_formatted_text(list(df_g[y_ax]) + [ts]) if lbl else None, textposition="auto", measure=["relative"] * len(df_g[y_ax]) + ["total"], increasing={"marker": {"color": color}}, textfont=dict(size=f_size, color=f_color)))

        if horiz and "Столбчатая" in style: fig.update_layout(yaxis=dict(type='category'), xaxis=dict(showgrid=True))
        else: fig.update_layout(xaxis=dict(type='category', tickangle=45), yaxis=dict(showgrid=True))
        
        fig.update_layout(
            template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
            font=dict(family="Inter, sans-serif", size=12, color="#334155"),
            showlegend=True, margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig, use_container_width=True, key=f"p_{i}")
    except Exception as chart_err: st.error(f"Ошибка графика №{i+1}: {chart_err}")
def power_query_clean_engine(uploaded_files_list):
    file_registry = {}
    for f_item in uploaded_files_list:
        try:
            df = pd.read_csv(io.StringIO(f_item.getvalue().decode('utf-8'))) if f_item.name.endswith('.csv') else pd.read_excel(f_item, engine='openpyxl')
            df = df.loc[:, ~df.columns.str.contains('^Без названия|^Unnamed|^Unnamed:')].loc[:, ~df.columns.duplicated()]
            file_registry[f_item.name] = df.dropna(how='all')
        except Exception as file_err: st.sidebar.error(f"Ошибка файла {f_item.name}: {file_err}")
    return file_registry

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
            sample_df = current_dataframe.head(3).copy()
            for c in sample_df.columns:
                if not pd.api.types.is_numeric_dtype(sample_df[c]): sample_df[c] = sample_df[c].astype(str)
            columns_schema = {str(col): str(current_dataframe[col].dtype) for col in current_dataframe.columns}
            sys_prompt = f"Ты — эксперт по Pandas. Напиши одну строку кода без ```. Исходный df — 'current_dataframe'. Присвой результат переменной 'result_output'. Без системных вызовов os, sys, eval. Структура: {json.dumps(columns_schema, ensure_ascii=False)}"
            with chat_container, st.chat_message("assistant"), st.spinner("🤖 Вычисляю..."):
                response = client.models.generate_content(model='gemini-3.5-flash', contents=f"Вопрос: {user_prompt}", config=types.GenerateContentConfig(system_instruction=sys_prompt, temperature=0.1))
                raw_code = response.text.strip().replace("```python", "").replace("```", "")
                if any(kw in raw_code for kw in ['import ', 'os.', 'sys.', 'open', 'subprocess', 'eval']): return st.error("🔒 Блокировка: небезопасный код.")
                local_vars = {"current_dataframe": current_dataframe, "result_output": None}
                exec(raw_code, {"__builtins__": {}}, local_vars)
                res = local_vars.get("result_output")
                fmt_prompt = f"Ты — BI-аналитик. Переведи результат {str(res)} на понятный язык. Контекст: {context_mode_text}. Вопрос: '{user_prompt}'"
                final_res = client.models.generate_content(model='gemini-3.5-flash', contents=f"Результат:\n{str(res)}", config=types.GenerateContentConfig(system_instruction=fmt_prompt, temperature=0.2))
                assistant_response = final_res.text
                st.write(assistant_response)
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
        except Exception as chat_err: st.sidebar.error(f"Ошибка чата: {chat_err}")
def render_cross_file_mapping_ui(file_registry):
    st.markdown("---")
    st.markdown("### 🔀 Панель ручного сопоставления разнородных структур и категорий")
    file_names = list(file_registry.keys())
    if not file_names: return st.info("ℹ️ Для настройки кросс-анализа загрузите файлы.")
    if len(file_names) == 1:
        single_name = file_names
        base_df = file_registry[single_name]
        st.info(f"💡 Загружен 1 файл: `{single_name}`. Сопоставьте два столбца категорий.")
        c1, c2 = st.columns(2)
        with c1: f1_col = st.selectbox("Базовый столбец (Слой 1):", ["-- Выберите --"] + list(base_df.columns), key="cf_ui_1")
        with c2: f2_col = st.selectbox("Сравниваемый столбец (Слой 2):", ["-- Выберите --"] + list(base_df.columns), key="cf_ui_2")
        if f1_col == "-- Выберите --" or f2_col == "-- Выберите --": return st.warning("⚠️ Укажите оба столбца.")
        unique_f1_vals = list(base_df[f1_col].dropna().astype(str).unique())
        unique_f2_vals = ["-- Не сопоставлено / Игнорировать --"] + list(base_df[f2_col].dropna().astype(str).unique())
        df1, df2 = base_df.copy(), base_df.copy()
    else:
        st.info(f"💡 Загружено несколько файлов ({len(file_names)} шт.). Настройте кросс-связи.")
        f1_name, f2_name = file_names, file_names
        df1, df2 = file_registry[f1_name], file_registry[f2_name]
        c1, c2 = st.columns(2)
        with c1: f1_col = st.selectbox(f"Категория в Слое 1 ({f1_name}):", ["-- Выберите --"] + list(df1.columns), key="cf_ui_1")
        with c2: f2_col = st.selectbox(f"Категория в Слое 2 ({f2_name}):", ["-- Выберите --"] + list(df2.columns), key="cf_ui_2")
        if f1_col == "-- Выберите --" or f2_col == "-- Выберите --": return st.warning("⚠️ Укажите столбцы связи.")
        unique_f1_vals = list(df1[f1_col].dropna().astype(str).unique())
        unique_f2_vals = ["-- Не сопоставлено / Игнорировать --"] + list(df2[f2_col].dropna().astype(str).unique())

    st.markdown("#### 🔗 Установите логические соответствия между элементами вручную:")
    grid_cols, temp_mapping = st.columns(2), {}
    for idx, val_f1 in enumerate(unique_f1_vals[:40]):
        with grid_cols[idx % 2]:
            prev_sel = st.session_state.category_mapping_dict.get(val_f1, "-- Не сопоставлено / Игнорировать --")
            def_idx = unique_f2_vals.index(prev_sel) if prev_sel in unique_f2_vals else 0
            chosen_f2_val = st.selectbox(f"Элемент '{val_f1}' эквивалентен:", unique_f2_vals, index=def_idx, key=f"map_item_{idx}")
            if chosen_f2_val != "-- Не сопоставлено / Игнорировать --": temp_mapping[val_f1] = chosen_f2_val
    st.session_state.category_mapping_dict = temp_mapping
    
    if st.button("🚀 Применить кросс-маппинг и собрать объединенную витрину", key="apply_cross_map_btn"):
        clean_df1, clean_df2 = df1.copy(), df2.copy()
        clean_df1['Унифицированная_Категория'], clean_df1['Тип_Слоя'] = clean_df1[f1_col].astype(str), "Слой_1 (Базовый)"
        clean_df2['Унифицированная_Категория'] = clean_df2[f2_col].astype(str).map({v: k for k, v in temp_mapping.items()})
        clean_df2['Тип_Слоя'] = "Слой_2 (Сравниваемый)"
        st.session_state.main_df = pd.concat([clean_df1, clean_df2.dropna(subset=['Унифицированная_Категория'])], ignore_index=True, join='outer')
        st.session_state.files_processed = True
        st.success("✅ Сформировано поле связи: 'Унифицированная_Категория'.")
        st.rerun()
