from django.contrib import admin
from .models import Student, Event, StudentFeatures

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'name', 'course', 'semester')
    search_fields = ('name', 'student_id')
    list_filter = ('course', 'semester')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('student', 'timestamp', 'event_type')
    list_filter = ('event_type',)
    search_fields = ('student__name', 'student__student_id')
    date_hierarchy = 'timestamp'

@admin.register(StudentFeatures)
class StudentFeaturesAdmin(admin.ModelAdmin):
    list_display = ('student', 'calculated_at', 'risk_level', 'risk_score')
    list_filter = ('risk_level',)
    search_fields = ('student__name', 'student__student_id')