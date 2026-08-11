import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Enterprise BI Конструктор - Диаграммы", layout="wide")
st.title("🛠️ Enterprise No-Code Конструктор Панелей")

# НАДЁЖНАЯ ССЫЛКА НАВИГАЦИИ: Главный файл указывается как чистая строка названия файла
st.sidebar.markdown("### 🗺️ Навигация по BI-платформе")
st.sidebar.page_link("app.py", label="🗂️ 1. Загрузка и очистка данных", icon="📁")
st.sidebar.page_link("pages/charts.py", label="📊 2. Конструктор диаграмм", icon="📈")
st.sidebar.markdown("---")

# Достаем отфильтрованную и очищенную базу данных из общей памяти сессии первого файла
if "main_df" in st.session_state and not st.session_state.main_df.empty:
    main_df = st.session_state.main_df
    all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)
    
    # МЯГКИЙ СБРОС ФИЛЬТРА В БОКОВОЙ ПАНЕЛИ КОНСТРУКТОРА
    if st.session_state.active_filter_val is not None:
        st.sidebar.markdown(f"**Активный фильтр:**\n`{st.session_state.active_filter_col}` = `{st.session_state.active_filter_val}`")
        if st.sidebar.button("🧹 Очистить все фильтры", type="primary", key="clear_filters_charts_page"):
            st.session_state.active_filter_val = None
            st.session_state.active_filter_col = None
            st.rerun()

    df_filtered = main_df.copy()
    if st.session_state.active_filter_val is not None and st.session_state.active_filter_col in df_filtered.columns:
        df_filtered = df_filtered[df_filtered[st.session_state.active_filter_col].astype(str) == str(st.session_state.active_filter_val)]

    # Запускаем цикл построения графиков
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
            
        with st.expander("🎨 Полные настройки подписей, цветов, шрифтов и выносок текста"):
            cc1, cc2, cc3, cc4 = st.columns(4)
            with cc1:
                show_labels = st.checkbox("Отображать значения на графике", value=True, key=f"show_lbl_{i}")
                bar_orientation = "h" if "Bar" in chart_style and st.checkbox("Горизонтальные столбцы", value=False, key=f"bar_or_{i}") else "v"
                pie_labels_mode = st.selectbox("Стиль подписи кольца:", ["Текст на выноске (outside)", "Внутри секторов (inside)"], key=f"pie_mode_{i}") if "Donut" in chart_style else "auto"
            with cc2:
                label_pos = st.selectbox("Расположение надписи:", ["auto", "inside", "outside"], key=f"pos_{i}")
                chart_font = st.selectbox(f"Шрифт диаграммы:", ["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana"], key=f"ch_font_{i}")
            with cc3:
                label_orient = st.selectbox("Ориентация подписи осей:", ["Горизонтально (0°)", "Вертикально (90°)", "Наклонно (45°)"], key=f"orient_{i}")
                text_size = st.slider(f"Размер шрифта диаграммы (px):", 10, 24, 12, key=f"txt_sz_{i}")
            with cc4:
                text_color = st.color_picker(f"Цвет подписей и значений:", "#333333", key=f"t_color_{i}")
            
            pie_rotation = 0
            if "Donut" in chart_style:
                pie_rotation = st.slider("🔄 Поворот кольцевой диаграммы (в градусах):", 0, 360, 0, step=15, key=f"rot_{i}")
        if x_axis != "-- Выберите заголовок --" and y_axis != "-- Выберите заголовок --":
            try:
                df_m = df_filtered.copy()
                df_m[y_axis] = pd.to_numeric(df_m[y_axis], errors='coerce').fillna(0)
                df_g = df_m.groupby(x_axis, as_index=False)[y_axis].sum()
                try: df_g = df_g.sort_values(by=y_axis, ascending=True if bar_orientation == "h" else False)
                except: pass
                
                angle = 0 if "Горизонтально" in label_orient else (90 if "Вертикально" in label_orient else 45)
                fig = go.Figure()
                
                if "Waterfall" in chart_style:
                    x_data = list(df_g[x_axis].astype(str)) + ["ИТОГО"]
                    y_data = list(df_g[y_axis]) + [df_g[y_axis].sum()]
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
                
                elif "Funnel" in chart_style:
                    fig.add_trace(go.Funnel(
                        y=df_g[x_axis].astype(str), x=df_g[y_axis],
                        textposition=label_pos if show_labels else "none",
                        textinfo="value+percent initial" if show_labels else "none",
                        marker={"color": chart_color}
                    ))
                
                elif "Donut" in chart_style:
                    p_pos = "outside" if "выноске" in pie_labels_mode else "inside"
                    fig.add_trace(go.Pie(
                        labels=df_g[x_axis], values=df_g[y_axis], 
                        hole=0.4, rotation=pie_rotation, textposition=p_pos,
                        textinfo="label+value" if show_labels else "none"
                    ))
                
                elif "Line" in chart_style:
                    fig.add_trace(go.Scatter(
                        x=df_g[x_axis], y=df_g[y_axis], mode="lines+markers+text" if show_labels else "lines+markers",
                        text=df_g[y_axis].map(lambda x: f"{x:,.0f}") if show_labels else None,
                        textposition=f"{label_pos} top", line=dict(color=chart_color)
                    ))
                
                else:
                    if bar_orientation == "h":
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
                
                fig.update_layout(
                    xaxis=dict(tickangle=angle if bar_orientation == "v" else 0, tickfont=dict(color=text_color, size=text_size, family=chart_font)),
                    yaxis=dict(tickfont=dict(color=text_color, size=text_size, family=chart_font)),
                    uniformtext=dict(mode="hide", minsize=8),
                    font=dict(color=text_color, size=text_size, family=chart_font),
                    clickmode="event+select"
                )
                
                event_data = st.plotly_chart(fig, use_container_width=True, key=f"plotly_manual_{i}", on_select="rerun")
                
                if event_data and "selection" in event_data and "points" in event_data["selection"] and len(event_data["selection"]["points"]) > 0:
                    pt = event_data["selection"]["points"]
                    val = None
                    
                    if "Donut" in chart_style and "pointNumber" in pt:
                        idx = pt["pointNumber"]
                        if idx < len(df_g): val = df_g.iloc[idx][x_axis]
                    elif "label" in pt: val = pt["label"]
                    elif "x" in pt: val = pt["x"]
                    elif "y" in pt: val = pt["y"]
                    
                    if val is not None and str(val) != "ИТОГО":
                        st.session_state.active_filter_val = val
                        st.session_state.active_filter_col = x_axis
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Ошибка визуализации №{i+1}: {e}")
        else:
            st.info(f"ℹ️ Пожалуйста, выберите категории выше для построения Диаграммы № {i+1}")
            
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
    st.info("💡 Пожалуйста, перейдите на главную страницу, загрузите ваши файлы Excel/CSV, чтобы активировать Конструктор панелей.")
