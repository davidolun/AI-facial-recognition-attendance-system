from django.urls import path
from . import views


urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Teacher Class Management URLs
     path('class_management/', views.class_management, name='class_management'),
    path('create_class/', views.create_class, name='create_class'),
      path('get_teacher_students/', views.get_teacher_students, name='get_teacher_students'), 
    path('get_teacher_classes/', views.get_teacher_classes, name='get_teacher_classes'),
    path('assign_student_to_class/', views.assign_student_to_class, name='assign_student_to_class'),
    path('get_all_students/', views.get_all_students, name='get_all_students'),
    path('remove_student_from_class/', views.remove_student_from_class, name='remove_student_from_class'),
    path('advanced_analytics/', views.advanced_analytics, name='advanced_analytics'),
    path('advanced_analytics_data/', views.advanced_analytics_data, name='advanced_analytics_data'),

    
    
    path('', views.home, name='home'),
    path("take_attendance/", views.take_attendance_with_session, name="take_attendance"),
    path('records/', views.view_records, name='records'),
    path("add_student/", views.add_student, name="add_student"),
    
    path('detect_faces/', views.detect_faces, name='detect_faces'), 
    path('ai_assistant/', views.ai_assistant, name='ai_assistant'),
    path('take_attendance_with_session/', views.take_attendance_with_session, name='take_attendance_with_session'),  # New one
    
    path('get_sessions/', views.get_sessions, name='get_sessions'),  # New endpoint to get sessions
    path('create_session/', views.create_session, name='create_session'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard_data/', views.dashboard_data, name='dashboard_data'),
    path('export_data/', views.export_data, name='export_data'),
    path('mark_onboarding_complete/', views.mark_onboarding_complete, name='mark_onboarding_complete'),
    path('test_onboarding/', views.test_onboarding, name='test_onboarding'),
]
