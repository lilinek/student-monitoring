"""
Полный дашборд для мониторинга успеваемости студентов
с системой оповещений и анализом конформности
Запуск: streamlit run dashboard_with_ml.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import django
import os
import sys
from datetime import datetime, timedelta
import numpy as np
import joblib
import glob
import traceback

# Настройка Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Импорт моделей Django
from api.models import Student, Event, StudentFeatures
import django.db.models as models

# Загрузка ML модели
@st.cache_resource
def load_ml_model():
    """Загружает ML модель и компоненты"""
    try:
        model = joblib.load('risk_model.pkl')
        scaler = joblib.load('scaler.pkl')
        le = joblib.load('label_encoder.pkl')
        feature_columns = joblib.load('feature_columns.pkl')
        return model, scaler, le, feature_columns, True
    except Exception as e:
        print(f"Ошибка загрузки модели: {e}")
        return None, None, None, None, False

# Загрузка системы оповещений
@st.cache_resource
def get_alert_system():
    try:
        sys.path.append(os.path.dirname(__file__))
        from alerts_system import AlertSystem
        return AlertSystem()
    except Exception as e:
        print(f"Ошибка загрузки AlertSystem: {e}")
        return None

# Загрузка калькулятора конформности
@st.cache_resource
def get_conformance_calculator():
    try:
        sys.path.append(os.path.dirname(__file__))
        from conformance import ConformanceCalculator
        return ConformanceCalculator()
    except Exception as e:
        print(f"Ошибка загрузки ConformanceCalculator: {e}")
        return None

# Загружаем модели
model, scaler, le, feature_columns, model_loaded = load_ml_model()
alert_system = get_alert_system()
conformance_calc = get_conformance_calculator()

# Настройка страницы
st.set_page_config(
    page_title="Мониторинг студентов",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Заголовок
st.title("📊 Система мониторинга успеваемости с прогнозами на основе машинного обучения")
st.markdown("---")

# ======================================================================
# БОКОВАЯ ПАНЕЛЬ С ФИЛЬТРАМИ И ОПОВЕЩЕНИЯМИ
# ======================================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/student-center.png", width=100)
    st.header("🔍 Фильтры")
    
    # Получаем данные из БД
    students = Student.objects.all()
    courses = list(set([s.course for s in students]))
    
    selected_course = st.selectbox(
        "Курс",
        ["Все"] + courses
    )
    
    risk_levels = ['low', 'medium', 'high']
    selected_risk = st.selectbox(
        "Уровень риска",
        ["Все"] + risk_levels
    )
    
    if model_loaded:
        st.success("✅ ML модель загружена")
    else:
        st.warning("⚠️ ML модель не загружена")
    
    st.markdown("---")
    st.markdown("**Информация**")
    st.info("🟢 Низкий риск\n🟡 Средний риск\n🔴 Высокий риск")
    
    # ===== СИСТЕМА ОПОВЕЩЕНИЙ =====
    st.markdown("---")
    st.header("🔔 Система оповещений")
    
    if alert_system:
        try:
            # Проверяем алерты
            red_alerts = alert_system.check_red_alerts()
            yellow_alerts = alert_system.check_yellow_alerts()
            
            # Отображаем красные алерты
            if red_alerts:
                st.error(f"🔴 **{len(red_alerts)} студентов требуют срочного вмешательства!**")
                with st.expander(f"Показать список ({len(red_alerts)} чел.)"):
                    for alert in red_alerts[:10]:
                        st.write(f"**{alert['student'].name}**")
                        st.write(f"Риск: {alert['risk_score']:.2f}")
                        if st.button(f"📧 Уведомить", key=f"red_{alert['student'].student_id}"):
                            alert_system.send_email_alert('curator@university.ru', alert)
                            st.success(f"Уведомление отправлено")
                        st.markdown("---")
            
            # Отображаем желтые алерты
            if yellow_alerts:
                st.warning(f"🟡 **{len(yellow_alerts)} студентов требуют внимания**")
                with st.expander(f"Показать список ({len(yellow_alerts)} чел.)"):
                    for alert in yellow_alerts[:10]:
                        st.write(f"**{alert['student'].name}**")
                        st.write(f"Причина: {alert['reason']}")
                        st.markdown("---")
            
            # Статистика
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔴 Красный", len(red_alerts))
            with col2:
                st.metric("🟡 Желтый", len(yellow_alerts))
            with col3:
                total = Student.objects.count()
                st.metric("👥 Всего", total)
                
        except Exception as e:
            st.error(f"Ошибка в системе оповещений: {e}")
    else:
        st.warning("⚠️ Система оповещений не загружена")
    
    # ===== ОТЧЕТЫ =====
    st.markdown("---")
    st.header("📑 Отчеты")
    
    # Простой отчет
    if st.button("📊 Сгенерировать простой отчет", use_container_width=True):
        with st.spinner("Генерация отчета..."):
            try:
                red, yellow = alert_system.generate_report()
                st.success(f"✅ Простой отчет создан! Красных: {len(red)}, Желтых: {len(yellow)}")
                
                report_files = glob.glob("report_*.txt")
                if report_files:
                    latest_report = max(report_files, key=os.path.getctime)
                    with open(latest_report, 'r', encoding='utf-8') as f:
                        report_content = f.read()
                        st.download_button(
                            label="📥 Скачать простой отчет",
                            data=report_content,
                            file_name=latest_report,
                            mime="text/plain",
                            use_container_width=True
                        )
            except Exception as e:
                st.error(f"Ошибка при генерации отчета: {e}")
    
    # Подробный отчет
    if st.button("📊 Сгенерировать подробный отчет", use_container_width=True):
        with st.spinner("Генерация подробного отчета... Это может занять несколько секунд"):
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, "improved_report.py"], 
                    capture_output=True, 
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    st.success("✅ Подробные отчеты успешно созданы!")
                    
                    txt_files = glob.glob("detailed_report_*.txt")
                    html_files = glob.glob("detailed_report_*.html")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if txt_files:
                            latest_txt = max(txt_files, key=os.path.getctime)
                            with open(latest_txt, 'r', encoding='utf-8') as f:
                                txt_content = f.read()
                                st.download_button(
                                    label="📥 Скачать подробный TXT отчет",
                                    data=txt_content,
                                    file_name=latest_txt,
                                    mime="text/plain",
                                    use_container_width=True
                                )
                    
                    with col2:
                        if html_files:
                            latest_html = max(html_files, key=os.path.getctime)
                            with open(latest_html, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                                st.download_button(
                                    label="📥 Скачать подробный HTML отчет",
                                    data=html_content,
                                    file_name=latest_html,
                                    mime="text/html",
                                    use_container_width=True
                                )
                    
                    with st.expander("👁️ Предпросмотр отчета"):
                        if txt_files:
                            with open(latest_txt, 'r', encoding='utf-8') as f:
                                preview = f.read()[:2000]
                                st.text(preview)
                                st.info("... и т.д. (отчет сокращен для предпросмотра)")
                else:
                    st.error(f"❌ Ошибка при генерации отчета: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                st.error("❌ Превышено время ожидания генерации отчета")
            except Exception as e:
                st.error(f"❌ Ошибка: {e}")
    
    # Функция для быстрого отчета
    def generate_dashboard_report():
        students_count = Student.objects.count()
        events_count = Event.objects.count()
        
        risk_stats = StudentFeatures.objects.values('risk_level').annotate(
            count=models.Count('id')
        )
        
        risk_dict = {item['risk_level']: item['count'] for item in risk_stats}
        high_count = risk_dict.get('high', 0)
        medium_count = risk_dict.get('medium', 0)
        low_count = risk_dict.get('low', 0)
        
        report = f"""
        {"="*60}
        ОТЧЕТ ПО МОНИТОРИНГУ СТУДЕНТОВ
        Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}
        {"="*60}
        
        ОБЩАЯ СТАТИСТИКА:
        • Всего студентов: {students_count}
        • Всего событий: {events_count}
        
        РАСПРЕДЕЛЕНИЕ ПО РИСКАМ:
        • 🔴 Высокий риск: {high_count} чел. ({high_count/students_count*100:.1f}%)
        • 🟡 Средний риск: {medium_count} чел. ({medium_count/students_count*100:.1f}%)
        • 🟢 Низкий риск: {low_count} чел. ({low_count/students_count*100:.1f}%)
        
        СТУДЕНТЫ С ВЫСОКИМ РИСКОМ:
        """
        
        high_risk_students = StudentFeatures.objects.filter(
            risk_level='high'
        ).select_related('student').order_by('-risk_score')[:10]
        
        for i, fs in enumerate(high_risk_students, 1):
            report += f"\n        {i}. {fs.student.name} ({fs.student.course}) - риск {fs.risk_score:.2f}"
        
        report += f"""
        
        РЕКОМЕНДАЦИИ:
        🔴 Высокий риск: Немедленно связаться с кураторами
        🟡 Средний риск: Увеличить частоту коммуникации
        🟢 Низкий риск: Продолжать в том же духе
        
        {"="*60}
        Отчет сгенерирован автоматически
        {"="*60}
        """
        
        return report
    
    # Быстрый отчет
    if st.button("⚡ Сгенерировать быстрый отчет", use_container_width=True):
        try:
            report_content = generate_dashboard_report()
            st.download_button(
                label="📥 Скачать быстрый отчет",
                data=report_content,
                file_name=f"quick_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Ошибка при генерации быстрого отчета: {e}")
    
    # ZIP архив
    if st.button("📦 Скачать все отчеты (ZIP)", use_container_width=True):
        try:
            import zipfile
            import io
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_pattern in ["report_*.txt", "detailed_report_*.txt", "detailed_report_*.html", "quick_report_*.txt"]:
                    for file in glob.glob(file_pattern):
                        if os.path.exists(file):
                            zip_file.write(file, os.path.basename(file))
            
            zip_buffer.seek(0)
            
            st.download_button(
                label="📥 Скачать ZIP архив",
                data=zip_buffer,
                file_name=f"reports_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
                mime="application/zip",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Ошибка при создании архива: {e}")

# ======================================================================
# ПОЛУЧЕНИЕ ДАННЫХ
# ======================================================================
students_qs = Student.objects.all()
if selected_course != "Все":
    students_qs = students_qs.filter(course=selected_course)

features = StudentFeatures.objects.filter(student__in=students_qs)
if selected_risk != "Все":
    features = features.filter(risk_level=selected_risk)

# Преобразуем в DataFrame
students_data = []
for f in features:
    students_data.append({
        'id': f.student.student_id,
        'name': f.student.name,
        'course': f.student.course,
        'semester': f.student.semester,
        'risk_score': f.risk_score,
        'risk_level': f.risk_level,
        'activity': f.activity_count_last_week,
        'missed': f.missed_deadlines_count,
        'avg_score': f.success_rate_midterms,
        'days_since_login': f.days_since_last_login,
        'avg_delay': f.avg_assignment_delay
    })

df = pd.DataFrame(students_data)

# ======================================================================
# ВКЛАДКИ
# ======================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Общая", 
    "👥 Студенты", 
    "🔄 Process Mining", 
    "📊 Аналитика",
    "🤖 ML Прогнозы"
])

# ======================================================================
# ВКЛАДКА 1: ОБЩАЯ
# ======================================================================
with tab1:
    st.header("Общая панель мониторинга")
    
    if df.empty:
        st.warning("Нет данных для отображения")
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_students = len(df)
            st.metric("Всего студентов", total_students)
        with col2:
            high = len(df[df['risk_level'] == 'high'])
            st.metric("🔴 Высокий риск", high, 
                     delta=f"{high/total_students*100:.1f}%" if total_students > 0 else "0%")
        with col3:
            medium = len(df[df['risk_level'] == 'medium'])
            st.metric("🟡 Средний риск", medium,
                     delta=f"{medium/total_students*100:.1f}%" if total_students > 0 else "0%")
        with col4:
            low = len(df[df['risk_level'] == 'low'])
            st.metric("🟢 Низкий риск", low,
                     delta=f"{low/total_students*100:.1f}%" if total_students > 0 else "0%")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(df, names='risk_level', title='Распределение риска',
                        color='risk_level',
                        color_discrete_map={'low': 'green', 'medium': 'orange', 'high': 'red'})
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.histogram(df, x='risk_score', nbins=20, 
                              title='Распределение оценок риска')
            st.plotly_chart(fig, use_container_width=True)

# ======================================================================
# ВКЛАДКА 2: СТУДЕНТЫ
# ======================================================================
with tab2:
    st.header("Детальная информация по студентам")
    
    if df.empty:
        st.warning("Нет данных для отображения")
    else:
        search = st.text_input("🔍 Поиск по имени", placeholder="Введите имя студента...")
        
        filtered_df = df
        if search:
            filtered_df = df[df['name'].str.contains(search, case=False, na=False)]
        
        st.dataframe(
            filtered_df,
            use_container_width=True,
            column_config={
                'risk_score': st.column_config.NumberColumn(format="%.2f"),
                'avg_score': st.column_config.NumberColumn(format="%.1f")
            }
        )
        
        st.markdown("---")
        
        if not filtered_df.empty:
            selected_student = st.selectbox(
                "Выберите студента для детального просмотра",
                filtered_df['name'].tolist()
            )
            
            if selected_student:
                student_row = filtered_df[filtered_df['name'] == selected_student].iloc[0]
                student = Student.objects.get(student_id=student_row['id'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("**Основная информация**")
                    st.write(f"ID: {student.student_id}")
                    st.write(f"Имя: {student.name}")
                    st.write(f"Курс: {student.course}")
                    st.write(f"Семестр: {student.semester}")
                
                with col2:
                    st.markdown("**Показатели риска**")
                    risk_color = "🟢" if student_row['risk_level'] == 'low' else "🟡" if student_row['risk_level'] == 'medium' else "🔴"
                    st.write(f"Уровень: {risk_color} {student_row['risk_level']}")
                    st.write(f"Риск: {student_row['risk_score']:.2f}")
                    st.write(f"Ср. балл: {student_row['avg_score']:.1f}")
                
                with col3:
                    st.markdown("**Активность**")
                    st.write(f"Активность: {student_row['activity']} соб/нед")
                    st.write(f"Пропуски: {student_row['missed']}")
                    st.write(f"Дней без входа: {student_row['days_since_login']}")
                
                # ===== АНАЛИЗ ТРАЕКТОРИИ =====
                if conformance_calc:
                    st.markdown("---")
                    st.subheader("🔄 Анализ траектории")
                    
                    try:
                        successful, problematic = conformance_calc.calculate_conformance(student)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            delta_success = successful - 0.5
                            st.metric(
                                "Сходство с успешными студентами", 
                                f"{successful:.2f}",
                                delta=f"{delta_success:+.2f}" if abs(delta_success) > 0.1 else None
                            )
                        with col2:
                            delta_problem = problematic - 0.5
                            st.metric(
                                "Сходство с проблемными студентами", 
                                f"{problematic:.2f}",
                                delta=f"{delta_problem:+.2f}" if abs(delta_problem) > 0.1 else None
                            )
                        
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            name='Сходство',
                            x=['Успешные студенты', 'Проблемные студенты'],
                            y=[successful, problematic],
                            marker_color=['green', 'red'],
                            text=[f"{successful:.2f}", f"{problematic:.2f}"],
                            textposition='outside'
                        ))
                        fig.add_hline(y=0.5, line_dash="dash", line_color="gray")
                        fig.update_layout(title="Сравнение с эталонными траекториями",
                                        yaxis_range=[0, 1], height=400)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        if successful > problematic + 0.2:
                            st.success("✅ **Траектория ближе к успешным студентам**")
                        elif problematic > successful + 0.2:
                            st.warning("⚠️ **Траектория ближе к проблемным студентам**")
                        else:
                            st.info("➡️ **Смешанная траектория**")
                            
                    except Exception as e:
                        st.error(f"Ошибка расчета конформности: {e}")

# ======================================================================
# ВКЛАДКА 3: PROCESS MINING
# ======================================================================
with tab3:
    st.header("🔄 Process Mining - Анализ образовательных траекторий")
    
    if df.empty:
        st.warning("Нет данных для отображения")
    else:
        def get_transition_graph_data():
            from collections import Counter
            events = Event.objects.all().order_by('student', 'timestamp')
            transitions = []
            current_student = None
            prev_event = None
            
            for event in events:
                if event.student_id != current_student:
                    current_student = event.student_id
                    prev_event = None
                    continue
                if prev_event:
                    transitions.append((prev_event.event_type, event.event_type))
                prev_event = event
            
            return Counter(transitions)
        
        min_transitions = st.slider("Минимальное число переходов", 1, 20, 5)
        transitions = get_transition_graph_data()
        
        if len(transitions) > 0:
            nodes = set()
            edges = []
            for (source, target), count in transitions.most_common(30):
                if count >= min_transitions:
                    nodes.add(source)
                    nodes.add(target)
                    edges.append((source, target, count))
            
            if len(nodes) > 0:
                pos = {}
                for i, node in enumerate(nodes):
                    angle = 2 * 3.14159 * i / len(nodes)
                    pos[node] = (0.5 + 0.4 * np.cos(angle), 0.5 + 0.4 * np.sin(angle))
                
                edge_traces = []
                for source, target, count in edges:
                    if source in pos and target in pos:
                        x0, y0 = pos[source]
                        x1, y1 = pos[target]
                        edge_trace = go.Scatter(
                            x=[x0, (x0+x1)/2, x1, None],
                            y=[y0, (y0+y1)/2, y1, None],
                            line=dict(width=min(count/5, 10), color='rgba(100,100,100,0.8)'),
                            hoverinfo='text',
                            text=f"{source} → {target}: {count}",
                            mode='lines'
                        )
                        edge_traces.append(edge_trace)
                
                node_x = [pos[node][0] for node in nodes]
                node_y = [pos[node][1] for node in nodes]
                
                node_trace = go.Scatter(
                    x=node_x, y=node_y, mode='markers+text',
                    text=list(nodes), textposition="middle center",
                    marker=dict(size=30, color='lightblue', line=dict(color='darkblue', width=2))
                )
                
                fig = go.Figure(data=edge_traces + [node_trace],
                              layout=go.Layout(title='Карта процесса обучения',
                                             showlegend=False, height=600,
                                             xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                             yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))
                st.plotly_chart(fig, use_container_width=True)

# ======================================================================
# ВКЛАДКА 4: АНАЛИТИКА
# ======================================================================
with tab4:
    st.header("📊 Аналитика и статистика")
    
    if df.empty:
        st.warning("Нет данных для отображения")
    else:
        if len(df) > 0:
            course_stats = df.groupby('course').agg({
                'risk_score': ['mean', 'std'],
                'activity': 'mean',
                'missed': 'sum',
                'avg_score': 'mean',
                'name': 'count'
            }).round(2)
            
            course_stats.columns = ['Ср. риск', 'Стд. риск', 'Ср. активность', 
                                   'Всего пропусков', 'Ср. балл', 'Кол-во']
            st.dataframe(course_stats, use_container_width=True)
        
        corr_features = ['risk_score', 'activity', 'missed', 'avg_score', 'days_since_login']
        available = [f for f in corr_features if f in df.columns]
        
        if len(available) > 1:
            corr_df = df[available].corr()
            fig = px.imshow(corr_df, text_auto=True, aspect="auto",
                          title="Корреляция признаков", color_continuous_scale='RdBu_r')
            st.plotly_chart(fig, use_container_width=True)

# ======================================================================
# ВКЛАДКА 5: ML ПРОГНОЗЫ
# ======================================================================
with tab5:
    st.header("🤖 ML-прогнозы с пояснениями")
    
    if not model_loaded:
        st.error("⚠️ ML модель не загружена! Обучите модель командой: python train_ml_model.py")
    else:
        st.success("✅ Модель машинного обучения загружена и готова к работе")
        
        if len(df) > 0:
            selected_student = st.selectbox(
                "👤 Выберите студента для анализа",
                df['name'].tolist(),
                key="ml_student"
            )
            
            show_details = st.checkbox("🔍 Показать детали", value=True)
            
            if selected_student:
                try:
                    student_row = df[df['name'] == selected_student].iloc[0]
                    student = Student.objects.get(student_id=student_row['id'])
                    
                    feature_vector = []
                    for col in feature_columns:
                        if col in student_row.index:
                            try:
                                val = float(student_row[col])
                                if np.isnan(val) or np.isinf(val):
                                    val = 0.0
                                feature_vector.append(val)
                            except:
                                feature_vector.append(0.0)
                        else:
                            feature_vector.append(0.0)
                    
                    feature_scaled = scaler.transform([feature_vector])
                    probabilities = model.predict_proba(feature_scaled)[0]
                    pred_class = model.predict(feature_scaled)[0]
                    pred_label = le.inverse_transform([pred_class])[0]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        risk_color = {'low': '🟢', 'medium': '🟡', 'high': '🔴'}.get(
                            student_row['risk_level'], '⚪')
                        st.metric("Текущий уровень риска",
                                 f"{risk_color} {student_row['risk_level'].upper()}",
                                 f"Оценка: {student_row['risk_score']:.2f}")
                    
                    with col2:
                        pred_color = {'low': '🟢', 'medium': '🟡', 'high': '🔴'}.get(pred_label, '⚪')
                        st.metric("ML прогноз",
                                 f"{pred_color} {pred_label.upper()}",
                                 f"Уверенность: {probabilities[pred_class]*100:.1f}%")
                    
                    with col3:
                        if pred_label == student_row['risk_level']:
                            st.success("✅ Прогноз совпадает")
                        else:
                            st.warning("⚠️ Прогноз отличается")
                    
                    prob_df = pd.DataFrame({
                        'Риск': ['Низкий', 'Средний', 'Высокий'],
                        'Вероятность': probabilities * 100
                    })
                    
                    fig = px.bar(prob_df, x='Риск', y='Вероятность',
                               color='Риск', text_auto='.1f',
                               color_discrete_map={'Низкий': 'green', 'Средний': 'orange', 'Высокий': 'red'})
                    fig.update_traces(textposition='outside')
                    fig.update_layout(yaxis_range=[0, 100])
                    st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"Ошибка: {e}")

# ======================================================================
# НИЖНИЙ КОЛОНТИТУЛ
# ======================================================================
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"📊 **Всего студентов:** {Student.objects.count()}")
with col2:
    st.markdown(f"📅 **Последнее обновление:** {datetime.now().strftime('%d.%m.%Y %H:%M')}")
with col3:
    st.markdown(f"📈 **Событий в БД:** {Event.objects.count()}")

st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.8em;'>
        <p>📚 Система мониторинга успеваемости v3.0</p>
        <p>Разработано с использованием Django, Streamlit, PostgreSQL, Scikit-learn</p>
    </div>
    """,
    unsafe_allow_html=True
)