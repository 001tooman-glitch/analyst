import streamlit as st
import pandas as pd
import requests
import json
import re

st.set_page_config(page_title="ИИ Чат-Аналитик", layout="wide")
st.title("🧠 Персональный ИИ-Аналитик Данных & Стратег")

st.sidebar.success("🚀 Свободный чат-движок ИИ активен!")
st.sidebar.info("Вы можете выбирать готовые шаблоны из меню, либо просто вводить абсолютно любые кастомные вопросы в чат-инпут внизу.")

# Компонент для загрузки файлов в ИИ-чат
uploaded_files = st.file_uploader(
    "Загрузите один или несколько любых файлов Excel/CSV для глубокого ИИ-анализа:", 
    type=["csv", "xlsx"], 
    accept_multiple_files=True
)

if uploaded_files:
    st.subheader("📋 Загруженные таблицы в памяти ИИ:")
    combined_frames = []
    data_summary_for_ai = ""
    
    for file in uploaded_files:
        try:
            df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
            df.columns = df.columns.str.strip()
            period_name = file.name.replace(".xlsx", "").replace(".xls", "").replace(".csv", "")
            df['Отчетный период'] = period_name
            combined_frames.append(df)
            
            st.markdown(f"📄 **{file.name}** (Строк: {df.shape}, Колонок: {df.shape})")
            sample_records = df.head(3).to_dict(orient='records')
            data_summary_for_ai += f"\nИмя файла: '{file.name}'\nВсе доступные столбцы: {list(df.columns)}\n---"
        except Exception as e:
            st.error(f"Не удалось прочитать файл {file.name}: {e}")

    if combined_frames:
        main_df = pd.concat(combined_frames, ignore_index=True)
        all_cols = list(main_df.columns)
        numeric_cols = list(main_df.select_dtypes(include=['number']).columns)
        text_cols = [col for col in all_cols if col not in numeric_cols and col != 'Отчетный период']

        # Выпадающее меню готовых No-Code сценариев
        st.markdown("---")
        st.subheader("🎯 Справочные шаблоны экспресс-анализа")
        
        selected_scenario = st.selectbox(
            "Выберите шаблон из списка (или введите свой запрос в чат внизу без выбора меню):",
            [
                "-- Использовать свободный ввод вопросов в чате --",
                "🔍 Показать чистый справочный список уникальных значений (Вывод сроков, фондов, ПФМ и т.д.)",
                "📊 Рассчитать общую финансовую стоимость по выбранной категории",
                "⚠️ Выявить критические аномалии и крупные затраты по базе"
            ]
        )
        
        cat_col = text_cols if text_cols else all_cols
        sort_col = numeric_cols if numeric_cols else all_cols
        
        if selected_scenario != "-- Использовать свободный ввод вопросов в чате --":
            c1, c2 = st.columns(2)
            with c1:
                cat_col = st.selectbox("Выберите категорию (Ось X):", text_cols if text_cols else all_cols)
            with c2:
                sort_col = st.selectbox("Выберите числовой показатель (Ось Y):", numeric_cols if numeric_cols else all_cols)
            run_template = st.button("🚀 Выполнить выбранный шаблон")
        else:
            run_template = False

        st.markdown("---")
        st.subheader("💬 Диалог с ИИ-Аналитиком")
        
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "Здравствуйте! Я изучил структуру ваших файлов. Вы можете выбрать готовый шаблон аналитики выше, либо задать мне любой кастомный вопрос в свободной строке чата в самом низу."}
            ]

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        # Нижняя чат-строка для ввода ЛЮБЫХ вопросов руками
        user_query = st.chat_input("Задайте собственный вопрос по таблице сюда (например: дай названия столбцов)...")
        
        execute_analysis = False
        current_task = ""
        is_custom_mode = False
        
        if user_query:
            current_task = user_query
            execute_analysis = True
            is_custom_mode = True
        elif run_template:
            current_task = f"{selected_scenario} по категории {cat_col} и показателю {sort_col}"
            execute_analysis = True
            
        if execute_analysis:
            with st.chat_message("user"):
                st.markdown(current_task)
            st.session_state.messages.append({"role": "user", "content": current_task})

            with st.chat_message("assistant"):
                with st.spinner("Обработка данных и генерация отчета..."):
                    
                    ai_success = False
                    try:
                        prompt = f"Ты — Главный дата-аналитик. Изучи данные:\n{data_summary_for_ai}\nЗадача: \"{current_task}\"\nВыдай подробный профессиональный разбор со списками и жирным шрифтом на русском языке."
                        url = "https://openrouter.ai"
                        headers = {"Content-Type": "application/json"}
                        data = {"model": "qwen/qwen-2.5-7b-instruct:free", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
                        
                        response = requests.post(url, headers=headers, json=data, timeout=12)
                        if response.status_code == 200:
                            ai_response = response.json()['choices']['message']['content'].strip()
                            st.markdown(ai_response)
                            st.session_state.messages.append({"role": "assistant", "content": ai_response})
                            ai_success = True
                    except:
                        ai_success = False

                    if not ai_success:
                        try:
                            res_df = main_df.copy()
                            task_lower = current_task.lower()
                            
                            if any(w in task_lower for w in ['столб', 'загол', 'колон', 'назван', 'имя', 'перечисл']):
                                ai_response = "### 📋 Список всех обнаруженных заголовков и столбцов в таблице:\n\n"
                                ai_response += "Локальный парсер успешно распознал структуру загруженных файлов:\n\n"
                                for idx, col in enumerate(all_cols):
                                    type_word = "Числовой показатель" if col in numeric_cols else "Текстовая категория"
                                    if col == 'Отчетный период': type_word = "Служебный временной маркер"
                                    ai_response += f"{idx+1}. **{col}** — *({type_word})*\n"
                                ai_response += "\n Вы можете использовать любое из этих точных названий в своих запросах чата."
                                
                            else:
                                if is_custom_mode:
                                    cat_col = text_cols if text_cols else all_cols
                                    for col in all_cols:
                                        if any(root in task_lower and root in col.lower() for root in ['срок', 'хран', 'матер', 'фонд', 'пфм', 'зап', 'счёт', 'групп']):
                                            cat_col = col
                                            break
                                    sort_col = numeric_cols if numeric_cols else all_cols
                                    for col in numeric_cols:
                                        if any(w in col.lower() for w in ['стоимост', 'сумм', 'цена', 'объем', 'итого']):
                                            sort_col = col
                                            break

                                res_df[sort_col] = pd.to_numeric(res_df[sort_col], errors='coerce').fillna(0)
                                res_df[cat_col] = res_df[cat_col].astype(str).str.strip()
                                
                                limit_match = re.search(r'(топ|top|первые)\s*(\d+)', task_lower)
                                limit_val = int(limit_match.group(2)) if limit_match else 15
                                
                                if "справочный список" in selected_scenario or (is_custom_mode and not any(w in task_lower for w in ['стоимост', 'сумм', 'цена', 'объем', 'итого', 'сколько'])):
                                    val_counts = res_df[cat_col].value_counts()
                                    ai_response = f"### 📋 Справочный список уникальных значений\n\n"
                                    for idx, (val_name, count) in enumerate(val_counts.items()):
                                        if val_name and val_name != "nan" and val_name != "None":
                                            ai_response += f"{idx+1}. **{val_name}** — *(строк: {count})*\n"
                                    
                                elif "критические аномалии" in selected_scenario:
                                    mean_line = res_df[sort_col].mean()
                                    anomalies_df = res_df[res_df[sort_col] > (mean_line * 3)].sort_values(by=sort_col, ascending=False).head(10)
                                    ai_response = f"### ⚠️ Отчет по критическим финансовым аномалиям\n\n"
                                    if not anomalies_df.empty:
                                        for idx, row in anomalies_df.reset_index(drop=True).iterrows():
                                            ai_response += f"{idx+1}. В файле *{row['Отчетный период']}* позиция стоимостью **{row[sort_col]:,.2f}** (аналитика: *{row[cat_col]}*)\n"
                                    else:
                                        ai_response += "Критических скачков не обнаружено.\n"
                                else:
                                    df_grouped = res_df.groupby(cat_col, as_index=False)[sort_col].sum()
                                    df_grouped = df_grouped.sort_values(by=sort_col, ascending=False).head(limit_val)
                                    total_all = res_df[sort_col].sum()
                                    
                                    ai_response = f"### 💡 Результаты калькуляции и анализа\n\n"
                                    for idx, row in df_grouped.reset_index(drop=True).iterrows():
                                        share = (row[sort_col] / total_all * 100) if total_all > 0 else 0
                                        ai_response += f"{idx+1}. Группа **{row[cat_col]}** — общая сумма: **{row[sort_col]:,.2f}** (Доля: **{share:.1f}%**)\n"
                                
                                # Защитное исправление: если в процессе генерации текста произошла непредвиденная ошибка
                                if not ai_response:
                                    ai_response = "Массив данных успешно сгруппирован локальным модулем."
                                    
                            st.markdown(ai_response)
                            st.session_state.messages.append({"role": "assistant", "content": ai_response})
                        except Exception as parse_err:
                            st.warning("🤖 Текст запроса абстрактный. Сформирована сводная таблица по вашим данным:")
                            st.dataframe(main_df.head(10))
                            st.session_state.messages.append({"role": "assistant", "content": "Сформирован ручной просмотр базы данных."})
else:
    st.info("💡 Пожалуйста, загрузите один или несколько файлов Excel/CSV сверху, чтобы активировать аналитический мозг ИИ.")
