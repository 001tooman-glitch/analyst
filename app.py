import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="Enterprise BI Конструктор", layout="wide")
st.title("🚀 Модуль Предобработки & Импорта Данных")

# ИСПРАВЛЕННАЯ ССЫЛКА НАВИГАЦИИ: Главная страница обозначается точкой "."
st.sidebar.markdown("### 🗺️ Навигация по BI-платформе")
st.sidebar.page_link(".", label="🗂️ 1. Загрузка и очистка данных", icon="📁")
st.sidebar.page_link("pages/charts.py", label="📊 2. Конструктор диаграмм", icon="📈")
st.sidebar.markdown("---")

if "manual_charts" not in st.session_state:
    st.session_state.manual_charts = 1
if "manual_cards" not in st.session_state:
    st.session_state.manual_cards = 1
if "active_filter_val" not in st.session_state:
    st.session_state.active_filter_val = None
if "active_filter_col" not in st.session_state:
    st.session_state.active_filter_col = None
if "main_df" not in st.session_state:
    st.session_state.main_df = pd.DataFrame()

# КЭШ-ДВИЖОК С АВТОМАТИЧЕСКОЙ ОЧИСТКОЙ И ВЫРАВНИВАНИЕМ СТРУКТУРЫ ТАБЛИЦ
@st.cache_data
def load_clean_and_merge_files(uploaded_files_list):
    frames_dict = {}
    if not uploaded_files_list:
        return pd.DataFrame(), {}, False
        
    for f in uploaded_files_list:
        try:
            df_i = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f, header=None)
            
            if df_i.shape > 1:
                row0 = df_i.iloc[0].astype(str).str.strip()
                row1 = df_i.iloc[1].astype(str).str.strip()
                is_row1_text = pd.to_numeric(row1, errors='coerce').isna().all()
                
                if is_row1_text:
                    new_cols = []
                    for c0, c1 in zip(row0, row1):
                        c0_c = "" if c0 in ['nan', 'None', 'Unnamed:'] or 'Unnamed' in c0 else c0
                        c1_c = "" if c1 in ['nan', 'None', 'Unnamed:'] or 'Unnamed' in c1 else c1
                        combined_name = f"{c0_c} {c1_c}".strip()
                        new_cols.append(combined_name if combined_name else "Без названия")
                    df_i.columns = new_cols
                    df_i = df_i.iloc[2:].reset_index(drop=True)
                else:
                    df_i.columns = row0
                    df_i = df_i.iloc[1:].reset_index(drop=True)
            
            # ОЧИСТКА ЗАГОРОВКОВ: полностью вырезаем артефакты nan, nan №, Unnamed из шапки
            cleaned_cols = []
            for col in df_i.columns:
                c_str = str(col).replace('nan №', '').replace('№ nan', '').replace('nan', '').replace('Unnamed:', '').strip()
                c_str = re.sub(r'\s+', ' ', c_str).strip()
                cleaned_cols.append(c_str if c_str else "Без названия")
                
            df_i.columns = cleaned_cols
            df_i = df_i.loc[:, ~df_i.columns.str.contains('^Без названия|^Unnamed')]
            df_i = df_i.loc[:, ~df_i.columns.duplicated()]
            
            period_name = f.name.replace(".xlsx", "").replace(".xls", "").replace(".csv", "")
            df_i['Источник (Файл)'] = period_name
            frames_dict[f.name] = df_i
        except:
            pass
            
    if not frames_dict:
        return pd.DataFrame(), {}, False
        
    f_keys = list(frames_dict.keys())
    first_file_name = f_keys[0] if f_keys else ""
    if not first_file_name: 
        return pd.DataFrame(), {}, False
    
    base_cols = set(frames_dict[first_file_name].columns) - {'Источник (Файл)'}
    merge_possible = True
    
    for n, df_c in frames_dict.items():
        c_cols = set(df_c.columns) - {'Источник (Файл)'}
        if not base_cols.intersection(c_cols):
            merge_possible = False
            break
            
    if merge_possible:
        merged_df = pd.concat(frames_dict.values(), ignore_index=True)
        merged_df = merged_df.dropna(how='all')
        return merged_df, frames_dict, True
    else:
        merged_df = pd.concat(frames_dict.values(), ignore_index=True, join='outer')
        merged_df = merged_df.dropna(how='all')
        return merged_df, frames_dict, False
