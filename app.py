import streamlit as st
import pandas as pd
import io
import json
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

st.set_page_config(layout="wide", page_title="BI Enterprise Platform")

# Схема для гарантированного JSON-ответа от Gemini Developer API
class ColumnMappingSchema(BaseModel):
    model_config = {"extra": "forbid"}
    
    mapping: dict[str, str] = Field(
        description="Словарь, где ключ - исходное имя колонки, а значение - строго одно из fields: 'ОЗМ', 'Наименование материала', 'Количество' или 'Сумма'"
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
            "Используй контекст и смысл слов."
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
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
# 🧠 МОДУЛЬ 2: УЛЬТРА-ГИБКИЙ ИИ-АНАЛИЗАТОР БИЗНЕС-ПРОЦЕССОВ
def ai_generate_text_report(pivot_matrix_df, report_type="ABC/XYZ", data_context="Расход", api_key=None):
    if not api_key: 
        return st.warning("⚠️ Введите API Key Gemini в сайдбаре.")
    try:
        client = genai.Client(api_key=api_key)
        
        context_mapping = {
            "Закупки": "Данные — это ПЛАНИРУЕМЫЕ ЗАКУПКИ / БИЗНЕС-ПЛАНЫ. Группа AZ — это стратегические контракты. Группа CZ — мелкая операционная текучка.",
            "Запасы": "Данные — это СУЩЕСТВУЮЩИЕ СКЛАДСКИЕ ЗАПАСЫ. Группа AZ — это жестко замороженный рабочий капитал предприятия. Группа CZ — складской хлам, неликвиды.",
            "Расход": "Данные — это РЕАЛЬНЫЙ ФАКТИЧЕСКИЙ РАСХОД / ПОТРЕБЛЕНИЕ. Группа AZ — это внеплановые ремонты оборудования. Группа CZ — административная нагрузка мелких заявок."
        }
        
        context_rules = next((v for k, v in context_mapping.items() if k in data_context), 
                             "Данные — это КОММЕРЧЕСКИЕ ПРОДАЖИ / СБЫТ / РИТЕЙЛ. Группа AZ — это товары-локомотивы. Группа CZ — длинный хвост ассортимента с низким чеком.")

        system_instruction = f"""
        Ты — директор по логистике и снабжению комбината. Напиши аналитический отчет для генерального директора по матрице {report_type}.
        БИЗНЕС-КОНТЕКСТ ДАННЫХ: {context_rules}
        
        СТРОГИЕ ПРАВИЛА ОФОРМЛЕНИЯ:
        - НАЧИНАЙ ОТЧЕТ СРАЗУ с содержательного анализа.
        - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать метаданные документа: "Генеральному директору", "От:", приветствия или вводные подписи.
        """
        with st.spinner(f"🔮 ИИ генерирует чистый отчет для контекста '{data_context}'..."):
            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=f"Матрица плотности ({data_context}):\n{pivot_matrix_df.to_string()}", 
                config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.2)
            )
            st.markdown("---")
            st.markdown(f"### 📝 Аналитический ИИ-Отчет: {data_context} ({report_type})")
            st.info(response.text)
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
    x_lim = st.slider("Граница группы X (KV ≤ %):", 5, 20, 10, key="xyz_s")
    
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
    except Exception as e: 
        st.error(f"Ошибка расчета ABC/XYZ: {e}")
