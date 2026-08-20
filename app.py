import streamlit as st
import pandas as pd
import io
import json
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from google import genai
from google.genai import types

# Инициализация конфигурации страницы на самом старте скрипта
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
        return json.loads(response.text)
    except:
        return {}

# 🧠 МОДУЛЬ 2: УЛЬТРА-ГИБКИЙ ИИ-АНАЛИЗАТОР БИЗНЕС-ПРОЦЕССОВ
def ai_generate_text_report(pivot_matrix_df, report_type="ABC/XYZ", data_context="Расход", api_key=None):
    if not api_key: 
        return st.warning("⚠️ Введите API Key Gemini в сайдбаре.")
    try:
        client = genai.Client(api_key=api_key)
        system_instruction = f"Ты — директор по логистике и снабжению комбината. Напиши аналитический отчет для генерального директора по матрице {report_type}. Контекст: {data_context}. Начинай отчет сразу с Раздела 1."
        with st.spinner("🔮 ИИ генерирует чистый отчет..."):
            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=f"Матрица:\n{pivot_matrix_df.to_string()}", 
                config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.2)
            )
            st.markdown("---")
            st.markdown(f"### 📝 Аналитический ИИ-Отчет")
            st.info(response.text)
    except Exception as report_err: 
        st.error(f"❌ Ошибка ИИ: {report_err}")
# 🧮 МОДУЛЬ 3: ABC/XYZ АНАЛИЗАТОР
def internal_show_abc_xyz_page(filtered_df, api_key, data_context):
    st.title("🧮 Универсальный Конструктор матриц ABC/XYZ")
    if filtered_df.empty: return st.info("ℹ️ Выборка пуста. Загрузите файлы.")
    df = filtered_df.copy()
    available_cols = list(df.columns)
    
    c1, c2, c3 = st.columns(3)
    with c1: abc_target = st.selectbox("1. Объект анализа:", [c for c in available_cols if c not in ['Сумма', 'Количество']], key="abc_t")
    with c2: abc_value = st.selectbox("2. Критерий масштаба:", ['Сумма', 'Количество'], key="abc_v")
    with c3: xyz_period = st.selectbox("3. Шкала времени:", [c for c in available_cols if c != abc_target], key="xyz_p")
    
    try:
        df[abc_value] = pd.to_numeric(df[abc_value], errors='coerce').fillna(0.0)
        df_abc = df.groupby(abc_target, as_index=False)[abc_value].sum().sort_values(by=abc_value, ascending=False).reset_index(drop=True)
        df_abc['Cum'] = (df_abc[abc_value] / df_abc[abc_value].sum()).cumsum() * 100
        df_abc['Class_ABC'] = df_abc['Cum'].map(lambda x: 'A' if x <= 80 else ('B' if x <= 95 else 'C'))
        
        p_matrix = df.groupby([abc_target, xyz_period])[abc_value].sum().unstack(fill_value=0.0)
        xyz_res = []
        for name, rows in p_matrix.iterrows():
            m, s = rows.mean(), rows.std(ddof=1) if len(rows) > 1 else 0.0
            kv = (s / m) * 100 if m > 0 and np.count_nonzero(rows) > 1 else 999.0
            xyz_res.append({abc_target: name, 'Класс XYZ': 'X' if kv <= 10 else ('Y' if kv <= 25 else 'Z')})
        
        df_m = pd.merge(df_abc[[abc_target, abc_value, 'Class_ABC']], pd.DataFrame(xyz_res), on=abc_target)
        pivot_m = df_m.pivot_table(index='Class_ABC', columns='Класс XYZ', values=abc_target, aggfunc='count', fill_value=0)
        
        st.dataframe(pivot_m, use_container_width=True)
        st.plotly_chart(px.imshow(pivot_m, text_auto=True, color_continuous_scale="Blues"), use_container_width=True)
        if st.button("✍️ Сгенерировать ИИ-отчет по матрице ABC/XYZ"):
            ai_generate_text_report(pivot_m, "ABC/XYZ", data_context, api_key)
    except Exception as e: st.error(f"Ошибка расчета ABC/XYZ: {e}")

