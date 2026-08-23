import streamlit as st
import pandas as pd
import io
import json
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from google import genai
from google.genai import types

# Инициализация интерфейса на самом старте
st.set_page_config(layout="wide", page_title="BI Custom Platform")

# Инициализация переменных памяти Streamlit
if "manual_charts" not in st.session_state: st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state: st.session_state.manual_cards = 1
if "main_df" not in st.session_state: st.session_state.main_df = pd.DataFrame()
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# Переменные ручного ноу-код маппинга осей данных
if "map_target" not in st.session_state: st.session_state.map_target = ""
if "map_value" not in st.session_state: st.session_state.map_value = ""
if "map_time" not in st.session_state: st.session_state.map_time = ""

# Память для кросс-структурного мэтчинга категорий и элементов
if "category_mapping_dict" not in st.session_state: st.session_state.category_mapping_dict = {}
if "raw_file_frames" not in st.session_state: st.session_state.raw_file_frames = {}

def add_chart_cb(): st.session_state.manual_charts += 1
def remove_chart_cb(): 
    if st.session_state.manual_charts > 1: st.session_state.manual_charts -= 1
def add_card_cb(): st.session_state.manual_cards += 1
def remove_card_cb(): 
    if st.session_state.manual_cards > 1: st.session_state.manual_cards -= 1

# 🧠 МОДУЛЬ ИИ-АНАЛИЗАТОРA МАТРИЦ ABC/XYZ И RFM
def ai_generate_text_report(pivot_matrix_df, report_type="ABC/XYZ", data_context="Расход", api_key=None):
    if not api_key: 
        return st.warning("⚠️ Введите API Key Gemini в сайдбаре для активации ИИ.")
    try:
        client = genai.Client(api_key=api_key)
        context_rules = f"Отчет строится в рамках аналитического контекста: {data_context}."
        
        system_instruction = f"""
        Ты — ведущий бизнес-аналитик международной компании. Напиши краткий аналитический отчет по матрице {report_type}.
        БИЗНЕС-КОНТЕКСТ ДАННЫХ: {context_rules}
        
        СТРОГИЕ ПРАВИЛА ОФОРМЛЕНИЯ:
        - Использовать исключительно нейтральные термины: 'предприятие', 'компания', 'структура активов', 'номенклатурные группы'.
        - НАЧИНАЙ ОТЧЕТ СРАЗУ с содержательного анализа (Раздел "1. Анализ распределения ресурсов").
        - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать приветствия, вводные слова, метаданные или подписи автора.
        """
        with st.spinner(f"🔮 ИИ интерпретирует матричные слои..."):
            response = client.models.generate_content(
                model='gemini-3.5-flash', 
                contents=f"Данные сводной матрицы:\n{pivot_matrix_df.to_string()}", 
                config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.2)
            )
            report_text = response.text
            st.markdown("---")
            st.markdown(f"### 📝 Аналитический ИИ-Отчет ({report_type})")
            st.info(report_text)
            
            st.download_button(
                label="📥 Скачать заключение ИИ (.txt)",
                data=report_text,
                file_name=f"ai_report_{report_type.lower().replace('/', '_')}.txt",
                mime="text/plain"
            )
    except Exception as report_err: 
        st.error(f"❌ Ошибка ИИ при генерации отчета: {report_err}")
