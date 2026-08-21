import streamlit as st
import pandas as pd
import io
import json
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

st.set_page_config(layout="wide", page_title="BI Enterprise Platform")

class ColumnMappingSchema(BaseModel):
    model_config = {"extra": "forbid"}
    mapping: dict[str, str] = Field(
        description="Словарь, где ключ - исходное имя колонки, а значение - строго одно из полей: 'ОЗМ', 'Наименование материала', 'Количество' или 'Сумма'"
    )
@st.cache_data(show_spinner=False)
def ai_column_mapper_engine(raw_columns_list, api_key):
    if not api_key: 
        return {}
    try:
        client = genai.Client(api_key=api_key)
        sys_instruction = (
            "Ты — BI-аналитик. Сопоставь заголовки закупщика с полями: "
            "'ОЗМ', 'Наименование материала', 'Количество', 'Сумма'. "
            "Используй контекст и смысл слов."
        )
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=f"Выполни маппинг списка заголовков: {str(raw_columns_list)}",
            config=types.GenerateContentConfig(
                system_instruction=sys_instruction,
                response_mime_type="application/json",
                response_schema=ColumnMappingSchema,
                temperature=0.1
            ),
        )
        return json.loads(response.text).get("mapping", {})
    except:
        return {}
def ai_generate_text_report(pivot_matrix_df, report_type="ABC/XYZ", data_context="Расход", api_key=None):
    if not api_key: 
        return st.warning("⚠️ Введите API Key Gemini.")
    try:
        client = genai.Client(api_key=api_key)
        context_mapping = {
            "Закупки": "Данные — закупки. Группа AZ — стратегические контракты. Группа CZ — мелкая текучка.",
            "Запасы": "Данные — складские запасы. Группа AZ — замороженный капитал. Группа CZ — хлам и неликвиды.",
            "Расход": "Данные — фактический расход ТМЦ. Группа AZ — аварийные ремонты. Группа CZ — мелкие заявки."
        }
        context_rules = context_mapping.get(data_context, "Данные — коммерческий оборот.")
        system_instruction = f"""
        Ты — ведущий бизнес-аналитик предприятия. Напиши аналитический отчет для руководства по матрице {report_type}. Контекст: {context_rules}
        ПРАВИЛА: Запрещено писать слова 'комбинат' или 'эксперт по цепям поставок'. Начинай сразу с Раздела "1. Анализ текущего процесса".
        """
        with st.spinner("🔮 ИИ генерирует чистый отчет..."):
            response = client.models.generate_content(
                model='gemini-3.5-flash', 
                contents=f"Матрица:\n{pivot_matrix_df.to_string()}", 
                config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.2)
            )
            st.markdown("---")
            st.markdown(f"### 📝 Аналитический ИИ-Отчет")
            st.info(response.text)
            st.download_button(label="📥 Скачать отчет (.txt)", data=response.text, file_name="ai_report.txt", mime="text/plain")
    except Exception as e: 
        st.error(f"❌ Ошибка ИИ: {e}")
