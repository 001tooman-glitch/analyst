import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

st.set_page_config(page_title="Enterprise BI Конструктор", layout="wide")
st.title("🚀 Enterprise BI Конструктор & Аналитическая Панель")

# Инициализируем переменные памяти сессии
if "manual_charts" not in st.session_state:
    st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state:
    st.session_state.manual_cards = 1
# ПАМЯТЬ СКВОЗНОГО ФИЛЬТРА: запоминаем кликнутую категорию и по какой колонке кликнули
if "active_filter_val" not in st.session_state:
    st.session_state.active_filter_val = None
if "active_filter_col" not in st.session_state:
    st.session_state.active_filter_col = None

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

# БЛОК УПРАВЛЕНИЯ ДАННЫМИ (МУЛЬТИЗАГРУЗКА И СШИВАНИЕ)
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
            st.warning("⚠️ Файлы имеют разную структуру. Сводная таблица не создана. Анализ переключен на первый файл.")
            
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)

        # ПРИМЕНЕНИЕ СКВОЗНОГО ФИЛЬТРА: Если пользователь кликнул на график, режем всю базу данных!
        df_filtered = main_df.copy()
        if st.session_state.active_filter_val is not None and st.session_state.active_filter_col in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[st.session_state.active_filter_col].astype(str) == str(st.session_state.active_filter_val)]
            
            # Показываем красивую интерактивную кнопку сброса фильтра сверху
            if st.button(f"🧹 Сбросить активный фильтр: {st.session_state.active_filter_col} = {st.session_state.active_filter_val}"):
                st.session_state.active_filter_val = None
                st.session_state.active_filter_col = None
                st.rerun()

        # БЛОК ENTERPRISE KPI КАРТОЧЕК (Они теперь динамически пересчитываются от кликов!)
        st.markdown("---")
        st.subheader("🎴 Панель Ключевых Показателей (KPI Карточки)")
        
        card_cols = st.columns(st.session_state.manual_cards)
        
        for j in range(st.session_state.manual_cards):
            with card_cols[j % len(card_cols)]:
                st.markdown(f"**📌 Настройка карточки № {j+1}**")
                card_title_col = st.selectbox(f"Заголовок для карточки:", all_cols, key=f"card_t_col_{j}")
                calc_mode = st.selectbox(f"Функция расчета:", ["Сумма (SUM)", "Среднее значение (AVERAGE)"], key=f"card_calc_{j}")
                
                with st.expander(f"🎨 Стили карточки № {j+1}"):
                    bg_color = st.color_picker(f"Цвет фона карточки:", "#f8f9fa", key=f"card_bg_{j}")
                    lbl_color = st.color_picker(f"Цвет текста названия:", "#6c757d", key=f"card_lbl_c_{j}")
                    val_color = st.color_picker(f"Цвет значения:", "#1f77b4", key=f"card_val_c_{j}")
                    font_style = st.selectbox(f"Шрифт карточки:", ["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana"], key=f"card_font_{j}")
                    lbl_size = st.slider(f"Размер названия (px):", 12, 30, 16, key=f"card_lbl_sz_{j}")
                    val_size = st.slider(f"Размер значения (px):", 20, 60, 36, key=f"card_val_sz_{j}")
                
                if card_title_col != "-- Выберите заголовок --":
                    try:
                        # Расчет идет по ИЗМЕНЕННОЙ ФИЛЬТРОМ таблице df_filtered!
                        df_card_clean = df_filtered.copy()
                        df_card_clean[card_title_col] = pd.to_numeric(df_card_clean[card_title_col], errors='coerce').fillna(0)
                        
                        if "Сумма" in calc_mode:
                            card_value = df_card_clean[card_title_col].sum()
                            mode_text = "(Сумма)"
                        else:
                            card_value = df_card_clean[card_title_col].mean()
                            mode_text = "(Среднее)"
                            
                        st.markdown(f"""
                        <div style="background-color:{bg_color}; border:1px solid #dee2e6; border-radius:10px; padding:20px; text-align:center; margin-bottom:15px; font-family:{font_style}, sans-serif;">
                            <div style="color:{lbl_color}; font-size:{lbl_size}px; font-weight:500; margin-bottom:10px;">{card_title_col} {mode_text}</div>
                            <div style="color:{val_color}; font-size:{val_size}px; font-weight:bold;">{card_value:,.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    except:
                        st.error("Ошибка расчета")
                else:
                    st.caption("ℹ️ Выберите заголовок выше")
                    
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("➕ Добавить карточку показателя"):
                st.session_state.manual_cards += 1
                st.rerun()
        with c_btn2:
            if st.session_state.manual_cards > 1:
                if st.button("🗑️ Удалить последнюю карточку"):
                    st.session_state.manual_cards -= 1
                    st.rerun()
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
                    # Графики строятся по отфильтрованной базе df_filtered!
                    df_m = df_filtered.copy()
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
                    
                    # КОЛЬЦЕВАЯ
                    elif "Donut" in chart_style:
                        p_pos = "outside" if "выноске" in pie_labels_mode else "inside"
                        fig.add_trace(go.Pie(
                            labels=df_g[x_axis], values=df_g[y_axis], 
                            hole=0.4, rotation=pie_rotation, textposition=p_pos,
                            textinfo="label+value" if show_labels else "none"
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
                    
                    # СТОЛБЧАТАЯ
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
                        fig.update_layout(title=f"Распределение показателя '{y_axis}' по '{x_axis}'")
                    
                    fig.update_layout(
                        xaxis=dict(tickangle=angle if bar_orientation == "v" else 0, tickfont=dict(color=text_color, size=text_size, family=chart_font)),
                        yaxis=dict(tickfont=dict(color=text_color, size=text_size, family=chart_font)),
                        uniformtext=dict(mode="hide", minsize=8),
                        font=dict(color=text_color, size=text_size, family=chart_font),
                        clickmode="event+select" # Включаем режим перехвата кликов мыши в браузере
                    )
                    
                    # ОТОБРАЖЕНИЕ С ФУНКЦИЕЙ ОПРОСА КЛИКОВ (on_select="rerun")
                    event_data = st.plotly_chart(fig, use_container_width=True, key=f"plotly_manual_{i}", on_select="rerun")
                    
                    # Логика перехвата: если пользователь нажал на столбец или сектор
                    if event_data and "selection" in event_data and "points" in event_data["selection"] and len(event_data["selection"]["points"]) > 0:
                        clicked_point = event_data["selection"]["points"][0]
                        
                        # Записываем кликнутое значение в глобальную память сессии
                        if "x" in clicked_point:
                            st.session_state.active_filter_val = clicked_point["x"]
                            st.session_state.active_filter_col = x_axis
                            st.rerun()
                        elif "label" in clicked_point:
                            st.session_state.active_filter_val = clicked_point["label"]
                            st.session_state.active_filter_col = x_axis
                            st.rerun()
                            
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