@st.cache_data
def calculate_abc_xyz(df, t_col, v_col, p_col, a_lim, x_lim):
    df_clean = df.copy()
    df_clean[v_col] = pd.to_numeric(df_clean[v_col], errors='coerce').fillna(0.0)
    df_clean = df_clean[(df_clean[t_col].astype(str).str.strip() != "") & (df_clean[p_col].astype(str).str.strip() != "")]
    
    df_abc = df_clean.groupby(t_col, as_index=False)[v_col].sum().sort_values(by=v_col, ascending=False).reset_index(drop=True)
    total_sum = df_abc[v_col].sum()
    if total_sum == 0:
        return None, None, "Сумма значений по выбранному критерию равна нулю."
        
    df_abc['Cum'] = (df_abc[v_col] / total_sum).cumsum() * 100
    df_abc['Class_ABC'] = df_abc['Cum'].map(lambda x: 'A' if x <= a_lim else ('B' if x <= a_lim + 15 else 'C'))
    
    p_matrix = df_clean.groupby([t_col, p_col])[v_col].sum().unstack(fill_value=0.0)
    xyz_res = []
    for name, rows in p_matrix.iterrows():
        m = rows.mean()
        s = rows.std(ddof=1) if len(rows) > 1 else 0.0
        kv = (s / m) * 100 if m > 0 and np.count_nonzero(rows) > 1 else (0.0 if m > 0 and s == 0 else 999.0)
        xyz_res.append({t_col: name, 'KV': kv, 'Класс XYZ': 'X' if kv <= x_lim else ('Y' if kv <= x_lim + 15 else 'Z')})
        
    df_m = pd.merge(df_abc[[t_col, v_col, 'Class_ABC']], pd.DataFrame(xyz_res), on=t_col)
    raw_pivot = df_m.pivot_table(index='Class_ABC', columns='Класс XYZ', values=t_col, aggfunc='count', fill_value=0)
    
    pivot_m = pd.DataFrame(0, index=['A', 'B', 'C'], columns=['X', 'Y', 'Z'])
    for idx in pivot_m.index:
        for col in pivot_m.columns:
            if idx in raw_pivot.index and col in raw_pivot.columns:
                pivot_m.loc[idx, col] = raw_pivot.loc[idx, col]
    return df_m, pivot_m, None