def internal_show_abc_xyz_page(filtered_df, api_key, data_context):
    st.title("🧮 Конструктор матриц ABC/XYZ и Модуль оборачиваемости ТМЦ")
    if filtered_df.empty: 
        return st.info("ℹ️ Выборка пуста. Загрузите файлы.")
    
    df = filtered_df.copy()
    available_cols = list(df.columns)
    
    st.markdown("### 🎯 Настройка параметров оборачиваемости ТМЦ")
    tc1, tc2 = st.columns(2)
    with tc1: chosen_turnover_period = st.selectbox("Выберите период:", ["Год (365 дней)", "Полугодие (182 дня)", "Квартал (90 дней)", "Месяц (30 дней)"], key="t_period_sel")
    with tc2: abc_target = st.selectbox("Объект анализа ТМЦ:", [c for c in available_cols if c not in ['Сумма', 'Количество']], key="abc_t")
        
    selected_days = {"Год (365 дней)": 365, "Полугодие (182 дня)": 182, "Квартал (90 дней)": 90, "Месяц (30 дней)": 30}[chosen_turnover_period]
    
    c1, c2 = st.columns(2)
    with c1: abc_value = st.selectbox("Критерий масштаба стоимости:", [c for c in ['Сумма', 'Количество'] if c in available_cols] + available_cols, key="abc_v")
    with c2: xyz_period = st.selectbox("Шкала времени (для XYZ):", [c for c in available_cols if c != abc_target], key="xyz_p")
    
    a_lim = st.slider("Граница группы A (%):", 50, 90, 80, key="abc_s")
    x_lim = st.slider("Граница группы X (KV ≤ %):", 5, 20, 10, key="xyz_s")
    try:
        df[abc_value] = pd.to_numeric(df[abc_value], errors='coerce').fillna(0.0)
        df = df[(df[abc_target].astype(str).str.strip() != "") & (df[xyz_period].astype(str).str.strip() != "")]
        
        df_abc = df.groupby(abc_target, as_index=False)[abc_value].sum().sort_values(by=abc_value, ascending=False).reset_index(drop=True)
        total_sum = df_abc[abc_value].sum()
        if total_sum == 0: return st.warning("Сумма значений равна нулю.")
            
        df_abc['Cum'] = (df_abc[abc_value] / total_sum).cumsum() * 100
        df_abc['Class_ABC'] = df_abc['Cum'].map(lambda x: 'A' if x <= a_lim else ('B' if x <= a_lim + 15 else 'C'))
        
        p_matrix = df.groupby([abc_target, xyz_period])[abc_value].sum().unstack(fill_value=0.0)
        xyz_res = []
        for name, rows in p_matrix.iterrows():
            m, s = rows.mean(), rows.std(ddof=1) if len(rows) > 1 else 0.0
            kv = (s / m) * 100 if m > 0 and np.count_nonzero(rows) > 1 else 999.0
            xyz_res.append({abc_target: name, 'Класс XYZ': 'X' if kv <= x_lim else ('Y' if kv <= x_lim + 15 else 'Z')})
        
        df_m = pd.merge(df_abc[[abc_target, abc_value, 'Class_ABC']], pd.DataFrame(xyz_res), on=abc_target)
        df_m['Средний запас на складе'] = df_m[abc_value] * 1.15
        df_m['Расход за период'] = df_m[abc_value]
        df_m['Коэф. Оборачиваемости (раз)'] = (df_m['Расход за период'] / df_m['Средний запас на складе']).fillna(0).round(2)
        df_m['Оборачиваемость (в днях)'] = (selected_days / df_m['Коэф. Оборачиваемости (раз)']).replace([np.inf, -np.inf], 999).fillna(999).astype(int)
        
        pivot_m = df_m.pivot_table(index='Class_ABC', columns='Класс XYZ', values=abc_target, aggfunc='count', fill_value=0)
        
        mc1, mc2 = st.columns(2)
        with mc1: st.dataframe(pivot_m, use_container_width=True)
        with mc2: st.plotly_chart(px.imshow(pivot_m, text_auto=True, color_continuous_scale="Blues"), use_container_width=True)
        
        if st.button("✍️ Сгенерировать ИИ-отчет по матрице ABC/XYZ", key="ai_report_abc_btn"):
            ai_generate_text_report(pivot_m, "ABC/XYZ", data_context, api_key)
            
        st.dataframe(df_m.sort_values(by=abc_value, ascending=False), use_container_width=True)
    except Exception as e: st.error(f"Ошибка расчета: {e}")
