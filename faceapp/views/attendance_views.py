"""
Attendance management views for taking and tracking attendance
"""
from .common_imports import *


@login_required
@csrf_exempt
def take_attendance_with_session(request):
    """Take attendance for a specific session using face recognition"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            session_id = data.get("session_id")
            
            if not image_data:
                return JsonResponse({"error": "No image received"}, status=400)
            
            if not session_id:
                return JsonResponse({"error": "No session selected"}, status=400)

            if not AWS_CONFIGURED:
                return JsonResponse({"error": "Face recognition service not configured"}, status=500)

            try:
                session = AttendanceSession.objects.get(id=session_id, teacher=request.user)
            except AttendanceSession.DoesNotExist:
                return JsonResponse({"error": "Session not found or you do not have permission"}, status=400)

            # Decode image
            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_bytes = base64.b64decode(img_str)

            # Search for face in AWS Rekognition
            print("Searching for face in AWS Rekognition collection...")
            matched_student_id, similarity = search_face_rekognition(img_bytes, threshold=80)
            
            if not matched_student_id:
                print("Trying with lower threshold (70%)...")
                matched_student_id, similarity = search_face_rekognition(img_bytes, threshold=70)
            
            # Detect faces for visualization
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            pil_image = Image.fromarray(rgb_frame)
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)
            detect_bytes = img_byte_arr.read()
            
            detected_faces = detect_faces_rekognition(detect_bytes)
            
            # Convert to frontend format
            height, width = rgb_frame.shape[:2]
            faces_for_js = []
            for face in detected_faces:
                faces_for_js.append({
                    "top": int(face['top'] * height),
                    "right": int((face['left'] + face['width']) * width),
                    "bottom": int((face['top'] + face['height']) * height),
                    "left": int(face['left'] * width)
                })
            
            if not matched_student_id:
                print(f"\n❌ NO MATCH FOUND")
                print(f"Best similarity: {similarity:.2f}%")
                return JsonResponse({
                    "message": f"No match found - Face not recognized\nBest similarity: {similarity:.1f}%\nThreshold: 70%",
                    "faces": faces_for_js,
                    "debug": {
                        "best_similarity": float(similarity),
                        "threshold": 70,
                        "service": "aws_rekognition"
                    }
                })

            # Find student by student_id
            try:
                best_match = Student.objects.get(student_id=matched_student_id, is_active=True)
            except Student.DoesNotExist:
                print(f"❌ Student with ID {matched_student_id} not found in database")
                return JsonResponse({
                    "message": "Student record not found in database",
                    "faces": faces_for_js
                })
            
            # Check if student is in this class
            if not session.class_session.students.filter(id=best_match.id).exists():
                return JsonResponse({
                    "message": f"{best_match.name} is not enrolled in {session.class_session.name}",
                    "faces": faces_for_js
                })
            
            print(f"\n✅ MATCH FOUND: {best_match.name} ({similarity:.2f}%)")
            
            # Process attendance
            current_time = datetime.now()
            
            existing_record = AttendanceRecord.objects.filter(
                student=best_match,
                session=session
            ).first()
            
            if not existing_record:
                arrival_time = current_time.time()
                is_late = arrival_time > session.start_time
                
                AttendanceRecord.objects.create(
                    student=best_match,
                    session=session,
                    arrival_time=arrival_time,
                    is_late=is_late
                )
                
                time_str = arrival_time.strftime("%H:%M:%S")
                status = f" (Late - {time_str})" if is_late else f" (On time - {time_str})"
                confidence_str = f" [Confidence: {similarity:.1f}%]"
                message = f"Attendance taken: {best_match.name}{status}{confidence_str}"
            else:
                original_time = existing_record.arrival_time.strftime("%H:%M:%S")
                message = f"{best_match.name} (Already marked at {original_time})"
            
            total_attendance = AttendanceRecord.objects.filter(session=session).count()
            total_students = session.class_session.students.filter(is_active=True).count()

            return JsonResponse({
                "message": message,
                "faces": faces_for_js,
                "attendance_count": total_attendance,
                "total_students": total_students,
                "session_name": session.name,
                "class_name": session.class_session.name,
                "confidence": float(similarity)
            })

        except Exception as e:
            print(f"❌ ATTENDANCE ERROR: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=400)
            
    return JsonResponse({"message": "Use POST request."})


@csrf_exempt
def detect_faces(request):
    """Detect faces in an image for visualization"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            if not image_data:
                return JsonResponse({"faces": []})

            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_bytes = base64.b64decode(img_str)

            detected_faces = detect_faces_rekognition(img_bytes)
            
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            height, width = frame.shape[:2]
            
            faces_list = []
            for face in detected_faces:
                faces_list.append({
                    "top": int(face['top'] * height),
                    "right": int((face['left'] + face['width']) * width),
                    "bottom": int((face['top'] + face['height']) * height),
                    "left": int(face['left'] * width)
                })

            return JsonResponse({"faces": faces_list})
        except Exception as e:
            return JsonResponse({"error": str(e), "faces": []})
    return JsonResponse({"faces": []})


@login_required
@csrf_exempt
def create_session(request):
    """Create a new attendance session"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name")
            date_str = data.get("date")
            start_time_str = data.get("start_time")
            end_time_str = data.get("end_time", "")
            class_id = data.get("class_id")
            session_type = data.get("session_type", "Regular")
            
            if not name or not date_str or not start_time_str or not class_id:
                return JsonResponse({"error": "Missing required fields"}, status=400)
            
            try:
                class_obj = Class.objects.get(id=class_id, teacher=request.user)
            except Class.DoesNotExist:
                return JsonResponse({"error": "Class not found or you do not have permission"}, status=404)
            
            session_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
            end_time = datetime.strptime(end_time_str, "%H:%M").time() if end_time_str else None
            
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
@csrf_exempt
def get_sessions(request):
    """Get sessions for the logged-in teacher"""
    if request.method == "GET":
        try:
            today = date.today()
            upcoming_date = today + timedelta(days=7)
            
            sessions = AttendanceSession.objects.filter(
                teacher=request.user,
                date__gte=today,
                date__lte=upcoming_date
            ).order_by('date', 'start_time')
            
            session_data = []
            for session in sessions:
                attendance_records = AttendanceRecord.objects.filter(session=session)
                unique_attendees = attendance_records.values_list('student_id', flat=True).distinct().count()
                total_students = session.class_session.students.filter(is_active=True).count()
                
                session_data.append({
                    'id': session.id,
                    'name': session.name,
                    'class_name': session.class_session.name,
                    'date': session.date.strftime('%Y-%m-%d'),
                    'date_display': session.date.strftime('%B %d, %Y'),
                    'start_time': session.start_time.strftime('%H:%M'),
                    'end_time': session.end_time.strftime('%H:%M') if session.end_time else 'Ongoing',
                    'attendance_count': unique_attendees,
                    'total_students': total_students,
                    'is_today': session.date == today,
                    'is_past': session.date < today,
                    'status': 'Active' if session.date == today else 'Upcoming'
                })
            
            return JsonResponse({
                'sessions': session_data,
                'today': today.strftime('%Y-%m-%d')
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
