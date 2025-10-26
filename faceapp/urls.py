from django.urls import path
# Import views from the new modular structure
from .views import (
    # Authentication views
    signup_view,
    login_view,
    logout_view,
    # Student views
    home,
    add_student,
    get_all_students,
    get_teacher_students,
    # Attendance views
    take_attendance_with_session,
    detect_faces,
    create_session,
    get_sessions,
    # Class views
    class_management,
    create_class,
    get_teacher_classes,
    assign_student_to_class,
    remove_student_from_class,
    # Dashboard views
    dashboard,
    view_records,
    advanced_analytics,
    advanced_analytics_data,
    dashboard_data,
    mark_onboarding_complete,
    export_data,
    generate_export_file,
    test_onboarding,
    # AI views
    ai_assistant,
)


urlpatterns = [
    # Authentication URLs
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Home & Student Management
    path('', home, name='home'),
    path('add_student/', add_student, name='add_student'),
    path('get_all_students/', get_all_students, name='get_all_students'),
    path('get_teacher_students/', get_teacher_students, name='get_teacher_students'),
    
    # Attendance URLs
    path('take_attendance/', take_attendance_with_session, name='take_attendance'),
    path('take_attendance_with_session/', take_attendance_with_session, name='take_attendance_with_session'),
    path('detect_faces/', detect_faces, name='detect_faces'),
    path('get_sessions/', get_sessions, name='get_sessions'),
    path('create_session/', create_session, name='create_session'),
    
    # Class Management URLs
    path('class_management/', class_management, name='class_management'),
    path('create_class/', create_class, name='create_class'),
    path('get_teacher_classes/', get_teacher_classes, name='get_teacher_classes'),
    path('assign_student_to_class/', assign_student_to_class, name='assign_student_to_class'),
    path('remove_student_from_class/', remove_student_from_class, name='remove_student_from_class'),
    
    # Dashboard & Analytics URLs
    path('dashboard/', dashboard, name='dashboard'),
    path('dashboard_data/', dashboard_data, name='dashboard_data'),
    path('records/', view_records, name='records'),
    path('advanced_analytics/', advanced_analytics, name='advanced_analytics'),
    path('advanced_analytics_data/', advanced_analytics_data, name='advanced_analytics_data'),
    path('export_data/', export_data, name='export_data'),
    path('mark_onboarding_complete/', mark_onboarding_complete, name='mark_onboarding_complete'),
    path('test_onboarding/', test_onboarding, name='test_onboarding'),
    
    # AI Assistant URLs
    path('ai_assistant/', ai_assistant, name='ai_assistant'),
]
