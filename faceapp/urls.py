from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("take_attendance/", views.take_attendance, name="take_attendance"),
    path('records/', views.view_records, name='records'),
    path("add_student/", views.add_student, name="add_student"),    ]