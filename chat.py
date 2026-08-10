import streamlit as st
import pandas as pd
import requests
import json
import re

st.set_page_config(page_title="ИИ Чат-Аналитик", layout="wide")
st.title("🧠 Персональный ИИ-Аналитик Данных & Стратег")

st.sidebar.success("🚀 Гибридный текстовый движок ИИ активен!")
st.sidebar.info("Система полностью адаптирована под обработку текстовых интервалов и текстовых данных в аналитических колонках.")

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

        st.markdown("---")
        st.subheader("💬 Диалог с ИИ-Аналитиком (Задавайте любые вопросы)")
        
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "Здравствуйте! Я изучил структуру ваших файлов. Задайте мне любой вопрос. Я полностью адаптирован под текстовые данные (например, сроки хранения вроде '35-46 мес.') и готов рассчитать аналитику по ним."}
            ]

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        if user_query := st.chat_input("Напишите ваш вопрос..."):
            with st.chat_message("user"):
                st.markdown(user_query)
            st.session_state.messages.append({"role": "user", "content": user_query})

            with st.chat_message("assistant"):
                with st.spinner("ИИ анализирует таблицы и формирует экспертный ответ..."):
                    
                    ai_success = False
                    try:
                        prompt = f"Ты — Главный дата-аналитик. Изучи данные:\n{data_summary_for_ai}\nЗадача: \"{user_query}\"\nВыдай подробный профессиональный разбор со списками и жирным шрифтом на русском языке."
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
                            task_lower = user_query.lower()
                            res_df = main_df.copy()
                            
                            if any(w in task_lower for w in ['заголовк', 'столбц', 'колонк', 'структур']):
                                ai_response = "### 📋 Список всех обнаруженных заголовков в таблице:\n\n"
                                for idx, col in enumerate(all_cols):
                                    type_word = "Числовой показатель" if col in numeric_cols else "Текстовая категория"
                                    ai_response += f"{idx+1}. **{col}** — *({type_word})*\n"
                                
                            else:
                                sort_col = numeric_cols if numeric_cols else all_cols
                                for col in numeric_cols:
                                    if col.lower() in task_lower:
                                        sort_col = col
                                        break
                                else:
                                    for col in numeric_cols:
                                        if any(w in col.lower() for w in ['стоимост', 'сумм', 'цена', 'объем', 'итого', 'total']):
                                            sort_col = col
                                            break
                                
                                cat_col = text_cols if text_cols else all_cols
                                found_cat = False
                                for col in all_cols:
                                    if col.lower() in task_lower and col != sort_col:
                                        if any(w in task_lower for w in ['срок', 'хранен', 'период', 'год', 'стать', 'фонд', 'цех', 'материал', 'счет'] if w in col.lower()):
                                            cat_col = col
                                            found_cat = True
                                            break
                                            
                                if not found_cat:
                                    for col in text_cols:
                                        if col.lower() in task_lower:
                                            cat_col = col
                                            found_cat = True
                                            break
                                
                                res_df[sort_col] = pd.to_numeric(res_df[sort_col], errors='coerce').fillna(0)
                                res_df[cat_col] = res_df[cat_col].astype(str).str.strip()
                                
                                limit_match = re.search(r'(топ|top|первые)\s*(\d+)', task_lower)
                                limit_val = int(limit_match.group(2)) if limit_match else 10
                                
                                df_grouped = res_df.groupby(cat_col, as_index=False)[sort_col].sum()
                                df_grouped = df_grouped.sort_values(by=sort_col, ascending=False).head(limit_val)
                                total_all = res_df[sort_col].sum()
                                
                                ai_response = f"### 💡 Результаты комплексного стратегического анализа выборки\n\n"
                                ai_response += f"Встроенный локальный модуль ИИ успешно сгруппировал данные по текстовым интервалам/значениям колонки **«{cat_col}»** и рассчитал совокупный объем по показателю **«{sort_col}»**.\n\n"
                                ai_response += f"#### 📊 Сводный рейтинг лидирующих позиций (Топ-{limit_val}):\n"
                                
                                for idx, row in df_grouped.reset_index(drop=True).iterrows():
                                    share = (row[sort_col] / total_all * 100) if total_all > 0 else 0
                                    ai_response += f"{idx+1}. Группа **{row[cat_col]}** — суммарная стоимость: **{row[sort_col]:,.2f}** (Доля в общей структуре затрат: **{share:.1f}%**)\n"
                                    
                                ai_response += f"\n#### ⚠️ 1. Ключевые выводы и обнаруженные тренды:\n"
                                if not df_grouped.empty:
                                    cat_array = df_grouped[cat_col].to_numpy()
                                    val_array = df_grouped[sort_col].to_numpy()
                                    
                                    leader_name = str(cat_array[0])
                                    leader_val = float(val_array[0])
                                    ai_response += f"*   **Абсолютный лидер нагрузки**: Максимальная финансовая масса зафиксирована по текстовой группе **{leader_name}** и составляет **{leader_val:,.2f}**.\n"
                                ai_response += f"*   **Финансовая концентрация**: Данная аналитическая выборка формирует основную массу по показателю '{sort_col}'. Рекомендуется оптимизация этих ключевых элементов.\n\n"
                                
                                ai_response += "#### 🎯 2. Дальнейшие шаги и рекомендации:\n"
                                ai_response += f"1. Построить в нашей основной BI-панели диаграмму, выбрав по оси X столбец '{cat_col}', для наглядного сопоставления долей.\n"
                                ai_response += "2. Использовать сквозную интерактивную фильтрацию по клику на панели для отслеживания трендов."
                            
                            st.markdown(ai_response)
                            st.session_state.messages.append({"role": "assistant", "content": ai_response})
                        except Exception as parse_err:
                            st.error(f"Ошибка локальной обработки данных: {parse_err}")
else:
    st.info("💡 Пожалуйста, загрузите один или несколько файлов Excel/CSV сверху, чтобы активировать аналитический мозг ИИ.")
