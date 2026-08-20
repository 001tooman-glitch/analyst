import streamlit as st
import pandas as pd
import io
import json
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from google import genai
from google.genai import types

# Инициализация настроек страницы на самом старте скрипта
st.set_page_config(layout="wide", page_title="BI Enterprise Platform")
# 🤖 МОДУЛЬ 1: ИИ-АВТОМАППИНГ С ОПТИМИЗАЦИЕЙ И КЭШЕМ
@st.cache_data(show_spinner=False)
def ai_column_mapper_engine(raw_columns_list, api_key):
    if not api_key: 
        return {}
    try:
        client = genai.Client(api_key=api_key)
        sys_instruction = (
            "Ты — BI-аналитик. Сопоставь заголовки закупщика с полями: "
            "'ОЗМ', 'Наименование материала', 'Количество', 'Сумма'. "
            "Возвращай СТРОГО JSON-словарь, где ключ - исходная колонка, а значение - новая."
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Выполни маппинг списка заголовков: {str(raw_columns_list)}",
            config=types.GenerateContentConfig(
                system_instruction=sys_instruction,
                response_mime_type="application/json",
                temperature=0.1
            ),
        )
        mapping_result = json.loads(response.text)
        return mapping_result
    except Exception as e:
        return {}
# 🧠 МОДУЛЬ 2: УЛЬТРА-ГИБКИЙ ИИ-АНАЛИЗАТОР С ФУНКЦИЕЙ СКАЧИВАНИЯ ОТЧЕТА
def ai_generate_text_report(pivot_matrix_df, report_type="ABC/XYZ", data_context="Расход", api_key=None):
    if not api_key: 
        return st.warning("⚠️ Введите API Key Gemini в сайдбаре.")
    try:
        client = genai.Client(api_key=api_key)
        
        context_mapping = {
            "Закупки": "Данные — это ПЛАНИРУЕМЫЕ ЗАКУПКИ / БИЗНЕС-ПЛАНЫ. Группа AZ — это стратегические контракты (риск срыва сроков проектов). Группа CZ — мелкая операционная текучка (риск бюрократии, недоосвоения бюджета).",
            "Запасы": "Данные — это СУЩЕСТВУЮЩИЕ СКЛАДСКИЕ ЗАПАСЫ. Группа AZ — это жестко замороженный рабочий капитал предприятия (дорогие ТМЦ без движения). Группа CZ — складской хлам, неликвиды, забивающие полки.",
            "Расход": "Данные — это РЕАЛЬНЫЙ ФАКТИЧЕСКИЙ РАСХОД / ПОТРЕБЛЕНИЕ. Группа AZ — это внеплановые, аварийные ремонты оборудования, сжигающие огромный бюджет. Группа CZ — административная нагрузка мелких заявок."
        }
        
        context_rules = next((v for k, v in context_mapping.items() if k in data_context), 
                             "Данные — это КОММЕРЧЕСКИЕ ПРОДАЖИ / СБЫТ / РИТЕЙЛ. Группа AZ — это товары-локомотивы, генерирующие 80% выручки (риск упущенной прибыли). Группа CZ — длинный хвост ассортимента с низким чеком.")

        system_instruction = f"""
        Ты — директор по логистике и снабжению комбината. Напиши аналитический отчет для генерального директора по матрице {report_type}.
        БИЗНЕС-КОНТЕКСТ ДАННЫХ: {context_rules}
        
        СТРОГИЕ ПРАВИЛА ОФОРМЛЕНИЯ:
        - НАЧИНАЙ ОТЧЕТ СРАЗУ с содержательного анализа (Раздел "1. Анализ текущего процесса").
        - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать метаданные документа: "Генеральному директору", "От:", "Дата:", "Тема:", приветствия или вводные подписи.
        
        Структура отчета: 1. Анализ текущего процесса ({data_context}). 2. Выявление скрытых аномалий и рисков (оцени группы AZ и CZ). 3. Рекомендации. Пиши емко, списками Markdown. Используй деловой снабженческий сленг.
        """
        with st.spinner(f"🔮 ИИ генерирует чистый отчет для контекста '{data_context}'..."):
            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=f"Матрица плотности ({data_context}):\n{pivot_matrix_df.to_string()}", 
                config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.2)
            )
            report_text = response.text
            st.markdown("---")
            st.markdown(f"### 📝 Аналитический ИИ-Отчет: {data_context} ({report_type})")
            st.info(report_text)
            
            st.download_button(
                label="📥 Скачать аналитическое заключение ИИ (.txt)",
                data=report_text,
                file_name=f"ai_report_{report_type.lower().replace('/', '_')}.txt",
                mime="text/plain"
            )
    except Exception as report_err: 
        st.error(f"❌ Ошибка ИИ: {report_err}")