# 👥 МОДУЛЬ 4: RFM АНАЛИЗАТОР
def internal_show_rfm_page(filtered_df, api_key, data_context):
    st.title("👥 Модуль RFM-сегментации номенклатуры")
    if filtered_df.empty: return st.info("ℹ️ Текущий срез пуст.")
    df = filtered_df.copy()
    
    rfm_target = st.selectbox("Выберите анализируемое поле:", [c for c in list(df.columns) if c not in ['Сумма', 'Количество']], key="rfm_target_select")
    try:
        df['Сумма'] = pd.to_numeric(df['Сумма'], errors='coerce').fillna(0.0)
        rfm = df.groupby(rfm_target).agg(F=('Сумма', 'count'), M=('Сумма', 'sum')).reset_index()
        rfm['F_Score'] = pd.qcut(rfm['F'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        rfm['M_Score'] = pd.qcut(rfm['M'].rank(method='first'), 3, labels=['3', '2', '1']).astype(str)
        rfm['RFM'] = rfm['F_Score'] + rfm['M_Score']
        seg_counts = rfm.groupby('RFM').size().reset_index(name='Количество объектов')
        
        st.plotly_chart(px.bar(seg_counts, x='RFM', y='Количество объектов', text_auto=True, color='RFM', color_continuous_scale="Purples"), use_container_width=True)
        st.dataframe(rfm.sort_values(by='M', ascending=False), use_container_width=True)
    except Exception as e: st.error(f"Ошибка RFM: {e}")
# 📊 ФУНКЦИЯ 5: КЛАССИЧЕСКИЙ БЕЗОПАСНЫЙ ГРАФИЧЕСКИЙ ДВИЖОК PLOTLY EXPRESS
def render_custom_chart(active_df, x_ax, y_ax, style, color, horiz, top_limit, i):
    try:
        df_c = active_df.copy()
        df_c[y_ax] = pd.to_numeric(df_c[y_ax], errors='coerce').fillna(0)
        df_g = df_c.groupby(x_ax, as_index=False)[y_ax].sum().sort_values(by=y_ax, ascending=False).head(top_limit)
        if horiz: df_g = df_g.sort_values(by=y_ax, ascending=True)

        if "Line" in style: fig = px.line(df_g, x=x_ax, y=y_ax, markers=True, color_discrete_sequence=[color])
        elif "Donut" in style: fig = px.pie(df_g, names=x_ax, values=y_ax, hole=0.4)
        else: fig = px.bar(df_g, x=y_ax if horiz else x_ax, y=x_ax if horiz else y_ax, orientation="h" if horiz else "v", text_auto=True, color_discrete_sequence=[color])
            
        fig.update_layout(xaxis=dict(type='category', tickangle=45 if not horiz else 0))
        st.plotly_chart(fig, use_container_width=True, key=f"p_{i}")
    except Exception as chart_err: st.error(f"Ошибка графика №{i+1}: {chart_err}")

# 🛠️ МОДУЛЬ СБОРКИ ДАННЫХ: КЛАССИЧЕСКИЙ CONCAT НА БАЗЕ СТАНДАРТНОГО ДВИЖКА OPENPYXL
def power_query_clean_engine(uploaded_files_list, gemini_key):
    frames = []
    for f_obj in uploaded_files_list:
        try:
            df = pd.read_csv(f_obj, dtype=str) if f_obj.name.endswith('.csv') else pd.read_excel(f_obj, dtype=str, engine='openpyxl')
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
                    elif any(w in c_low for w in ['сумма', 'стоимость', 'цена']): mapped.append('Сумма')
                    else: mapped.append(col)
            df.columns = mapped
            df = df.loc[:, ~df.columns.str.contains('^Без названия|^Unnamed|^Unnamed:')].loc[:, ~df.columns.duplicated()]
            frames.append(df.dropna(how='all'))
        except Exception as file_err: st.sidebar.error(f"Ошибка файла {f_obj.name}: {file_err}")
            
    if not frames: return pd.DataFrame()
    base_df = pd.concat(frames, ignore_index=True, join='outer')
    for c in ['Количество', 'Сумма']:
        if c in base_df.columns: base_df[c] = pd.to_numeric(base_df[c].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.'), errors='coerce').fillna(0.0)
    return base_df.dropna(how='all')
# ⚙️ ИНИЦИАЛИЗАЦИЯ И СТАТИЧЕСКИЕ КОЛЛБЭКИ СЕССИИ
if "manual_charts" not in st.session_state: st.session_state.manual_charts = 1
if "main_df" not in st.session_state: st.session_state.main_df = pd.DataFrame()

st.sidebar.markdown("### 🤖 Интеллектуальный ИИ-Ассистент")
gemini_api_key = st.sidebar.text_input("Введите Gemini API Key:", type="password")
ai_context_mode = st.sidebar.selectbox("Контекст для AI:", ["📅 Закупки", "📦 Запасы", "📉 Расход", "💰 Продажи"])

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
            st.rerun()
            
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)
        f_col1 = st.sidebar.selectbox("Поле среза №1:", all_cols, key="fl_c1")
        act_df = main_df.copy()
        if f_col1 != "-- Выберите заголовок --":
            u_v1 = ["-- Все значения --"] + list(act_df[f_col1].astype(str).unique())
            f_v1 = st.sidebar.selectbox("Значение среза №1:", u_v1, key="fl_v1")
            if f_v1 != "-- Все значения --": act_df = act_df[act_df[f_col1].astype(str) == str(f_v1)]
        
        page = st.sidebar.radio("Перейти к разделу:", ["🗂️ 1. Данные", "📊 2. Диаграммы", "🧮 3. ABC/XYZ-аналитика", "👥 4. RFM-сегментация"])
        
        if "1. Данные" in page:
            st.success(f"📊 База сформирована! Строк: {len(act_df):,}")
            st.dataframe(act_df.head(100), use_container_width=True)
            
        elif "2. Диаграммы" in page:
            st.title("📊 Интерактивный Конструктор Диаграмм")
            for i in range(st.session_state.manual_charts):
                c1, c2, c3 = st.columns(3)
                with c1: style = st.selectbox(f"Тип №{i+1}:", ["Столбчатая диаграмма (Bar)", "Линейный тренд (Line)", "Кольцевая долей (Donut)"], key=f"s_{i}")
                with c2: x_ax = st.selectbox(f"Ось X №{i+1}:", all_cols, key=f"x_{i}")
                with c3: y_ax = st.selectbox(f"Ось Y №{i+1}:", ['Сумма', 'Количество'] + all_cols, key=f"y_{i}")
                
                horiz = st.checkbox("Горизонтально", value=False, key=f"h_{i}") if "Bar" in style else False
                top_limit = st.slider("🔝 ТОП позиций:", 5, 100, 15, key=f"top_{i}")
                        
                if x_ax != "-- Выберите заголовок --" and y_ax != "-- Выберите заголовок --":
                    render_custom_chart(act_df, x_ax, y_ax, style, "#1f77b4", horiz, top_limit, i)
                st.markdown("<hr style='border:1px dashed #ddd'>", unsafe_allow_html=True)
            if st.button("➕ Добавить диаграмму"):
                st.session_state.manual_charts += 1
                st.rerun()
                
        elif "3. ABC/XYZ-аналитика" in page:
            internal_show_abc_xyz_page(act_df, gemini_api_key, ai_context_mode)
            
        elif "4. RFM-сегментация" in page:
            internal_show_rfm_page(act_df, gemini_api_key, ai_context_mode)
else:
    st.info("📊 Ожидание загрузки любых файлов Excel/CSV...")