def internal_show_rfm_page(filtered_df, api_key, data_context):
    st.title("👥 Модуль RFM-сегментации номенклатуры и категорий")
    if filtered_df.empty: return st.info("ℹ️ Текущий срез пуст.")
    df = filtered_df.copy()
    available_cols = list(df.columns)
    
    rfm_target = st.selectbox("Выберите анализируемое поле:", [c for c in available_cols if c not in ['Сумма', 'Количество']], key="rfm_target_select")
    rfm_value_col = st.selectbox("Выберите поле стоимости:", ['Сумма', 'Количество'], key="rfm_value_select")
    
    try:
        df[rfm_value_col] = pd.to_numeric(df[rfm_value_col], errors='coerce').fillna(0.0)
        rfm = df.groupby(str(rfm_target)).agg(F=(rfm_value_col, 'count'), M=(rfm_value_col, 'sum')).reset_index()
        rfm.columns = ['Объект Анализа', 'F', 'M']
        
        rfm['F_Score'] = pd.qcut(rfm['F'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        rfm['M_Score'] = pd.qcut(rfm['M'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        rfm['RFM'] = rfm['F_Score'] + rfm['M_Score']
        seg_counts = rfm.groupby('RFM').size().reset_index(name='Количество объектов')
        
        st.plotly_chart(px.bar(seg_counts, x='RFM', y='Количество объектов', text_auto=True, color='RFM', color_continuous_scale="Purples"), use_container_width=True)
        if st.button("👥 Сгенерировать ИИ-отчет по матрице RFM", key="ai_report_rfm_btn"):
            ai_generate_text_report(seg_counts, f"RFM ({rfm_target})", data_context, api_key)
        st.dataframe(rfm.sort_values(by='M', ascending=False), use_container_width=True)
    except Exception as e: st.error(f"Ошибка RFM: {e}")
def render_custom_chart(active_df, x_ax, y_ax, style, color, lbl, f_format, f_round, f_size, f_color, f_pos, horiz, rot, top_limit, i, date_format_type="Исходный", custom_currency="", forecast_periods=0):
    try:
        df_c = active_df.copy()
        
        # 🛡️ Продвинутая конвертация временных меток с поддержкой смешанных форматов (dayfirst=True)
        converted_dates = pd.to_datetime(df_c[x_ax], errors='coerce', dayfirst=True, format='mixed')
        check_y_dates = pd.to_datetime(df_c[y_ax], errors='coerce', dayfirst=True, format='mixed')
        
        # Автоматическая рокировка осей, если поле даты ошибочно поставили на ось Y
        if check_y_dates.notna().sum() > (0.5 * len(df_c)) and converted_dates.notna().sum() <= (0.5 * len(df_c)):
            x_ax, y_ax = y_ax, x_ax
            converted_dates = check_y_dates
            
        df_c[y_ax] = pd.to_numeric(df_c[y_ax], errors='coerce').fillna(0)
        curr_suffix = f" {custom_currency.strip()}" if custom_currency.strip() else ""
        
        scatter_pos = "top center"
        if f_pos == "inside": scatter_pos = "middle center"
        elif f_pos == "outside": scatter_pos = "top center"

        def get_formatted_text(value_array):
            labels = []
            for v in value_array:
                if f_format == "Финансовый": f_val = f"{round(v, f_round):,}".replace(",", " ") + curr_suffix
                elif f_format == "Сжатый (млн/млрд)":
                    f_val = f"{v/1e9:,.2f} млрд{curr_suffix}" if abs(v)>=1e9 else f"{v/1e6:,.2f} млн{curr_suffix}"
                else: f_val = f"{round(v, f_round):,}".replace(",", " ")
                labels.append(f_val)
            return labels

        is_date_axis = converted_dates.notna().sum() > (0.3 * len(df_c))

        if is_date_axis:
            df_c['_datetime_clean_'] = converted_dates
            # Удаляем мусорные записи дат, чтобы не ломать ось в 1970 год
            df_c = df_c.dropna(subset=['_datetime_clean_']).copy()
            df_c['_month_period_'] = df_c['_datetime_clean_'].dt.to_period('M').dt.to_timestamp()
            
            # Строго группируем и сортируем хронологически, чтобы тренд шел слева направо
            df_fact = df_c.groupby('_month_period_', as_index=False)[y_ax].sum()
            df_fact = df_fact.sort_values(by='_month_period_', ascending=True).reset_index(drop=True)
            
            if df_fact.empty:
                st.warning(f"⚠️ Не удалось извлечь валидные даты из колонки {x_ax}.")
                return
                
            chosen_pattern = {"ММ.ГГГГ (01.2014)": "%m.%Y", "Месяц ГГГГ (Янв 2014)": "%b %Y", "ДД.ММ.ГГГГ (15.01.2014)": "%d.%m.%Y", "ГГГГ (2014)": "%Y"}.get(date_format_type, "%m.%Y")
            final_x = list(df_fact['_month_period_'].dt.strftime(chosen_pattern).astype(str))
            final_y = list(df_fact[y_ax].values)
            legend_names = ["Факт"] * len(final_y)
            
            if forecast_periods > 0 and len(df_fact) > 1:
                last_value = df_fact[y_ax].iloc[-1]
                pct_changes = df_fact[y_ax].pct_change().dropna()
                avg_drop = max(pct_changes.tail(3).mean() if len(pct_changes)>=3 else pct_changes.mean(), -0.15)
                current_val = last_value
                last_date = df_fact['_month_period_'].max()
                
                for m in range(1, forecast_periods + 1):
                    next_date = last_date + pd.DateOffset(months=m)
                    current_val *= (1 + avg_drop)
                    final_x.append(next_date.strftime(chosen_pattern))
                    final_y.append(current_val)
                    legend_names.append("Прогноз ИИ")
            df_g = pd.DataFrame({x_ax: final_x, y_ax: final_y, "Тип данных": legend_names})
        else:
            df_g = df_c.groupby(x_ax, as_index=False)[y_ax].sum().sort_values(by=y_ax, ascending=False).head(top_limit).reset_index(drop=True)
            df_g["Тип данных"] = "Факт"

        fig = go.Figure()
        if "Линейный" in style or (is_date_axis and "Столбчатая" not in style and "Кольцевая" not in style and "Водопад" not in style):
            if is_date_axis and forecast_periods > 0:
                idx_split = len(df_fact) - 1
                txt_full = get_formatted_text(df_g[y_ax].values)
                fig.add_trace(go.Scatter(x=df_g[x_ax].iloc[:idx_split+1], y=df_g[y_ax].iloc[:idx_split+1], mode="lines+markers+text" if lbl else "lines+markers", name="Факт", line=dict(color=color, width=4), text=txt_full[:idx_split+1] if lbl else None, textposition=scatter_pos, textfont=dict(size=f_size, color=f_color)))
                fig.add_trace(go.Scatter(x=df_g[x_ax].iloc[idx_split:], y=df_g[y_ax].iloc[idx_split:], mode="lines+markers+text" if lbl else "lines+markers", name="Прогноз ИИ", line=dict(color="#ff4b4b", width=4, dash="dash"), text=txt_full[idx_split:] if lbl else None, textposition=scatter_pos, textfont=dict(size=f_size, color=f_color)))
            else:
                txt = get_formatted_text(df_g[y_ax].values)
                fig.add_trace(go.Scatter(x=df_g[x_ax], y=df_g[y_ax], mode="lines+markers+text" if lbl else "lines+markers", name="Факт", line=dict(color=color, width=4), text=txt if lbl else None, textposition=scatter_pos, textfont=dict(size=f_size, color=f_color)))
        elif "Столбчатая" in style:
            safe_pos = f_pos if f_pos in ["inside", "outside", "auto"] else "auto"
            if horiz:
                df_g = df_g.iloc[::-1].reset_index(drop=True) if is_date_axis else df_g.sort_values(by=y_ax, ascending=True).reset_index(drop=True)
                fig.add_trace(go.Bar(y=df_g[x_ax].astype(str), x=df_g[y_ax].values, text=get_formatted_text(df_g[y_ax].values) if lbl else None, textposition=safe_pos, orientation="h", marker_color=color, textfont=dict(size=f_size, color=f_color)))
            else:
                fig.add_trace(go.Bar(x=df_g[x_ax].astype(str), y=df_g[y_ax].values, text=get_formatted_text(df_g[y_ax].values) if lbl else None, textposition=safe_pos, orientation="v", marker_color=color, textfont=dict(size=f_size, color=f_color)))
        elif "Кольцевая" in style:
            fig.add_trace(go.Pie(labels=df_g[x_ax], values=df_g[y_ax], hole=0.4, rotation=rot, textinfo="label+value" if lbl else "none", texttemplate="%{label}<br>%{text}" if lbl else None, text=get_formatted_text(df_g[y_ax].values), textfont=dict(size=f_size, color=f_color)))
        elif "Водопад" in style:
            fig.add_trace(go.Waterfall(x=list(df_g[x_ax].astype(str)) + ["ИТОГО"], y=list(df_g[y_ax]) + [df_g[y_ax].sum()], text=get_formatted_text(df_g[y_ax].values) + get_formatted_text([df_g[y_ax].sum()]), textposition=f_pos if f_pos in ["inside", "outside", "auto"] else "auto", measure=["relative"] * len(df_g[y_ax]) + ["total"], increasing={"marker": {"color": color}}, textfont=dict(size=f_size, color=f_color)))

        fig.update_layout(yaxis=dict(type='category' if (horiz and "Столбчатая" in style) else None), xaxis=dict(type='category' if not (horiz and "Столбчатая" in style) else None, tickangle=45), showlegend=True, margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig, use_container_width=True, key=f"p_{i}")
    except Exception as chart_err: st.error(f"Ошибка графика №{i+1}: {chart_err}")
def power_query_clean_engine(uploaded_files_list, gemini_key):
    frames = []
    for f in uploaded_files_list:
        try:
            # Автоматическое угадывание разделителя (запятая/точка с запятой)
            if f.name.endswith('.csv'):
                df = pd.read_csv(f, dtype=str, sep=None, engine='python', encoding='utf-8')
            else:
                df = pd.read_excel(f, dtype=str, engine='openpyxl')
                
            raw_cols = [str(c).strip() for c in df.columns]
            ai_map = ai_column_mapper_engine(raw_cols, gemini_key)
            mapped = []
            for col in raw_cols:
                if col in ai_map: mapped.append(ai_map[col])
                else:
                    c_low = col.lower()
                    if any(w in c_low for w in ['озм', 'код материала', 'номенклатур']): mapped.append('ОЗМ')
                    elif any(w in c_low for w in ['наименование', 'материал']): mapped.append('Наименование материала')
                    elif any(w in c_low for w in ['количество', 'кол-во', 'объем']): mapped.append('Количество')
                    elif any(w in c_low for w in ['сумма', 'стоимость', 'цена']): mapped.append('Сумма')
                    else: mapped.append(col)
            df.columns = mapped
            df = df.loc[:, ~df.columns.str.contains('^Без названия|^Unnamed|^Unnamed:')].loc[:, ~df.columns.duplicated()]
            frames.append(df.dropna(how='all'))
        except Exception as file_err: st.sidebar.error(f"Ошибка файла {f.name}: {file_err}")
            
    if not frames: return pd.DataFrame()
    base_df = pd.concat(frames, ignore_index=True, join='outer')
    for c in ['Количество', 'Сумма']:
        if c in base_df.columns: base_df[c] = pd.to_numeric(base_df[c].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.'), errors='coerce').fillna(0.0)
    return base_df.dropna(how='all')
# Инициализация сессий
if "manual_charts" not in st.session_state: st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state: st.session_state.manual_cards = 1
if "main_df" not in st.session_state: st.session_state.main_df = pd.DataFrame()

st.sidebar.markdown("### 🤖 Интеллектуальный ИИ-Ассистент")
gemini_api_key = st.sidebar.text_input("Введите Gemini API Key:", type="password")
ai_context_mode = st.sidebar.selectbox("Тип данных (Контекст для AI):", ["📅 Закупки", "📦 Запасы", "📉 Расход", "💰 Продажи"])

uploaded_files = st.file_uploader("Загрузите файлы Excel/CSV:", type=["csv", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    if st.session_state.main_df.empty:
        with st.spinner("⏳ Идёт глубокая сборка данных..."):
            calc_df = power_query_clean_engine(uploaded_files, gemini_api_key)
            if not calc_df.empty: st.session_state.main_df = calc_df
            
    main_df = st.session_state.main_df
    if not main_df.empty:
        if st.sidebar.button("♻️ Сбросить/Очистить базу данных"):
            st.session_state.main_df = pd.DataFrame()
            st.rerun()
            
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)
        f_col1 = st.sidebar.selectbox("Поле среза №1:", all_cols, key="fl_c1")
        act_df = main_df.copy()
        if f_col1 != "-- Выберите заголовок --":
            u_v1 = ["-- Все значения --"] + list(act_df[f_col1].astype(str).unique())
            f_v1 = st.sidebar.selectbox("Значение среза №1:", u_v1, key="fl_v1")
            if f_v1 != "-- Все значения --": act_df = act_df[act_df[f_col1].astype(str) == str(f_v1)]
        
        page = st.sidebar.radio("Перейти к разделу:", ["🗂️ 1. Загрузка и очистка данных", "📊 2. Executive Диаграммы", "🗮️ 3. ABC/XYZ-аналитика ОЗМ", "👥 4. RFM-сегментация"])
        
        if "1. Загрузка и очистка данных" in page:
            st.success(f"📊 База сформирована! Строк: {len(act_df):,}")
            st.dataframe(act_df.head(100), use_container_width=True)
            
        elif "2. Executive Диаграммы" in page:
            st.title("📊 Интерактивная BI-Панель Показателей")
            
            # 🔥 ОБНОВЛЕНО: Интерактивный конструктор KPI-карточек с выбором представления данных
            st.markdown("### 🎴 Конструктор KPI Карточек")
            card_cols = st.columns(st.session_state.manual_cards)
            for j in range(st.session_state.manual_cards):
                with card_cols[j]:
                    with st.container(border=True):
                        c_title = st.text_input(f"Название KPI #{j+1}:", f"Показатель {j+1}", key=f"ct_{j}")
                        c_val_col = st.selectbox(f"Поле расчета #{j+1}:", [c for c in all_cols if c != "-- Выберите заголовок --"], key=f"cv_{j}")
                        c_agg = st.selectbox(f"Функция #{j+1}:", ["Сумма (SUM)", "Количество строк (COUNT)", "Уникальных (NUNIQUE)", "Среднее (MEAN)"], key=f"ca_{j}")
                        
                        # Добавленные селекторы представления данных для карточки
                        c_fmt = st.selectbox(f"Представление #{j+1}:", ["Числовой", "Финансовый", "Сжатый (млн/млрд)"], key=f"cfmt_{j}")
                        c_curr = st.text_input(f"Валюта/Знак #{j+1}:", value="₸", key=f"ccur_{j}")
                        
                        try:
                            if c_agg == "Сумма (SUM)":
                                val = pd.to_numeric(act_df[c_val_col], errors='coerce').sum()
                            elif c_agg == "Количество строк (COUNT)":
                                val = act_df[c_val_col].count()
                            elif c_agg == "Уникальных (NUNIQUE)":
                                val = act_df[c_val_col].nunique()
                            else:
                                val = pd.to_numeric(act_df[c_val_col], errors='coerce').mean()
                            
                            # Логика форматирования представления данных в карточке
                            suffix = f" {c_curr.strip()}" if c_curr.strip() else ""
                            if c_fmt == "Финансовый":
                                formatted_value = f"{round(val, 0):,}".replace(",", " ") + suffix
                            elif c_fmt == "Сжатый (млн/млрд)":
                                if abs(val) >= 1e9:
                                    formatted_value = f"{val/1e9:,.2f} млрд{suffix}"
                                elif abs(val) >= 1e6:
                                    formatted_value = f"{val/1e6:,.2f} млн{suffix}"
                                else:
                                    formatted_value = f"{round(val, 2):,}".replace(",", " ") + suffix
                            else:
                                formatted_value = f"{round(val, 2):,}".replace(",", " ")
                                
                            st.metric(label=c_title, value=formatted_value)
                        except:
                            st.metric(label=c_title, value="0")
            
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("➕ Добавить KPI карточку"):
                    st.session_state.manual_cards += 1
                    st.rerun()
            with cc2:
                if st.button("➖ Удалить карточку") and st.session_state.manual_cards > 1:
                    st.session_state.manual_cards -= 1
                    st.rerun()
            st.markdown("---")
            
            # 📊 Настройка диаграмм с автосортировкой дат
            st.markdown("### 📈 Настройка диаграмм")
            for i in range(st.session_state.manual_charts):
                c1, c2, c3, c4 = st.columns(4)
                with c1: style = st.selectbox(f"Тип №{i+1}:", ["Линейный тренд (Line)", "Столбчатая диаграмма (Bar)", "Кольцевая долей (Donut)", "Диаграмма Водопад (Waterfall)"], key=f"s_{i}")
                with c2: x_ax = st.selectbox(f"Ось X №{i+1}:", all_cols, key=f"x_{i}")
                with c3: y_ax = st.selectbox(f"Ось Y №{i+1}:", all_cols, key=f"y_{i}")
                with c4: color = st.color_picker(f"Цвет №{i+1}:", "#1f77b4", key=f"col_{i}")
                with st.expander("🎨 Настройки отображения"):
                    lbl_g = st.checkbox("Показывать значения", value=True, key=f"lbl_{i}")
                    f_format = st.selectbox("Формат:", ["Числовой", "Финансовый", "Сжатый (млн/млрд)"], key=f"fmt_{i}")
                    f_round = st.slider("Округление:", 0, 4, 0, key=f"rnd_{i}")
                    f_size = st.slider("Шрифт (px):", 8, 24, 14, key=f"sz_{i}")
                    f_color = st.color_picker("Цвет:", "#000000", key=f"fcol_{i}")
                    f_curr_text = st.text_input("Валюта:", value="₸", key=f"fcur_tx_{i}")
                    f_pos = st.selectbox("Положение:", ["auto", "inside", "outside"], key=f"pos_{i}")
                    horiz = st.checkbox("Горизонтально", value=False, key=f"h_{i}") if "Bar" in style else False
                    rot = st.slider("🔄 Поворот:", 0, 360, 0, step=15, key=f"rot_{i}") if "Donut" in style else 0
                    top_limit = st.slider("🔝 ТОП:", 5, 200, 15, key=f"top_{i}")
                    d_fmt = st.selectbox("Формат даты:", ["Исходный", "ММ.ГГГГ (01.2014)", "Месяц ГГГГ (Янв 2014)"], key=f"dfmt_{i}")
                    f_cast = st.slider("🔮 Прогноз:", 0, 5, 0, key=f"fcast_{i}")
                if x_ax != "-- Выберите заголовок --" and y_ax != "-- Выберите заголовок --":
                    render_custom_chart(act_df, x_ax, y_ax, style, color, lbl_g, f_format, f_round, f_size, f_color, f_pos, horiz, rot, top_limit, i, date_format_type=d_fmt, custom_currency=f_curr_text, forecast_periods=f_cast)
            if st.button("➕ Добавить диаграмму"):
                st.session_state.manual_charts += 1
                st.rerun()
        elif "3. ABC/XYZ-аналитика ОЗМ" in page:
            internal_show_abc_xyz_page(act_df, gemini_api_key, ai_context_mode)
        elif "4. RFM-сегментация" in page:
            internal_show_rfm_page(act_df, gemini_api_key, ai_context_mode)
else:
    st.info("📊 Ожидание загрузки любых файлов Excel/CSV...")