# 🧮 МОДУЛЬ 3: УНИВЕРСАЛЬНЫЙ КОНСТРУКТОР ABC/XYZ
def internal_show_abc_xyz_page(filtered_df, api_key, data_context):
    st.title("🧮 Универсальный Конструктор матриц ABC/XYZ")
    if filtered_df.empty: 
        return st.info("ℹ️ Выборка пуста. Загрузите файлы.")
    
    df = filtered_df.copy()
    available_cols = list(df.columns)
    
    c1, c2, c3 = st.columns(3)
    with c1: abc_target = st.selectbox("1. Объект анализа:", [c for c in available_cols if c not in ['Сумма', 'Количество']], key="abc_t")
    with c2: abc_value = st.selectbox("2. Критерий масштаба:", [c for c in ['Сумма', 'Количество'] if c in available_cols] + available_cols, key="abc_v")
    with c3: xyz_period = st.selectbox("3. Шкала времени:", [c for c in available_cols if c != abc_target], key="xyz_p")
    
    a_lim = st.slider("Граница группы A (%):", 50, 90, 80, key="abc_s")
    x_lim = st.slider("Граница group_X (KV ≤ %):", 5, 20, 10, key="xyz_s")
    
    try:
        df[abc_value] = pd.to_numeric(df[abc_value], errors='coerce').fillna(0.0)
        df = df[(df[abc_target].astype(str).str.strip() != "") & (df[xyz_period].astype(str).str.strip() != "")]
        
        df_abc = df.groupby(abc_target, as_index=False)[abc_value].sum().sort_values(by=abc_value, ascending=False).reset_index(drop=True)
        total_sum = df_abc[abc_value].sum()
        if total_sum == 0: 
            return st.warning("Сумма значений равна нулю. Расчет невозможен.")
            
        df_abc['Cum'] = (df_abc[abc_value] / total_sum).cumsum() * 100
        df_abc['Class_ABC'] = df_abc['Cum'].map(lambda x: 'A' if x <= a_lim else ('B' if x <= a_lim + 15 else 'C'))
        
        p_matrix = df.groupby([abc_target, xyz_period])[abc_value].sum().unstack(fill_value=0.0)
        xyz_res = []
        for name, rows in p_matrix.iterrows():
            m = rows.mean()
            s = rows.std(ddof=1) if len(rows) > 1 else 0.0
            kv = (s / m) * 100 if m > 0 and np.count_nonzero(rows) > 1 else 999.0
            xyz_res.append({abc_target: name, 'KV': kv, 'Класс XYZ': 'X' if kv <= x_lim else ('Y' if kv <= x_lim + 15 else 'Z')})
        
        df_m = pd.merge(df_abc[[abc_target, abc_value, 'Class_ABC']], pd.DataFrame(xyz_res), on=abc_target)
        
        raw_pivot = df_m.pivot_table(index='Class_ABC', columns='Класс XYZ', values=abc_target, aggfunc='count', fill_value=0)
        pivot_m = pd.DataFrame(0, index=['A', 'B', 'C'], columns=['X', 'Y', 'Z'])
        for idx in pivot_m.index:
            for col in pivot_m.columns:
                if idx in raw_pivot.index and col in raw_pivot.columns:
                    pivot_m.loc[idx, col] = raw_pivot.loc[idx, col]
                    
        mc1, mc2 = st.columns(2)
        with mc1: st.dataframe(pivot_m, use_container_width=True)
        with mc2: st.plotly_chart(px.imshow(pivot_m, text_auto=True, color_continuous_scale="Blues"), use_container_width=True)
        
        if st.button("✍️ Сгенерировать ИИ-отчет по матрице ABC/XYZ", key="ai_report_abc_btn"):
            ai_generate_text_report(pivot_m, report_type="ABC/XYZ", data_context=data_context, api_key=api_key)
            
        st.dataframe(df_m.sort_values(by=abc_value, ascending=False), use_container_width=True)
        
        towrite = io.BytesIO()
        df_m.to_excel(towrite, index=False, engine='openpyxl')
        st.download_button(label="📥 Скачать результаты аналитики в Excel", data=towrite.getvalue(), file_name="abc_xyz_output.xlsx", mime="application/vnd.ms-excel")
        
    except Exception as e: 
        st.error(f"Ошибка расчета ABC/XYZ: {e}")