# 👥 МОДУЛЬ 4: УНИВЕРСАЛЬНЫЙ КОНСТРУКТОР RFM С ДИНАМИЧЕСКИМ ВЫБОРОМ КОЛОНОК
def internal_show_rfm_page(filtered_df, api_key, data_context):
    st.title("👥 Модуль RFM-сегментации номенклатуры и категорий")
    if filtered_df.empty: 
        return st.info("ℹ Lent: Текущий срез пуст. Выберите другие фильтры.")
    df = filtered_df.copy()
    available_cols = list(df.columns)
    
    st.markdown("### 🎯 Настройка объекта сегментации")
    rc1, rc2 = st.columns(2)
    with rc1: rfm_target = st.selectbox("Выберите аналистрируемое поле:", [c for c in available_cols if c not in ['Сумма', 'Количество']], key="rfm_target_select")
    with rc2: rfm_value_col = st.selectbox("Выберите поле стоимости/суммы:", ['Сумма', 'Количество'], key="rfm_value_select")
    
    try:
        df[rfm_value_col] = pd.to_numeric(df[rfm_value_col], errors='coerce').fillna(0.0)
        rfm = df.groupby(str(rfm_target)).agg(F=(rfm_value_col, 'count'), M=(rfm_value_col, 'sum')).reset_index()
        rfm.columns = ['Объект Анализа', 'F', 'M']
        
        if len(rfm) < 3 or rfm['F'].nunique() <= 1 or rfm['M'].nunique() <= 1:
            st.dataframe(rfm.sort_values(by='M', ascending=False), use_container_width=True)
            return

        rfm['F_Score'] = pd.qcut(rfm['F'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        rfm['M_Score'] = pd.qcut(rfm['M'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        rfm['RFM'] = rfm['F_Score'] + rfm['M_Score']
        seg_counts = rfm.groupby('RFM').size().reset_index(name='Количество объектов')
        
        st.plotly_chart(px.bar(seg_counts, x='RFM', y='Количество объектов', text_auto=True, title=f"📊 Динамическое RFM-распределение", color='RFM', color_continuous_scale="Purples"), use_container_width=True)
        st.dataframe(rfm.sort_values(by='M', ascending=False), use_container_width=True)
    except Exception as rfe: 
        st.error(f"❌ Ошибка расчета RFM: {rfe}")
# 📊 ФУНКЦИЯ 5: КЛАССИЧЕСКИЙ БЕЗОПАСНЫЙ ГРАФИЧЕСКИЙ ДВИЖОК PLOTLY EXPRESS
def render_custom_chart(active_df, x_ax, y_ax, style, color, lbl, f_format, f_round, f_size, f_color, f_pos, horiz, rot, top_limit, i):
    try:
        df_c = active_df.copy()
        df_c[y_ax] = pd.to_numeric(df_c[y_ax], errors='coerce').fillna(0)
        df_g = df_c.groupby(x_ax, as_index=False)[y_ax].sum().sort_values(by=y_ax, ascending=False).head(top_limit)
        if horiz: df_g = df_g.sort_values(by=y_ax, ascending=True)

        if "Waterfall" in style: fig = px.bar(df_g, x=x_ax, y=y_ax, text_auto=True, color_discrete_sequence=[color])
        elif "Donut" in style: fig = px.pie(df_g, names=x_ax, values=y_ax, hole=0.4)
        elif "Line" in style: fig = px.line(df_g, x=x_ax, y=y_ax, markers=True, color_discrete_sequence=[color])
        else: fig = px.bar(df_g, x=y_ax if horiz else x_ax, y=x_ax if horiz else y_ax, orientation="h" if horiz else "v", text_auto=True, color_discrete_sequence=[color])
            
        fig.update_layout(xaxis=dict(type='category', tickangle=45 if not horiz else 0))
        st.plotly_chart(fig, use_container_width=True, key=f"p_{i}")
    except Exception as chart_err:
        st.error(f"Ошибка графика №{i+1}: {chart_err}")

# 🛠️ МОДУЛЬ СБОРКИ ДАННЫХ: КЛАССИЧЕСКИЙ CONCAT БЕЗ ГОРИЗОНТАЛЬНЫХ MERGE-РИСКОВ
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
                    if any(w in c_low for w in ['озм', 'код', 'номенклатур']): mapped.append('ОЗМ')
                    elif any(w in c_low for w in ['наименование', 'материал']): mapped.append('Наименование материала')
                    elif any(w in c_low for w in ['количество', 'кол-во']): mapped.append('Количество')
                    elif any(w in c_low for w in ['сумма', 'стоимость']): mapped.append('Сумма')
                    else: mapped.append(col)
            df.columns = mapped
            df = df.loc[:, ~df.columns.str.contains('^Без названия|^Unnamed|^Unnamed:')].loc[:, ~df.columns.duplicated()]
            frames.append(df.dropna(how='all'))
        except Exception as file_err:
            st.sidebar.error(f"Ошибка файла {f.name}: {file_err}")
            
    if not frames: return pd.DataFrame()
    base_df = pd.concat(frames, ignore_index=True, join='outer')
    for c in ['Количество', 'Сумма']:
        if c in base_df.columns: 
            base_df[c] = pd.to_numeric(base_df[c].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.'), errors='coerce').fillna(0.0)
    return base_df.dropna(how='all')
# ⚙️ ИНИЦИАЛИЗАЦИЯ И СТАТИЧЕСКИЕ КОЛЛБЭКИ ВМЕСТО ST.RERUN
if "manual_charts" not in st.session_state: st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state: st.session_state.manual_cards = 1
if "main_df" not in st.session_state: st.session_state.main_df = pd.DataFrame()

st.sidebar.markdown("### 🤖 Интеллектуальный ИИ-Ассистент")
gemini_api_key = st.sidebar.text_input("Введите Gemini API Key:", type="password")

ai_context_mode = st.sidebar.selectbox("Тип данных (Контекст для AI):", [
    "📅 Закупки (Планируемые)", "📦 Запасы (Складские остатки)", "📉 Расход (Потребление)", "💰 Продажи / Сбыт"
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
                    t_col = st.selectbox(f"Поле метрики №{j+1}:", columns_input, key=f"c_t_{j}")
                    if t_col != "-- Выберите заголовок --":
                        try:
                            dataframe_input[t_col] = pd.to_numeric(dataframe_input[t_col], errors='coerce').fillna(0)
                            cv = dataframe_input[t_col].sum()
                            st.metric(label=f"Сумма {t_col}", value=f"{cv:,.2f}")
                        except: pass
                            
            st.button("➕ Добавить карточку", on_click=add_card_cb)
            st.markdown("---")
            st.subheader("🛠️ No-Code Конструктор Графиков")
            for i in range(st.session_state.manual_charts):
                c1, c2, c3, c4 = st.columns(4)
                with c1: style = st.selectbox(f"Тип №{i+1}:", ["Столбчатая диаграмма (Bar)", "Линейный тренд (Line)", "Кольцевая долей (Donut)"], key=f"s_{i}")
                with c2: x_ax = st.selectbox(f"Ось X №{i+1}:", columns_input, key=f"x_{i}")
                with c3: y_ax = st.selectbox(f"Ось Y №{i+1}:", columns_input, key=f"y_{i}")
                with c4: color = st.color_picker(f"Цвет №{i+1}:", "#1f77b4", key=f"col_{i}")
                
                horiz = st.checkbox("Горизонтально", value=False, key=f"h_{i}") if "Bar" in style else False
                top_limit = st.slider("🔝 ТОП позиций:", 5, 200, 15, key=f"top_{i}")
                        
                if x_ax != "-- Выберите заголовок --" and y_ax != "-- Выберите заголовок --":
                    render_custom_chart(dataframe_input, x_ax, y_ax, style, color, True, "Числовой", 0, 12, "#0000", "auto", horiz, 0, top_limit, i)
                st.markdown("<hr style='border:1px dashed #ddd'>", unsafe_allow_html=True)
            st.button("➕ Добавить диаграмму", on_click=add_chart_cb)

        router_pages = {
            "🗂️ 1. Загрузка и очистка данных": lambda: show_page_1(main_df, all_cols),
            "📊 2. Executive Диаграммы": lambda: show_page_2(act_df, all_cols),
            "🧮 3. ABC/XYZ-аналитика ОЗМ": lambda: internal_show_abc_xyz_page(act_df, gemini_api_key, ai_context_mode),
            "👥 4. RFM-сегментация": lambda: internal_show_rfm_page(act_df, gemini_api_key, ai_context_mode)
        }
        router_pages[page]()
else:
    st.info("📊 Ожидание загрузки любых файлов Excel/CSV...")
