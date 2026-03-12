"""
Обучение модели машинного обучения для прогнозирования рисков студентов
Запуск: python train_ml_model.py
"""

import os
import sys
import django
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib
import warnings
warnings.filterwarnings('ignore')

# Настройка Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Student, Event, StudentFeatures

# Импорт ML библиотек
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler, LabelEncoder
import matplotlib.pyplot as plt
import seaborn as sns

print("\n" + "="*70)
print("🤖 ОБУЧЕНИЕ МОДЕЛИ МАШИННОГО ОБУЧЕНИЯ")
print("="*70)

# ======================================================================
# 1. СБОР ДАННЫХ И FEATURE ENGINEERING
# ======================================================================
print("\n📊 1. Сбор данных и создание признаков...")

students = Student.objects.all()
print(f"   Найдено студентов: {students.count()}")

data = []

for student in students:
    print(f"   Обработка студента: {student.name}")
    
    # Получаем все события студента
    events = Event.objects.filter(student=student).order_by('timestamp')
    
    if events.count() < 3:  # Пропускаем студентов с малым количеством событий
        print(f"      ⚠️ Слишком мало событий ({events.count()}), пропускаем")
        continue
    
    # Получаем признаки из StudentFeatures (если есть)
    try:
        features = StudentFeatures.objects.get(student=student)
    except StudentFeatures.DoesNotExist:
        print(f"      ⚠️ Нет признаков для студента, пропускаем")
        continue
    
    # ===== БАЗОВЫЕ ПРИЗНАКИ =====
    row = {
        'student_id': student.student_id,
        'name': student.name,
        'course': student.course,
        'semester': student.semester,
    }
    
    # Признаки из модели
    row['avg_delay'] = float(features.avg_assignment_delay)
    row['days_since_login'] = int(features.days_since_last_login)
    row['activity_week'] = int(features.activity_count_last_week)
    row['missed_deadlines'] = int(features.missed_deadlines_count)
    row['avg_score'] = float(features.success_rate_midterms)
    row['risk_score_current'] = float(features.risk_score)
    row['risk_level_current'] = features.risk_level
    
    # ===== ДОПОЛНИТЕЛЬНЫЕ ПРИЗНАКИ =====
    
    # 1. Временные паттерны
    now = datetime.now()
    month_ago = now - timedelta(days=30)
    
    # Активность за последний месяц
    activity_month = events.filter(timestamp__gte=month_ago).count()
    row['activity_month'] = activity_month
    
    # Соотношение активностей
    total_events = events.count()
    row['total_events'] = total_events
    
    # 2. Разнообразие типов событий
    event_types = set(events.values_list('event_type', flat=True))
    row['event_diversity'] = len(event_types)
    
    # 3. Пропуски относительно активности
    if total_events > 0:
        row['missed_ratio'] = features.missed_deadlines_count / total_events
    else:
        row['missed_ratio'] = 0
    
    # 4. Регулярность (стандартное отклонение интервалов между событиями)
    if events.count() > 1:
        timestamps = [e.timestamp for e in events]
        intervals = [(timestamps[i] - timestamps[i-1]).total_seconds() / 3600 
                    for i in range(1, len(timestamps))]
        row['regularity'] = float(np.std(intervals)) if intervals else 0
    else:
        row['regularity'] = 0
    
    # 5. Время суток активности (0-23)
    hours = [e.timestamp.hour for e in events]
    row['avg_activity_hour'] = float(np.mean(hours)) if hours else 12
    
    # 6. Выходные vs будни
    weekend_events = sum(1 for e in events if e.timestamp.weekday() >= 5)
    row['weekend_ratio'] = weekend_events / total_events if total_events > 0 else 0
    
    # 7. Тренд активности (растет/падает) - ИСПРАВЛЕНО!
    if events.count() >= 10:
        events_list = list(events)
        half = len(events_list) // 2
        first_half_count = len(events_list[:half])
        second_half_count = len(events_list[half:])
        row['activity_trend'] = second_half_count - first_half_count
    else:
        row['activity_trend'] = 0
    
    # 8. Средняя оценка за последние 5 работ
    recent_grades = []
    for e in events.order_by('-timestamp')[:10]:
        if e.details:
            if 'grade' in e.details:
                try:
                    recent_grades.append(float(e.details['grade']))
                except:
                    pass
            if 'score' in e.details:
                try:
                    recent_grades.append(float(e.details['score']))
                except:
                    pass
    row['recent_avg'] = float(np.mean(recent_grades)) if recent_grades else row['avg_score']
    
    # 9. Скорость реакции
    row['reaction_time'] = 24.0  # значение по умолчанию
    
    data.append(row)
    print(f"      ✅ Добавлено {len(row)-4} признаков")

