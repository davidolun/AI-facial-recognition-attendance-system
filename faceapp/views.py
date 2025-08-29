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

# Initialize OpenAI client with new API
client = OpenAI(api_key=settings.OPENAI_API_KEY)

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

            student = Student.objects.create(
                name=student_name,
                student_id=student_id if student_id else None,
                email=email if email else None,
                phone=phone if phone else None,
                image_path=save_path
            )

            return JsonResponse({
                "message": f"Student {student_name} added successfully!",
                "student_id": student.id
            })

        except Exception as e:
            print("ERROR in add_student:", e)
            return JsonResponse({"error": str(e)}, status=400)

    return render(request, "add_student.html")

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

def view_records(request):
    return render(request, 'ai_assistant.html')

def get_complete_attendance_data():
    """Get COMPLETE attendance data for AI with proper absence tracking"""
    
    # Get all students
    all_students = list(Student.objects.filter(is_active=True).values('id', 'name', 'student_id', 'email'))
    
    # Get all sessions with detailed info
    all_sessions = list(AttendanceSession.objects.all().order_by('-date', '-start_time').values(
        'id', 'name', 'date', 'start_time', 'end_time'
    ))
    
    # Convert dates and times to strings for JSON serialization
    for session in all_sessions:
        session['date'] = session['date'].strftime('%Y-%m-%d')
        session['start_time'] = session['start_time'].strftime('%H:%M:%S')
        if session['end_time']:
            session['end_time'] = session['end_time'].strftime('%H:%M:%S')
    
    # Get ALL attendance records with related data
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

def query_attendance_data_with_context(user_query: str, session_id: str) -> str:
    """
    Enhanced AI query with conversation context and complete data access
    """
    # Get complete data
    data = get_complete_attendance_data()
    
    # Get or initialize conversation context for this session
    if session_id not in conversation_contexts:
        conversation_contexts[session_id] = []
    
    conversation_history = conversation_contexts[session_id]
    
    # Add current query to history
    conversation_history.append({"role": "user", "content": user_query})
    
    # Keep only last 10 exchanges to prevent token limit issues
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]
    
    # Create comprehensive system prompt
    system_prompt = f"""
You are an advanced AI assistant for a student attendance tracking system. You have access to COMPLETE attendance data and can maintain conversation context.

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

CONVERSATION CONTEXT:
Remember the conversation history to provide contextual responses. If someone asks a follow-up question without specifying details, use the context from previous messages.

Current date: {data['today_date']}
Total students in system: {data['total_students']}
Total sessions in system: {data['total_sessions']}
"""

    try:
        # Prepare messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last few exchanges for context)
        messages.extend(conversation_history[-6:])  # Last 6 messages for context
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,  # Lower temperature for more consistent responses
            max_tokens=1000
        )
        
        ai_response = response.choices[0].message.content
        
        # Add AI response to conversation history
        conversation_history.append({"role": "assistant", "content": ai_response})
        
        # Update conversation context
        conversation_contexts[session_id] = conversation_history
        
        # Save query to database
        AIQuery.objects.create(
            query=user_query,
            response=ai_response
        )
        
        return ai_response
        
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"

@csrf_exempt
def ai_assistant(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_query = data.get("query", "").strip()
            session_id = data.get("session_id", "default")  # Use session ID for context
            
            if not user_query:
                return JsonResponse({"error": "No query provided"}, status=400)
            
            # Get AI response with context
            ai_response = query_attendance_data_with_context(user_query, session_id)
            
            return JsonResponse({
                "query": user_query,
                "response": ai_response,
                "session_id": session_id
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return render(request, 'ai_assistant.html')

@csrf_exempt
def get_sessions(request):
    """Get available sessions for today or upcoming days"""
    if request.method == "GET":
        try:
            today = date.today()
            upcoming_date = today + timedelta(days=7)
            
            sessions = AttendanceSession.objects.filter(
                date__gte=today,
                date__lte=upcoming_date
            ).order_by('date', 'start_time')
            
            session_data = []
            for session in sessions:
                attendance_count = AttendanceRecord.objects.filter(session=session).count()
                total_students = Student.objects.filter(is_active=True).count()
                
                session_data.append({
                    'id': session.id,
                    'name': session.name,
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
                session = AttendanceSession.objects.get(id=session_id)
            except AttendanceSession.DoesNotExist:
                return JsonResponse({"error": "Session not found"}, status=400)

            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_bytes = base64.b64decode(img_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_frame)
            if not face_locations:
                return JsonResponse({"message": "No face detected", "faces": []})

            faces_for_js = [{"top": f[0], "right": f[1], "bottom": f[2], "left": f[3]} for f in face_locations]

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
            total_students = Student.objects.filter(is_active=True).count()

            message = f"Attendance taken for {session.name}: {', '.join(recognized_students) if recognized_students else 'No match'}"
            
            return JsonResponse({
                "message": message, 
                "faces": faces_for_js,
                "attendance_count": total_attendance,
                "total_students": total_students,
                "session_name": session.name
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
            
    return JsonResponse({"message": "Use POST request."})

@csrf_exempt 
def create_session(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name")
            date_str = data.get("date")
            start_time_str = data.get("start_time")
            end_time_str = data.get("end_time", "")
            
            if not name or not date_str or not start_time_str:
                return JsonResponse({"error": "Missing required fields"}, status=400)
            
            session_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
            end_time = datetime.strptime(end_time_str, "%H:%M").time() if end_time_str else None
            
            session = AttendanceSession.objects.create(
                name=name,
                date=session_date,
                start_time=start_time,
                end_time=end_time
            )
            
            return JsonResponse({
                "message": f"Session '{name}' created successfully",
                "session_id": session.id
            })
            
        except ValueError as e:
            return JsonResponse({"error": "Invalid date/time format"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Use POST request"}, status=405)