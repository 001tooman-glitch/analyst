import streamlit as st
import pandas as pd
import requests
import json
import re

st.set_page_config(page_title="ИИ Чат-Аналитик", layout="wide")
st.title("🧠 Персональный ИИ-Аналитик Данных & Стратег")

st.sidebar.success("🚀 Интерактивный No-Code движок ИИ активен!")
st.sidebar.info("Выберите готовый сценарий анализа из выпадающего меню или введите свой запрос вручную.")

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

        # 🛠️ НОВЫЙ БЛОК: ИНТЕРАКТИВНОЕ NO-CODE МЕНЮ СЦЕНАРИЕВ
        st.markdown("---")
        st.subheader("🎯 Панель выбора аналитического сценария")
        
        selected_scenario = st.selectbox(
            "Выберите тип анализа, который хотите провести:",
            [
                "🔍 Показать чистый справочный список уникальных значений (Вывод сроков, фондов, ПФМ и т.д.)",
                "📊 Рассчитать общую финансовую стоимость по выбранной категории",
                "⚠️ Выявить критические аномалии и крупные затраты по базе",
                "💬 Мой собственный текстовый запрос (Ввести задачу вручную текстом)"
            ]
        )
        
        # Переменные для осей
        c1, c2 = st.columns(2)
        with c1:
            target_category = st.selectbox("Выберите категорию для исследования (Ось X):", text_cols if text_cols else all_cols)
        with c2:
            target_metric = st.selectbox("Выберите числовой показатель (Ось Y):", numeric_cols if numeric_cols else all_cols)

        # Поле ввода показываем только если выбран кастомный режим
        user_input_task = ""
        if "Собственный" in selected_scenario:
            user_input_task = st.text_area("Опишите вашу уникальную задачу своими словами:", value="какие сроки хранения указаны?")

        st.markdown("---")
        st.subheader("💬 Диалог с ИИ-Аналитиком")
        
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "Здравствуйте! Я изучил структуру файлов. Выберите готовый аналитический сценарий выше или введите свой запрос, и я мгновенно сформирую отчет."}
            ]

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        # Кнопка запуска анализа по выбранному сценарию
        if st.button("🚀 Выполнить выбранный сценарий анализа"):
            # Формируем итоговый текст задачи
            if "Собственный" in selected_scenario:
                current_task = user_input_task
            else:
                current_task = f"{selected_scenario} по категории {target_category} и показателю {target_metric}"
                
            with st.chat_message("user"):
                st.markdown(current_task)
            st.session_state.messages.append({"role": "user", "content": current_task})

            with st.chat_message("assistant"):
                with st.spinner("ИИ обрабатывает данные и строит отчет..."):
                    
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
                            cat_col = target_category
                            sort_col = target_metric
                            
                            # Если выбран кастомный режим — перехватываем умный подбор колонок по тексту
                            if "Собственный" in selected_scenario:
                                task_lower = current_task.lower()
                                for col in all_cols:
                                    if any(root in task_lower and root in col.lower() for root in ['срок', 'хран', 'матер', 'фонд', 'пфм', 'зап', 'счёт']):
                                        cat_col = col
                                        break
                                for col in numeric_cols:
                                    if any(w in col.lower() for w in ['стоимост', 'сумм', 'цена', 'объем', 'итого']):
                                        sort_col = col
                                        break

                            # Принудительная очистка типов данных
                            res_df[sort_col] = pd.to_numeric(res_df[sort_col], errors='coerce').fillna(0)
                            res_df[cat_col] = res_df[cat_col].astype(str).str.strip()
                            
                            # ИСПОЛНЕНИЕ СЦЕНАРИЯ №1: ЧИСТЫЙ СПРАВОЧНЫЙ СПИСОК (БЕЗ ДЕНЕГ)
                            if "чистый справочный список" in selected_scenario or ( "Собственный" in selected_scenario and not any(w in current_task.lower() for w in ['стоимост', 'сумм', 'цена', 'объем', 'итого']) ):
                                val_counts = res_df[cat_col].value_counts()
                                
                                ai_response = f"### 📋 Справочный список уникальных значений\n\n"
                                ai_response += f"В соответствии с выбранным сценарием, извлечены все уникальные текстовые элементы из столбца **«{cat_col}»**:\n\n"
                                for idx, (val_name, count) in enumerate(val_counts.items()):
                                    if val_name and val_name != "nan" and val_name != "None":
                                        ai_response += f"{idx+1}. **{val_name}** — *(зафиксировано строк в базе: {count})*\n"
                                ai_response += f"\n Всего в таблице обнаружено уникальных групп: **{len(val_counts)}**."
                            
                            # ИСПОЛНЕНИЕ СЦЕНАРИЯ №3: ПОИСК КРИТИЧЕСКИХ АНОМАЛИЙ
                            elif "критические аномалии" in selected_scenario:
                                mean_line = res_df[sort_col].mean()
                                anomalies_df = res_df[res_df[sort_col] > (mean_line * 3)].sort_values(by=sort_col, ascending=False).head(10)
                                
                                ai_response = f"### ⚠️ Отчет по критическим финансовым аномалиям\n\n"
                                ai_response += f"Локальный модуль просканировал колонку **«{sort_col}»** на предмет единичных записей, превышающих средний уровень по базе ({mean_line:,.2f}) более чем в 3 раза.\n\n"
                                if not anomalies_df.empty:
                                    ai_response += "**Обнаружены следующие крупные пиковые расходы:**\n"
                                    for idx, row in anomalies_df.reset_index(drop=True).iterrows():
                                        ai_response += f"{idx+1}. В периоде *{row['Отчетный период']}* зафиксирована позиция стоимостью **{row[sort_col]:,.2f}** (аналитический срез: *{row[cat_col]}*)\n"
                                else:
                                    ai_response += "Критических единичных скачков и аномалий в строках не обнаружено, расходы распределены равномерно.\n"

                            # ИСПОЛНЕНИЕ СЦЕНАРИЯ №2: ЭКОНОМИЧЕСКИЙ РАСЧЕТ СУММЫ (Ваш прошлый точный отчет по ОЗМ/Срокам)
                            else:
                                df_grouped = res_df.groupby(cat_col, as_index=False)[sort_col].sum()
                                df_grouped = df_grouped.sort_values(by=sort_col, ascending=False).head(15)
                                total_all = res_df[sort_col].sum()
                                
                                ai_response = f"### 💡 Результаты комплексного анализа и калькуляции\n\n"
                                ai_response += f"Модуль успешно сгруппировал таблицу по значениям **«{cat_col}»** и рассчитал суммарный объем по показателю **«{sort_col}»**:\n\n"
                                
                                for idx, row in df_grouped.reset_index(drop=True).iterrows():
                                    share = (row[sort_col] / total_all * 100) if total_all > 0 else 0
                                    ai_response += f"{idx+1}. Группа/Интервал **{row[cat_col]}** — суммарная стоимость: **{row[sort_col]:,.2f}** (Доля в общей структуре: **{share:.1f}%**)\n"
                                    
                                ai_response += f"\n#### ⚠️ Ключевые рекомендации:\n"
                                ai_response += f"1. Рекомендуется построить в нашей основной BI-панели диаграмму по оси X '{cat_col}' для наглядного контроля долей.\n"
                                ai_response += f"2. Используйте сквозную фильтрацию по клику на дашборде для сквозного контроля трендов."
                            
                            st.markdown(ai_response)
                            st.session_state.messages.append({"role": "assistant", "content": ai_response})
                        except Exception as parse_err:
                            st.error(f"Ошибка локальной обработки данных: {parse_err}")
else:
    st.info("💡 Пожалуйста, загрузите один или несколько файлов Excel/CSV сверху, чтобы активировать аналитический мозг ИИ.")