# Создаем DataFrame
df = pd.DataFrame(data)
print(f"\n✅ Собрано {len(df)} записей с {len(df.columns)} признаками")

if len(df) == 0:
    print("❌ Нет данных для обучения! Сначала запустите generate_data.py")
    sys.exit(1)

# ======================================================================
# 2. ПОДГОТОВКА ДАННЫХ ДЛЯ ОБУЧЕНИЯ
# ======================================================================
print("\n🔧 2. Подготовка данных...")

# Проверяем распределение классов
print("\n   Распределение классов:")
print(df['risk_level_current'].value_counts())

# Кодируем целевую переменную
le = LabelEncoder()
df['target'] = le.fit_transform(df['risk_level_current'])
print(f"\n   Классы: {dict(zip(le.classes_, le.transform(le.classes_)))}")

# Выбираем признаки для обучения
feature_columns = [
    'avg_delay', 'days_since_login', 'activity_week', 'missed_deadlines',
    'avg_score', 'risk_score_current', 'activity_month', 'event_diversity',
    'missed_ratio', 'regularity', 'avg_activity_hour', 'weekend_ratio',
    'activity_trend', 'recent_avg', 'reaction_time'
]

# Проверяем, что все признаки есть в DataFrame
available_features = [col for col in feature_columns if col in df.columns]
print(f"\n   Доступные признаки: {len(available_features)} из {len(feature_columns)}")

X = df[available_features]
y = df['target']

print(f"   Размер выборки: {X.shape}")

# Заполняем пропущенные значения средними
X = X.fillna(X.mean())

# Масштабируем признаки
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Разделяем на train/test
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.25, random_state=42, stratify=y
)

print(f"   Обучающая выборка: {X_train.shape}")
print(f"   Тестовая выборка: {X_test.shape}")

# ======================================================================
# 3. ОБУЧЕНИЕ МОДЕЛЕЙ
# ======================================================================
print("\n🤖 3. Обучение моделей...")

models = {
    'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
    'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42)
}

results = {}

for name, model in models.items():
    print(f"\n   📈 Обучение {name}...")
    
    # Обучение
    model.fit(X_train, y_train)
    
    # Оценка
    accuracy = model.score(X_test, y_test)
    
    # Cross-validation
    try:
        cv_scores = cross_val_score(model, X_scaled, y, cv=min(5, len(df)))
        cv_mean = cv_scores.mean()
        cv_std = cv_scores.std()
    except:
        cv_mean = accuracy
        cv_std = 0
    
    results[name] = {
        'model': model,
        'accuracy': accuracy,
        'cv_mean': cv_mean,
        'cv_std': cv_std
    }
    
    print(f"      Accuracy: {accuracy:.3f}")
    print(f"      CV Score: {cv_mean:.3f} (+/- {cv_std*2:.3f})")

# Выбираем лучшую модель
best_model_name = max(results, key=lambda x: results[x]['cv_mean'])
best_model = results[best_model_name]['model']

print(f"\n🏆 Лучшая модель: {best_model_name}")

