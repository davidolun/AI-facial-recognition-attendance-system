"""
Dashboard views for analytics, reporting, and data visualization
"""
from .common_imports import *
import csv
from io import StringIO


def get_complete_attendance_data(teacher=None):
    """Get COMPLETE attendance data for dashboard and analytics"""
    
    if teacher:
        all_students = list(Student.objects.filter(is_active=True, classes__teacher=teacher).distinct().values('id', 'name', 'student_id', 'email'))
        all_sessions = list(AttendanceSession.objects.filter(teacher=teacher).order_by('-date', '-start_time').values(
            'id', 'name', 'date', 'start_time', 'end_time', 'class_session__name'
        ))
    else:
        all_students = list(Student.objects.filter(is_active=True).values('id', 'name', 'student_id', 'email'))
        all_sessions = list(AttendanceSession.objects.all().order_by('-date', '-start_time').values(
            'id', 'name', 'date', 'start_time', 'end_time', 'class_session__name'
        ))
    
    for session in all_sessions:
        session['date'] = session['date'].strftime('%Y-%m-%d')
        session['start_time'] = session['start_time'].strftime('%H:%M:%S')
        if session['end_time']:
            session['end_time'] = session['end_time'].strftime('%H:%M:%S')
    
    if teacher:
        all_records = list(AttendanceRecord.objects.filter(session__teacher=teacher).select_related('student', 'session').values(
            'student__name', 'student_id', 'session__name', 'session_id', 
            'date', 'time', 'arrival_time', 'is_late', 'timestamp'
        ))
    else:
        all_records = list(AttendanceRecord.objects.select_related('student', 'session').values(
            'student__name', 'student_id', 'session__name', 'session_id', 
            'date', 'time', 'arrival_time', 'is_late', 'timestamp'
        ))
    
    for record in all_records:
        record['date'] = record['date'].strftime('%Y-%m-%d')
        record['time'] = record['time'].strftime('%H:%M:%S')
        record['timestamp'] = record['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        if record['arrival_time']:
            record['arrival_time'] = record['arrival_time'].strftime('%H:%M:%S')
    
    student_stats = {}
    for student in all_students:
        student_records = [r for r in all_records if r['student_id'] == student['id']]
        sessions_attended = len(set(r['session_id'] for r in student_records))
        times_late = len([r for r in student_records if r['is_late']])
        times_on_time = len([r for r in student_records if not r['is_late']])
        
        student_session_ids = set(r['session_id'] for r in student_records)
        
        if teacher:
            current_available_sessions = AttendanceSession.objects.filter(
                teacher=teacher,
                class_session__students__id=student['id']
            ).values_list('id', flat=True)
        else:
            current_available_sessions = AttendanceSession.objects.filter(
                class_session__students__id=student['id']
            ).values_list('id', flat=True)
        
        available_session_count = max(len(student_session_ids), len(list(current_available_sessions)))
        
        if available_session_count > 0:
            attendance_percentage = min(round((sessions_attended / available_session_count) * 100, 1), 100.0)
        else:
            attendance_percentage = 0
        
        student_stats[student['name']] = {
            'total_sessions_attended': sessions_attended,
            'available_sessions': available_session_count,
            'times_late': times_late,
            'times_on_time': times_on_time,
            'attendance_percentage': attendance_percentage
        }
    
    session_details = {}
    for session in all_sessions:
        session_key = f"{session['name']}_{session['date']}"
        session_records = [r for r in all_records if r['session_id'] == session['id']]
        present_students = [r['student__name'] for r in session_records]
        
        if teacher:
            eligible_students = list(Student.objects.filter(
                classes__sessions__id=session['id'], 
                is_active=True
            ).values_list('name', flat=True))
        else:
            eligible_students = [s['name'] for s in all_students]
        
        if not eligible_students:
            eligible_students = present_students
        
        absent_students = [name for name in eligible_students if name not in present_students]
        
        session_details[session_key] = {
            'session_info': session,
            'present_students': present_students,
            'absent_students': absent_students,
            'present_count': len(present_students),
            'absent_count': len(absent_students),
            'eligible_count': len(eligible_students),
            'late_students': [r['student__name'] for r in session_records if r['is_late']],
            'on_time_students': [r['student__name'] for r in session_records if not r['is_late']]
        }
    
    sessions_list = list(set(session['name'] for session in all_sessions))
    unique_dates = sorted(list(set(session['date'] for session in all_sessions)))
    
    return {
        'total_students': len(all_students),
        'total_sessions': len(all_sessions),
        'today_date': date.today().strftime('%Y-%m-%d'),
        'all_students': all_students,
        'all_sessions': all_sessions,
        'all_attendance_records': all_records,
        'student_statistics': student_stats,
        'session_details': session_details,
        'sessions_list': sessions_list,
        'unique_dates': unique_dates
    }


@login_required
def dashboard(request):
    """Render the main dashboard page"""
    needs_onboarding = not request.user.onboarding_completed
    return render(request, 'dashboard.html', {'needs_onboarding': needs_onboarding})


@login_required
@require_http_methods(["GET"])
def dashboard_data(request):
    """API endpoint for dashboard data"""
    try:
        teacher = None if request.user.is_admin else request.user
        data = get_complete_attendance_data(teacher)
        
        data['analytics'] = {
            'total_records': len(data['all_attendance_records']),
            'late_percentage': 0
        }
        
        if data['all_attendance_records']:
            late_records = [r for r in data['all_attendance_records'] if r['is_late']]
            data['analytics']['late_percentage'] = round((len(late_records) / len(data['all_attendance_records'])) * 100, 2)
        
        data['teacher_info'] = {
            'name': request.user.get_full_name(),
            'username': request.user.username,
            'department': request.user.department,
            'is_admin': request.user.is_admin
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@csrf_exempt
def mark_onboarding_complete(request):
    """Mark onboarding as completed"""
    if request.method == 'POST':
        try:
            request.user.onboarding_completed = True
            request.user.save()
            return JsonResponse({'success': True, 'message': 'Onboarding marked as complete'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def view_records(request):
    """Render the attendance records view"""
    return render(request, 'ai_assistant.html')


@login_required
def advanced_analytics(request):
    """Render the advanced analytics page"""
    return render(request, 'advanced_analytics.html')


@login_required
def advanced_analytics_data(request):
    """API endpoint for advanced analytics"""
    try:
        teacher = None if request.user.is_admin else request.user
        base_data = get_complete_attendance_data(teacher)
        
        enhanced_data = {
            **base_data,
            'analytics_ready': True
        }
        
        return JsonResponse(enhanced_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@csrf_exempt
def export_data(request):
    """Export attendance data in various formats"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            export_type = data.get("type", "csv")
            date_from = data.get("date_from")
            date_to = data.get("date_to")
            report_title = data.get("title", "Attendance Report")

            teacher = None if request.user.is_admin else request.user
            return generate_export_file(export_type, date_from, date_to, report_title, teacher)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def generate_export_file(export_type, date_from=None, date_to=None, report_title="Attendance Report", teacher=None):
    """Helper function to generate export files"""
    attendance_data = get_complete_attendance_data(teacher)

    if date_from and date_to:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        attendance_data['all_attendance_records'] = [
            record for record in attendance_data['all_attendance_records']
            if date_from_obj <= datetime.strptime(record['date'], '%Y-%m-%d').date() <= date_to_obj
        ]

    if export_type == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Student Name', 'Session', 'Date', 'Time', 'Status', 'Late'])
        for record in attendance_data['all_attendance_records']:
            writer.writerow([
                record['student__name'],
                record['session__name'] if record['session__name'] else 'N/A',
                record['date'],
                record['time'],
                'Present',
                'Yes' if record['is_late'] else 'No'
            ])
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_title}.csv"'
        return response

    return JsonResponse({'error': 'Export type not supported'}, status=400)


@login_required
def test_onboarding(request):
    """Test page for onboarding system"""
    return render(request, 'test_onboarding.html')
