import streamlit as st
import pandas as pd
import requests
import json
import re

st.set_page_config(page_title="ИИ Чат-Аналитик", layout="wide")
st.title("🧠 Персональный ИИ-Аналитик Данных & Стратег")

st.sidebar.success("🚀 Гибридный текстовый движок ИИ активен!")
st.sidebar.info("Система автоматически переключается на автономный локальный расчет отчетов, если внешний шлюз перегружен.")

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
            data_summary_for_ai += f"\nИмя файла: '{file.name}'\nВсе доступные столбцы: {list(df.columns)}\nПример реальных строк из таблицы:\n{json.dumps(sample_records, ensure_ascii=False)}\n---"
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
                {"role": "assistant", "content": "Здравствуйте! Я изучил структуру ваших файлов. Задайте мне любой вопрос. Я могу найти скрытые зависимости, сопоставить данные, выявить финансовые аномалии или составить готовый отчет для руководства."}
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
                            
                            # СПЕЦ-ФУНКЦИЯ ДЛЯ ВЫВОДА ЗАГОРОВКОВ
                            if any(w in task_lower for w in ['заголовк', 'столбц', 'колонк', 'структур']):
                                ai_response = "### 📋 Список всех обнаруженных заголовков в таблице:\n\n"
                                ai_response += "Локальный парсер успешно распознал следующие столбцы во всех загруженных файлах:\n\n"
                                for idx, col in enumerate(all_cols):
                                    type_word = "Числовой показатель" if col in numeric_cols else "Текстовая категория"
                                    if col == 'Отчетный период': type_word = "Служебный временной маркер"
                                    ai_response += f"{idx+1}. **{col}** — *({type_word})*\n"
                                ai_response += "\n Вы можете использовать любое из этих точных названий в своих аналитических запросах (например: 'покажи общую стоимость по срокам хранения')."
                                
                            else:
                                # 1. СМАРТ-ПОДБОР ЧИСЛОВОЙ КОЛОНКИ
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
                                        
                                # 2. СМАРТ-ПОДБОР КАТЕГОРИИ
                                cat_col = text_cols if text_cols else all_cols
                                found_cat = False
                                
                                # Поиск совпадений слов из запроса пользователя с именами колонок Excel
                                for col in all_cols:
                                    if col.lower() in task_lower and col != sort_col:
                                        if any(w in task_lower for w in ['срок', 'хранен', 'период', 'год', 'стать', 'фонд', 'цех', 'материал', 'счет'] if w in col.lower()):
                                            cat_col = col
                                            found_cat = True
                                            break
                                
                                if not found_cat:
                                    for col in text_cols:
                                        if any(w in col.lower() for w in ['озм', 'материал', 'наименование', 'стать', 'цех']):
                                            cat_col = col
                                            break
                                        
                                res_df[sort_col] = pd.to_numeric(res_df[sort_col], errors='coerce').fillna(0)
                                limit_match = re.search(r'(топ|top|первые)\s*(\d+)', task_lower)
                                limit_val = int(limit_match.group(2)) if limit_match else 10
                                
                                df_grouped = res_df.groupby(cat_col)[sort_col].sum().reset_index()
                                df_grouped = df_grouped.sort_values(by=sort_col, ascending=False).head(limit_val)
                                total_all = res_df[sort_col].sum()
                                
                                ai_response = f"### 💡 Результаты комплексного стратегического анализа\n\n"
                                ai_response += f"По вашему персональному аналитическому запросу встроенный локальный модуль ИИ провел обработку базы данных. "
                                ai_response += f"Выполнена точная динамическая фильтрация и ранжирование по показателю **«{sort_col}»** в разрезе аналитики **«{cat_col}»**.\n\n"
                                ai_response += f"#### 📊 Рейтинг лидирующих позиций (Выборка Топ-{limit_val}):\n"
                                
                                for idx, row in df_grouped.reset_index(drop=True).iterrows():
                                    share = (row[sort_col] / total_all * 100) if total_all > 0 else 0
                                    ai_response += f"{idx+1}. **{row[cat_col]}** — суммарный объем по базе: **{row[sort_col]:,.2f}** (Доля в общей структуре: **{share:.1f}%**)\n"
                                    
                                ai_response += f"\n#### ⚠️ 1. Ключевые выводы и обнаруженные тренды:\n"
                                if not df_grouped.empty:
                                    # ГАРАНТИРОВАННОЕ ИСПРАВЛЕНИЕ: Точные двумерные координаты строки и столбца [0, 0]
                                    leader_name = df_grouped.iloc[0, 0]
                                    leader_val = df_grouped.iloc[0, 1]
                                    ai_response += f"*   **Абсолютный лидер нагрузки**: Наибольший объем по выбранному срезу зафиксирован по позиции **{leader_name}** (**{leader_val:,.2f}**).\n"
                                ai_response += f"*   **Структурная концентрация**: Выведенные топ-{limit_val} сегментов формируют основную финансовую массу по колонке '{sort_col}'. Управленческий контроль этих элементов имеет ключевое значение.\n\n"
                                
                                ai_response += "#### 🎯 2. Дальнейшие шаги и рекомендации:\n"
                                if not df_grouped.empty:
                                    leader_name_rec = df_grouped.iloc[0, 0]
                                    ai_response += f"1. Провести детальный аудит спецификаций элементов, входящих в группу **{leader_name_rec}**.\n"
                                ai_response += f"2. Перейти во вторую вкладку нашей BI-панели и построить там кольцевую диаграмму, выбрав по оси X столбец '{cat_col}', чтобы наглядно оценить долю каждого сегмента визуально.\n"
                                ai_response += f"3. Использовать сквозную интерактивную фильтрацию по клику на панели для сопоставления категорий '{cat_col}' с годами."
                            
                            st.markdown(ai_response)
                            st.session_state.messages.append({"role": "assistant", "content": ai_response})
                        except Exception as parse_err:
                            st.error(f"Ошибка локальной обработки данных: {parse_err}")
else:
    st.info("💡 Пожалуйста, загрузите один или несколько файлов Excel/CSV сверху, чтобы активировать аналитический мозг ИИ.")
