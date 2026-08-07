import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json

st.set_page_config(page_title="Enterprise ИИ-Аналитик", layout="wide")
st.title("🚀 Предприятие ИИ-Аналитик и BI Конструктор")

# Проверяем ключ ИИ в Secrets
api_key = st.secrets.get("openrouter_key", "")

if "manual_charts" not in st.session_state:
    st.session_state.manual_charts = 1

# Кэшируем чтение файлов для мгновенного отклика интерфейса
@st.cache_data
def load_and_merge_files(uploaded_files_list):
    frames_dict = {}
    for f in uploaded_files_list:
        try:
            df_i = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
            df_i.columns = df_i.columns.str.strip()
            df_i['Источник (Файл)'] = f.name
            frames_dict[f.name] = df_i
        except:
            pass
            
    if not frames_dict:
        return pd.DataFrame(), {}, False
        
    f_keys = list(frames_dict.keys())
    f_name = f_keys[0]
    b_cols = set(frames_dict[f_name].columns) - {'Источник (Файл)'}
    merge_possible = True
    
    for n, df_c in frames_dict.items():
        c_cols = set(df_c.columns) - {'Источник (Файл)'}
        if not b_cols.intersection(c_cols):
            merge_possible = False
            break
            
    if merge_possible:
        merged_df = pd.concat(frames_dict.values(), ignore_index=True)
        return merged_df, frames_dict, True
    else:
        return frames_dict[f_name], frames_dict, False

