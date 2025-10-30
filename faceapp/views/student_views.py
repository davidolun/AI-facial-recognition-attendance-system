"""
Student management views for adding and retrieving students
"""
from .common_imports import *
from .face_recognition_utils import delete_face_rekognition
import cloudinary.uploader
import json


@login_required
def home(request):
    """Render the home page for taking attendance"""
    start_time = time.time()
    logger.info(f"User {request.user.username} accessed home page")
    response = render(request, 'home.html')
    performance_logger.info(f"Home page load time: {time.time() - start_time:.2f}s for user {request.user.username}")
    return response


@login_required
@csrf_exempt
def add_student(request):
    """Add a new student with face recognition"""
    start_time = time.time()
    logger.info(f"User {request.user.username} initiated student addition")

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            student_name = data.get("name")
            student_id = data.get("student_id", "")
            email = data.get("email", "")
            phone = data.get("phone", "")

            if not student_name:
                logger.warning(f"Student addition failed: No name provided by user {request.user.username}")
                return JsonResponse({"error": "No name provided"}, status=400)
            if not image_data:
                logger.warning(f"Student addition failed: No image provided by user {request.user.username}")
                return JsonResponse({"error": "No image provided"}, status=400)

            if not AWS_CONFIGURED:
                logger.error("AWS Rekognition not configured")
                return JsonResponse({"error": "Face recognition service not configured"}, status=500)

            # Decode base64 image
            try:
                image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
            except Exception as e:
                logger.error(f"Image decoding failed for user {request.user.username}: {str(e)}")
                return JsonResponse({"error": "Invalid image format"}, status=400)

            # Convert to RGB if needed
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')

            # Convert image to bytes for AWS
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG', quality=95)
            img_byte_arr.seek(0)
            aws_image_bytes = img_byte_arr.read()

            # Generate unique student ID if not provided
            if not student_id:
                student_id = f"STU{int(time.time())}"

            # Index face in AWS Rekognition
            try:
                face_id = index_face_rekognition(aws_image_bytes, student_id, student_name)
                
                if face_id is None:
                    logger.warning(f"No face detected in image for {student_name}")
                    return JsonResponse({
                        "error": "No face detected. Please ensure:\n• Your face is clearly visible\n• Good lighting (no shadows)\n• Look directly at camera\n• Remove sunglasses/masks"
                    }, status=400)
                
                logger.info(f"Face indexed for {student_name} (Face ID: {face_id})")
                    
            except Exception as e:
                logger.error(f"Face detection failed for {student_name}: {str(e)}")
                return JsonResponse({"error": "Face detection failed. Please try again with better lighting."}, status=400)

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{student_name.lower().replace(' ', '_')}_{timestamp}.jpg"
            
            # Try to upload to Cloudinary first, fallback to local storage
            try:
                logger.info(f"Attempting to upload {filename} to Cloudinary...")
                img_byte_arr.seek(0)
                
                upload_result = cloudinary.uploader.upload(
                    img_byte_arr,
                    folder="attendance_students",
                    public_id=filename.replace('.jpg', ''),
                    resource_type="image"
                )
                relative_path = upload_result['secure_url']
                logger.info(f"Successfully uploaded to Cloudinary: {relative_path}")
            except Exception as cloudinary_error:
                logger.warning(f"Cloudinary upload failed: {cloudinary_error}. Saving locally...")
                file_path = os.path.join(settings.MEDIA_ROOT, 'students', filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                image.save(file_path, 'JPEG', quality=95)
                relative_path = os.path.join('students', filename)
                logger.info(f"Saved locally: {relative_path}")

            # Store AWS Face ID as face encoding
            face_encoding_data = json.dumps({
                'face_id': face_id,
                'student_id': student_id,
                'indexed_at': datetime.now().isoformat(),
                'service': 'aws_rekognition'
            })

            # Create student record
            student = Student.objects.create(
                name=student_name,
                student_id=student_id,
                email=email if email else None,
                phone=phone if phone else None,
                image_path=relative_path,
                face_encoding=face_encoding_data
            )

            # Automatically add student to all classes of the logged-in teacher
            teacher_classes = Class.objects.filter(teacher=request.user, is_active=True)
            if teacher_classes.exists():
                student.classes.add(*teacher_classes)
                logger.info(f"Student {student_name} automatically added to {teacher_classes.count()} classes")

            processing_time = time.time() - start_time
            logger.info(f"Student {student_name} added successfully in {processing_time:.2f}s")
            
            return JsonResponse({
                "message": f"Student {student_name} added successfully!",
                "student_id": student.id,
                "processing_time": f"{processing_time:.2f}s"
            })

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Student addition failed after {processing_time:.2f}s: {str(e)}")
            return JsonResponse({"error": str(e)}, status=400)
    
    return render(request, "add_student.html")


@login_required
def get_all_students(request):
    """Get all students in the system"""
    try:
        all_students = Student.objects.filter(is_active=True).prefetch_related('classes')
        students_data = []
        
        for student in all_students:
            current_classes = student.classes.filter(is_active=True)
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
        students = Student.objects.filter(
            classes__teacher=request.user,
            is_active=True
        ).distinct().prefetch_related('classes')
        
        students_data = []
        
        for student in students:
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
def delete_student(request, student_id):
    """Delete a student and all their data"""
    logger.info(f"User {request.user.username} initiated student deletion for student ID {student_id}")
    
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        # Get the student
        student = Student.objects.get(id=student_id, is_active=True)
        
        # Check if student belongs to the teacher's classes
        teacher_classes = Class.objects.filter(teacher=request.user, is_active=True)
        student_classes = student.classes.filter(id__in=teacher_classes.values_list('id', flat=True))
        
        if not student_classes.exists():
            logger.warning(f"Unauthorized deletion attempt: Student {student_id} not in teacher's classes")
            return JsonResponse({"error": "You don't have permission to delete this student"}, status=403)
        
        # Extract face ID from face_encoding and delete from AWS Rekognition
        if student.face_encoding:
            try:
                face_data = json.loads(student.face_encoding)
                if 'face_id' in face_data:
                    face_id = face_data['face_id']
                    delete_face_rekognition(face_id)
                    logger.info(f"Deleted face {face_id} from AWS Rekognition")
            except Exception as e:
                logger.warning(f"Failed to delete face from AWS: {e}")
        
        # Delete image from Cloudinary if stored there
        try:
            if student.image_path and isinstance(student.image_path, str) and student.image_path.startswith('http') and 'res.cloudinary.com' in student.image_path:
                # Extract public_id from URL: .../upload/v<ver>/<folder>/<name>.<ext>
                # We take the part after '/upload/' and drop version and extension
                parts = student.image_path.split('/upload/')
                if len(parts) == 2:
                    tail = parts[1]
                    # Remove version segment if present (e.g., v1729989999/)
                    if tail.startswith('v'):
                        tail = '/'.join(tail.split('/')[1:])
                    # Drop file extension
                    public_id = tail.rsplit('.', 1)[0]
                    # Perform delete
                    cloudinary.uploader.destroy(public_id, resource_type='image')
                    logger.info(f"Deleted Cloudinary asset {public_id} for student {student.name}")
        except Exception as e:
            logger.warning(f"Failed to delete Cloudinary image for student {student.name}: {e}")

        # Remove student from all classes
        student.classes.clear()
        
        # Delete all attendance records for this student
        attendance_count = AttendanceRecord.objects.filter(student=student).delete()[0]
        logger.info(f"Deleted {attendance_count} attendance records for student {student.name}")
        
        # Mark student as inactive
        student.is_active = False
        student.save()
        
        logger.info(f"Student {student.name} deleted successfully by user {request.user.username}")
        
        return JsonResponse({
            "message": f"Student {student.name} has been deleted successfully",
            "attendance_records_deleted": attendance_count
        })
        
    except Student.DoesNotExist:
        logger.warning(f"Attempted to delete non-existent student ID {student_id}")
        return JsonResponse({"error": "Student not found"}, status=404)
    except Exception as e:
        logger.error(f"Error deleting student: {str(e)}")
        return JsonResponse({"error": str(e)}, status=400)
