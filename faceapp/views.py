import base64
import re
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import os
import face_recognition
import datetime
import json
import numpy as np
import cv2
from openai import OpenAI
from django.db.models import Count, Q
from datetime import datetime, date, timedelta
from django.conf import settings
import json
from .models import Student, AttendanceRecord, AttendanceSession, AIQuery
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from .models import Teacher, Class
from django.db import transaction


# Initialize OpenAI client with new API
client = OpenAI(api_key=settings.OPENAI_API_KEY)

@login_required
def home(request):
    return render(request, 'home.html')


@csrf_exempt
def take_attendance(request):
    if request.method == "POST":
        try:
            import json, base64, re, datetime, os, face_recognition, cv2, numpy as np

            data = json.loads(request.body)
            image_data = data.get("image")
            if not image_data:
                return JsonResponse({"error": "No image received"}, status=400)

            # decode image
            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_bytes = base64.b64decode(img_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # detect faces
            face_locations = face_recognition.face_locations(rgb_frame)

            if not face_locations:
                return JsonResponse({"message": "No face detected", "faces": []})

            # Prepare face rectangles for JS: [top, right, bottom, left]
            faces_for_js = [{"top": f[0], "right": f[1], "bottom": f[2], "left": f[3]} for f in face_locations]

            # Face recognition part (optional)
            students_dir = os.path.join(settings.BASE_DIR, "students")
            student_encodings = []
            student_names = []

            for file in os.listdir(students_dir):
                if file.endswith(".jpg") or file.endswith(".png"):
                    img = face_recognition.load_image_file(os.path.join(students_dir, file))
                    enc = face_recognition.face_encodings(img)
                    if enc:
                        student_encodings.append(enc[0])
                        student_names.append(file.rsplit(".", 1)[0])

            recognized = []
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(student_encodings, face_encoding)
                if True in matches:
                    match_index = matches.index(True)
                    name = student_names[match_index]
                    recognized.append(name)

                    # log attendance
                    now = datetime.datetime.now()
                    time_str = now.strftime("%H:%M:%S")
                    date_str = now.strftime("%Y-%m-%d")
                    log_path = os.path.join(settings.BASE_DIR, "attendance.csv")
                    with open(log_path, "a") as f:
                        f.write(f"{name},{time_str},{date_str}\n")

            return JsonResponse({"message": f"Attendance taken: {', '.join(recognized) if recognized else 'No match'}",
                                 "faces": faces_for_js})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"message": "Use POST request."})