def internal_show_abc_xyz_page(filtered_df, api_key, data_context):
    st.title("🧮 Конструктор матриц ABC/XYZ")
    t_col = st.session_state.map_target
    v_col = st.session_state.map_value
    p_col = st.session_state.map_time
    
    if not t_col or not v_col or not p_col or t_col == "-- Выберите --" or v_col == "-- Выберите --" or p_col == "-- Выберите --":
        return st.warning("⚠️ Сначала настройте ручной маппинг колонок в сайдбаре!")
        
    st.markdown(f"### 🎯 Анализ: Объект **{t_col}** | Критерий **{v_col}** | Период **{p_col}**")
    a_lim = st.slider("Доля класса А (%):", 50, 90, 80, key="abc_s_slider")
    x_lim = st.slider("Граница класса X (KV ≤ %):", 5, 50, 10, key="xyz_s_slider")
    
    df_m, pivot_m, err = calculate_abc_xyz(filtered_df, t_col, v_col, p_col, a_lim, x_lim)
    if err:
        return st.warning(err)
        
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
    
    rfm = df_clean.groupby(str(t_col)).agg(
        R_days=(p_col, lambda x: (max_date - x.max()).days if x.notna().any() else 999),
        F=(v_col, 'count'),
        M=(v_col, 'sum')
    ).reset_index()
    rfm.columns = ['Объект Анализа', 'R', 'F', 'M']
    
    if len(rfm) < 3:
        return None, None, "Недостаточно уникальных элементов для перцентильного деления."
        
    rfm['R_Score'] = pd.qcut(rfm['R'].rank(method='first'), 3, labels=['1', '2', '3']).astype(str)
    rfm['F_Score'] = pd.qcut(rfm['F'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
    rfm['M_Score'] = pd.qcut(rfm['M'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
    rfm['RFM'] = rfm['R_Score'] + rfm['F_Score'] + rfm['M_Score']
    
    seg_counts = rfm.groupby('RFM').size().reset_index(name='Количество элементов')
    return rfm, seg_counts, None

def internal_show_rfm_page(filtered_df, api_key, data_context):
    st.title("👥 Молдуль многомерной RFM-сегментации")
    t_col = st.session_state.map_target
    v_col = st.session_state.map_value
    p_col = st.session_state.map_time
    
    if not t_col or not v_col or not p_col or t_col == "-- Выберите --" or v_col == "-- Выберите --" or p_col == "-- Выберите --":
        return st.warning("⚠️ Настройте маппинг колонок (включая Шкалу Времени для расчета Давности/Recency)!")
        
    st.markdown(f"### 🎯 Сегментация: Объект **{t_col}** | Ценность **{v_col}** | Время **{p_col}**")
    rfm, seg_counts, err = calculate_rfm(filtered_df, t_col, v_col, p_col)
    if err:
        st.warning(err)
        if rfm is not None: st.dataframe(rfm, use_container_width=True)
        return
        
    st.plotly_chart(px.bar(seg_counts, x='RFM', y='Количество элементов', text_auto=True, color='RFM', color_continuous_scale="Purples"), use_container_width=True)
    if st.button("👥 Сгенерировать ИИ-отчет по сегментам", key="ai_report_rfm_btn"):
        ai_generate_text_report(seg_counts, report_type=f"RFM ({t_col})", data_context=data_context, api_key=api_key)
    st.dataframe(rfm.sort_values(by='M', ascending=False), use_container_width=True)
# Полностью восстановлен ваш исходный графический движок без сторонних модификаций
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
                if f_format == "Финансовый": formatted_val = f"{round(v, f_round):,}".replace(",", " ") + curr_suffix
                elif f_format == "Сжатый (млн/млрд)":
                    if abs(v) >= 1_000_000_000: formatted_val = f"{v / 1_000_000_000:,.2f} млрд{curr_suffix}"
                    else: formatted_val = f"{v / 1_000_000:,.2f} млн{curr_suffix}"
                else: formatted_val = f"{round(v, f_round):,}".replace(",", " ")
                labels.append(formatted_val)
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
                x_arr = np.arange(len(y_arr))
                slope, intercept = np.polyfit(x_arr, y_arr, 1)
                
                date_diffs = df_fact['_month_period_'].diff().dropna()
                is_yearly_data = date_diffs.dt.days.mean() > 300
                last_date = df_fact['_month_period_'].max()
                
                for m in range(1, forecast_periods + 1):
                    next_date = last_date + pd.DateOffset(years=m) if is_yearly_data else last_date + pd.DateOffset(months=m)
                    f_index = len(y_arr) - 1 + m
                    pred_val = slope * f_index + intercept
                    if pred_val < 0: pred_val = 0.0
                    
                    final_x.append(next_date.strftime(chosen_pattern))
                    final_y.append(pred_val)
                    legend_names.append("Прогноз ИИ")
            df_g = pd.DataFrame({x_ax: final_x, y_ax: final_y, "Тип данных": legend_names})
        else:
            sort_asc = is_year_col or pd.api.types.is_numeric_dtype(df_c[x_ax])
            df_g = df_c.groupby(x_ax, as_index=False)[y_ax].sum().sort_values(by=x_ax if sort_asc else y_ax, ascending=sort_asc).head(top_limit).reset_index(drop=True)
            df_g["Тип данных"] = "Факт"
            idx_split = len(df_g) - 1
            
            if forecast_periods > 0 and (is_year_col or pd.api.types.is_numeric_dtype(df_c[x_ax])) and len(df_g) > 1:
                try:
                    last_year_numeric = int(float(df_g[x_ax].iloc[-1]))
                    y_arr = df_g[y_ax].values
                    x_arr = np.arange(len(y_arr))
                    slope, intercept = np.polyfit(x_arr, y_arr, 1)
                    
                    f_x_list = list(df_g[x_ax].astype(str).values)
                    f_y_list = list(df_g[y_ax].values)
                    f_leg_list = ["Факт"] * len(df_g)
                    
                    for offset in range(1, forecast_periods + 1):
                        f_x_list.append(str(last_year_numeric + offset))
                        f_index = len(y_arr) - 1 + offset
                        pred_val = slope * f_index + intercept
                        if pred_val < 0: pred_val = 0.0
                        f_y_list.append(pred_val)
                        f_leg_list.append("Прогноз ИИ")
                    df_g = pd.DataFrame({x_ax: f_x_list, y_ax: f_y_list, "Тип данных": f_leg_list})
                except: pass

        fig = go.Figure()
        if "Линейный" in style or (is_date_axis and "Столбчатая" not in style and "Кольцевая" not in style and "Водопад" not in style):
            if forecast_periods > 0 and idx_split > 0 and len(df_g) > idx_split + 1:
                txt_full = get_formatted_text(df_g[y_ax].values)
                fig.add_trace(go.Scatter(x=df_g[x_ax].iloc[:idx_split+1], y=df_g[y_ax].iloc[:idx_split+1], mode="lines+markers+text" if lbl else "lines+markers", name="Факт", line=dict(color=color, width=4), text=txt_full[:idx_split+1] if lbl else None, textposition=scatter_pos, textfont=dict(size=f_size, color=f_color)))
                fig.add_trace(go.Scatter(x=df_g[x_ax].iloc[idx_split:], y=df_g[y_ax].iloc[idx_split:], mode="lines+markers+text" if lbl else "lines+markers", name="Прогноз ИИ", line=dict(color="#ff4b4b", width=4, dash="dash"), text=txt_full[idx_split:] if lbl else None, textposition=scatter_pos, textfont=dict(size=f_size, color=f_color)))
            else:
                txt = get_formatted_text(df_g[y_ax].values)
                fig.add_trace(go.Scatter(x=df_g[x_ax], y=df_g[y_ax], mode="lines+markers+text" if lbl else "lines+markers", name="Факт", line=dict(color=color, width=4), text=txt if lbl else None, textposition=scatter_pos, textfont=dict(size=f_size, color=f_color)))
        elif "Столбчатая" in style:
            safe_pos = f_pos if f_pos in ["inside", "outside", "auto"] else "auto"
            if horiz:
                if not is_date_axis: df_g = df_g.sort_values(by=y_ax, ascending=True).reset_index(drop=True)
                fig.add_trace(go.Bar(y=df_g[x_ax].astype(str), x=df_g[y_ax].values, text=get_formatted_text(df_g[y_ax].values) if lbl else None, textposition=safe_pos, orientation="h", marker_color=color, textfont=dict(size=f_size, color=f_color)))
            else:
                fig.add_trace(go.Bar(x=df_g[x_ax].astype(str), y=df_g[y_ax].values, text=get_formatted_text(df_g[y_ax].values) if lbl else None, textposition=safe_pos, orientation="v", marker_color=color, textfont=dict(size=f_size, color=f_color)))
        elif "Кольцевая" in style:
            fig.add_trace(go.Pie(labels=df_g[x_ax], values=df_g[y_ax], hole=0.4, rotation=rot, textinfo="label+value" if lbl else "none", textposition="auto", text=get_formatted_text(df_g[y_ax].values), textfont=dict(size=f_size, color=f_color)))
        elif "Водопад" in style:
            total_sum_val = df_g[y_ax].sum()
            fig.add_trace(go.Waterfall(x=list(df_g[x_ax].astype(str)) + ["ИТОГО"], y=list(df_g[y_ax]) + [total_sum_val], text=get_formatted_text(list(df_g[y_ax]) + [total_sum_val]) if lbl else None, textposition="auto", measure=["relative"] * len(df_g[y_ax]) + ["total"], increasing={"marker": {"color": color}}, textfont=dict(size=f_size, color=f_color)))

        if horiz and "Столбчатая" in style: fig.update_layout(yaxis=dict(type='category'), xaxis=dict(showgrid=True))
        else: fig.update_layout(xaxis=dict(type='category', tickangle=45), yaxis=dict(showgrid=True))
        fig.update_layout(showlegend=True, margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig, use_container_width=True, key=f"p_{i}")
    except Exception as chart_err:
        st.error(f"Ошибка графика №{i+1}: {chart_err}")
def power_query_clean_engine(uploaded_files_list):
    file_registry = {}
    for f_item in uploaded_files_list:
        try:
            df = pd.read_csv(io.StringIO(f_item.getvalue().decode('utf-8'))) if f_item.name.endswith('.csv') else pd.read_excel(f_item, engine='openpyxl')
            df = df.loc[:, ~df.columns.str.contains('^Без названия|^Unnamed|^Unnamed:')].loc[:, ~df.columns.duplicated()]
            file_registry[f_item.name] = df.dropna(how='all')
        except Exception as file_err:
            st.sidebar.error(f"Ошибка обработки файла {f_item.name}: {file_err}")
    return file_registry

def render_ai_sidebar_chat(current_dataframe, api_key, context_mode_text):
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💬 Чат-ассистент к данным")
    
    if current_dataframe.empty:
        st.sidebar.info("Загрузите файлы для активации чата.")
        return
        
    if st.sidebar.button("🧹 Очистить историю чата", key="clear_chat_btn"):
        st.session_state.chat_history = []
        st.sidebar.success("История очищена!")
        st.rerun()
        
    chat_container = st.sidebar.container(height=250)
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]): st.write(message["content"])

    if user_prompt := st.sidebar.chat_input("Спросить ИИ о таблице...", key="chat_input_text"):
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with chat_container:
            with st.chat_message("user"): st.write(user_prompt)
                
        if not api_key:
            with chat_container:
                with st.chat_message("assistant"): st.error("Ошибка: Введите API Key.")
            return

        try:
            client = genai.Client(api_key=api_key)
            sample_df = current_dataframe.head(3).copy()
            
            for c in sample_df.columns:
                if not pd.api.types.is_numeric_dtype(sample_df[c]):
                    sample_df[c] = sample_df[c].astype(str)
                    
            columns_schema = {str(col): str(current_dataframe[col].dtype) for col in current_dataframe.columns}
            sample_json = sample_df.to_dict(orient='records')
            
            sys_prompt = f"""
            Ты — эксперт по анализу данных на Python и Pandas. Напиши ОДНУ строчку кода на Python, которая ответит на вопрос пользователя.
            Исходный датафрейм называется 'current_dataframe'.
            
            ТЕКУЩАЯ СТРУКТУРА ТАБЛИЦЫ:
            {json.dumps(columns_schema, ensure_ascii=False)}
            
            ПРИМЕРЫ СТРОК:
            {json.dumps(sample_json, ensure_ascii=False)}
            
            СТРОГИЕ ПРАВИЛА:
            1. Твой ответ должен содержать ИСКЛЮЧИТЕЛЬНО одну строку чистого рабочего кода на Python, без знаков ```.
            2. Результат обязательно присваивай переменной 'result_output'.
            3. Запрещено использовать системные вызовы вроде os, sys, eval, open, subprocess во избежание угроз безопасности.
            """
            
            with chat_container:
                with st.chat_message("assistant"):
                    with st.spinner("🤖 Вычисляю..."):
                        response = client.models.generate_content(
                            model='gemini-3.5-flash',
                            contents=f"Вопрос пользователя: {user_prompt}",
                            config=types.GenerateContentConfig(system_instruction=sys_prompt, temperature=0.1)
                        )
                        raw_code = response.text.strip().replace("```python", "").replace("```", "")
                        
                        forbidden_keywords = ['import ', 'os.', 'sys.', 'open', 'subprocess', 'shutil', 'eval']
                        if any(kw in raw_code for kw in forbidden_keywords):
                            st.error("🔒 Запрос отклонен политикой безопасности выполнения кода.")
                            return
                            
                        local_vars = {"current_dataframe": current_dataframe, "result_output": None}
                        exec(raw_code, {"__builtins__": {}}, local_vars)
                        execution_result = local_vars.get("result_output")
                        
                        formatting_prompt = f"""
                        Ты — BI-аналитик. Переведи технический результат {str(execution_result)} на понятный человеческий язык.
                        Бизнес-контекст: {context_mode_text}. Вопрос: '{user_prompt}'
                        Отвечай структурированно, кратко, цифры форматируй пробелами.
                        """
                        final_response = client.models.generate_content(
                            model='gemini-3.5-flash',
                            contents=f"Результат выполнения Pandas-кода:\n{str(execution_result)}",
                            config=types.GenerateContentConfig(system_instruction=formatting_prompt, temperature=0.2)
                        )
                        assistant_response = final_response.text
                        st.write(assistant_response)
                        
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
        except Exception as chat_err:
            st.sidebar.error(f"Ошибка чата: {chat_err}")

def render_cross_file_mapping_ui(file_registry):
    st.markdown("---")
    st.markdown("### 🔀 Панель ручного сопоставления разнородных структур и категорий")
    
    file_names = list(file_registry.keys())
    if not file_names:
        st.info("ℹ️ Для настройки кросс-анализа загрузите файлы в форму выше.")
        return pd.DataFrame()
        
    if len(file_names) == 1:
        single_name = file_names
        base_df = file_registry[single_name]
        
        st.info(f"💡 Загружен 1 файл: `{single_name}`. Вы можете сопоставить две разные категориальные колонки.")
        c1, c2 = st.columns(2)
        with c1: f1_col = st.selectbox("Базовый столбец (Слой 1):", ["-- Выберите --"] + list(base_df.columns), key="cf_ui_1")
        with c2: f2_col = st.selectbox("Сравниваемый столбец (Слой 2):", ["-- Выберите --"] + list(base_df.columns), key="cf_ui_2")
        
        if f1_col == "-- Выберите --" or f2_col == "-- Выберите --":
            st.warning("⚠️ Укажите оба столбца для сопоставления внутри файла.")
            return pd.DataFrame()
            
        unique_f1_vals = list(base_df[f1_col].dropna().astype(str).unique())
        unique_f2_vals = ["-- Не сопоставлено / Игнорировать --"] + list(base_df[f2_col].dropna().astype(str).unique())
        df1 = base_df.copy()
        df2 = base_df.copy()
    else:
        st.info(f"💡 Загружено несколько файлов ({len(file_names)} шт.). Настройте связи между первыми двумя таблицами.")
        f1_name = file_names
        f2_name = file_names
        df1, df2 = file_registry[f1_name], file_registry[f2_name]
        
        c1, c2 = st.columns(2)
        with c1: f1_col = st.selectbox(f"Категория в Базовом слое ({f1_name}):", ["-- Выберите --"] + list(df1.columns), key="cf_ui_1")
        with c2: f2_col = st.selectbox(f"Категория в Сравниваемом слое ({f2_name}):", ["-- Выберите --"] + list(df2.columns), key="cf_ui_2")
        
        if f1_col == "-- Выберите --" or f2_col == "-- Выберите --":
            st.warning("⚠️ Укажите связующие столбцы в обоих слоях данных.")
            return pd.DataFrame()
            
        unique_f1_vals = list(df1[f1_col].dropna().astype(str).unique())
        unique_f2_vals = ["-- Не сопоставлено / Игнорировать --"] + list(df2[f2_col].dropna().astype(str).unique())

    st.markdown("#### 🔗 Установите логические соответствия между элементами вручную:")
    grid_cols = st.columns(2)
    
    temp_mapping = {}
    for idx, val_f1 in enumerate(unique_f1_vals[:40]):
        col_side = grid_cols[idx % 2]
        with col_side:
            prev_sel = st.session_state.category_mapping_dict.get(val_f1, "-- Не сопоставлено / Игнорировать --")
            def_idx = unique_f2_vals.index(prev_sel) if prev_sel in unique_f2_vals else 0
            
            chosen_f2_val = st.selectbox(f"Элемент '{val_f1}' эквивалентен:", unique_f2_vals, index=def_idx, key=f"map_item_{idx}")
            if chosen_f2_val != "-- Не сопоставлено / Игнорировать --":
                temp_mapping[val_f1] = chosen_f2_val
                
    st.session_state.category_mapping_dict = temp_mapping
    
    if st.button("🚀 Применить кросс-маппинг и собрать объединенную витрину", key="apply_cross_map_btn"):
        clean_df1 = df1.copy()
        clean_df2 = df2.copy()
        
        clean_df1['Унифицированная_Категория'] = clean_df1[f1_col].astype(str)
        clean_df1['Тип_Слоя'] = "Слой_1 (Базовый)"
        
        inv_map = {v: k for k, v in temp_mapping.items()}
        clean_df2['Унифицированная_Категория'] = clean_df2[f2_col].astype(str).map(inv_map)
        clean_df2['Тип_Слоя'] = "Слой_2 (Сравниваемый)"
        
        clean_df2 = clean_df2.dropna(subset=['Унифицированная_Категория'])
        united_bi_warehouse = pd.concat([clean_df1, clean_df2], ignore_index=True, join='outer')
        st.session_state.main_df = united_bi_warehouse
        st.success("✅ Универсальная витрина кросс-анализа успешно сформирована! Создано поле связи: 'Унифицированная_Категория'.")
        st.rerun()
st.sidebar.markdown("### 🤖 Настройки ИИ-Слой")
gemini_api_key = st.sidebar.text_input("Введите Gemini API Key:", type="password")
ai_context_mode = st.sidebar.selectbox("Контекст для AI:", [
    "📊 Сравнительный кросс-анализ структур и категорий",
    "📊 Продажи / Сбыт / Ритейл", 
    "📅 Закупки / Материальное обеспечение", 
    "📦 Запасы / Складские остатки"
])

uploaded_files = st.file_uploader("Загрузите файлы Excel/CSV:", type=["csv", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    if not st.session_state.raw_file_frames:
        with st.spinner("⏳ Чтение структуры файлов..."):
            st.session_state.raw_file_frames = power_query_clean_engine(uploaded_files)
            
    if "Сравнительный" in ai_context_mode:
        if st.session_state.main_df.empty:
            render_cross_file_mapping_ui(st.session_state.raw_file_frames)
    else:
        if st.session_state.main_df.empty:
            frames_list = list(st.session_state.raw_file_frames.values())
            if frames_list: st.session_state.main_df = pd.concat(frames_list, ignore_index=True, join='outer')

    main_df = st.session_state.main_df
    if not main_df.empty:
        render_ai_sidebar_chat(main_df, gemini_api_key, ai_context_mode)
        
        if st.sidebar.button("♻️ Сбросить базу данных"):
            st.session_state.main_df = pd.DataFrame()
            st.session_state.raw_file_frames = {}
            st.session_state.chat_history = []
            st.session_state.category_mapping_dict = {}
            st.rerun()
            
        st.sidebar.markdown("### 🎛️ Ручной маппинг аналитических шкал")
        raw_headers = list(main_df.columns)
        
        st.session_state.map_target = st.sidebar.selectbox("🔑 КЛЮЧ АНАЛИЗА:", ["-- Выберите --"] + raw_headers, index=raw_headers.index(st.session_state.map_target) + 1 if st.session_state.map_target in raw_headers else (raw_headers.index('Унифицированная_Категория') + 1 if 'Унифицированная_Категория' in raw_headers else 0))
        st.session_state.map_value = st.sidebar.selectbox("💰 КРИТЕРИЙ ОБЪЕМА:", ["-- Выберите --"] + raw_headers, index=raw_headers.index(st.session_state.map_value) + 1 if st.session_state.map_value in raw_headers else 0)
        st.session_state.map_time = st.sidebar.selectbox("📅 ШКАЛА ВРЕМЕНИ:", ["-- Выберите --"] + raw_headers, index=raw_headers.index(st.session_state.map_time) + 1 if st.session_state.map_time in raw_headers else 0)
        
        if st.session_state.map_value != "-- Выберите --":
            main_df[st.session_state.map_value] = pd.to_numeric(main_df[st.session_state.map_value].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.'), errors='coerce').fillna(0.0)

        all_cols_list = ["-- Выберите заголовок --"] + raw_headers
        page = st.sidebar.radio("Перейти к разделу:", ["🗂️ 1. Загрузка и очистка данных", "📊 2. Executive Диаграммы", "🗮️ 3. ABC/XYZ-аналитика элементов", "👥 4. RFM-сегментация"])
        
        if page == "🗂️ 1. Загрузка и очистка данных":
            st.success(f"📊 База сформирована! Загружено строк: {len(main_df):,}")
            if "Сравнительный" in ai_context_mode:
                render_cross_file_mapping_ui(st.session_state.raw_file_frames)
            cp = st.number_input(f"Страница (из {(len(main_df) // 50) + 1}):", min_value=1, value=1, step=1)
            st.dataframe(main_df.iloc[(cp - 1) * 50: cp * 50], height=350, use_container_width=True)
            
        elif page == "📊 2. Executive Диаграммы":
            st.title("📊 Интерактивная BI-Панель Показателей")
            card_cols = st.columns(st.session_state.manual_cards)
            for j in range(st.session_state.manual_cards):
                with card_cols[j % len(card_cols)]:
                    st.markdown(f"**📌 Карточка № {j+1}**")
                    t_col_metric = st.selectbox(f"Поле метрики:", all_cols_list, key=f"c_t_{j}")
                    c_mode = st.selectbox(f"Агрегация:", ["Сумма", "Среднее"], key=f"c_m_{j}")
                    st.markdown("---")
                    group_col = st.selectbox(f"Группировать по полю:", ["-- Без фильтра --"] + raw_headers, key=f"c_g_{j}")
                    filter_value = None
                    if group_col != "-- Без фильтра --":
                        filter_value = st.selectbox(f"Значение элемента:", list(main_df[group_col].astype(str).unique()), key=f"c_v_{j}")
                    with st.expander("🎨 Настройки"):
                        c_fmt = st.selectbox("Формат:", ["Числовой", "Финансовый", "Сжатый (млн/млрд)"], key=f"c_f_{j}")
                        c_curr_text = st.text_input("Валюта:", value="$", key=f"c_cur_{j}")
                        c_rnd = st.slider("Округление:", 0, 4, 2, key=f"c_r_{j}")
                    if t_col_metric != "-- Выберите заголовок --":
                        try:
                            df_card = main_df.copy()
                            if group_col != "-- Без фильтра --" and filter_value is not None:
                                df_card = df_card[df_card[group_col].astype(str) == str(filter_value)]
                            df_card[t_col_metric] = pd.to_numeric(df_card[t_col_metric], errors='coerce').fillna(0)
                            cv = df_card[t_col_metric].sum() if "Сумма" in c_mode else df_card[t_col_metric].mean()
                            lbl = f"{round(cv, c_rnd):,}".replace(",", " ") + f" {c_curr_text}" if c_fmt == "Финансовый" else f"{round(cv, c_rnd):,}".replace(",", " ")
                            st.markdown(f'<div style="background-color:#f8f9fa; border:1px solid #dee2e6; border-radius:10px; padding:20px; text-align:center;"><div style="color:#6c757d; font-size:13px; font-weight:bold;">{t_col_metric}</div><div style="color:#1f77b4; font-size:26px; font-weight:bold;">{lbl}</div></div>', unsafe_allow_html=True)
                        except: pass
            bc1, bc2 = st.columns(2)
            with bc1: st.button("➕ Добавить карточку", on_click=add_card_cb)
            with bc2: st.button("🗑️ Удалить карточку", on_click=remove_card_cb)
            st.markdown("---")
            st.subheader("🛠️ No-Code Конструктор Графиков")
            for i in range(st.session_state.manual_charts):
                c1, c2, c3, c4 = st.columns(4)
                with c1: style = st.selectbox(f"Тип №{i+1}:", ["Столбчатая диаграмма (Bar)", "Линейный тренд (Line)", "Кольцевая долей (Donut)", "Диаграмма Водопад (Waterfall)"], key=f"s_{i}")
                with c2: x_ax = st.selectbox(f"Ось X №{i+1}:", all_cols_list, key=f"x_{i}")
                with c3: y_ax = st.selectbox(f"Ось Y №{i+1}:", all_cols_list, key=f"y_{i}")
                with c4: color = st.color_picker(f"Цвет №{i+1}:", "#1f77b4", key=f"col_{i}")
                with st.expander("🎨 Настройки временной оси и Прогноза"):
                    cu1, cu2 = st.columns(2)
                    with cu1:
                        lbl_g = st.checkbox("Показывать значения", value=True, key=f"lbl_{i}")
                        f_format = st.selectbox("Формат:", ["Числовой", "Финансовый", "Сжатый (млн/млрд)"], key=f"fmt_{i}")
                        f_round = st.slider("Округление:", 0, 4, 0, key=f"rnd_{i}")
                        f_curr_text = st.text_input("Валюта графика:", value="$", key=f"fcur_tx_{i}")
                    with cu2:
                        f_size = st.slider("Шрифт:", 8, 24, 14, key=f"sz_{i}")
                        f_color = st.color_picker("Цвет шрифта:", "#000000", key=f"fcol_{i}")
                        f_pos = st.selectbox("Положение:", ["auto", "inside", "outside"], key=f"pos_{i}")
                        horiz = st.checkbox("Горизонтально", value=False, key=f"h_{i}") if "Bar" in style else False
                        rot = st.slider("🔄 Поворот:", 0, 360, 0, step=15, key=f"rot_{i}") if "Donut" in style else 0
                        top_limit = st.slider("🔝 ТОП позиций:", 5, 200, 15, key=f"top_{i}")
                        d_fmt = st.selectbox("Формат даты:", ["Исходный", "ММ.ГГГГ (01.2014)", "Месяц ГГГГ (Янв 2014)", "ДД.ММ.ГГГГ (15.01.2014)", "ГГГГ (2014)"], key=f"dfmt_{i}")
                        f_cast = st.slider("🔮 Прогноз периодов:", 0, 5, 2, key=f"fcast_{i}")
                if x_ax != "-- Выберите заголовок --" and y_ax != "-- Выберите заголовок --":
                    render_custom_chart(main_df, x_ax, y_ax, style, color, lbl_g, f_format, f_round, f_size, f_color, f_pos, horiz, rot, top_limit, i, date_format_type=d_fmt, custom_currency=f_curr_text, forecast_periods=f_cast)
            b1, b2 = st.columns(2)
            with b1: st.button("➕ Добавить диаграмму", on_click=add_chart_cb)
            with b2: st.button("🗑️ Удалить диаграмму", on_click=remove_chart_cb)
            
        elif page == "🗮️ 3. ABC/XYZ-аналитика элементов":
            internal_show_abc_xyz_page(main_df, gemini_api_key, ai_context_mode)
        elif page == "👥 4. RFM-сегментация":
            internal_show_rfm_page(main_df, gemini_api_key, ai_context_mode)
else:
    st.sidebar.info("📊 Ожидание загрузки файлов для кросс-анализа...")
    st.info("📊 BI-платформа ожидает загрузки любых файлов Excel/CSV...")
