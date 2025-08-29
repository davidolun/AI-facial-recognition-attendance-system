from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("take_attendance/", views.take_attendance, name="take_attendance"),
    path('records/', views.view_records, name='records'),
    path("add_student/", views.add_student, name="add_student"),
    path('detect_faces/', views.detect_faces, name='detect_faces'), 
    path('ai_assistant/', views.ai_assistant, name='ai_assistant'),
    path('take_attendance_with_session/', views.take_attendance_with_session, name='take_attendance_with_session'),  # New one
    path('get_sessions/', views.get_sessions, name='get_sessions'),  # New endpoint to get sessions
    path('create_session/', views.create_session, name='create_session'), 
            ]