@login_required
@csrf_exempt
def add_student(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            student_name = data.get("name")
            student_id = data.get("student_id", "")
            email = data.get("email", "")
            phone = data.get("phone", "")
            class_ids = data.get("class_ids", [])  # NEW: Allow multiple class assignment

            if not student_name:
                return JsonResponse({"error": "No name provided"}, status=400)
            if not image_data:
                return JsonResponse({"error": "No image provided"}, status=400)

            if Student.objects.filter(name=student_name).exists():
                return JsonResponse({"error": f"Student '{student_name}' already exists"}, status=400)

            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_bytes = base64.b64decode(img_str)

            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_frame)
            if not face_locations:
                return JsonResponse({"error": "No face detected. Please ensure your face is clearly visible."}, status=400)

            students_dir = os.path.join(settings.BASE_DIR, "students")
            os.makedirs(students_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{student_name}_{timestamp}.jpg"
            save_path = os.path.join(students_dir, filename)
            
            with open(save_path, "wb") as f:
                f.write(img_bytes)

            # Create student
            student = Student.objects.create(
                name=student_name,
                student_id=student_id if student_id else None,
                email=email if email else None,
                phone=phone if phone else None,
                image_path=save_path
            )
            
            # Assign to classes if provided
            if class_ids:
                # Verify all classes belong to the logged-in teacher
                teacher_classes = Class.objects.filter(id__in=class_ids, teacher=request.user)
                if teacher_classes.count() != len(class_ids):
                    return JsonResponse({"error": "Some classes not found or you do not have permission"}, status=400)
                
                student.classes.set(teacher_classes)

            return JsonResponse({
                "message": f"Student {student_name} added successfully!",
                "student_id": student.id
            })

        except Exception as e:
            print("ERROR in add_student:", e)
            return JsonResponse({"error": str(e)}, status=400)

    return render(request, "add_student.html")

@login_required
def class_management(request):
    """Render the class management page"""
    return render(request, 'class_management.html')

@csrf_exempt
def take_attendance_enhanced(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            session_name = data.get("session", f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            if not image_data:
                return JsonResponse({"error": "No image received"}, status=400)

            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_bytes = base64.b64decode(img_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_frame)
            if not face_locations:
                return JsonResponse({"message": "No face detected", "faces": []})

            faces_for_js = [{"top": f[0], "right": f[1], "bottom": f[2], "left": f[3]} for f in face_locations]

            today = date.today()
            current_time = datetime.now()
            session, created = AttendanceSession.objects.get_or_create(
                name=session_name,
                date=today,
                defaults={'start_time': current_time.time()}
            )

            students = Student.objects.filter(is_active=True)
            student_encodings = []
            student_objects = []

            for student in students:
                if os.path.exists(student.image_path):
                    try:
                        img = face_recognition.load_image_file(student.image_path)
                        enc = face_recognition.face_encodings(img)
                        if enc:
                            student_encodings.append(enc[0])
                            student_objects.append(student)
                    except Exception as e:
                        print(f"Error processing image for {student.name}: {e}")
                        continue

            recognized_students = []
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(student_encodings, face_encoding)
                if True in matches:
                    match_index = matches.index(True)
                    student = student_objects[match_index]
                    
                    existing_record = AttendanceRecord.objects.filter(
                        student=student,
                        session=session
                    ).first()
                    
                    if not existing_record:
                        arrival_time = current_time.time()
                        is_late = arrival_time > session.start_time
                        
                        AttendanceRecord.objects.create(
                            student=student,
                            session=session,
                            arrival_time=arrival_time,
                            is_late=is_late
                        )
                        
                        time_str = arrival_time.strftime("%H:%M:%S")
                        status = f" (Late - {time_str})" if is_late else f" (On time - {time_str})"
                        recognized_students.append(f"{student.name}{status}")
                    else:
                        original_time = existing_record.arrival_time.strftime("%H:%M:%S") if hasattr(existing_record, 'arrival_time') and existing_record.arrival_time else existing_record.time.strftime("%H:%M:%S")
                        recognized_students.append(f"{student.name} (Already marked at {original_time})")

            message = f"Attendance taken: {', '.join(recognized_students) if recognized_students else 'No match'}"
            return JsonResponse({"message": message, "faces": faces_for_js})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
            
    return JsonResponse({"message": "Use POST request."})

@csrf_exempt
def detect_faces(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            if not image_data:
                return JsonResponse({"faces": []})

            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_bytes = base64.b64decode(img_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_frame = frame[:, :, ::-1]

            face_locations = face_recognition.face_locations(rgb_frame)
            faces_list = []
            for top, right, bottom, left in face_locations:
                faces_list.append({"top": top, "right": right, "bottom": bottom, "left": left})

            return JsonResponse({"faces": faces_list})
        except Exception as e:
            return JsonResponse({"error": str(e), "faces": []})
    return JsonResponse({"faces": []})

@login_required
def view_records(request):
    return render(request, 'ai_assistant.html')

def get_complete_attendance_data(teacher=None):
    """Get COMPLETE attendance data for AI with proper absence tracking"""
    
    # Filter by teacher if provided (for teacher-specific data)
    if teacher:
        all_students = list(Student.objects.filter(is_active=True, classes__teacher=teacher).distinct().values('id', 'name', 'student_id', 'email'))
        all_sessions = list(AttendanceSession.objects.filter(teacher=teacher).order_by('-date', '-start_time').values(
            'id', 'name', 'date', 'start_time', 'end_time', 'class_session__name'
        ))
    else:
        # For admins - get all data
        all_students = list(Student.objects.filter(is_active=True).values('id', 'name', 'student_id', 'email'))
        all_sessions = list(AttendanceSession.objects.all().order_by('-date', '-start_time').values(
            'id', 'name', 'date', 'start_time', 'end_time', 'class_session__name'
        ))
    
    # Convert dates and times to strings for JSON serialization
    for session in all_sessions:
        session['date'] = session['date'].strftime('%Y-%m-%d')
        session['start_time'] = session['start_time'].strftime('%H:%M:%S')
        if session['end_time']:
            session['end_time'] = session['end_time'].strftime('%H:%M:%S')
    
    # Get ALL attendance records with related data
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
    
    # Convert dates and times to strings
    for record in all_records:
        record['date'] = record['date'].strftime('%Y-%m-%d')
        record['time'] = record['time'].strftime('%H:%M:%S')
        record['timestamp'] = record['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        if record['arrival_time']:
            record['arrival_time'] = record['arrival_time'].strftime('%H:%M:%S')
    
    # Calculate attendance statistics for each student
    student_stats = {}
    for student in all_students:
        student_records = [r for r in all_records if r['student_id'] == student['id']]
        student_stats[student['name']] = {
            'total_sessions_attended': len(student_records),
            'times_late': len([r for r in student_records if r['is_late']]),
            'times_on_time': len([r for r in student_records if not r['is_late']]),
            'attendance_percentage': round((len(student_records) / len(all_sessions)) * 100, 1) if all_sessions else 0
        }
    
    # For each session, calculate who was present and who was absent
    session_details = {}
    for session in all_sessions:
        session_key = f"{session['name']}_{session['date']}"
        present_students = [r['student__name'] for r in all_records if r['session_id'] == session['id']]
        absent_students = [s['name'] for s in all_students if s['name'] not in present_students]
        
        session_details[session_key] = {
            'session_info': session,
            'present_students': present_students,
            'absent_students': absent_students,
            'present_count': len(present_students),
            'absent_count': len(absent_students),
            'late_students': [r['student__name'] for r in all_records if r['session_id'] == session['id'] and r['is_late']],
            'on_time_students': [r['student__name'] for r in all_records if r['session_id'] == session['id'] and not r['is_late']]
        }
    
    return {
        'total_students': len(all_students),
        'total_sessions': len(all_sessions),
        'today_date': date.today().strftime('%Y-%m-%d'),
        'all_students': all_students,
        'all_sessions': all_sessions,
        'all_attendance_records': all_records,
        'student_statistics': student_stats,
        'session_details': session_details
    }

# Store conversation context in memory (in production, use database or cache)
conversation_contexts = {}

def query_attendance_data_with_context(user_query: str, session_id: str, teacher=None) -> str:
    """Enhanced AI query with conversation context and complete data access"""
    
    # Get complete data (filtered by teacher if not admin)
    data = get_complete_attendance_data(teacher)
    
    # Get or initialize conversation context for this session
    if session_id not in conversation_contexts:
        conversation_contexts[session_id] = []
    
    conversation_history = conversation_contexts[session_id]
    conversation_history.append({"role": "user", "content": user_query})
    
    # Keep only last 10 exchanges to prevent token limit issues
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]
    
    # Create comprehensive system prompt with teacher context
    teacher_info = ""
    if teacher:
        teacher_info = f"""
TEACHER CONTEXT:
You are responding to {teacher.get_full_name()} ({teacher.username}).
This data is filtered to show only their classes and sessions.
Department: {teacher.department or 'Not specified'}
"""
    
    system_prompt = f"""
You are an advanced AI assistant for a student attendance tracking system. You have access to COMPLETE attendance data and can maintain conversation context.

{teacher_info}

COMPLETE ATTENDANCE DATABASE:
{json.dumps(data, indent=2)}

CAPABILITIES:
- Track attendance, absences, late arrivals, and on-time arrivals
- Calculate statistics for individual students and sessions
- Analyze attendance patterns over time
- Maintain conversation context (remember previous questions in this chat)
- Answer detailed questions about specific dates, sessions, and students

IMPORTANT INSTRUCTIONS:
1. When asked about absences, check the 'absent_students' list in session_details
2. For attendance totals, use the 'total_sessions_attended' from student_statistics
3. Always specify the exact date, session, and numbers in your responses
4. Maintain conversation context - if someone asks "who was absent" after asking about a specific session, refer to that same session
5. Be precise with numbers and always show your reasoning
6. If you're responding to a teacher, remember this data is specific to their classes only

CONVERSATION CONTEXT:
Remember the conversation history to provide contextual responses. If someone asks a follow-up question without specifying details, use the context from previous messages.

Current date: {data['today_date']}
Total students in system: {data['total_students']}
Total sessions in system: {data['total_sessions']}
"""

    try:
        # Prepare messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history[-6:])
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,
            max_tokens=1000
        )
        
        ai_response = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": ai_response})
        conversation_contexts[session_id] = conversation_history
        
        # Save query to database
        AIQuery.objects.create(
            query=user_query,
            response=ai_response
        )
        
        return ai_response
        
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"
@login_required
@csrf_exempt
def ai_assistant(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_query = data.get("query", "").strip()
            session_id = data.get("session_id", "default")
            
            if not user_query:
                return JsonResponse({"error": "No query provided"}, status=400)
            
            # Pass teacher context for data filtering (unless admin)
            teacher = None if request.user.is_admin else request.user
            ai_response = query_attendance_data_with_context(user_query, session_id, teacher)
            
            return JsonResponse({
                "query": user_query,
                "response": ai_response,
                "session_id": session_id
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return render(request, 'ai_assistant.html')


@login_required
@csrf_exempt
def get_sessions(request):
    """Get sessions for the logged-in teacher only"""
    if request.method == "GET":
        try:
            today = date.today()
            upcoming_date = today + timedelta(days=7)
            
            # Filter sessions by logged-in teacher
            sessions = AttendanceSession.objects.filter(
                teacher=request.user,  # NEW: Filter by teacher
                date__gte=today,
                date__lte=upcoming_date
            ).order_by('date', 'start_time')
            
            session_data = []
            for session in sessions:
                attendance_count = AttendanceRecord.objects.filter(session=session).count()
                # Only count students from the session's class
                total_students = session.class_session.students.filter(is_active=True).count()
                
                session_data.append({
                    'id': session.id,
                    'name': session.name,
                    'class_name': session.class_session.name,  # NEW: Include class name
                    'date': session.date.strftime('%Y-%m-%d'),
                    'date_display': session.date.strftime('%B %d, %Y'),
                    'start_time': session.start_time.strftime('%H:%M'),
                    'end_time': session.end_time.strftime('%H:%M') if session.end_time else 'Ongoing',
                    'attendance_count': attendance_count,
                    'total_students': total_students,
                    'is_today': session.date == today,
                    'is_past': session.date < today,
                    'status': 'Active' if session.date == today else 'Upcoming' if session.date > today else 'Past'
                })
            
            return JsonResponse({
                'sessions': session_data,
                'today': today.strftime('%Y-%m-%d')
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
@csrf_exempt
def take_attendance_with_session(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            session_id = data.get("session_id")
            
            if not image_data:
                return JsonResponse({"error": "No image received"}, status=400)
            
            if not session_id:
                return JsonResponse({"error": "No session selected"}, status=400)

            try:
                # Ensure session belongs to logged-in teacher
                session = AttendanceSession.objects.get(id=session_id, teacher=request.user)
            except AttendanceSession.DoesNotExist:
                return JsonResponse({"error": "Session not found or you do not have permission"}, status=400)

            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_bytes = base64.b64decode(img_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_frame)
            if not face_locations:
                return JsonResponse({"message": "No face detected", "faces": []})

            faces_for_js = [{"top": f[0], "right": f[1], "bottom": f[2], "left": f[3]} for f in face_locations]

            # Only get students from the session's class
            students = session.class_session.students.filter(is_active=True)
            student_encodings = []
            student_objects = []

            for student in students:
                if os.path.exists(student.image_path):
                    try:
                        img = face_recognition.load_image_file(student.image_path)
                        enc = face_recognition.face_encodings(img)
                        if enc:
                            student_encodings.append(enc[0])
                            student_objects.append(student)
                    except Exception as e:
                        print(f"Error processing image for {student.name}: {e}")
                        continue

            recognized_students = []
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            current_time = datetime.now()
            
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(student_encodings, face_encoding)
                if True in matches:
                    match_index = matches.index(True)
                    student = student_objects[match_index]
                    
                    existing_record = AttendanceRecord.objects.filter(
                        student=student,
                        session=session
                    ).first()
                    
                    if not existing_record:
                        arrival_time = current_time.time()
                        is_late = arrival_time > session.start_time
                        
                        AttendanceRecord.objects.create(
                            student=student,
                            session=session,
                            arrival_time=arrival_time,
                            is_late=is_late
                        )
                        
                        time_str = arrival_time.strftime("%H:%M:%S")
                        status = f" (Late - {time_str})" if is_late else f" (On time - {time_str})"
                        recognized_students.append(f"{student.name}{status}")
                    else:
                        original_time = existing_record.arrival_time.strftime("%H:%M:%S") if hasattr(existing_record, 'arrival_time') and existing_record.arrival_time else existing_record.time.strftime("%H:%M:%S")
                        recognized_students.append(f"{student.name} (Already marked at {original_time})")

            total_attendance = AttendanceRecord.objects.filter(session=session).count()
            total_students = session.class_session.students.filter(is_active=True).count()

            message = f"Attendance taken for {session.name} ({session.class_session.name}): {', '.join(recognized_students) if recognized_students else 'No match'}"
            
            return JsonResponse({
                "message": message, 
                "faces": faces_for_js,
                "attendance_count": total_attendance,
                "total_students": total_students,
                "session_name": session.name,
                "class_name": session.class_session.name
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
            
    return JsonResponse({"message": "Use POST request."})

# @login_required
# @csrf_exempt
# def create_session(request):
#     if request.method == "POST":
#         try:
#             data = json.loads(request.body)
#             name = data.get("name")
#             date_str = data.get("date")
#             start_time_str = data.get("start_time")
#             end_time_str = data.get("end_time", "")
#             class_id = data.get("class_id")  # NEW: Require class selection
            
#             if not name or not date_str or not start_time_str or not class_id:
#                 return JsonResponse({"error": "Missing required fields"}, status=400)
            
#             # Verify the class belongs to the logged-in teacher
#             try:
#                 class_obj = Class.objects.get(id=class_id, teacher=request.user)
#             except Class.DoesNotExist:
#                 return JsonResponse({"error": "Class not found or you do not have permission"}, status=404)
            
#             session_date = datetime.strptime(date_str, "%Y-%m-%d").date()
#             start_time = datetime.strptime(start_time_str, "%H:%M").time()
#             end_time = datetime.strptime(end_time_str, "%H:%M").time() if end_time_str else None
            
#             session = AttendanceSession.objects.create(
#                 name=name,
#                 date=session_date,
#                 start_time=start_time,
#                 end_time=end_time,
#                 teacher=request.user,  # NEW: Link to logged-in teacher
#                 class_session=class_obj  # NEW: Link to selected class
#             )
            
#             return JsonResponse({
#                 "message": f"Session '{name}' created successfully for {class_obj.name}",
#                 "session_id": session.id
#             })
            
#         except ValueError as e:
#             return JsonResponse({"error": "Invalid date/time format"}, status=400)
#         except Exception as e:
#             return JsonResponse({"error": str(e)}, status=400)
    
#     return JsonResponse({"error": "Use POST request"}, status=405)

@login_required
def get_all_students(request):
    """Get all students in the system for assignment to classes"""
    try:
        # Get all active students
        all_students = Student.objects.filter(is_active=True).prefetch_related('classes')
        
        students_data = []
        
        for student in all_students:
            # Get all classes the student is currently in
            current_classes = student.classes.filter(is_active=True)
            
            # Check if student is already in any of the teacher's classes
            teacher_classes = current_classes.filter(teacher=request.user)
            is_in_teacher_classes = teacher_classes.exists()
            
            students_data.append({
                'id': student.id,
                'name': student.name,
                'student_id': student.student_id,
                'email': student.email,
                'phone': student.phone,
                'created_at': student.created_at.strftime('%Y-%m-%d'),
                'current_classes': [
                    {
                        'id': cls.id,
                        'name': cls.name,
                        'code': cls.code,
                        'teacher_name': cls.teacher.get_full_name()
                    }
                    for cls in current_classes
                ],
                'is_in_teacher_classes': is_in_teacher_classes,
                'teacher_classes': [
                    {
                        'id': cls.id,
                        'name': cls.name,
                        'code': cls.code
                    }
                    for cls in teacher_classes
                ]
            })
        
        return JsonResponse({
            'students': students_data,
            'total_students': len(students_data)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
@login_required
def get_teacher_students(request):
    """Get all students in the logged-in teacher's classes"""
    try:
        # Get all students that are in any of the teacher's classes
        students = Student.objects.filter(
            classes__teacher=request.user,
            is_active=True
        ).distinct().prefetch_related('classes')
        
        students_data = []
        
        for student in students:
            # Get only the classes taught by this teacher
            student_classes = student.classes.filter(teacher=request.user, is_active=True)
            
            students_data.append({
                'id': student.id,
                'name': student.name,
                'student_id': student.student_id,
                'email': student.email,
                'phone': student.phone,
                'created_at': student.created_at.strftime('%Y-%m-%d'),
                'classes': [
                    {
                        'id': cls.id,
                        'name': cls.name,
                        'code': cls.code
                    }
                    for cls in student_classes
                ]
            })
        
        return JsonResponse({
            'students': students_data,
            'total_students': len(students_data)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
@login_required
@csrf_exempt
def create_session(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name")
            date_str = data.get("date")
            start_time_str = data.get("start_time")
            end_time_str = data.get("end_time", "")
            class_id = data.get("class_id")
            session_type = data.get("session_type", "Regular")  # NEW: Handle session type
            
            if not name or not date_str or not start_time_str or not class_id:
                return JsonResponse({"error": "Missing required fields"}, status=400)
            
            # Verify the class belongs to the logged-in teacher
            try:
                class_obj = Class.objects.get(id=class_id, teacher=request.user)
            except Class.DoesNotExist:
                return JsonResponse({"error": "Class not found or you do not have permission"}, status=404)
            
            session_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
            end_time = datetime.strptime(end_time_str, "%H:%M").time() if end_time_str else None
            
            # Create enhanced session name with type if not Regular
            enhanced_name = f"{name} ({session_type})" if session_type != "Regular" else name
            
            session = AttendanceSession.objects.create(
                name=enhanced_name,
                date=session_date,
                start_time=start_time,
                end_time=end_time,
                teacher=request.user,
                class_session=class_obj
            )
            
            return JsonResponse({
                "message": f"Session '{enhanced_name}' created successfully for {class_obj.name}",
                "session_id": session.id,
                "session_data": {
                    "id": session.id,
                    "name": enhanced_name,
                    "class_name": class_obj.name,
                    "date": session_date.strftime('%Y-%m-%d'),
                    "start_time": start_time.strftime('%H:%M'),
                    "end_time": end_time.strftime('%H:%M') if end_time else None,
                }
            })
            
        except ValueError as e:
            return JsonResponse({"error": "Invalid date/time format"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Use POST request"}, status=405)

@login_required
@require_http_methods(["GET"])
def dashboard_data(request):
    """Enhanced API endpoint that returns comprehensive attendance data for the dashboard"""
    try:
        # Get data filtered by teacher (unless admin)
        teacher = None if request.user.is_admin else request.user
        data = get_complete_attendance_data(teacher)
        
        # Add additional analytics
        data['analytics'] = {
            'total_records': len(data['all_attendance_records']),
            'late_percentage': 0,
            'best_performing_student': None,
            'worst_performing_student': None,
            'most_attended_session': None,
            'least_attended_session': None
        }
        
        # Calculate late percentage
        if data['all_attendance_records']:
            late_records = [r for r in data['all_attendance_records'] if r['is_late']]
            data['analytics']['late_percentage'] = round((len(late_records) / len(data['all_attendance_records'])) * 100, 2)
        
        # Find best and worst performing students
        if data['student_statistics']:
            students_by_performance = sorted(
                data['student_statistics'].items(), 
                key=lambda x: x[1]['attendance_percentage'], 
                reverse=True
            )
            if students_by_performance:
                data['analytics']['best_performing_student'] = {
                    'name': students_by_performance[0][0],
                    'percentage': students_by_performance[0][1]['attendance_percentage']
                }
                data['analytics']['worst_performing_student'] = {
                    'name': students_by_performance[-1][0],
                    'percentage': students_by_performance[-1][1]['attendance_percentage']
                }
        
        # Find most and least attended sessions
        if data['session_details']:
            sessions_by_attendance = sorted(
                data['session_details'].items(),
                key=lambda x: x[1]['present_count'],
                reverse=True
            )
            if sessions_by_attendance:
                data['analytics']['most_attended_session'] = {
                    'name': sessions_by_attendance[0][1]['session_info']['name'],
                    'count': sessions_by_attendance[0][1]['present_count']
                }
                data['analytics']['least_attended_session'] = {
                    'name': sessions_by_attendance[-1][1]['session_info']['name'],
                    'count': sessions_by_attendance[-1][1]['present_count']
                }
        
        # Add teacher info
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
def dashboard(request):
    """
    Render the main dashboard page
    """
    return render(request, 'dashboard.html')


@csrf_exempt
def export_data(request):
    """
    Export attendance data in various formats
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            export_type = data.get("type", "csv")  # csv, excel, pdf
            date_from = data.get("date_from")
            date_to = data.get("date_to")
            
            # Get filtered data
            attendance_data = get_complete_attendance_data()
            
            if export_type == "csv":
                # Create CSV content
                import csv
                from io import StringIO
                
                output = StringIO()
                writer = csv.writer(output)
                
                # Write headers
                writer.writerow(['Student Name', 'Session', 'Date', 'Time', 'Status', 'Late'])
                
                # Write data
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
                response['Content-Disposition'] = 'attachment; filename="attendance_data.csv"'
                return response
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)




#new


def signup_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '').strip()
            confirm_password = data.get('confirm_password', '').strip()
            first_name = data.get('first_name', '').strip()
            last_name = data.get('last_name', '').strip()
            phone = data.get('phone', '').strip()
            department = data.get('department', '').strip()
            employee_id = data.get('employee_id', '').strip()
            
            # Validation
            if not all([username, email, password, first_name, last_name]):
                return JsonResponse({'error': 'Please fill in all required fields'}, status=400)
            
            if password != confirm_password:
                return JsonResponse({'error': 'Passwords do not match'}, status=400)
            
            if len(password) < 8:
                return JsonResponse({'error': 'Password must be at least 8 characters long'}, status=400)
            
            if Teacher.objects.filter(username=username).exists():
                return JsonResponse({'error': 'Username already exists'}, status=400)
            
            if Teacher.objects.filter(email=email).exists():
                return JsonResponse({'error': 'Email already registered'}, status=400)
            
            if employee_id and Teacher.objects.filter(employee_id=employee_id).exists():
                return JsonResponse({'error': 'Employee ID already exists'}, status=400)
            
            # Create teacher account
            with transaction.atomic():
                teacher = Teacher.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    department=department,
                    employee_id=employee_id if employee_id else None
                )
                
                # Auto-login after successful signup
                login(request, teacher)
                
            return JsonResponse({
                'message': 'Account created successfully!',
                'redirect': '/dashboard/'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return render(request, 'auth/signup.html')

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            
            if not username or not password:
                return JsonResponse({'error': 'Please enter both username and password'}, status=400)
            
            # Authenticate user
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                return JsonResponse({
                    'message': 'Login successful!',
                    'redirect': '/dashboard/',
                    'user': {
                        'name': user.get_full_name(),
                        'username': user.username,
                        'is_admin': user.is_admin
                    }
                })
            else:
                return JsonResponse({'error': 'Invalid username or password'}, status=400)
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return render(request, 'auth/login.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('/login/')

@login_required
@csrf_exempt
def create_class(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            code = data.get('code', '').strip()
            description = data.get('description', '').strip()
            academic_year = data.get('academic_year', '2024-2025').strip()
            semester = data.get('semester', 'Fall').strip()
            
            if not name or not code:
                return JsonResponse({'error': 'Class name and code are required'}, status=400)
            
            # Check if class code already exists for this teacher
            if Class.objects.filter(teacher=request.user, code=code).exists():
                return JsonResponse({'error': 'You already have a class with this code'}, status=400)
            
            # Create class
            new_class = Class.objects.create(
                name=name,
                code=code,
                teacher=request.user,
                description=description,
                academic_year=academic_year,
                semester=semester
            )
            
            return JsonResponse({
                'message': f'Class "{name}" created successfully!',
                'class_id': new_class.id,
                'class_data': {
                    'id': new_class.id,
                    'name': new_class.name,
                    'code': new_class.code,
                    'student_count': 0
                }
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def get_teacher_classes(request):
    """Get classes for the logged-in teacher"""
    try:
        classes = Class.objects.filter(teacher=request.user, is_active=True)
        classes_data = []
        
        for cls in classes:
            student_count = cls.students.filter(is_active=True).count()
            session_count = cls.sessions.count()
            
            classes_data.append({
                'id': cls.id,
                'name': cls.name,
                'code': cls.code,
                'description': cls.description,
                'academic_year': cls.academic_year,
                'semester': cls.semester,
                'student_count': student_count,
                'session_count': session_count,
                'created_at': cls.created_at.strftime('%Y-%m-%d')
            })
        
        return JsonResponse({
            'classes': classes_data,
            'teacher': {
                'name': request.user.get_full_name(),
                'username': request.user.username,
                'department': request.user.department
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@csrf_exempt
def assign_student_to_class(request):
    """Assign a student to one of teacher's classes"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id')
            class_id = data.get('class_id')
            
            if not student_id or not class_id:
                return JsonResponse({'error': 'Student ID and Class ID are required'}, status=400)
            
            # Verify the class belongs to the logged-in teacher
            try:
                class_obj = Class.objects.get(id=class_id, teacher=request.user)
            except Class.DoesNotExist:
                return JsonResponse({'error': 'Class not found or you do not have permission'}, status=404)
            
            try:
                student = Student.objects.get(id=student_id, is_active=True)
            except Student.DoesNotExist:
                return JsonResponse({'error': 'Student not found'}, status=404)
            
            # Add student to class
            class_obj.students.add(student)
            
            return JsonResponse({
                'message': f'{student.name} assigned to {class_obj.name} successfully!',
                'class_name': class_obj.name,
                'student_name': student.name
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)