# 1. БЛОК УПРАВЛЕНИЯ ДАННЫМИ (МУЛЬТИЗАГРУЗКА И СШИВАНИЕ)
uploaded_files = st.file_uploader(
    "Загрузите один или несколько любых файлов Excel/CSV:", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

main_df = pd.DataFrame()
dataframes_dict = {}
is_merged = False

if uploaded_files:
    main_df, dataframes_dict, is_merged = load_and_merge_files(uploaded_files)

    if not main_df.empty:
        if is_merged:
            st.success(f"📊 Создана единая сводная база данных! Файлов: {len(uploaded_files)}. Строк: {main_df.shape}")
        else:
            st.warning("⚠️ Файлы имеют разную структуру. Анализ переключен на автоматическое установление внутренних связей.")
            
        with st.expander("📋 Просмотр структуры текущих данных (первые 5 строк)"):
            st.dataframe(main_df.head(5))
            
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)

        # 2. ВЗАИМОДЕЙСТВИЕ С ИИ КАК С АНАЛИТИКОМ ДАННЫХ
        st.markdown("---")
        st.subheader("🧠 Чат со стратегическим ИИ-Аналитиком данных")
        user_task = st.text_area("Задайте вопрос ИИ (анализ зависимостей, поиск аномалий, аудит трендов):", 
                                value="Проанализируй взаимосвязи в данных, выяви скрытые аномалии и предложи план оптимизации.")
        
        if st.button("🚀 Запустить ИИ-Консультацию"):
            if not api_key:
                st.error("Ключ ИИ не найден в Secrets!")
            else:
                with st.spinner("ИИ исследует ваши датасеты..."):
                    meta_summary = ""
                    for name, df_i in dataframes_dict.items():
                        meta_summary += f"Файл: {name}, Колонки: {list(df_i.columns)}, Строк: {df_i.shape}\nПревью:\n{json.dumps(df_i.head(2).to_dict(orient='records'), ensure_ascii=False)}\n"
                    
                    prompt = f"Ты — Главный дата-аналитик. Изучи данные:\n{meta_summary}\nЗадача от пользователя:\n{user_task}\nВыдай подробный профессиональный разбор со списками и жирным шрифтом на русском языке."
                    
                    try:
                        url = "https://sambanova.ai"
                        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                        data = {"model": "Meta-Llama-3.1-70B-Instructor", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
                        response = requests.post(url, headers=headers, json=data, timeout=20)
                        if response.status_code == 200:
                            st.markdown("### 💡 Аналитический отчет ИИ:")
                            st.markdown(response.json()['choices']['message']['content'])
                        else:
                            st.error(f"ИИ-сервер временно занят (Код {response.status_code}). Воспользуйтесь конструктором ниже.")
                    except Exception as e:
                        st.error(f"Не удалось получить ответ ИИ: {e}")
        # 3. ENTERPRISE NO-CODE КОНСТРУКТОР ДИАГРАММ
        st.markdown("---")
        st.subheader("🛠️ Enterprise No-Code Конструктор Панелей")
        
        for i in range(st.session_state.manual_charts):
            st.markdown(f"##### 📊 Настройка диаграммы № {i+1}")
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                chart_style = st.selectbox(f"Тип диаграммы:", [
                    "Столбчатая диаграмма (Bar)", "Линейный тренд (Line)", 
                    "Кольцевая долей (Donut)", "Диаграмма Водопад (Waterfall)", "Диаграмма Воронка (Funnel)"
                ], key=f"style_{i}")
            with c2:
                x_axis = st.selectbox(f"Ось X (Категории):", all_cols, key=f"x_{i}")
            with c3:
                y_axis = st.selectbox(f"Ось Y (Показатели):", all_cols, key=f"y_{i}")
            with c4:
                chart_color = st.color_picker(f"Цвет элементов:", "#1f77b4", key=f"color_{i}")
                
            # Продвинутые настройки отображения значений, шрифтов, вращения и ориентации
            with st.expander("🎨 Настройки подписей, цветов, углов поворота и ориентации осей"):
                cc1, cc2, cc3, cc4 = st.columns(4)
                with cc1:
                    show_labels = st.checkbox("Отображать значения на графике", value=True, key=f"show_lbl_{i}")
                    # Динамическая кнопка горизонтального режима для столбчатого графика
                    bar_orientation = "h" if "Bar" in chart_style and st.checkbox("Горизонтальные столбцы", value=False, key=f"bar_or_{i}") else "v"
                with cc2:
                    label_pos = st.selectbox("Расположение надписи:", ["auto", "inside", "outside"], key=f"pos_{i}")
                with cc3:
                    label_orient = st.selectbox("Ориентация надписи на осях:", ["Горизонтально (0°)", "Вертикально (90°)", "Наклонно (45°)"], key=f"orient_{i}")
                with cc4:
                    text_color = st.color_picker(f"Цвет подписей и значений:", "#333333", key=f"t_color_{i}")
                
                # Добавляем ползунок вращения только для кольцевой диаграммы
                pie_rotation = 0
                if "Donut" in chart_style:
                    pie_rotation = st.slider("🔄 Поворот кольцевой диаграммы (в градусах):", 0, 360, 0, step=15, key=f"rot_{i}")
            
            if x_axis != "-- Выберите заголовок --" and y_axis != "-- Выберите заголовок --":
                try:
                    df_m = main_df.copy()
                    df_m[y_axis] = pd.to_numeric(df_m[y_axis], errors='coerce').fillna(0)
                    df_g = df_m.groupby(x_axis, as_index=False)[y_axis].sum()
                    try: df_g = df_g.sort_values(by=y_axis, ascending=True if bar_orientation == "h" else False)
                    except: pass
                    
                    angle = 0 if "Горизонтально" in label_orient else (90 if "Вертикально" in label_orient else 45)
                    fig = go.Figure()
                    
                    # СТРОИМ ВОДОПАД
                    if "Waterfall" in chart_style:
                        x_data = list(df_g[x_axis].astype(str)) + ["ИТОГО"]
                        y_data = list(df_g[y_axis]) + [0]
                        measure_data = ["relative"] * len(df_g[y_axis]) + ["total"]
                        text_data = [f"{v:,.0f}" for v in df_g[y_axis]] + [f"{df_g[y_axis].sum():,.0f}"]
                        
                        fig.add_trace(go.Waterfall(
                            x=x_data, y=y_data, measure=measure_data,
                            textposition=label_pos if show_labels else "none",
                            text=text_data if show_labels else None,
                            increasing={"marker": {"color": chart_color}},
                            decreasing={"marker": {"color": "red"}},
                            totals={"marker": {"color": "green"}}
                        ))
                        fig.update_layout(title=f"Водопад изменений '{y_axis}' по '{x_axis}'")
                    
                    # СТРОИМ ВОРОНКУ
                    elif "Funnel" in chart_style:
                        fig.add_trace(go.Funnel(
                            y=df_g[x_axis].astype(str), x=df_g[y_axis],
                            textposition=label_pos if show_labels else "none",
                            textinfo="value+percent initial" if show_labels else "none",
                            marker={"color": chart_color}
                        ))
                        fig.update_layout(title=f"Воронка распределения '{y_axis}' по '{x_axis}'")
                    
                    # КРУГОВАЯ / КОЛЬЦЕВАЯ С ФУНКЦИЕЙ ВРАЩЕНИЯ
                    elif "Donut" in chart_style:
                        fig.add_trace(go.Pie(
                            labels=df_g[x_axis], values=df_g[y_axis], 
                            hole=0.4, rotation=pie_rotation, textinfo="label+value" if show_labels else "none"
                        ))
                        fig.update_layout(title=f"Доли распределения '{y_axis}'")
                    
                    # ЛИНЕЙНЫЙ
                    elif "Line" in chart_style:
                        fig.add_trace(go.Scatter(
                            x=df_g[x_axis], y=df_g[y_axis], mode="lines+markers+text" if show_labels else "lines+markers",
                            text=df_g[y_axis].map(lambda x: f"{x:,.0f}") if show_labels else None,
                            textposition=f"{label_pos} top", line=dict(color=chart_color)
                        ))
                        fig.update_layout(title=f"Тренд показателя '{y_axis}' по '{x_axis}'")
                    
                    # СТОЛБЧАТАЯ С УПРАВЛЕНИЕМ ВЕРТИКАЛЬНОЙ/ГОРИЗОНТАЛЬНОЙ ОРИЕНТАЦИЕЙ
                    else:
                        if bar_orientation == "h":
                            # Переворачиваем x и y для горизонтального отображения
                            fig.add_trace(go.Bar(
                                y=df_g[x_axis].astype(str), x=df_g[y_axis],
                                text=df_g[y_axis].map(lambda x: f"{x:,.0f}") if show_labels else None,
                                textposition=label_pos, orientation="h", marker_color=chart_color
                            ))
                        else:
                            fig.add_trace(go.Bar(
                                x=df_g[x_axis].astype(str), y=df_g[y_axis],
                                text=df_g[y_axis].map(lambda x: f"{x:,.0f}") if show_labels else None,
                                textposition=label_pos, orientation="v", marker_color=chart_color
                            ))
                        fig.update_layout(title=f"Распределение показателя '{y_axis}' по '{x_axis}'")
                    
                    fig.update_layout(
                        xaxis=dict(tickangle=angle if bar_orientation == "v" else 0, tickfont=dict(color=text_color)),
                        yaxis=dict(tickfont=dict(color=text_color)),
                        uniformtext=dict(mode="hide", minsize=8),
                        font=dict(color=text_color)
                    )
                    st.plotly_chart(fig, use_container_width=True, key=f"plotly_manual_{i}")
                    
                except Exception as e:
                    st.error(f"Ошибка визуализации №{i+1}: {e}")
            else:
                st.info(f"ℹ️ Пожалуйста, выберите категорию (Ось X) и числовой показатель (Ось Y) выше для построения Диаграммы № {i+1}")
                
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
else:
    st.info("Ожидание загрузки любых файлов Excel/CSV для активации BI-панели...")
