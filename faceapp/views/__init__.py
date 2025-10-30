"""
Views package - exports all view functions for the attendance system
"""
from .auth_views import (
    signup_view,
    login_view,
    logout_view,
)

from .student_views import (
    home,
    add_student,
    get_all_students,
    get_teacher_students,
    delete_student,
)

from .attendance_views import (
    take_attendance_with_session,
    detect_faces,
    create_session,
    get_sessions,
)

from .class_views import (
    class_management,
    create_class,
    get_teacher_classes,
    assign_student_to_class,
    remove_student_from_class,
)

# Note: dashboard_views and ai_views imported here to avoid circular imports
# Import dashboard views first (no deps)
from . import dashboard_views

# Import ai_views after dashboard_views is loaded (has deps on dashboard_views)
from . import ai_views

# Re-export dashboard and ai views
from .dashboard_views import *
from .ai_views import *

__all__ = [
    # Auth
    'signup_view',
    'login_view',
    'logout_view',
    # Student
    'home',
    'add_student',
    'get_all_students',
    'get_teacher_students',
    'delete_student',
    # Attendance
    'take_attendance_with_session',
    'detect_faces',
    'create_session',
    'get_sessions',
    # Class
    'class_management',
    'create_class',
    'get_teacher_classes',
    'assign_student_to_class',
    'remove_student_from_class',
]
