# Система мониторинга успеваемости студентов

## Описание
Интеллектуальная система для мониторинга и прогнозирования успеваемости студентов на основе анализа образовательных траекторий.

## Функциональность
- 📊 Дашборд с визуализацией метрик
- 🤖 ML модель (Random Forest) для прогнозирования рисков
- 🔄 Process Mining анализ траекторий
- 🔔 Система оповещений для кураторов
- 📑 Генерация подробных отчетов (TXT, HTML)

## Технологии
- Python, Django, PostgreSQL
- Streamlit, Plotly
- Scikit-learn, Pandas
- ReportLab, Matplotlib

## Установка и запуск
```bash
# Клонировать репозиторий
git clone https://github.com/lilinek/student-monitoring.git
cd student-monitoring

# Создать виртуальное окружение
python -m venv venv
venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt

# Настроить базу данных PostgreSQL
# (создать БД student_monitoring)

# Запустить дашборд
streamlit run dashboard_with_ml.py