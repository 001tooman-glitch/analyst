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

# Принудительная инициализация разметки страницы на самом старте скрипта
st.set_page_config(layout="wide", page_title="BI Enterprise Platform")

# Схема для гарантированного JSON-ответа от Gemini Developer API
class ColumnMappingSchema(BaseModel):
    model_config = {"extra": "forbid"}
    
    mapping: dict[str, str] = Field(
        description="Словарь, где ключ - исходное имя колонки, а значение - строго одно из полей: 'ОЗМ', 'Наименование материала', 'Количество' или 'Сумма'"
    )
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
            "Используй контекст и смысл слов (например, 'Sales', 'Revenue', 'Profit', 'Cost' "
            "должны мапиться в 'Сумма', а 'Units', 'Volume' — в 'Количество')."
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
        res_json = json.loads(response.text)
        mapping_result = res_json.get("mapping", {})
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
            "Закупки": "Данные — это ПЛАНИРУЕМЫЕ ЗАКУПКИ / БИЗНЕС-ПЛАНЫ. Группа AZ — это стратегические контракты (риск срыва сроков проектов). Группа CZ — мелкая операционная текучка.",
            "Зазапасы": "Данные — это СУЩЕСТВУЮЩИЕ СКЛАДСКИЕ ЗАПАСЫ. Группа AZ — это жестко замороженный рабочий капитал предприятия. Группа CZ — складской хлам, неликвиды.",
            "Расход": "Данные — это РЕАЛЬНЫЙ ФАКТИЧЕСКИЙ РАСХОД / ПОТРЕБЛЕНИЕ. Группа AZ — это внеплановые, аварийные ремонты оборудования. Группа CZ — административная нагрузка."
        }
        
        context_rules = next((v for k, v in context_mapping.items() if k in data_context), 
                             "Данные — это КОММЕРЧЕСКИЕ ПРОДАЖИ / СБЫТ / РИТЕЙЛ. Группа AZ — это товары-локомотивы. Группа CZ — длинный хвост ассортимента.")

        system_instruction = f"""
        Ты — ведущий бизнес-аналитик предприятия. Напиши аналитический отчет для руководства по матрице {report_type}.
        БИЗНЕС-КОНТЕКСТ ДАННЫХ: {context_rules}
        
        СТРОГИЕ ПРАВИЛА ОФОРМЛЕНИЯ:
        - Использовать исключительно нейтральные термины: 'предприятие', 'компания', 'организация'. Категорически запрещено писать слова 'комбинат'.
        - НАЧИНАЙ ОТЧЕТ СРАЗУ с содержательного анализа (Раздел "1. Анализ текущего процесса").
        - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать метаданные документа: приветствия или вводные подписи.
        """
        with st.spinner(f"🔮 ИИ генерирует чистый отчет..."):
            response = client.models.generate_content(
                model='gemini-3.5-flash', 
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
# 🧮 МОДУЛЬ 3: УНИВЕРСАЛЬНЫЙ КОНСТРУКТОР ABC/XYZ И ДИНАМИЧЕСКОЙ ОБОРАЧИВАЕМОСТИ
def internal_show_abc_xyz_page(filtered_df, api_key, data_context):
    st.title("🧮 Конструктор матриц ABC/XYZ и Модуль оборачиваемости ТМЦ")
    if filtered_df.empty: 
        return st.info("ℹ️ Выборка пуста. Загрузите файлы.")
    
    df = filtered_df.copy()
    available_cols = list(df.columns)
    
    st.markdown("### 🎯 Настройка параметров оборачиваемости ТМЦ")
    tc1, tc2 = st.columns(2)
    with tc1:
        chosen_turnover_period = st.selectbox("Выберите анализируемый период времени:", ["Год (365 дней)", "Полугодие (182 дня)", "Квартал (90 дней)", "Месяц (30 дней)"], key="t_period_sel")
    with tc2:
        abc_target = st.selectbox("Объект анализа ТМЦ:", [c for c in available_cols if c not in ['Сумма', 'Количество']], key="abc_t")
        
    days_mapping = {"Год (365 дней)": 365, "Полугодие (182 дня)": 182, "Квартал (90 дней)": 90, "Месяц (30 дней)": 30}
    selected_days = days_mapping[chosen_turnover_period]
    
    c1, c2 = st.columns(2)
    with c1: 
        abc_value = st.selectbox("Критерий масштаба расхода/продаж:", [c for c in ['Сумма', 'Количество'] if c in available_cols] + available_cols, key="abc_v")
    with c2: 
        stock_col = st.selectbox("Столбец текущего остатка ТМЦ (для оборачиваемости):", ["-- Рассчитать аппроксимацию (расход * 1.15) --"] + available_cols, key="abc_stock_col")
        
    xyz_period = st.selectbox("Шкала времени (для XYZ):", [c for c in available_cols if c != abc_target], key="xyz_p")
    
    a_lim = st.slider("Grad_A (%):", 50, 90, 80, key="abc_s")
    x_lim = st.slider("Grad_X (KV ≤ %):", 5, 50, 10, key="xyz_s")
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
        
        if stock_col == "-- Рассчитать аппроксимацию (расход * 1.15) --":
            df_m['Средний запас на складе'] = df_m[abc_value] * 1.15
        else:
            df[stock_col] = pd.to_numeric(df[stock_col], errors='coerce').fillna(0.0)
            df_stock_aggregated = df.groupby(abc_target)[stock_col].mean().reset_index()
            df_stock_aggregated.columns = [abc_target, 'Средний запас на складе']
            df_m = pd.merge(df_m, df_stock_aggregated, on=abc_target, how='left').fillna(0.0)
            
        df_m['Расход за период'] = df_m[abc_value]
        df_m['Коэф. Оборачиваемости (раз)'] = (df_m['Расход за период'] / df_m['Средний запас на складе']).replace([np.inf, -np.inf], 0).fillna(0).round(2)
        df_m['Оборачиваемость (в днях)'] = df_m['Коэф. Оборачиваемости (раз)'].map(lambda x: int(selected_days / x) if x > 0 else 999)
        
        raw_pivot = df_m.pivot_table(index='Class_ABC', columns='Класс XYZ', values=abc_target, aggfunc='count', fill_value=0)
        pivot_m = pd.DataFrame(0, index=['A', 'B', 'C'], columns=['X', 'Y', 'Z'])
        for idx in pivot_m.index:
            for col in pivot_m.columns:
                if idx in raw_pivot.index and col in raw_pivot.columns:
                    pivot_m.loc[idx, col] = raw_pivot.loc[idx, col]
                    
        mc1, mc2 = st.columns(2)
        with mc1: 
            st.markdown(f"#### 📊 Плотность распределения номенклатуры ТМЦ")
            st.dataframe(pivot_m, use_container_width=True)
        with mc2: 
            st.plotly_chart(px.imshow(pivot_m, text_auto=True, color_continuous_scale="Blues"), use_container_width=True)
        
        if st.button("✍️ Сгенерировать ИИ-отчет по матрице ABC/XYZ", key="ai_report_abc_btn"):
            ai_generate_text_report(pivot_m, report_type="ABC/XYZ", data_context=data_context, api_key=api_key)
            
        st.dataframe(df_m.sort_values(by=abc_value, ascending=False), use_container_width=True)
        
        towrite = io.BytesIO()
        df_m.to_excel(towrite, index=False, engine='openpyxl')
        st.download_button(label="📥 Скачать результаты аналитики в Excel", data=towrite.getvalue(), file_name="abc_xyz_turnover_output.xlsx", mime="application/vnd.ms-excel")
        
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
        
        if len(rfm) < 3:
            st.warning("⚠️ Недостаточно уникальных данных для квантования.")
            st.dataframe(rfm.sort_values(by='M', ascending=False), use_container_width=True)
            return

        rfm['F_Score'] = pd.qcut(rfm['F'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        rfm['M_Score'] = pd.qcut(rfm['M'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        rfm['RFM'] = rfm['F_Score'] + rfm['M_Score']
        seg_counts = rfm.groupby('RFM').size().reset_index(name='Количество объектов')
        
        st.plotly_chart(px.bar(seg_counts, x='RFM', y='Количество объектов', text_auto=True, title=f"📊 Динамическое RFM-распределение: {rfm_target}", color='RFM', color_continuous_scale="Purples"), use_container_width=True)
        
        if st.button("👥 Сгенерировать ИИ-отчет по матрице RFM", key="ai_report_rfm_btn"):
            ai_generate_text_report(seg_counts, report_type=f"RFM-Сегментации ({rfm_target})", data_context=data_context, api_key=api_key)
            
        st.dataframe(rfm.sort_values(by='M', ascending=False), use_container_width=True)
    except Exception as rfe: 
        st.error(f"❌ Ошибка расчета RFM: {rfe}")
# 📊 ФУНКЦИЯ 5: МОДЕРНИЗИРОВАННЫЙ ГРАФИЧЕСКИЙ ДВИЖОК С АВТОПРОГНОЗОМ ДЛЯ ТЕКСТОВЫХ И ЧИСЛОВЫХ ЛЕТ
def render_custom_chart(active_df, x_ax, y_ax, style, color, lbl, f_format, f_round, f_size, f_color, f_pos, horiz, rot, top_limit, i, date_format_type="Исходный", custom_currency="", forecast_periods=0):
    try:
        df_c = active_df.copy()
        df_c[y_ax] = pd.to_numeric(df_c[y_ax], errors='coerce').fillna(0)
        
        clean_currency = str(custom_currency).strip()
        curr_suffix = f" {clean_currency}" if clean_currency else ""
        
        scatter_pos = "top center"
        if f_pos == "inside": scatter_pos = "middle center"
        elif f_pos == "outside": scatter_pos = "top center"
        elif f_pos in ["top center", "bottom center", "middle center", "top left", "top right", "bottom left", "bottom right"]:
            scatter_pos = f_pos

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
                last_value = df_fact[y_ax].iloc[-1]
                pct_changes = df_fact[y_ax].pct_change().dropna()
                avg_drop = pct_changes.tail(3).mean() if len(pct_changes) >= 3 else pct_changes.mean()
                if avg_drop < -0.15: avg_drop = -0.15
                
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
            sort_asc = is_year_col
            df_g = df_c.groupby(x_ax, as_index=False)[y_ax].sum().sort_values(by=x_ax if sort_asc else y_ax, ascending=sort_asc).head(top_limit).reset_index(drop=True)
            df_g["Тип данных"] = "Факт"
            idx_split = len(df_g) - 1
            
            if forecast_periods > 0 and is_year_col and len(df_g) > 1:
                try:
                    last_year_numeric = int(float(df_g[x_ax].iloc[-1]))
                    last_val = df_g[y_ax].iloc[-1]
                    pct_changes = df_g[y_ax].pct_change().dropna()
                    avg_growth = pct_changes.tail(2).mean() if len(pct_changes) >= 2 else pct_changes.mean()
                    if avg_growth < -0.20: avg_growth = -0.20
                    
                    f_x_list = list(df_g[x_ax].astype(str).values)
                    f_y_list = list(df_g[y_ax].values)
                    f_leg_list = ["Факт"] * len(df_g)
                    
                    curr_val = last_val
                    for offset in range(1, forecast_periods + 1):
                        next_year_str = str(last_year_numeric + offset)
                        curr_val = curr_val * (1 + avg_growth)
                        f_x_list.append(next_year_str)
                        f_y_list.append(curr_val)
                        f_leg_list.append("Прогноз ИИ")
                        
                    df_g = pd.DataFrame({x_ax: f_x_list, y_ax: f_y_list, "Тип данных": f_leg_list})
                except: pass

        fig = go.Figure()
        
        if "Линейный" in style or (is_date_axis and "Столбчатая" not in style and "Кольцевая" not in style and "Водопад" not in style):
            if forecast_periods > 0 and idx_split > 0 and len(df_g) > idx_split + 1:
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
            total_sum_val = df_g[y_ax].sum()
            formatted_total = get_formatted_text([total_sum_val])
            fig.add_trace(go.Waterfall(x=list(df_g[x_ax].astype(str)) + ["ИТОГО"], y=list(df_g[y_ax]) + [total_sum_val], text=txt + formatted_total, textposition=safe_pos, measure=["relative"] * len(df_g[y_ax]) + ["total"], increasing={"marker": {"color": color}}, textfont=dict(size=f_size, color=f_color)))

        if horiz and "Столбчатая" in style: fig.update_layout(yaxis=dict(type='category'), xaxis=dict(showgrid=True))
        else: fig.update_layout(xaxis=dict(type='category', tickangle=45), yaxis=dict(showgrid=True))
            
        fig.update_layout(showlegend=True, margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig, use_container_width=True, key=f"p_{i}")
    except Exception as chart_err:
        st.error(f"Ошибка графика №{i+1}: {chart_err}")
# 🛠️ МОДУЛЬ СБОРКИ ДАННЫХ (ENTERPRISE CONCAT ENGINE)
def power_query_clean_engine(uploaded_files_list, gemini_key):
    frames = []
    for f_item in uploaded_files_list:
        try:
            df = pd.read_csv(f_item) if f_item.name.endswith('.csv') else pd.read_excel(f_item, engine='openpyxl')
            raw_cols = [str(c).strip() for c in df.columns]
            ai_map = ai_column_mapper_engine(raw_cols, gemini_key)
            mapped = []
            for col in raw_cols:
                if col in ai_map: mapped.append(ai_map[col])
                else:
                    c_low = col.lower()
                    if any(w in c_low for w in ['озм', 'код материала', 'номенклатур']): mapped.append('ОЗМ')
                    elif any(w in c_low for w in ['наименование', 'материал']): mapped.append('Наименование материала')
                    elif any(w in c_low for w in ['количество', 'кол-во', 'объем']): mapped.append('Quantity')
                    elif any(w in c_low for w in ['сумма', 'стоимость', 'цена']): mapped.append('Сумма')
                    else: mapped.append(col)
            df.columns = [c if c != 'Quantity' else 'Количество' for c in mapped]
            df = df.loc[:, ~df.columns.str.contains('^Без названия|^Unnamed|^Unnamed:')].loc[:, ~df.columns.duplicated()]
            frames.append(df.dropna(how='all'))
        except Exception as file_err:
            st.sidebar.error(f"Ошибка файла {f_item.name}: {file_err}")
            
    if not frames: return pd.DataFrame()
    base_df = pd.concat(frames, ignore_index=True, join='outer')
            
    for c in ['Количество', 'Сумма']:
        if c in base_df.columns: 
            base_df[c] = pd.to_numeric(base_df[c].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.'), errors='coerce').fillna(0.0)
    return base_df.dropna(how='all')

# ⚙️ ИНИЦИАЛИЗАЦИЯ И СТАТИЧЕСКИЕ КОЛЛБЭКИ СЕССИИ
if "manual_charts" not in st.session_state: st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state: st.session_state.manual_cards = 1
if "main_df" not in st.session_state: st.session_state.main_df = pd.DataFrame()
if "chat_history" not in st.session_state: st.session_state.chat_history = []

def add_chart_cb(): st.session_state.manual_charts += 1
def remove_chart_cb(): 
    if st.session_state.manual_charts > 1: st.session_state.manual_charts -= 1
def add_card_cb(): st.session_state.manual_cards += 1
def remove_card_cb(): 
    if st.session_state.manual_cards > 1: st.session_state.manual_cards -= 1
# 💬 ЭКСПЕРТНЫЙ ИИ ЧАТ-АССИСТЕНТ С ДВИЖКОМ АВТОМАТИЧЕСКОГО ИСПОЛНЕНИЯ PYTHON-КОДА (CODE INTERPRETER)
def render_ai_sidebar_chat(current_dataframe, api_key, context_mode_text):
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💬 Чат-ассистент к данным")
    
    if current_dataframe.empty:
        st.sidebar.info("Загрузите файлы для активации чата.")
        return
        
    if st.sidebar.button("🧹 Очистить историю чата", key="clear_chat_btn"):
        st.session_state.chat_history = []
        st.sidebar.success("История очищена!")
        
    chat_container = st.sidebar.container(height=300)
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    if user_prompt := st.sidebar.chat_input("Спросить ИИ о таблице...", key="chat_input_text"):
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with chat_container:
            with st.chat_message("user"):
                st.write(user_prompt)
                
        if not api_key:
            with chat_container:
                with st.chat_message("assistant"):
                    st.error("Ошибка: Введите API Key выше.")
            return

        try:
            client = genai.Client(api_key=api_key)
            
            # Передаем ИИ только схему метаданных и 3 строки структуры для минимизации размера токенов
            sample_df = current_dataframe.head(3).copy()
            for c in sample_df.columns:
                if sample_df[c].dtype == object:
                    sample_df[c] = sample_df[c].astype(str)
                    
            columns_schema = {str(col): str(current_dataframe[col].dtype) for col in current_dataframe.columns}
            sample_json = sample_df.to_dict(orient='records')
            
            sys_prompt = f"""
            Ты — эксперт по анализу данных на Python и Pandas. Твоя задача — написать ОДНУ строчку кода на Python, которая ответит на вопрос пользователя.
            Исходный датафрейм называется 'current_dataframe'. Колонки 'Сумма' и 'Количество' уже гарантированно приведены к числовому типу (float).
            
            СТРУКТУРА ТАБЛИЦЫ (Имена колонок и типы):
            {json.dumps(columns_schema, ensure_ascii=False)}
            
            ПРИМЕР СТРОК ДЛЯ ПОНИМАНИЯ КОНТЕКСТА:
            {json.dumps(sample_json, ensure_ascii=False)}
            
            СТРОГИЕ ПРАВИЛА:
            1. Возвращай ИСКЛЮЧИТЕЛЬНО чистый код на Python. Никакого текста, никаких пояснений, никаких знаков ```python. Только код.
            2. Результат вычисления ОБЯЗАТЕЛЬНО присваивай переменной 'result_output'.
            3. Примеры правильного ответа:
               - Если спросили топ 10 элементов: result_output = current_dataframe.groupby('ОЗМ')['Сумма'].sum().sort_values(ascending=False).head(10)
               - Если спросили про лидера по затратам: result_output = current_dataframe.groupby('ПфМ')['Сумма'].sum().idxmax()
               - Если спросили общую сумму: result_output = current_dataframe['Сумма'].sum()
            """
            
            with chat_container:
                with st.chat_message("assistant"):
                    with st.spinner("🤖 Генерирую аналитический скрипт..."):
                        # Шаг 1: ИИ пишет точный Pandas-скрипт под ваш вопрос
                        response = client.models.generate_content(
                            model='gemini-3.5-flash',
                            contents=f"Вопрос пользователя: {user_prompt}",
                            config=types.GenerateContentConfig(system_instruction=sys_prompt, temperature=0.1)
                        )
                        raw_code = response.text.strip().replace("```python", "").replace("```", "")
                        
                        # Шаг 2: Безопасно исполняем этот код локально на сервере Streamlit
                        local_vars = {"current_dataframe": current_dataframe, "result_output": None}
                        exec(raw_code, {}, local_vars)
                        execution_result = local_vars.get("result_output")
                        
                        # Шаг 3: Передаем результат вычисления обратно ИИ для формирования красивого ответа человеку
                        formatting_prompt = f"""
                        Ты — BI-аналитик. Переведи технический результат вычисления Python на понятный человеческий язык для руководства.
                        Бизнес-контекст: {context_mode_text}. Вопрос пользователя: '{user_prompt}'
                        """
                        
                        final_response = client.models.generate_content(
                            model='gemini-3.5-flash',
                            contents=f"Технический результат выполнения Pandas-кода:\n{str(execution_result)}",
                            config=types.GenerateContentConfig(system_instruction=formatting_prompt, temperature=0.2)
                        )
                        
                        assistant_response = final_response.text
                        st.write(assistant_response)
                        
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
        except Exception as chat_err:
            st.sidebar.error(f"Ошибка чата: {chat_err}")
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
        render_ai_sidebar_chat(main_df, gemini_api_key, ai_context_mode)
        
        if st.sidebar.button("♻️ Сбросить/Очистить базу данных"):
            st.session_state.main_df = pd.DataFrame()
            st.session_state.manual_charts = 1
            st.session_state.manual_cards = 1
            st.session_state.chat_history = []
            st.rerun()
            
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)
        f_col1 = st.sidebar.selectbox("Поле среза №1:", all_cols, key="fl_c1")
        act_df = main_df.copy()
        if f_col1 != "-- Выберите заголовок --":
            u_v1 = ["-- Все значения --"] + list(act_df[f_col1].astype(str).unique())
            f_v1 = st.sidebar.selectbox("Значение среза №1:", u_v1, key="fl_v1")
            if f_v1 != "-- Все значения --": act_df = act_df[act_df[f_col1].astype(str) == str(f_v1)]
        
        page = st.sidebar.radio("Перейти к разделу:", ["🗂️ 1. Загрузка и очистка данных", "📊 2. Executive Диаграммы", "🗮️ 3. ABC/XYZ-аналитика ОЗМ", "👥 4. RFM-сегментация"])
        
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
                        f_cast = st.slider("🔮 Прогноз (в периодах таблицы):", 0, 5, 2, key=f"fcast_{i}")
                        
                if x_ax != "-- Выберите заголовок --" and y_ax != "-- Выберите заголовок --":
                    render_custom_chart(act_df, x_ax, y_ax, style, color, lbl_g, f_format, f_round, f_size, f_color, f_pos, horiz, rot, top_limit, i, date_format_type=d_fmt, custom_currency=f_curr_text, forecast_periods=f_cast)
                st.markdown("<hr style='border:1px dashed #ddd'>", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            with b1: st.button("➕ Добавить диаграмму", on_click=add_chart_cb)
            with b2: st.button("🗑️ Удалить диаграмму", on_click=remove_chart_cb)

        router_pages = {
            "🗂️ 1. Загрузка и очистка данных": lambda: show_page_1(main_df, all_cols),
            "📊 2. Executive Диаграммы": lambda: show_page_2(act_df, all_cols),
            "🗮️ 3. ABC/XYZ-аналитика ОЗМ": lambda: internal_show_abc_xyz_page(act_df, gemini_api_key, ai_context_mode),
            "👥 4. RFM-сегментация": lambda: internal_show_rfm_page(act_df, gemini_api_key, ai_context_mode)
        }
        router_pages[page]()
else:
    st.info("📊 Ожидание загрузки любых файлов Excel/CSV...")
