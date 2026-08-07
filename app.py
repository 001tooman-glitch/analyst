import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json

st.set_page_config(page_title="Универсальный ИИ-Аналитик", layout="wide")
st.title("🚀 Полноценный ИИ Агент: Бизнес-Аналитика без ограничений")

st.sidebar.success("🧠 Гибридный аналитический движок активен!")
st.sidebar.info("Система автоматически переключается на ручной No-Code конструктор, если внешний ИИ-сервер занят.")

if "manual_charts" not in st.session_state:
    st.session_state.manual_charts = 1

api_key = st.secrets.get("openrouter_key", "")
uploaded_files = st.file_uploader("Загрузите файлы Excel/CSV", type=["csv", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    combined_frames = []
    for file in uploaded_files:
        try:
            current_df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
            current_df.columns = current_df.columns.str.strip()
            current_df['Отчетный период'] = file.name.split('.')[0]
            combined_frames.append(current_df)
        except Exception as e:
            st.error(f"Ошибка чтения {file.name}: {e}")
        
    if combined_frames:
        try:
            main_df = pd.concat(combined_frames, ignore_index=True)
            st.success(f"📊 База данных сформирована! Всего строк: {main_df.shape[0]}")
            
            with st.expander("📋 Посмотреть структуру данных (первые 5 строк)"):
                st.dataframe(main_df.head(5))
                
            all_cols = list(main_df.columns)
            numeric_cols = list(main_df.select_dtypes(include=['number']).columns)
            text_cols = [col for col in all_cols if col not in numeric_cols and col != 'Отчетный период']
            
            if not numeric_cols: numeric_cols = all_cols
            if not text_cols: text_cols = all_cols

            st.markdown("---")
            st.subheader("🧠 Постановка персональной бизнес-задачи для ИИ")
            user_task = st.text_area("Опишите вашу задачу ИИ:", value="построй столбчатую диаграмму по оси Х - год, по оси Y - значения Итого")
            
            run_ai = st.button("🚀 Запустить ИИ-Анализ и построить графики")
            ai_success = False
            
            if run_ai and api_key and "ВАШ_" not in api_key:
                with st.spinner("ИИ исследует структуру таблиц..."):
                    try:
                        prompt = f"Колонки: {all_cols}\nЧисла: {numeric_cols}\nЗапрос: {user_task}\nВыбери X и Y. Верни строго JSON без markdown: {{\"explanation\": \"текст\", \"x_axis\": \"X\", \"y_axis\": \"Y\", \"chart_type\": \"bar\"}}"
                        url = "https://sambanova.ai"
                        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                        data = {"model": "Meta-Llama-3.1-70B-Instructor", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
                        
                        response = requests.post(url, headers=headers, json=data, timeout=10)
                        if response.status_code == 200:
                            result = json.loads(response.json()['choices'][0]['message']['content'].strip().replace("```json", "").replace("```", ""))
                            st.subheader("💡 Стратегический ИИ-анализ:")
                            st.markdown(result["explanation"])
                            
                            x_ai, y_ai, style_ai = result["x_axis"].strip(), result["y_axis"].strip(), result["chart_type"]
                            if x_ai in main_df.columns and y_ai in main_df.columns:
                                df_c = main_df.copy()
                                df_c[y_ai] = pd.to_numeric(df_c[y_ai], errors='coerce').fillna(0)
                                df_g = df_c.groupby(x_ai, as_index=False)[y_ai].sum()
                                
                                st.markdown("---")
                                st.subheader("📈 Автоматический график от ИИ:")
                                fig = px.line(df_g, x=x_ai, y=y_ai, markers=True) if style_ai == 'line' else (px.pie(df_g, names=x_ai, values=y_ai, hole=0.4) if style_ai == 'pie' else px.bar(df_g, x=x_ai, y=y_ai, color=x_ai))
                                st.plotly_chart(fig, use_container_width=True)
                                ai_success = True
                    except:
                        ai_success = False

            if not ai_success and (run_ai or not run_ai):
                st.markdown("---")
                st.subheader("🛠️ Управляемый No-Code конструктор панелей (Локальный движок)")
                
                for i in range(st.session_state.manual_charts):
                    st.markdown(f"##### 📊 Настройка диаграммы № {i+1}")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        chart_style = st.selectbox(f"Тип диаграммы:", ["Столбчатая диаграмма (Bar Chart)", "Линейный график тренда (Line Chart)", "Кольцевая диаграмма долей (Donut Chart)", "Круговая диаграмма (Pie Chart)"], key=f"m_style_{i}")
                    with c2:
                        x_axis = st.selectbox(f"Ось X (Заголовки):", text_cols, key=f"m_x_{i}")
                    with c3:
                        y_axis = st.selectbox(f"Ось Y (Числовые показатели):", numeric_cols, key=f"m_y_{i}")
                    
                    try:
                        df_m = main_df.copy()
                        df_m[y_axis] = pd.to_numeric(df_m[y_axis], errors='coerce').fillna(0)
                        df_g_m = df_m.groupby(x_axis, as_index=False)[y_axis].sum()
                        try: df_g_m = df_g_m.sort_values(by=x_axis)
                        except: pass
                        
                        if "Кольцевая" in chart_style: fig_m = px.pie(df_g_m, names=x_axis, values=y_axis, hole=0.4)
                        elif "Круговая" in chart_style: fig_m = px.pie(df_g_m, names=x_axis, values=y_axis)
                        elif "Линейный" in chart_style: fig_m = px.line(df_g_m, x=x_axis, y=y_axis, markers=True)
                        else: fig_m = px.bar(df_g_m, x=x_axis, y=y_axis, color=x_axis)
                        
                        st.plotly_chart(fig_m, use_container_width=True, key=f"p_manual_{i}")
                    except Exception as e:
                        st.error(f"Ошибка графика №{i+1}: {e}")
                    st.markdown("<hr style='border:1px dashed #ddd'>", unsafe_allow_html=True)
                
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("➕ Добавить график/диаграмму"):
                        st.session_state.manual_charts += 1
                        st.rerun()
                with btn_col2:
                    if st.session_state.manual_charts > 1:
                        if st.button("🗑️ Удалить последнюю диаграмму"):
                            st.session_state.manual_charts -= 1
                            st.rerun()
        except Exception as merge_err:
            st.error(f"Не удалось объединить файлы: {merge_err}")
else:
    st.info("Ожидание загрузки любых файлов Excel/CSV для начала работы...")
