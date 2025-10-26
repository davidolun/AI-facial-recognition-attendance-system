"""
Student management views for adding and retrieving students
"""
from .common_imports import *
import cloudinary.uploader


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