# ======================================================================
# 4. ДЕТАЛЬНЫЙ АНАЛИЗ ЛУЧШЕЙ МОДЕЛИ
# ======================================================================
print("\n📊 4. Детальный анализ лучшей модели...")

# Предсказания
y_pred = best_model.predict(X_test)

# Classification report
print("\n   Classification Report:")
print("   " + "-"*50)
print(classification_report(y_test, y_pred, target_names=le.classes_))

# Матрица ошибок
cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=le.classes_,
            yticklabels=le.classes_)
plt.title(f'Матрица ошибок - {best_model_name}')
plt.ylabel('Реальное значение')
plt.xlabel('Предсказанное значение')
plt.tight_layout()
plt.savefig('confusion_matrix.png')
print("   ✅ Матрица ошибок сохранена в confusion_matrix.png")

# ======================================================================
# 5. ВАЖНОСТЬ ПРИЗНАКОВ
# ======================================================================
print("\n🌟 5. Анализ важности признаков...")

if hasattr(best_model, 'feature_importances_'):
    importances = best_model.feature_importances_
    feature_importance = pd.DataFrame({
        'feature': available_features,
        'importance': importances
    }).sort_values('importance', ascending=False)
    
    print("\n   Топ-10 самых важных признаков:")
    print("   " + "-"*50)
    for idx, row in feature_importance.head(10).iterrows():
        print(f"   {row['feature']}: {row['importance']:.3f}")
    
    # Визуализация
    plt.figure(figsize=(10, 6))
    sns.barplot(data=feature_importance.head(10), x='importance', y='feature')
    plt.title(f'Топ-10 важных признаков - {best_model_name}')
    plt.tight_layout()
    plt.savefig('feature_importance.png')
    print("   ✅ График важности признаков сохранен в feature_importance.png")
    
    # Сохраняем в CSV
    feature_importance.to_csv('feature_importance.csv', index=False)
    print("   ✅ Таблица важности сохранена в feature_importance.csv")

# ======================================================================
# 6. СОХРАНЕНИЕ МОДЕЛИ
# ======================================================================
print("\n💾 6. Сохранение модели...")

# Сохраняем модель
joblib.dump(best_model, 'risk_model.pkl')
print("   ✅ Модель сохранена: risk_model.pkl")

# Сохраняем скейлер
joblib.dump(scaler, 'scaler.pkl')
print("   ✅ Скейлер сохранен: scaler.pkl")

# Сохраняем LabelEncoder
joblib.dump(le, 'label_encoder.pkl')
print("   ✅ LabelEncoder сохранен: label_encoder.pkl")

# Сохраняем список признаков
joblib.dump(available_features, 'feature_columns.pkl')
print("   ✅ Список признаков сохранен: feature_columns.pkl")

# ======================================================================
# 7. ИТОГОВЫЙ ОТЧЕТ
# ======================================================================
print("\n" + "="*70)
print("✅ ОБУЧЕНИЕ ЗАВЕРШЕНО УСПЕШНО!")
print("="*70)
print(f"\n📊 Итоговые метрики лучшей модели ({best_model_name}):")
print(f"   - Accuracy: {results[best_model_name]['accuracy']:.3f}")
print(f"   - CV Score: {results[best_model_name]['cv_mean']:.3f}")

print(f"\n📁 Сохраненные файлы:")
print("   - risk_model.pkl (обученная модель)")
print("   - scaler.pkl (стандартизатор признаков)")
print("   - label_encoder.pkl (кодировщик меток)")
print("   - feature_columns.pkl (список признаков)")

if os.path.exists('feature_importance.png'):
    print("   - feature_importance.png (график важности)")
if os.path.exists('confusion_matrix.png'):
    print("   - confusion_matrix.png (матрица ошибок)")
if os.path.exists('feature_importance.csv'):
    print("   - feature_importance.csv (таблица важности)")

print("\n💡 Теперь модель можно использовать в дашборде!")
print("="*70 + "\n")