uploaded_files = st.file_uploader(
    "Загрузите один или несколько любых файлов Excel/CSV:", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

main_df = pd.DataFrame()
dataframes_dict = {}
is_merged = False

if uploaded_files:
    main_df, dataframes_dict, is_merged = load_clean_and_merge_files(uploaded_files)

    if not main_df.empty:
        # Сохраняем сводную базу в общую память сессии для графической страницы
        st.session_state.main_df = main_df
        
        if is_merged:
            st.success(f"📊 Создана единая сводная база данных! Файлов: {len(uploaded_files)}. Строк: {main_df.shape}, Колонок: {main_df.shape}")
        else:
            st.warning(f"⚠️ Файлы имеют разную структуру (колонки не совпадают на 100%). Сводная база объединена через режим 'Outer Join'. Строк: {main_df.shape}, Колонок: {main_df.shape}")
            
        st.markdown("### 📋 Структура сводной таблицы (Заголовки и первые 5 строк):")
        
        try:
            preview_df = main_df.head(5).copy()
            for col in preview_df.columns:
                preview_df[col] = preview_df[col].astype(str).fillna("Пусто")
            st.dataframe(preview_df, use_container_width=True)
        except Exception as table_err:
            st.error(f"Не удалось отобразить превью таблицы: {table_err}")
        
        # СКАЧИВАНИЕ СВОДНОГО EXCEL ЧЕРЕЗ OPENPYXL
        @st.cache_data
        def convert_df_to_excel(df):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as wr:
                df.to_excel(wr, index=False, sheet_name='Сводные данные')
            return output.getvalue()
            
        try:
            excel_data = convert_df_to_excel(main_df)
            st.download_button(
                label="📥 Скачать объединенную сводную базу (Excel)",
                data=excel_data,
                file_name="Сводный_отчет_очищенный.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as download_err:
            st.error(f"Не удалось подготовить файл для скачивания: {download_err}")
            
        all_cols = ["-- Выберите заголовок --"] + list(main_df.columns)

        st.sidebar.success("🟢 Интерактивный BI-движок активен!")
        if st.session_state.active_filter_val is not None:
            st.sidebar.markdown(f"**Активный фильтр:**\n`{st.session_state.active_filter_col}` = `{st.session_state.active_filter_val}`")
            if st.sidebar.button("🧹 Очистить все фильтры", type="primary", key="clear_filters_main_page"):
                st.session_state.active_filter_val = None
                st.session_state.active_filter_col = None

        df_filtered = main_df.copy()
        if st.session_state.active_filter_val is not None and st.session_state.active_filter_col in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[st.session_state.active_filter_col].astype(str) == str(st.session_state.active_filter_val)]

        st.markdown("---")
        st.subheader("🎴 Панель Ключевых Показателей (KPI Карточки)")
        
        card_cols = st.columns(st.session_state.manual_cards)
        
        for j in range(st.session_state.manual_cards):
            with card_cols[j % len(card_cols)]:
                st.markdown(f"**📌 Настройка карточки № {j+1}**")
                card_title_col = st.selectbox(f"Заголовок для карточки:", all_cols, key=f"card_t_col_{j}")
                calc_mode = st.selectbox(f"Функция расчета:", ["Сумма (SUM)", "Среднее значение (AVERAGE)"], key=f"card_calc_{j}")
                
                with st.expander("🎨 Стили карточки"):
                    bg_color = st.color_picker(f"Цвет фона карточки:", "#f8f9fa", key=f"card_bg_{j}")
                    lbl_color = st.color_picker(f"Цвет текста названия:", "#6c757d", key=f"card_lbl_c_{j}")
                    val_color = st.color_picker(f"Цвет значения:", "#1f77b4", key=f"card_val_c_{j}")
                    font_style = st.selectbox(f"Шрифт карточки:", ["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana"], key=f"card_font_{j}")
                    lbl_size = st.slider(f"Размер названия (px):", 12, 30, 16, key=f"card_lbl_sz_{j}")
                    val_size = st.slider(f"Размер значения (px):", 20, 60, 36, key=f"card_val_sz_{j}")
                
                if card_title_col != "-- Выберите заголовок --":
                    try:
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
        with c_btn2:
            if st.session_state.manual_cards > 1:
                if st.button("🗑️ Удалить последнюю карточку"):
                    st.session_state.manual_cards -= 1
else:
    st.info("Ожидание загрузки любых файлов Excel/CSV для активации BI-панели...")