# 👥 МОДУЛЬ 4: УНИВЕРСАЛЬНЫЙ КОНСТРУКТОР RFM С ДИНАМИЧЕСКИМ ВЫБОРОМ КОЛОНОК
def internal_show_rfm_page(filtered_df, api_key, data_context):
    st.title("👥 Модуль RFM-сегментации номенклатуры и категорий")
    if filtered_df.empty: 
        return st.info("ℹ️ Текущий срез пуст. Выберите другие фильтры в сайдбаре.")
    df = filtered_df.copy()
    available_cols = list(df.columns)
    
    st.markdown("### 🎯 Настройка объекта сегментации")
    
    rc1, rc2 = st.columns(2)
    with rc1:
        rfm_target = st.selectbox("Выберите анализируемое поле:", [c for c in available_cols if c not in ['Сумма', 'Количество']], key="rfm_target_select")
    with rc2:
        detected_sum_col = 'Сумма' if 'Сумма' in available_cols else (available_cols if available_cols else None)
        rfm_value_col = st.selectbox("Выберите поле стоимости/суммы:", available_cols, index=available_cols.index(detected_sum_col) if detected_sum_col in available_cols else 0, key="rfm_value_select")
    
    try:
        df[rfm_value_col] = pd.to_numeric(df[rfm_value_col], errors='coerce').fillna(0.0)
        rfm = df.groupby(str(rfm_target)).agg(F=(rfm_value_col, 'count'), M=(rfm_value_col, 'sum')).reset_index()
        rfm.columns = ['Объект Анализа', 'F', 'M']
        
        if len(rfm) < 3 or rfm['F'].nunique() <= 1 or rfm['M'].nunique() <= 1:
            st.warning("⚠️ Недостаточно уникальных данных в выбранных полях для разделения на квантили (qcut). Выведен общий список.")
            st.dataframe(rfm.sort_values(by='M', ascending=False), use_container_width=True)
            return

        rfm['F_Score'] = pd.qcut(rfm['F'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        rfm['M_Score'] = pd.qcut(rfm['M'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        rfm['RFM'] = rfm['F_Score'] + rfm['M_Score']
        seg_counts = rfm.groupby('RFM').size().reset_index(name='Количество объектов')
        
        st.plotly_chart(px.bar(seg_counts, x='RFM', y='Количество объектов', text_auto=True, title=f"📊 Динамическое RFM-распределение по полю: {rfm_target}", color='RFM', color_continuous_scale="Purples"), use_container_width=True)
        
        if st.button("👥 Сгенерировать ИИ-отчет по матрице RFM", key="ai_report_rfm_btn"):
            ai_generate_text_report(seg_counts, report_type=f"RFM-Сегментации ({rfm_target})", data_context=data_context, api_key=api_key)
            
        st.dataframe(rfm.sort_values(by='M', ascending=False), use_container_width=True)
    except Exception as rfe: 
        st.error(f"❌ Ошибка расчета RFM: {rfe}")
# 📊 ФУНКЦИЯ 5: ГРАФИЧЕСКИЙ ДВИЖОК С АВТОМАТИЧЕСКОЙ ЗАЩИТОЙ ИЗОЛЯЦИИ ВЕРТИКАЛЬНЫХ И ГОРИЗОНТАЛЬНЫХ СЛОЕВ В BAR
def render_custom_chart(active_df, x_ax, y_ax, style, color, lbl, f_format, f_round, f_size, f_color, f_pos, horiz, rot, top_limit, i, date_format_type="Исходный", custom_currency="", forecast_periods=0):
    try:
        df_c = active_df.copy()
        df_c[y_ax] = pd.to_numeric(df_c[y_ax], errors='coerce').fillna(0)
        
        clean_currency = str(custom_currency).strip()
        curr_suffix = f" {clean_currency}" if clean_currency else ""
        
        scatter_pos = f_pos
        if "Line" in style or forecast_periods > 0 or (pd.to_datetime(df_c[x_ax], errors='coerce').notna().sum() > (0.5 * len(df_c))):
            if scatter_pos in ["inside", "outside", "auto"]:
                scatter_pos = "top center"

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

        converted_dates = pd.to_datetime(df_c[x_ax], errors='coerce')
        is_date_axis = converted_dates.notna().sum() > (0.5 * len(df_c))
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
            
            if forecast_periods > 0 and len(df_fact) > 1:
                last_value = df_fact[y_ax].iloc[-1]
                pct_changes = df_fact[y_ax].pct_change().dropna()
                avg_drop = pct_changes.tail(3).mean() if len(pct_changes) >= 3 else pct_changes.mean()
                if avg_drop < 0: avg_drop = max(avg_drop, -0.15)
                
                date_diffs = df_fact['_month_period_'].diff().dropna()
                is_yearly_data = date_diffs.dt.days.mean() > 300
                
                current_val = last_value
                last_date = df_fact['_month_period_'].max()
                
                for m in range(1, forecast_periods + 1):
                    next_date = last_date + pd.DateOffset(years=m) if is_yearly_data else last_date + pd.DateOffset(months=m)
                    current_val = current_val * (1 + avg_drop)
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
                
                fig.add_trace(go.Scatter(x=df_g[x_ax].iloc[:idx_split+1], y=df_g[y_ax].iloc[:idx_split+1], mode="lines+markers+text" if lbl else "lines+markers", name="Факт", line=dict(color=color, width=4), marker=dict(size=8), text=txt_full[:idx_split+1] if lbl else None, textposition=scatter_pos, textfont=dict(size=f_size, color=f_color)))
                fig.add_trace(go.Scatter(x=df_g[x_ax].iloc[idx_split:], y=df_g[y_ax].iloc[idx_split:], mode="lines+markers+text" if lbl else "lines+markers", name="Прогноз ИИ", line=dict(color="#ff4b4b", width=4, dash="dash"), marker=dict(size=8, symbol="diamond"), text=txt_full[idx_split:] if lbl else None, textposition=scatter_pos, textfont=dict(size=f_size, color=f_color)))
            else:
                txt = get_formatted_text(df_g[y_ax].values)
                fig.add_trace(go.Scatter(x=df_g[x_ax], y=df_g[y_ax], mode="lines+markers+text" if lbl else "lines+markers", name="Факт", line=dict(color=color, width=4), marker=dict(size=8), text=txt if lbl else None, textposition=scatter_pos, textfont=dict(size=f_size, color=f_color)))
                
        elif "Столбчатая" in style:
            safe_pos = f_pos if f_pos in ["inside", "outside", "auto"] else "auto"
            if horiz:
                if is_date_axis: df_g = df_g.iloc[::-1].reset_index(drop=True)
                else: df_g = df_g.sort_values(by=y_ax, ascending=True).reset_index(drop=True)
                txt = get_formatted_text(df_g[y_ax].values)
                fig.add_trace(go.Bar(y=df_g[x_ax].astype(str), x=df_g[y_ax].values, text=txt if lbl else None, textposition=safe_pos, orientation="h", marker_color=color, textfont=dict(size=f_size, color=f_color)))
            else:
                txt = get_formatted_text(df_g[y_ax].values)
                fig.add_trace(go.Bar(x=df_g[x_ax].astype(str), y=df_g[y_ax].values, text=txt if lbl else None, textposition=safe_pos, orientation="v", marker_color=color, textfont=dict(size=f_size, color=f_color)))
                
        elif "Кольцевая" in style:
            donut_pos = f_pos if f_pos in ["inside", "outside", "auto"] else "auto"
            txt = get_formatted_text(df_g[y_ax].values)
            fig.add_trace(go.Pie(labels=df_g[x_ax], values=df_g[y_ax], hole=0.4, rotation=rot, textinfo="label+value" if lbl else "none", textposition=donut_pos, texttemplate="%{label}<br>%{text}" if lbl else None, text=txt, textfont=dict(size=f_size, color=f_color)))
            
        elif "Водопад" in style:
            safe_pos = f_pos if f_pos in ["inside", "outside", "auto"] else "auto"
            txt = get_formatted_text(df_g[y_ax].values)
            fig.add_trace(go.Waterfall(x=list(df_g[x_ax].astype(str)) + ["ИТОГО"], y=list(df_g[y_ax]) + [df_g[y_ax].sum()], text=txt + [f"{df_g[y_ax].sum():,}"], textposition=safe_pos, measure=["relative"] * len(df_g[y_ax]) + ["total"], increasing={"marker": {"color": color}}, textfont=dict(size=f_size, color=f_color)))

        if horiz and "Столбчатая" in style: fig.update_layout(yaxis=dict(type='category'), xaxis=dict(showgrid=True))
        else: fig.update_layout(xaxis=dict(type='category', tickangle=45), yaxis=dict(showgrid=True))
            
        fig.update_layout(showlegend=True, margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig, use_container_width=True, key=f"p_{i}")
    except Exception as chart_err:
        st.error(f"Ошибка графика №{i+1}: {chart_err}")
# 🛠️ ДВИЖОК ОЧИСТКИ И СБОРКИ ДАННЫХ (POWER QUERY MERGE ENGINE)
def power_query_clean_engine(uploaded_files_list, gemini_key):
    frames = []
    for f in uploaded_files_list:
        try:
            df = pd.read_csv(f, dtype=str) if f.name.endswith('.csv') else pd.read_excel(f, dtype=str, engine='calamine')
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
        except Exception as file_err:
            st.sidebar.error(f"Ошибка файла {f.name}: {file_err}")
            
    if not frames: return pd.DataFrame()
    
    # ⚙️ ИСПРАВЛЕНО: Клонируем первый Pandas DataFrame из списка frames для избавления от AttributeError
    base_df = frames[0].copy()
    
    for extra_df in frames[1:]:
        common_keys = list(set(base_df.columns) & set(extra_df.columns))
        common_keys = [k for k in common_keys if k not in ['Сумма', 'Количество']]
        if common_keys:
            base_df = pd.merge(base_df, extra_df, on=common_keys, how='outer')
        else:
            base_df = pd.concat([base_df, extra_df], ignore_index=True, join='outer')
            
    for c in ['Количество', 'Сумма']:
        if c in base_df.columns: 
            base_df[c] = pd.to_numeric(base_df[c].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.'), errors='coerce').fillna(0.0)
    return base_df.dropna(how='all')
# ⚙️ ИНИЦИАЛИЗАЦИЯ И СТАТИЧЕСКИЕ КОЛЛБЭКИ ВМЕСТО ST.RERUN
if "manual_charts" not in st.session_state: st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state: st.session_state.manual_cards = 1
if "main_df" not in st.session_state: st.session_state.main_df = pd.DataFrame()

def add_chart_cb(): st.session_state.manual_charts += 1
def remove_chart_cb(): 
    if st.session_state.manual_charts > 1: st.session_state.manual_charts -= 1
def add_card_cb(): st.session_state.manual_cards += 1
def remove_card_cb(): 
    if st.session_state.manual_cards > 1: st.session_state.manual_cards -= 1

st.sidebar.markdown("### 🤖 Интеллектуальный ИИ-Ассистент")
gemini_api_key = st.sidebar.text_input("Введите Gemini API Key:", type="password")

ai_context_mode = st.sidebar.selectbox("Тип данных (Контекст для AI):", [
    "📅 Закупки (Планируемые) / Бизнес-планы материалов и услуг", 
    "📦 Запасы (Складские остатки / ТМЦ без движения)", 
    "📉 Расход (Реальное потребление / Выдача в производство)", 
    "💰 Продажи / Сбыт (Коммерческий оборот и ритейл)"
])

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
            st.session_state.manual_charts = 1
            st.session_state.manual_cards = 1
            st.rerun()
            
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)
        f_col1 = st.sidebar.selectbox("Поле среза №1:", all_cols, key="fl_c1")
        act_df = main_df.copy()
        if f_col1 != "-- Выберите заголовок --":
            u_v1 = ["-- Все значения --"] + list(act_df[f_col1].astype(str).unique())
            f_v1 = st.sidebar.selectbox("Значение среза №1:", u_v1, key="fl_v1")
            if f_v1 != "-- Все значения --": act_df = act_df[act_df[f_col1].astype(str) == str(f_v1)]
        
        page = st.sidebar.radio("Перейти к разделу:", ["🗂️ 1. Загрузка и очистка данных", "📊 2. Executive Диаграммы", "🧮 3. ABC/XYZ-аналитика ОЗМ", "👥 4. RFM-сегментация"])
        
        def show_page_1(dataframe_input, columns_input):
            st.success(f"📊 База сформирована! Строк: {len(dataframe_input):,}")
            cp = st.number_input(f"Страница (из {(len(dataframe_input) // 50) + 1}):", min_value=1, value=1, step=1)
            st.dataframe(dataframe_input.iloc[(cp - 1) * 50: cp * 50], height=350, use_container_width=True)
            
        def show_page_2(dataframe_input, columns_input):
            st.title("📊 Интерактивная BI-Панель Показателей")
            card_cols = st.columns(st.session_state.manual_cards)
            for j in range(st.session_state.manual_cards):
                with card_cols[j % len(card_cols)]:
                    st.markdown(f"**📌 Карточка № {j+1}**")
                    t_col = st.selectbox(f"Поле метрики (Числовое):", columns_input, key=f"c_t_{j}")
                    c_mode = st.selectbox(f"Агрегация:", ["Сумма", "Среднее"], key=f"c_m_{j}")
                    st.markdown("---")
                    group_col = st.selectbox(f"Группировать по полю:", ["-- Без фильтра --"] + columns_input, key=f"c_g_{j}")
                    filter_value = None
                    if group_col != "-- Без фильтра --":
                        unique_vals = list(act_df[group_col].astype(str).unique())
                        filter_value = st.selectbox(f"Значение элемента:", unique_vals, key=f"c_v_{j}")
                    
                    with st.expander("🎨 Настройки отображения"):
                        c_fmt = st.selectbox("Формат:", ["Числовой", "Финансовый", "Сжатый (млн/млрд)"], key=f"c_f_{j}")
                        c_curr_text = st.text_input("Валюта/Ед. изм. (вручную):", value="₸", key=f"c_cur_{j}")
                        curr_sym = f" {c_curr_text.strip()}" if c_curr_text.strip() else ""
                        c_rnd = st.slider("Округление:", 0, 4, 2, key=f"c_r_{j}")
                        c_sz = st.slider("Шрифт (px):", 16, 48, 26, key=f"c_s_{j}")
                    
                    if t_col != "-- Выберите заголовок --":
                        try:
                            df_card = act_df.copy()
                            if group_col != "-- Без фильтра --" and filter_value is not None:
                                df_card = df_card[df_card[group_col].astype(str) == str(filter_value)]
                            df_card[t_col] = pd.to_numeric(df_card[t_col], errors='coerce').fillna(0)
                            cv = df_card[t_col].sum() if "Сумма" in c_mode else df_card[t_col].mean()
                            if c_fmt == "Финансовый": lbl = f"{round(cv, c_rnd):,}".replace(",", " ") + curr_sym
                            elif c_fmt == "Сжатый (млн/млрд)":
                                if abs(cv) >= 1_000_000_000: lbl = f"{cv / 1_000_000_000:,.2f} млрд{curr_sym}"
                                else: lbl = f"{cv / 1_000_000:,.2f} млн{curr_sym}"
                            else: lbl = f"{round(cv, c_rnd):,}".replace(",", " ")
                            card_title = f"{t_col}"
                            if group_col != "-- Без фильтра --": card_title += f" ({filter_value})"
                            st.markdown(f'<div style="background-color:#f8f9fa; border:1px solid #dee2e6; border-radius:10px; padding:20px; text-align:center; margin-bottom:15px;"><div style="color:#6c757d; font-size:13px; font-weight:bold; height:40px; display:flex; align-items:center; justify-content:center;">{card_title}</div><div style="color:#1f77b4; font-size:{c_sz}px; font-weight:bold;">{lbl}</div></div>', unsafe_allow_html=True)
                        except: pass
                            
            cc1, cc2 = st.columns(2)
            with cc1: st.button("➕ Добавить карточку", on_click=add_card_cb)
            with cc2: st.button("🗑️ Удалить карточку", on_click=remove_card_cb)
            st.markdown("---")
            st.subheader("🛠️ No-Code Конструктор Графиков")
            for i in range(st.session_state.manual_charts):
                c1, c2, c3, c4 = st.columns(4)
                with c1: style = st.selectbox(f"Тип №{i+1}:", ["Столбчатая диаграмма (Bar)", "Линейный тренд (Line)", "Кольцевая долей (Donut)", "Диаграмма Водопад (Waterfall)"], key=f"s_{i}")
                with c2: x_ax = st.selectbox(f"Ось X №{i+1}:", columns_input, key=f"x_{i}")
                with c3: y_ax = st.selectbox(f"Ось Y №{i+1}:", columns_input, key=f"y_{i}")
                with c4: color = st.color_picker(f"Цвет №{i+1}:", "#1f77b4", key=f"col_{i}")
                with st.expander("🎨 Настройки надписей и Временной оси"):
                    cu1, cu2, cu3 = st.columns(3)
                    with cu1:
                        lbl_g = st.checkbox("Показывать значения", value=True, key=f"lbl_{i}")
                        f_format = st.selectbox("Формат надписей:", ["Числовой", "Финансовый", "Сжатый (млн/млрд)"], key=f"fmt_{i}")
                        f_round = st.slider("Округление:", 0, 4, 0, key=f"rnd_{i}")
                    with cu2:
                        f_size = st.slider("Шрифт (px):", 8, 24, 14, key=f"sz_{i}")
                        f_color = st.color_picker("Цвет:", "#000000", key=f"fcol_{i}")
                        f_curr_text = st.text_input("Валюта/Ед. изм. графика:", value="$", key=f"fcur_tx_{i}")
                    with cu3:
                        f_pos = st.selectbox("Положение:", ["auto", "inside", "outside"], key=f"pos_{i}")
                        horiz = st.checkbox("Горизонтально", value=False, key=f"h_{i}") if "Bar" in style else False
                        rot = st.slider("🔄 Поворот:", 0, 360, 0, step=15, key=f"rot_{i}") if "Donut" in style else 0
                        top_limit = st.slider("🔝 ТОП позиций:", 5, 200, 15, key=f"top_{i}")
                        d_fmt = st.selectbox("Формат даты (Excel):", ["Исходный", "ММ.ГГГГ (01.2014)", "Месяц ГГГГ (Янв 2014)", "ДД.ММ.ГГГГ (15.01.2014)", "ГГГГ (2014)"], key=f"dfmt_{i}")
                        f_cast = st.slider("🔮 Прогноз (в периодах таблицы):", 0, 5, 0, key=f"fcast_{i}")
                        
                if x_ax != "-- Выберите заголовок --" and y_ax != "-- Выберите заголовок --":
                    render_custom_chart(act_df, x_ax, y_ax, style, color, lbl_g, f_format, f_round, f_size, f_color, f_pos, horiz, rot, top_limit, i, date_format_type=d_fmt, custom_currency=f_curr_text, forecast_periods=f_cast)
                st.markdown("<hr style='border:1px dashed #ddd'>", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            with b1: st.button("➕ Добавить диаграмму", on_click=add_chart_cb)
            with b2: st.button("🗑️ Удалить диаграмму", on_click=remove_chart_cb)

        router_pages = {
            "🗂️ 1. Загрузка и очистка данных": lambda: show_page_1(main_df, all_cols),
            "📊 2. Executive Диаграммы": lambda: show_page_2(act_df, all_cols),
            "🗮️ 3. ABC/XYZ-аналитика ОЗМ": lambda: internal_show_abc_xyz_page(act_df, gemini_api_key, api_context_mode),
            "👥 4. RFM-сегментация": lambda: internal_show_rfm_page(act_df, gemini_api_key, api_context_mode)
        }
        router_pages[page]()
else:
    st.info("📊 Ожидание загрузки любых файлов Excel/CSV...")
